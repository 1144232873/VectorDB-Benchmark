#!/usr/bin/env python3
"""
Phase 1: 向量生成性能测试 - 主程序

串行测试5个嵌入模型的推理性能并生成300万向量缓存
"""

import argparse
import logging
import sys
import yaml
from pathlib import Path
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase1_embedding.models.xinference_client import XinferenceClient
from phase1_embedding.data.ms_marco_loader import MSMARCOLoader
from phase1_embedding.benchmarks.inference_benchmark import InferenceBenchmark
from phase1_embedding.report_generator import Phase1ReportGenerator


def setup_logging(log_dir: str, log_file: str, console_level: str = "INFO"):
    """
    配置日志
    
    Args:
        log_dir: 日志目录
        log_file: 日志文件名
        console_level: 控制台日志级别
    """
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)
    
    # 文件日志
    log_path = log_dir_path / log_file
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # 控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, console_level.upper()))
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # 配置root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info(f"Logging initialized: {log_path}")


def load_config(config_file: str) -> dict:
    """
    加载配置文件
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        配置字典
    """
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Phase 1: 向量生成性能测试"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="../config/phase1_config.yaml",
        help="配置文件路径"
    )
    parser.add_argument(
        "--serial",
        action="store_true",
        default=True,
        help="串行执行（强制）"
    )
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        help="指定要测试的模型（默认测试所有）"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    print(f"Loading config from {args.config}")
    config = load_config(args.config)
    
    # 设置日志
    logging_config = config.get("logging", {})
    setup_logging(
        log_dir=logging_config.get("log_dir", "logs"),
        log_file=logging_config.get("log_file", "phase1.log"),
        console_level=logging_config.get("level", "INFO")
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("="*80)
    logger.info("Phase 1: 向量生成性能测试")
    logger.info("="*80)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 初始化Xinference客户端
        xinference_config = config["xinference"]
        logger.info(f"\nConnecting to Xinference at {xinference_config['host']}:{xinference_config['port']}")
        
        client = XinferenceClient(
            host=xinference_config["host"],
            port=xinference_config["port"],
            timeout=xinference_config.get("timeout", 300)
        )
        
        if not client.check_health():
            raise RuntimeError("Xinference service is not available")
        
        logger.info("✓ Xinference client connected")
        
        # 2. 准备数据集
        dataset_config = config["dataset"]
        logger.info(f"\nPreparing dataset: {dataset_config['name']}")
        logger.info(f"  Target size: {dataset_config['sample_size']} documents")
        
        loader = MSMARCOLoader(data_dir=dataset_config["path"])
        
        # 下载数据集（如果需要）
        if not loader.download_collection():
            raise RuntimeError("Failed to download MS MARCO dataset")
        
        # 采样文档
        documents = loader.sample_documents(
            num_samples=dataset_config["sample_size"],
            seed=dataset_config.get("seed", 42)
        )
        
        logger.info(f"✓ Dataset prepared: {len(documents)} documents")
        
        # 准备测试文本（用于性能测试）
        test_texts = [doc["text"] for doc in documents[:1000]]
        logger.info(f"✓ Test texts prepared: {len(test_texts)} samples")
        
        # 3. 初始化基准测试
        report_config = config.get("report", {})
        benchmark = InferenceBenchmark(
            xinference_client=client,
            output_dir=report_config.get("output_dir", "phase1_results")
        )
        
        # 4. 准备模型列表
        all_models = config["models"]
        if args.models:
            # 过滤指定的模型
            models_to_test = [
                m for m in all_models
                if m["name"] in args.models
            ]
            if not models_to_test:
                logger.error(f"No matching models found: {args.models}")
                return 1
        else:
            models_to_test = all_models
        
        logger.info(f"\nModels to test: {len(models_to_test)}")
        for model in models_to_test:
            logger.info(f"  - {model['name']} ({model['dimensions']}维)")
        
        # 5. 运行串行基准测试
        serial_config = config.get("serial_execution", {})
        cache_config = config.get("vector_cache", {})
        
        logger.info(f"\nStarting serial benchmark...")
        logger.info(f"  Cleanup between models: {serial_config.get('cleanup_between_models', True)}")
        logger.info(f"  Pause between models: {serial_config.get('pause_between_models', 5)}s")
        
        benchmark.run_serial_benchmark(
            models=models_to_test,
            test_texts=test_texts,
            documents=documents,
            cache_dir=cache_config.get("output_dir", "vector_cache"),
            cleanup_between_models=serial_config.get("cleanup_between_models", True),
            pause_between_models=serial_config.get("pause_between_models", 5)
        )
        
        # 6. 保存最终结果
        logger.info(f"\nSaving final results...")
        benchmark.save_results()
        
        # 7. 生成HTML报告
        logger.info(f"\nGenerating HTML report...")
        report_generator = Phase1ReportGenerator(
            results_file=str(Path(report_config.get("output_dir", "phase1_results")) / "benchmark_results.json"),
            output_dir=report_config.get("output_dir", "phase1_results")
        )
        report_path = report_generator.generate_report()
        logger.info(f"✓ HTML report generated: {report_path}")
        
        # 8. 打印摘要
        logger.info("\n" + "="*80)
        logger.info("BENCHMARK SUMMARY")
        logger.info("="*80)
        
        summary = benchmark.get_summary()
        for model_summary in summary["models"]:
            logger.info(f"\n{model_summary['name']}:")
            logger.info(f"  Throughput: {model_summary['throughput_docs_per_sec']:.2f} docs/s")
            logger.info(f"  Single latency (P99): {model_summary['single_latency_p99_ms']:.2f} ms")
            logger.info(f"  Optimal batch size: {model_summary['optimal_batch_size']}")
            logger.info(f"  GPU peak memory: {model_summary['gpu_peak_memory_mb']:.2f} MB")
            logger.info(f"  Time for 3M vectors: {model_summary['time_for_3m_vectors_hours']:.2f} hours")
            logger.info(f"  Time for 100M vectors (estimated): {model_summary['time_for_100m_vectors_hours']:.1f} hours")
        
        logger.info("\n" + "="*80)
        logger.info("✓ Phase 1 completed successfully!")
        logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
        
        return 0
        
    except Exception as e:
        logger.error(f"\n✗ Phase 1 failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
