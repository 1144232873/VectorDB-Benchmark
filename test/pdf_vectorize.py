"""
PDF向量化主脚本
读取PDF文件、向量化处理、导出ES格式、生成HTML报告
"""

import asyncio
import argparse
import logging
import time
import sys
from pathlib import Path
from typing import List, Dict, Any
import yaml
import numpy as np
from tqdm import tqdm

# 导入本地模块
from pdf_reader import PDFReader
from es_exporter import ESExporter
from report_generator import ReportGenerator
from async_client import AsyncXinferenceClient

# Token统计
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    try:
        from transformers import AutoTokenizer
        HAS_TRANSFORMERS = True
        HAS_TIKTOKEN = False
    except ImportError:
        HAS_TIKTOKEN = False
        HAS_TRANSFORMERS = False
        logging.warning("Neither tiktoken nor transformers available. Token counting will be disabled.")

logger = logging.getLogger(__name__)


class TokenCounter:
    """Token计数器"""
    
    def __init__(self, model_name: str = "qwen3-0.6b"):
        self.model_name = model_name
        self.encoder = None
        
        if HAS_TIKTOKEN:
            try:
                # 尝试使用tiktoken
                self.encoder = tiktoken.get_encoding("cl100k_base")  # 通用编码
                logger.info("Using tiktoken for token counting")
            except Exception as e:
                logger.warning(f"Failed to load tiktoken: {e}")
        
        if self.encoder is None and HAS_TRANSFORMERS:
            try:
                # 尝试使用transformers
                tokenizer_name = "Qwen/Qwen2.5-0.5B"  # 使用相近的tokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
                logger.info(f"Using transformers tokenizer: {tokenizer_name}")
            except Exception as e:
                logger.warning(f"Failed to load transformers tokenizer: {e}")
                self.tokenizer = None
    
    def count_tokens(self, text: str) -> int:
        """统计文本的token数"""
        if self.encoder:
            return len(self.encoder.encode(text))
        elif hasattr(self, 'tokenizer') and self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # 回退：粗略估算（中文按字符，英文按单词）
            return len(text)
    
    def count_batch(self, texts: List[str]) -> int:
        """批量统计token数"""
        return sum(self.count_tokens(text) for text in texts)


class PDFVectorizer:
    """PDF向量化处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化向量化处理器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.stats = {}
        
        # 初始化组件
        pdf_config = config.get('pdf', {})
        self.pdf_reader = PDFReader(
            chunk_size=pdf_config.get('chunk_size', 512),
            min_length=pdf_config.get('min_length', 10),
            max_length=pdf_config.get('max_length', 512)
        )
        
        es_config = config.get('elasticsearch', {})
        self.es_exporter = ESExporter(
            index_name=es_config.get('index_name', 'pdf_vectors'),
            bulk_size=es_config.get('bulk_size', 5000)
        )
        
        self.report_generator = ReportGenerator(
            output_dir=config.get('output', {}).get('results_dir', 'results')
        )
        
        # Token计数器
        model_name = config.get('model', {}).get('name', 'qwen3-0.6b')
        self.token_counter = TokenCounter(model_name)
    
    def expand_documents(
        self,
        documents: List[Dict[str, Any]],
        target_count: int,
        strategy: str = "repeat"
    ) -> List[Dict[str, Any]]:
        """
        扩展文档数量
        
        Args:
            documents: 原始文档列表
            target_count: 目标文档数
            strategy: 扩展策略 ("repeat" 或 "fuzzy")
            
        Returns:
            扩展后的文档列表
        """
        original_count = len(documents)
        if original_count >= target_count:
            logger.info(f"Documents already meet target count: {original_count}")
            return documents
        
        repeat_factor = (target_count + original_count - 1) // original_count
        logger.info(f"Expanding {original_count} documents to ~{target_count} (repeat_factor={repeat_factor})")
        
        expanded_docs = []
        
        if strategy == "repeat":
            # 简单重复
            for i in range(repeat_factor):
                for doc in documents:
                    new_doc = doc.copy()
                    new_doc['id'] = f"{doc['id']}_repeat_{i}"
                    new_doc['repeat_id'] = i
                    expanded_docs.append(new_doc)
                    if len(expanded_docs) >= target_count:
                        break
                if len(expanded_docs) >= target_count:
                    break
        else:
            # 模糊处理（轻微变换）
            import random
            for i in range(repeat_factor):
                for doc in documents:
                    new_doc = doc.copy()
                    text = doc['text']
                    
                    # 添加序号前缀
                    prefix = f"[副本{i+1}] "
                    new_doc['text'] = prefix + text
                    new_doc['id'] = f"{doc['id']}_fuzzy_{i}"
                    new_doc['repeat_id'] = i
                    expanded_docs.append(new_doc)
                    
                    if len(expanded_docs) >= target_count:
                        break
                if len(expanded_docs) >= target_count:
                    break
        
        logger.info(f"✓ Expanded to {len(expanded_docs)} documents")
        return expanded_docs[:target_count]
    
    async def vectorize_documents(
        self,
        documents: List[Dict[str, Any]],
        model_name: str,
        batch_size: int = None,
        auto_tune: bool = True
    ) -> np.ndarray:
        """
        向量化文档
        
        Args:
            documents: 文档列表
            model_name: 模型名称
            batch_size: 批次大小（None则自动调优）
            auto_tune: 是否自动调优batch size
            
        Returns:
            向量数组
        """
        xinference_config = self.config.get('xinference', {})
        perf_config = self.config.get('performance', {})
        
        async with AsyncXinferenceClient(
            host=xinference_config.get('host', '192.168.1.51'),
            port=xinference_config.get('port', 9997),
            timeout=xinference_config.get('timeout', 300),
            max_concurrent_requests=perf_config.get('max_concurrent_requests', 16)
        ) as client:
            # 检查服务健康（可选，失败不影响后续处理）
            try:
                models = await client.list_models()
                if models:
                    logger.info(f"Xinference service available, {len(models)} models")
                else:
                    logger.warning("Xinference service available but no models found")
            except Exception as e:
                logger.warning(f"Could not list models (will continue anyway): {e}")
            
            texts = [doc['text'] for doc in documents]
            
            # 自动调优batch size
            if auto_tune and batch_size is None:
                logger.info("Auto-tuning batch size...")
                max_batch = perf_config.get('max_batch_size', 2048)
                optimal_batch, _ = await client.find_optimal_batch_size(
                    texts[:min(1000, len(texts))],  # 使用前1000个文本测试
                    model_name,
                    start_size=64,
                    max_size=max_batch,
                    test_iterations=3
                )
                batch_size = optimal_batch
                logger.info(f"Using optimal batch size: {batch_size}")
            elif batch_size is None:
                batch_size = 128
            
            # 向量化
            logger.info(f"Vectorizing {len(documents)} documents...")
            start_time = time.time()
            
            vectors = await client.embed_concurrent(
                texts,
                model_name,
                batch_size=batch_size,
                show_progress=True
            )
            
            vectorization_time = time.time() - start_time
            
            if vectors is None:
                raise RuntimeError("Failed to generate vectors")
            
            self.stats['vectorization_time'] = vectorization_time
            self.stats['batch_size'] = batch_size
            
            logger.info(f"✓ Vectorized {len(vectors)} documents in {vectorization_time:.2f}s")
            
            return vectors
    
    def count_tokens(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        统计Token
        
        Args:
            documents: 文档列表
            
        Returns:
            Token统计信息
        """
        logger.info("Counting tokens...")
        start_time = time.time()
        
        texts = [doc['text'] for doc in documents]
        total_tokens = self.token_counter.count_batch(texts)
        
        token_count_time = time.time() - start_time
        
        avg_tokens = total_tokens / len(documents) if documents else 0
        token_count_speed = total_tokens / token_count_time if token_count_time > 0 else 0
        
        stats = {
            'total_tokens': total_tokens,
            'avg_tokens_per_doc': avg_tokens,
            'token_count_time': token_count_time,
            'token_count_speed': token_count_speed
        }
        
        logger.info(f"✓ Counted {total_tokens:,} tokens ({avg_tokens:.1f} tokens/doc)")
        
        return stats
    
    async def run(self):
        """运行完整的向量化流程"""
        logger.info("="*80)
        logger.info("PDF Vectorization Pipeline")
        logger.info("="*80)
        
        total_start_time = time.time()
        
        # 1. 提取PDF文本
        logger.info("\n[1/6] Extracting text from PDFs...")
        pdf_dir = Path(self.config.get('pdf', {}).get('input_dir', '向量测试文档'))
        pdf_start_time = time.time()
        documents = self.pdf_reader.extract_from_directory(pdf_dir)
        pdf_extraction_time = time.time() - pdf_start_time
        
        if not documents:
            logger.error("No documents extracted from PDFs!")
            return
        
        logger.info(f"✓ Extracted {len(documents)} text chunks in {pdf_extraction_time:.2f}s")
        self.stats['pdf_extraction_time'] = pdf_extraction_time
        self.stats['original_document_count'] = len(documents)
        
        # 2. 数据扩展
        logger.info("\n[2/6] Expanding documents...")
        expansion_config = self.config.get('expansion', {})
        target_count = expansion_config.get('target_count', 100000)
        strategy = expansion_config.get('strategy', 'repeat')
        
        expansion_start_time = time.time()
        documents = self.expand_documents(documents, target_count, strategy)
        expansion_time = time.time() - expansion_start_time
        
        logger.info(f"✓ Expanded to {len(documents)} documents in {expansion_time:.2f}s")
        self.stats['expansion_time'] = expansion_time
        self.stats['total_documents'] = len(documents)
        
        # 3. Token统计
        logger.info("\n[3/6] Counting tokens...")
        token_stats = self.count_tokens(documents)
        self.stats.update(token_stats)
        
        # 4. 向量化
        logger.info("\n[4/6] Vectorizing documents...")
        model_config = self.config.get('model', {})
        model_name = model_config.get('model_name', model_config.get('name', 'Qwen3-Embedding-0.6B'))
        perf_config = self.config.get('performance', {})
        auto_tune = perf_config.get('auto_tune_batch_size', True)
        
        vectors = await self.vectorize_documents(
            documents,
            model_name,
            batch_size=None,
            auto_tune=auto_tune
        )
        
        self.stats['total_vectors'] = len(vectors)
        self.stats['vector_dim'] = vectors.shape[1]
        
        # 5. 导出ES格式
        logger.info("\n[5/6] Exporting to ES format...")
        output_config = self.config.get('output', {})
        vectors_dir = Path(output_config.get('vectors_dir', 'results/vectors'))
        vectors_file = vectors_dir / 'bulk_import.json'
        
        export_start_time = time.time()
        self.es_exporter.export_to_bulk_json(
            documents,
            vectors,
            vectors_file,
            show_progress=True
        )
        export_time = time.time() - export_start_time
        
        self.stats['export_time'] = export_time
        self.config['output']['vectors_file'] = str(vectors_file)
        
        # 6. 生成报告
        logger.info("\n[6/6] Generating HTML report...")
        total_time = time.time() - total_start_time
        self.stats['total_time_seconds'] = total_time
        self.stats['docs_per_second'] = len(documents) / total_time if total_time > 0 else 0
        self.stats['vectors_per_second'] = len(vectors) / total_time if total_time > 0 else 0
        self.stats['tokens_per_second'] = token_stats['total_tokens'] / total_time if total_time > 0 else 0
        self.stats['token_throughput'] = token_stats['total_tokens'] / self.stats.get('vectorization_time', 1)
        
        report_file = output_config.get('report_file', 'results/report.html')
        self.report_generator.generate_report(self.stats, self.config, report_file)
        
        # 输出摘要
        logger.info("\n" + "="*80)
        logger.info("✓ Pipeline completed successfully!")
        logger.info("="*80)
        logger.info(f"Total documents: {len(documents):,}")
        logger.info(f"Total vectors: {len(vectors):,}")
        logger.info(f"Total tokens: {token_stats['total_tokens']:,}")
        logger.info(f"Total time: {total_time:.2f}s ({total_time/60:.2f} minutes)")
        logger.info(f"Processing speed: {self.stats['docs_per_second']:.2f} docs/s")
        logger.info(f"Token speed: {self.stats['tokens_per_second']:.2f} tokens/s")
        logger.info(f"\nES import file: {vectors_file}")
        logger.info(f"HTML report: {report_file}")


def load_config(config_file: str) -> Dict[str, Any]:
    """加载配置文件"""
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="PDF向量化测试脚本")
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='配置文件路径 (default: config.yaml)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志级别 (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 加载配置
        config = load_config(args.config)
        
        # 创建向量化处理器
        vectorizer = PDFVectorizer(config)
        
        # 运行
        asyncio.run(vectorizer.run())
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
