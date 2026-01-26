#!/usr/bin/env python3
"""
Phase 1: 向量生成性能基准测试（异步高性能模式）

使用异步并发，榨干GPU性能，生成300万向量缓存
"""

import argparse
import asyncio
import logging
import sys
import yaml
import httpx
from pathlib import Path
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase1_embedding.models.async_xinference_client import AsyncXinferenceClient
from phase1_embedding.data.dataset_loader import DatasetLoader
from phase1_embedding.benchmarks.async_inference_benchmark import AsyncInferenceBenchmark

# 设置 httpx 日志级别为 WARNING，减少刷屏
logging.getLogger("httpx").setLevel(logging.WARNING)


def setup_logging(log_dir: str, log_file: str, console_level: str = "WARNING"):
    """配置日志"""
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


def load_config(config_file: str) -> dict:
    """加载配置文件"""
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


async def run_benchmark(config, logger, validated_models, documents, test_texts):
    """运行异步基准测试"""
    xinference_config = config["xinference"]
    perf_config = config.get("performance", {})
    report_config = config.get("report", {})
    cache_config = config.get("vector_cache", {})
    
    # 使用极限性能配置
    concurrent_requests = perf_config.get("concurrent_requests", 16)
    connection_pool_size = perf_config.get("connection_pool_size", 32)
    
    logger.info(f"\n初始化异步客户端（极限性能模式）...")
    logger.info(f"  并发请求数: {concurrent_requests}")
    logger.info(f"  连接池大小: {connection_pool_size}")
    
    async with AsyncXinferenceClient(
        host=xinference_config["host"],
        port=xinference_config["port"],
        timeout=xinference_config.get("timeout", 300),
        max_concurrent_requests=concurrent_requests,
        connection_pool_size=connection_pool_size
    ) as async_client:
        
        if not await async_client.check_health():
            raise RuntimeError("Xinference 服务不可用")
        
        logger.info("✓ 异步客户端已连接")
        
        # 初始化基准测试
        benchmark = AsyncInferenceBenchmark(
            async_client=async_client,
            output_dir=report_config.get("output_dir", "results")
        )
        
        # 运行基准测试
        logger.info(f"\n开始基准测试...")
        logger.info(f"  自动批次调优: {perf_config.get('auto_batch_tuning', True)}")
        logger.info(f"  模型间暂停: {perf_config.get('pause_between_models', 5)}s")
        
        await benchmark.run_serial_benchmark_async(
            models=validated_models,
            test_texts=test_texts,
            documents=documents,
            cache_dir=cache_config.get("output_dir", "results/cache"),
            auto_tune_batch_size=perf_config.get("auto_batch_tuning", True),
            pause_between_models=perf_config.get("pause_between_models", 5)
        )
        
        # 保存结果
        logger.info(f"\n保存结果...")
        benchmark.save_results()
        
        # 打印摘要
        logger.info("\n" + "="*80)
        logger.info("基准测试摘要")
        logger.info("="*80)
        
        summary = benchmark.get_summary()
        for model_summary in summary["models"]:
            logger.info(f"\n{model_summary['name']}:")
            logger.info(f"  吞吐量: {model_summary['throughput_docs_per_sec']:.2f} docs/s")
            logger.info(f"  最优批次: {model_summary['optimal_batch_size']}")
            logger.info(f"  并发数: {model_summary['concurrent_requests']}")
            logger.info(f"  GPU峰值: {model_summary['gpu_peak_memory_mb']:.2f} MB")
            logger.info(f"  300万向量耗时: {model_summary['time_for_3m_vectors_hours']:.2f} 小时")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Phase 1: 向量生成性能基准测试（异步高性能）"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="../config/phase1_config.yaml",
        help="配置文件路径"
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
        help="指定批次ID（用于显存不足时分批测试）"
    )
    parser.add_argument(
        "--list-batches",
        action="store_true",
        help="列出所有可用批次"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    print(f"加载配置: {args.config}")
    config = load_config(args.config)
    
    # 设置日志
    logging_config = config.get("logging", {})
    setup_logging(
        log_dir=logging_config.get("log_dir", "logs"),
        log_file=logging_config.get("log_file", "phase1.log"),
        console_level=logging_config.get("level", "WARNING")
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("="*80)
    logger.info("Phase 1: 向量生成性能基准测试（异步极限性能）")
    logger.info("="*80)
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 列出批次
    if args.list_batches:
        batch_groups = config.get("batch_groups", [])
        if not batch_groups:
            print("配置文件中未定义批次")
            return 0
        
        print("\n可用批次:")
        for batch in batch_groups:
            batch_id = batch.get("batch_id", "?")
            batch_name = batch.get("batch_name", "unnamed")
            model_names = batch.get("model_names", [])
            print(f"\n  批次 {batch_id}: {batch_name}")
            print(f"    模型: {', '.join(model_names)}")
            print(f"    运行: python benchmark.py --batch {batch_id}")
        return 0
    
    try:
        # 检查依赖
        try:
            import httpx
        except ImportError:
            logger.error("需要 httpx 包，安装: uv add 'httpx[http2]'")
            return 1
        
        # 初始化异步客户端进行模型验证
        xinference_config = config["xinference"]
        logger.info(f"\n连接到 Xinference: {xinference_config['host']}:{xinference_config['port']}")
        
        async with AsyncXinferenceClient(
            host=xinference_config["host"],
            port=xinference_config["port"],
            timeout=xinference_config.get("timeout", 300)
        ) as client:
            
            if not await client.check_health():
                raise RuntimeError("Xinference 服务不可用")
            
            logger.info("✓ Xinference 已连接")
            
            # 处理批次配置
            all_models = config["models"]
            models_to_test = all_models
            
            if args.batch is not None:
                batch_groups = config.get("batch_groups", [])
                if not batch_groups:
                    logger.error("指定了 --batch 但配置文件中未定义 batch_groups")
                    return 1
                
                selected_batch = None
                for batch in batch_groups:
                    if batch.get("batch_id") == args.batch:
                        selected_batch = batch
                        break
                
                if not selected_batch:
                    logger.error(f"未找到批次 {args.batch}")
                    return 1
                
                batch_model_names = set(selected_batch.get("model_names", []))
                models_to_test = [m for m in all_models if m["name"] in batch_model_names]
                
                logger.info(f"\n运行批次 {args.batch}: {selected_batch.get('batch_name', 'unnamed')}")
                logger.info(f"  模型: {', '.join([m['name'] for m in models_to_test])}")
            
            # 指定模型过滤
            if args.models:
                models_to_test = [m for m in models_to_test if m["name"] in args.models]
                if not models_to_test:
                    logger.error(f"未找到匹配的模型: {args.models}")
                    return 1
            
            # 验证模型
            logger.info("\n验证模型...")
            available_models = await client.list_models()
            available_model_ids = [m.get("id", m.get("model_uid")) for m in available_models]
            
            logger.info(f"Xinference 上可用模型数: {len(available_model_ids)}")
            
            validated_models = []
            for model_config in models_to_test:
                model_name = model_config["name"]
                model_full_name = model_config["model_name"]
                
                # 简单检查模型是否在列表中
                if model_full_name in available_model_ids or any(model_full_name in m for m in available_model_ids):
                    validated_models.append(model_config)
                    logger.info(f"✓ 模型 '{model_name}' 已验证")
                else:
                    logger.warning(f"⚠ 模型 '{model_name}' ({model_full_name}) 未找到")
            
            if not validated_models:
                logger.error("未找到有效模型")
                return 1
            
            logger.info(f"\n✓ 已验证 {len(validated_models)}/{len(models_to_test)} 个模型")
            
            # 准备数据集
            dataset_config = config["dataset"]
            logger.info(f"\n准备数据集: {dataset_config['name']}")
            logger.info(f"  目标大小: {dataset_config['sample_size']} 文档")
            
            loader = DatasetLoader(data_dir=dataset_config["path"])
            
            if not loader.check_dataset():
                raise RuntimeError(
                    "数据集未找到，请先准备数据集:\n"
                    "  cd datasets/scripts && ./quick_start.sh 100000"
                )
            
            # 采样文档
            documents = loader.sample_documents(
                num_samples=dataset_config["sample_size"],
                seed=dataset_config.get("seed", 42)
            )
            
            logger.info(f"✓ 数据集已准备: {len(documents)} 文档")
            
            # 准备测试文本
            test_texts = [doc["text"] for doc in documents[:1000]]
            logger.info(f"✓ 测试文本已准备: {len(test_texts)} 样本")
            
            # 显示测试模型
            logger.info(f"\n待测试模型: {len(validated_models)}")
            for model in validated_models:
                logger.info(f"  - {model['name']} ({model['dimensions']}维)")
        
        # 运行基准测试
        logger.info("\n🚀 启动异步极限性能测试")
        await run_benchmark(config, logger, validated_models, documents, test_texts)
        
        logger.info("\n" + "="*80)
        logger.info("✓ Phase 1 完成")
        logger.info(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
        
        return 0
        
    except Exception as e:
        logger.error(f"\n✗ Phase 1 失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
