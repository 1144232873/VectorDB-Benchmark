"""
Elasticsearch批量导入模块
生成ES Bulk API格式的JSON文件，可直接导入ES
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from tqdm import tqdm

logger = logging.getLogger(__name__)


class ESExporter:
    """Elasticsearch批量导出器"""
    
    def __init__(
        self,
        index_name: str = "pdf_vectors",
        bulk_size: int = 5000
    ):
        """
        初始化ES导出器
        
        Args:
            index_name: ES索引名称
            bulk_size: 每批处理的文档数
        """
        self.index_name = index_name
        self.bulk_size = bulk_size
    
    def format_bulk_action(self, doc_id: str) -> Dict[str, Any]:
        """
        格式化Bulk API的action行
        
        Args:
            doc_id: 文档ID
            
        Returns:
            action字典
        """
        return {
            "index": {
                "_index": self.index_name,
                "_id": doc_id
            }
        }
    
    def format_document(
        self,
        doc_id: str,
        text: str,
        vector: np.ndarray,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        格式化文档数据
        
        Args:
            doc_id: 文档ID
            text: 文本内容
            vector: 向量数组
            metadata: 额外元数据
            
        Returns:
            文档字典
        """
        doc = {
            "text": text,
            "vector": vector.tolist() if isinstance(vector, np.ndarray) else vector
        }
        
        if metadata:
            doc.update(metadata)
        
        return doc
    
    def export_to_bulk_json(
        self,
        documents: List[Dict[str, str]],
        vectors: np.ndarray,
        output_file: Path,
        show_progress: bool = True
    ):
        """
        导出为ES Bulk API格式的JSON文件
        
        Args:
            documents: 文档列表，每个包含 {id, text, ...}
            vectors: 向量数组，形状为 (len(documents), vector_dim)
            output_file: 输出文件路径
            show_progress: 是否显示进度条
        """
        if len(documents) != len(vectors):
            raise ValueError(f"Documents count ({len(documents)}) != vectors count ({len(vectors)})")
        
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Exporting {len(documents)} documents to {output_file}")
        
        total_batches = (len(documents) + self.bulk_size - 1) // self.bulk_size
        
        with open(output_file, 'w', encoding='utf-8') as f:
            pbar = tqdm(total=len(documents), desc="Exporting to ES format", disable=not show_progress)
            
            for i in range(0, len(documents), self.bulk_size):
                batch_docs = documents[i:i+self.bulk_size]
                batch_vectors = vectors[i:i+self.bulk_size]
                
                for doc, vector in zip(batch_docs, batch_vectors):
                    # Action行
                    action = self.format_bulk_action(doc["id"])
                    f.write(json.dumps(action, ensure_ascii=False) + "\n")
                    
                    # 文档行
                    doc_data = self.format_document(
                        doc["id"],
                        doc["text"],
                        vector,
                        metadata={k: v for k, v in doc.items() if k not in ["id", "text"]}
                    )
                    f.write(json.dumps(doc_data, ensure_ascii=False) + "\n")
                    
                    pbar.update(1)
            
            pbar.close()
        
        logger.info(f"✓ Exported {len(documents)} documents to {output_file}")
        logger.info(f"  File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
        logger.info(f"  To import to ES, use: curl -X POST 'localhost:9200/_bulk' -H 'Content-Type: application/x-ndjson' --data-binary @{output_file}")
    
    def export_to_ndjson(
        self,
        documents: List[Dict[str, str]],
        vectors: np.ndarray,
        output_file: Path,
        show_progress: bool = True
    ):
        """
        导出为NDJSON格式（每行一个JSON对象，包含action和source）
        
        Args:
            documents: 文档列表
            vectors: 向量数组
            output_file: 输出文件路径
            show_progress: 是否显示进度条
        """
        if len(documents) != len(vectors):
            raise ValueError(f"Documents count ({len(documents)}) != vectors count ({len(vectors)})")
        
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Exporting {len(documents)} documents to NDJSON format: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            pbar = tqdm(total=len(documents), desc="Exporting to NDJSON", disable=not show_progress)
            
            for doc, vector in zip(documents, vectors):
                # 合并action和source
                bulk_item = {
                    "index": {
                        "_index": self.index_name,
                        "_id": doc["id"]
                    }
                }
                
                doc_data = self.format_document(
                    doc["id"],
                    doc["text"],
                    vector,
                    metadata={k: v for k, v in doc.items() if k not in ["id", "text"]}
                )
                
                # 写入action行
                f.write(json.dumps(bulk_item, ensure_ascii=False) + "\n")
                # 写入source行
                f.write(json.dumps(doc_data, ensure_ascii=False) + "\n")
                
                pbar.update(1)
            
            pbar.close()
        
        logger.info(f"✓ Exported {len(documents)} documents to {output_file}")


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    exporter = ESExporter(index_name="test_vectors", bulk_size=1000)
    
    # 创建测试数据
    test_docs = [
        {"id": f"doc_{i}", "text": f"测试文本 {i}", "source_file": "test.pdf", "chunk_id": i}
        for i in range(10)
    ]
    test_vectors = np.random.rand(10, 1024).astype(np.float32)
    
    # 测试导出
    output_file = Path("test_bulk.json")
    exporter.export_to_bulk_json(test_docs, test_vectors, output_file)
    print(f"\n测试文件已生成: {output_file}")
