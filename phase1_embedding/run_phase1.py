#!/usr/bin/env python3
"""
Phase 1: 向量生成性能测试 - 主程序

串行测试4个嵌入模型的推理性能并生成300万向量缓存
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
from phase1_embedding.data.dataset_loader import DatasetLoader
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
    parser.add_argument(
        "--batch",
        type=int,
        help="指定要运行的批次ID（如果配置文件中定义了batch_groups）"
    )
    parser.add_argument(
        "--list-batches",
        action="store_true",
        help="列出所有可用的批次并退出"
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
    
    # 如果指定了 --list-batches，列出所有批次并退出（不需要连接Xinference）
    if args.list_batches:
        batch_groups = config.get("batch_groups", [])
        if not batch_groups:
            print("No batch_groups defined in config file")
            return 0
        
        print("\nAvailable batches:")
        for batch in batch_groups:
            batch_id = batch.get("batch_id", "?")
            batch_name = batch.get("batch_name", "unnamed")
            model_names = batch.get("model_names", [])
            print(f"\n  Batch {batch_id}: {batch_name}")
            print(f"    Models: {', '.join(model_names)}")
            print(f"    Run with: python run_phase1.py --config {args.config} --batch {batch_id}")
        return 0
    
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
        
        # 1.5. 处理批次配置
        all_models = config["models"]
        models_to_test = all_models
        
        # 如果指定了批次，则过滤模型
        if args.batch is not None:
            batch_groups = config.get("batch_groups", [])
            if not batch_groups:
                logger.error("--batch specified but no batch_groups defined in config file")
                return 1
            
            # 查找指定的批次
            selected_batch = None
            for batch in batch_groups:
                if batch.get("batch_id") == args.batch:
                    selected_batch = batch
                    break
            
            if not selected_batch:
                logger.error(f"Batch {args.batch} not found in config. Available batches:")
                for batch in batch_groups:
                    logger.error(f"  Batch {batch.get('batch_id')}: {batch.get('batch_name', 'unnamed')}")
                return 1
            
            batch_model_names = set(selected_batch.get("model_names", []))
            models_to_test = [m for m in all_models if m["name"] in batch_model_names]
            
            if not models_to_test:
                logger.error(f"No models found in batch {args.batch}")
                return 1
            
            logger.info(f"\n📦 Running batch {args.batch}: {selected_batch.get('batch_name', 'unnamed')}")
            logger.info(f"  Models in this batch: {', '.join([m['name'] for m in models_to_test])}")
        
        # 如果指定了 --models，则进一步过滤
        if args.models:
            models_to_test = [m for m in models_to_test if m["name"] in args.models]
            if not models_to_test:
                logger.error(f"No matching models found: {args.models}")
                return 1
        
        # 1.6. 验证所有模型是否存在
        logger.info("\nValidating models...")
        
        # 获取可用模型列表
        available_models = client.get_available_model_ids()
        logger.info(f"Available models on Xinference ({len(available_models)}):")
        for m in available_models[:10]:  # 显示前10个
            logger.info(f"  - {m}")
        if len(available_models) > 10:
            logger.info(f"  ... and {len(available_models) - 10} more")
        
        # 验证每个模型
        validated_models = []
        for model_config in models_to_test:
            model_name = model_config["name"]
            model_full_name = model_config["model_name"]
            
            exists, actual_id = client.check_model_exists(model_full_name)
            if not exists:
                logger.error(
                    f"\n✗ Model '{model_full_name}' (config name: '{model_name}') not found!\n"
                    f"  Please ensure the model is loaded in Xinference.\n"
                    f"  You can check available models with: curl http://{xinference_config['host']}:{xinference_config['port']}/v1/models"
                )
                # 继续验证其他模型，但记录错误
            else:
                if actual_id and actual_id != model_full_name:
                    logger.warning(
                        f"⚠ Model name mismatch for '{model_name}':\n"
                        f"  Config uses: '{model_full_name}'\n"
                        f"  Xinference has: '{actual_id}'\n"
                        f"  Will use: '{actual_id}'"
                    )
                    # 更新配置中的模型名称
                    model_config["model_name"] = actual_id
                validated_models.append(model_config)
                logger.info(f"✓ Model '{model_name}' validated: {actual_id or model_full_name}")
        
        if not validated_models:
            logger.error("\n✗ No valid models found! Please check your configuration and Xinference setup.")
            return 1
        
        logger.info(f"\n✓ Validated {len(validated_models)}/{len(models_to_test)} models")
        
        # 2. 准备数据集
        dataset_config = config["dataset"]
        logger.info(f"\nPreparing dataset: {dataset_config['name']}")
        logger.info(f"  Target size: {dataset_config['sample_size']} documents")
        
        loader = DatasetLoader(data_dir=dataset_config["path"])
        
        # 检查数据集是否存在
        if not loader.check_dataset():
            raise RuntimeError(
                "Dataset not found. Please prepare dataset first:\n"
                "  cd datasets/scripts && ./quick_start.sh 100000"
            )
        
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
        
        # 4. 使用已验证的模型列表（已在前面验证）
        logger.info(f"\nModels to test: {len(validated_models)}")
        for model in validated_models:
            logger.info(f"  - {model['name']} ({model['dimensions']}维, model_id: {model['model_name']})")
        
        # 5. 运行串行基准测试
        serial_config = config.get("serial_execution", {})
        cache_config = config.get("vector_cache", {})
        
        logger.info(f"\nStarting serial benchmark...")
        logger.info(f"  Cleanup between models: {serial_config.get('cleanup_between_models', True)}")
        logger.info(f"  Pause between models: {serial_config.get('pause_between_models', 5)}s")
        
        benchmark.run_serial_benchmark(
            models=validated_models,
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
