#!/usr/bin/env python3
"""
异步性能对比测试脚本

快速测试同步 vs 异步模式的性能差异
"""

import asyncio
import time
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase1_embedding.models.xinference_client import XinferenceClient
from phase1_embedding.models.async_xinference_client import AsyncXinferenceClient
from phase1_embedding.data.dataset_loader import DatasetLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def save_result(result: dict, mode: str, model: str, num_docs: int, batch_size: int, concurrent: int = None):
    """保存测试结果到 JSON 文件
    
    Args:
        result: 测试结果字典
        mode: 测试模式 (sync/async)
        model: 模型名称
        num_docs: 文档数量
        batch_size: 批次大小
        concurrent: 并发数（仅异步模式）
    """
    # 创建结果目录
    results_dir = Path("quick_test_results")
    results_dir.mkdir(exist_ok=True)
    
    # 生成文件名：mode_timestamp.json
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{mode}_{timestamp}.json"
    filepath = results_dir / filename
    
    # 添加元数据
    full_result = {
        "test_info": {
            "mode": mode,
            "model": model,
            "num_docs": num_docs,
            "batch_size": batch_size,
            "concurrent_requests": concurrent if mode == "async" else None,
            "timestamp": timestamp,
            "datetime": datetime.now().isoformat()
        },
        "results": result
    }
    
    # 保存到文件
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(full_result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✓ Results saved to: {filepath}")
    return filepath


def test_sync_mode(client: XinferenceClient, model: str, texts: list, batch_size: int):
    """测试同步模式性能"""
    logger.info(f"\n{'='*60}")
    logger.info(f"SYNC MODE TEST")
    logger.info(f"{'='*60}")
    logger.info(f"Model: {model}")
    logger.info(f"Texts: {len(texts)}")
    logger.info(f"Batch size: {batch_size}")
    
    start_time = time.time()
    
    # 分批处理
    total_vectors = 0
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        embeddings = client.embed_batch(batch, model, batch_size)
        if embeddings is not None:
            total_vectors += len(embeddings)
    
    elapsed = time.time() - start_time
    throughput = total_vectors / elapsed
    
    logger.info(f"\n✓ SYNC Results:")
    logger.info(f"  Vectors generated: {total_vectors}")
    logger.info(f"  Time: {elapsed:.2f}s")
    logger.info(f"  Throughput: {throughput:.2f} docs/s")
    
    return {
        "mode": "sync",
        "vectors": total_vectors,
        "time": elapsed,
        "throughput": throughput
    }


async def test_async_mode(
    client: AsyncXinferenceClient,
    model: str,
    texts: list,
    batch_size: int
):
    """测试异步模式性能"""
    logger.info(f"\n{'='*60}")
    logger.info(f"ASYNC MODE TEST")
    logger.info(f"{'='*60}")
    logger.info(f"Model: {model}")
    logger.info(f"Texts: {len(texts)}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Concurrent requests: {client.max_concurrent_requests}")
    
    start_time = time.time()
    
    # 并发处理
    embeddings = await client.embed_concurrent(
        texts,
        model,
        batch_size=batch_size,
        show_progress=True
    )
    
    elapsed = time.time() - start_time
    total_vectors = len(embeddings) if embeddings is not None else 0
    throughput = total_vectors / elapsed if elapsed > 0 else 0
    
    logger.info(f"\n✓ ASYNC Results:")
    logger.info(f"  Vectors generated: {total_vectors}")
    logger.info(f"  Time: {elapsed:.2f}s")
    logger.info(f"  Throughput: {throughput:.2f} docs/s")
    
    return {
        "mode": "async",
        "vectors": total_vectors,
        "time": elapsed,
        "throughput": throughput
    }


async def main(test_mode="both", num_docs=1000, batch_size=128, concurrent=8):
    """主测试函数
    
    Args:
        test_mode: 测试模式 - "sync", "async", "both"
        num_docs: 测试文档数
        batch_size: 批次大小
        concurrent: 并发请求数（仅异步模式）
    """
    logger.info("="*80)
    logger.info(f"Phase 1 性能测试 - 模式: {test_mode.upper()}")
    logger.info("="*80)
    
    # 配置
    host = "192.168.1.51"
    port = 9997
    num_test_docs = num_docs
    concurrent_requests = concurrent
    
    try:
        # 1. 加载测试数据
        logger.info("\n1. Loading test data...")
        loader = DatasetLoader(data_dir="../datasets/processed")
        
        if not loader.check_dataset():
            logger.error("Dataset not found! Please prepare dataset first:")
            logger.error("  cd datasets/scripts && ./quick_start.sh 100000")
            return 1
        
        documents = loader.sample_documents(num_samples=num_test_docs, seed=42)
        texts = [doc["text"] for doc in documents]
        logger.info(f"✓ Loaded {len(texts)} test documents")
        
        # 2. 检查可用模型
        logger.info("\n2. Checking available models...")
        sync_client = XinferenceClient(host=host, port=port)
        
        if not sync_client.check_health():
            logger.error("Xinference service is not available!")
            return 1
        
        available_models = sync_client.get_available_model_ids()
        if not available_models:
            logger.error("No models available!")
            return 1
        
        # 选择第一个模型进行测试
        test_model = available_models[0]
        logger.info(f"✓ Using model: {test_model}")
        
        sync_results = None
        async_results = None
        
        # 3. 根据模式运行测试
        if test_mode in ["sync", "both"]:
            logger.info(f"\n3. Testing SYNC mode...")
            sync_results = test_sync_mode(sync_client, test_model, texts, batch_size)
            
            # 保存同步结果
            save_result(sync_results, "sync", test_model, num_test_docs, batch_size)
        
        if test_mode in ["async", "both"]:
            step = 4 if test_mode == "both" else 3
            logger.info(f"\n{step}. Testing ASYNC mode...")
            async with AsyncXinferenceClient(
                host=host,
                port=port,
                max_concurrent_requests=concurrent_requests
            ) as async_client:
                async_results = await test_async_mode(
                    async_client,
                    test_model,
                    texts,
                    batch_size
                )
            
            # 保存异步结果
            save_result(async_results, "async", test_model, num_test_docs, batch_size, concurrent_requests)
        
        # 5. 对比结果（仅在 both 模式下）
        if test_mode == "both" and sync_results and async_results:
            logger.info("\n" + "="*80)
            logger.info("PERFORMANCE COMPARISON")
            logger.info("="*80)
            
            speedup = async_results["throughput"] / sync_results["throughput"]
            time_saved = sync_results["time"] - async_results["time"]
            time_saved_percent = (time_saved / sync_results["time"]) * 100
            
            logger.info(f"\nSync Mode:")
            logger.info(f"  Time: {sync_results['time']:.2f}s")
            logger.info(f"  Throughput: {sync_results['throughput']:.2f} docs/s")
            
            logger.info(f"\nAsync Mode:")
            logger.info(f"  Time: {async_results['time']:.2f}s")
            logger.info(f"  Throughput: {async_results['throughput']:.2f} docs/s")
            
            logger.info(f"\n🚀 Performance Gain:")
            logger.info(f"  Speedup: {speedup:.2f}x")
            logger.info(f"  Time saved: {time_saved:.2f}s ({time_saved_percent:.1f}%)")
            logger.info(f"  Estimated time for 3M vectors:")
            logger.info(f"    Sync:  {(3000000 / sync_results['throughput']) / 3600:.2f} hours")
            logger.info(f"    Async: {(3000000 / async_results['throughput']) / 3600:.2f} hours")
            
            # 保存对比结果
            comparison = {
                "sync": sync_results,
                "async": async_results,
                "comparison": {
                    "speedup": speedup,
                    "time_saved_seconds": time_saved,
                    "time_saved_percent": time_saved_percent
                }
            }
            save_result(comparison, "comparison", test_model, num_test_docs, batch_size, concurrent_requests)
            
            # 建议
            logger.info("\n" + "="*80)
            logger.info("RECOMMENDATIONS")
            logger.info("="*80)
            
            if speedup >= 3.0:
                logger.info("✓ 异步模式性能提升显著！强烈建议使用异步模式。")
            elif speedup >= 2.0:
                logger.info("✓ 异步模式有明显性能提升，推荐使用。")
            elif speedup >= 1.5:
                logger.info("✓ 异步模式有一定性能提升。")
            else:
                logger.info("⚠ 异步模式提升有限，可能存在瓶颈：")
                logger.info("  - 检查 Xinference 服务端配置")
                logger.info("  - 检查网络延迟")
                logger.info("  - 尝试增大 concurrent_requests")
        
        # 6. 下一步建议
        logger.info(f"\n{'='*80}")
        logger.info("NEXT STEPS")
        logger.info("="*80)
        logger.info(f"  查看保存的结果: quick_test_results/")
        logger.info(f"  运行完整测试: python run_phase1.py --async --batch 1")
        logger.info(f"  汇总多次结果: python compare_results.py")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Phase 1 性能测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 仅测试同步模式
  python test_async_performance.py --mode sync
  
  # 仅测试异步模式
  python test_async_performance.py --mode async
  
  # 同时测试并对比
  python test_async_performance.py --mode both
  
  # 自定义参数
  python test_async_performance.py --mode async --num-docs 5000 --concurrent 16
        """
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["sync", "async", "both"],
        default="both",
        help="测试模式: sync(同步), async(异步), both(对比)"
    )
    parser.add_argument("--num-docs", type=int, default=1000, help="测试文档数量")
    parser.add_argument("--batch-size", type=int, default=128, help="批次大小")
    parser.add_argument("--concurrent", type=int, default=8, help="并发请求数（异步模式）")
    
    args = parser.parse_args()
    
    exit_code = asyncio.run(main(
        test_mode=args.mode,
        num_docs=args.num_docs,
        batch_size=args.batch_size,
        concurrent=args.concurrent
    ))
    sys.exit(exit_code)
