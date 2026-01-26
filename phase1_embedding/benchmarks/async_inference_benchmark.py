"""
异步推理性能基准测试 - 高并发向量生成

使用异步并发请求，最大化 GPU 利用率
"""

import asyncio
import time
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import numpy as np
from tqdm.asyncio import tqdm as async_tqdm

from ..models.async_xinference_client import AsyncXinferenceClient
from ..cache.vector_cache import VectorCache
from .gpu_monitor import GPUMonitor

logger = logging.getLogger(__name__)


@dataclass
class AsyncModelBenchmarkResult:
    """异步模型基准测试结果"""
    model_name: str
    model_full_name: str
    vector_dim: int
    
    # 单样本延迟测试（保留同步测试结果）
    single_latency_ms: Dict[str, float]
    
    # 异步批处理吞吐量测试
    async_batch_throughput: Dict[int, Dict[str, float]]  # {batch_size: {throughput, latency}}
    optimal_batch_size: int
    optimal_throughput: float
    
    # 并发配置
    concurrent_requests: int
    
    # 显存使用
    gpu_memory_mb: Dict[str, float]  # peak, average
    
    # 向量生成统计
    total_vectors_generated: int
    generation_time_seconds: float
    generation_throughput: float  # vectors/second
    
    # 推算
    extrapolation: Dict[int, Dict[str, float]]
    
    # 性能对比（相对于同步版本）
    speedup_factor: Optional[float] = None


class AsyncInferenceBenchmark:
    """异步推理性能基准测试"""
    
    def __init__(
        self,
        async_client: AsyncXinferenceClient,
        output_dir: str = "phase1_results"
    ):
        """
        初始化基准测试
        
        Args:
            async_client: 异步 Xinference 客户端
            output_dir: 输出目录
        """
        self.client = async_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.results: List[AsyncModelBenchmarkResult] = []
        
        logger.info("Async inference benchmark initialized")
    
    async def test_single_latency_sync(
        self,
        model_name: str,
        texts: List[str],
        num_samples: int = 1000,
        warmup: int = 10
    ) -> Dict[str, float]:
        """
        测试单样本推理延迟（使用同步客户端保持一致性）
        
        Args:
            model_name: 模型名称
            texts: 测试文本列表
            num_samples: 测试样本数
            warmup: 预热次数
            
        Returns:
            延迟统计
        """
        logger.info(f"Testing single latency for {model_name} (sync mode for consistency)")
        
        # 预热
        for i in range(warmup):
            text = texts[i % len(texts)]
            await self.client.embed_batch_async([text], model_name)
        
        # 测试
        latencies = []
        for i in range(num_samples):
            text = texts[i % len(texts)]
            start_time = time.time()
            await self.client.embed_batch_async([text], model_name)
            latency = time.time() - start_time
            latencies.append(latency)
        
        latencies_ms = np.array(latencies) * 1000
        
        metrics = {
            "model": model_name,
            "num_samples": num_samples,
            "avg_latency_ms": np.mean(latencies_ms),
            "std_latency_ms": np.std(latencies_ms),
            "min_latency_ms": np.min(latencies_ms),
            "max_latency_ms": np.max(latencies_ms),
            "p50_latency_ms": np.percentile(latencies_ms, 50),
            "p90_latency_ms": np.percentile(latencies_ms, 90),
            "p95_latency_ms": np.percentile(latencies_ms, 95),
            "p99_latency_ms": np.percentile(latencies_ms, 99),
        }
        
        logger.info(
            f"Single latency results: avg={metrics['avg_latency_ms']:.2f}ms, "
            f"p99={metrics['p99_latency_ms']:.2f}ms"
        )
        return metrics
    
    async def test_batch_throughput_async(
        self,
        model_name: str,
        texts: List[str],
        batch_sizes: List[int],
        num_iterations: int = 10
    ) -> Dict[int, Dict[str, float]]:
        """
        测试异步批处理吞吐量
        
        Args:
            model_name: 模型名称
            texts: 测试文本列表
            batch_sizes: 要测试的 batch size 列表
            num_iterations: 每个 batch size 的迭代次数
            
        Returns:
            {batch_size: {throughput, latency, ...}}
        """
        logger.info(f"Testing async batch throughput for {model_name}")
        
        results = {}
        for batch_size in batch_sizes:
            logger.info(f"  Testing batch_size={batch_size}")
            
            metrics = await self.client.test_throughput_async(
                texts,
                model_name,
                batch_size,
                num_iterations
            )
            
            results[batch_size] = {
                "throughput": metrics["throughput"],
                "avg_latency": metrics["avg_latency"],
                "std_latency": metrics["std_latency"]
            }
        
        return results
    
    async def generate_and_cache_vectors_async(
        self,
        model_name: str,
        model_config: Dict[str, Any],
        documents: List[Dict[str, str]],
        cache_file: str,
        batch_size: int = 128,
        show_progress: bool = True
    ) -> tuple[float, Dict[str, float]]:
        """
        异步生成向量并保存到缓存
        
        Args:
            model_name: 模型名称
            model_config: 模型配置
            documents: 文档列表
            cache_file: 缓存文件路径
            batch_size: 批处理大小
            show_progress: 是否显示进度条
            
        Returns:
            (生成时间, GPU 显存统计)
        """
        vector_dim = model_config["dimensions"]
        model_full_name = model_config.get("model_name", model_name)
        
        # 创建缓存文件
        cache = VectorCache(cache_file, mode="w")
        cache.create(
            total_vectors=len(documents),
            vector_dim=vector_dim,
            metadata={
                "model_name": model_name,
                "model_full_name": model_full_name,
                "vector_dim": vector_dim,
                "async_mode": True,
                "batch_size": batch_size,
                "concurrent_requests": self.client.max_concurrent_requests
            }
        )
        
        # 启动 GPU 监控
        gpu_monitor = GPUMonitor(interval=1.0)
        gpu_monitor.start()
        
        logger.info(f"Generating vectors for {model_name} (async mode)")
        logger.info(f"  Total documents: {len(documents)}")
        logger.info(f"  Batch size: {batch_size}")
        logger.info(f"  Concurrent requests: {self.client.max_concurrent_requests}")
        logger.info(f"  Cache file: {cache_file}")
        
        start_time = time.time()
        
        try:
            # 准备所有批次
            batches = []
            batch_indices = []
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_texts = [doc["text"] for doc in batch_docs]
                batch_ids = [doc["id"] for doc in batch_docs]
                batches.append((batch_texts, batch_ids, i))
                batch_indices.append(i)
            
            total_batches = len(batches)
            logger.info(f"  Total batches: {total_batches}")
            
            # 并发生成所有向量
            tasks = []
            for batch_texts, batch_ids, start_idx in batches:
                task = self.client.embed_batch_async(batch_texts, model_full_name)
                tasks.append((task, batch_ids, start_idx))
            
            # 使用进度条显示处理进度
            completed = 0
            if show_progress:
                pbar = async_tqdm(total=total_batches, desc=f"Generating {model_name}")
            
            # 按完成顺序处理结果
            for task, batch_ids, start_idx in tasks:
                embeddings = await task
                
                if embeddings is None:
                    logger.error(f"Failed to generate embeddings at index {start_idx}")
                    continue
                
                # 写入缓存
                cache.write_batch(embeddings, batch_ids, start_idx)
                
                completed += 1
                if show_progress:
                    pbar.update(1)
            
            if show_progress:
                pbar.close()
            
        finally:
            cache.close()
            gpu_monitor.stop()
        
        generation_time = time.time() - start_time
        
        # 获取 GPU 统计
        gpu_summary = gpu_monitor.get_summary()
        peak_memory = gpu_summary.get("peak_memory_mb", {})
        avg_memory = gpu_summary.get("average_memory_mb", {})
        
        gpu_memory = {
            "peak_mb": max(peak_memory.values()) if peak_memory else 0,
            "average_mb": max(avg_memory.values()) if avg_memory else 0
        }
        
        logger.info(f"✓ {model_name}: Generated {len(documents)} vectors in {generation_time:.2f}s")
        logger.info(f"  Throughput: {len(documents) / generation_time:.2f} docs/s")
        logger.info(f"  GPU peak memory: {gpu_memory['peak_mb']:.2f} MB")
        
        return generation_time, gpu_memory
    
    async def benchmark_model_async(
        self,
        model_config: Dict[str, Any],
        test_texts: List[str],
        documents: List[Dict[str, str]],
        cache_dir: str,
        auto_tune_batch_size: bool = True
    ) -> AsyncModelBenchmarkResult:
        """
        对单个模型进行完整异步基准测试
        
        Args:
            model_config: 模型配置
            test_texts: 用于性能测试的文本列表
            documents: 用于向量生成的完整文档列表
            cache_dir: 向量缓存目录
            auto_tune_batch_size: 是否自动调优 batch size
            
        Returns:
            测试结果
        """
        model_name = model_config["name"]
        model_full_name = model_config["model_name"]
        
        logger.info("="*80)
        logger.info(f"Benchmarking model (async): {model_name}")
        logger.info("="*80)
        
        # 1. 单样本延迟测试
        logger.info("Step 1: Single latency test")
        latency_metrics = await self.test_single_latency_sync(model_full_name, test_texts)
        
        # 2. 批处理吞吐量测试
        logger.info("Step 2: Async batch throughput test")
        
        if auto_tune_batch_size:
            # 自动寻找最优 batch size
            logger.info("  Auto-tuning batch size...")
            optimal_batch_size, optimal_throughput = await self.client.find_optimal_batch_size(
                test_texts,
                model_full_name,
                start_size=model_config.get("batch_sizes", [64])[0],
                max_size=2048
            )
            
            # 测试最优 batch size 周围的几个值
            batch_sizes_to_test = [
                optimal_batch_size // 2,
                optimal_batch_size,
                optimal_batch_size * 2
            ]
            batch_sizes_to_test = [bs for bs in batch_sizes_to_test if bs >= 8 and bs <= 2048]
        else:
            # 使用配置的 batch sizes
            batch_sizes_to_test = model_config.get("batch_sizes", [64, 128, 256, 512])
        
        throughput_metrics = await self.test_batch_throughput_async(
            model_full_name,
            test_texts,
            batch_sizes_to_test
        )
        
        # 找到最优 batch size
        optimal_batch = max(throughput_metrics.items(), key=lambda x: x[1]["throughput"])
        optimal_batch_size = optimal_batch[0]
        optimal_throughput = optimal_batch[1]["throughput"]
        
        logger.info(f"  Optimal batch size: {optimal_batch_size} ({optimal_throughput:.2f} docs/s)")
        
        # 3. 向量生成测试
        logger.info("Step 3: Async vector generation with GPU monitoring")
        cache_file = Path(cache_dir) / f"{model_name}_async.h5"
        generation_time, gpu_memory = await self.generate_and_cache_vectors_async(
            model_name,
            model_config,
            documents,
            str(cache_file),
            batch_size=optimal_batch_size
        )
        
        generation_throughput = len(documents) / generation_time
        
        # 4. 推算大规模生成时间
        extrapolation_scales = [5000000, 10000000, 50000000, 100000000]
        extrapolation = {}
        for scale in extrapolation_scales:
            est_seconds = scale / generation_throughput
            extrapolation[scale] = {
                "seconds": est_seconds,
                "minutes": est_seconds / 60,
                "hours": est_seconds / 3600
            }
        
        # 创建结果对象
        result = AsyncModelBenchmarkResult(
            model_name=model_name,
            model_full_name=model_full_name,
            vector_dim=model_config["dimensions"],
            single_latency_ms=latency_metrics,
            async_batch_throughput=throughput_metrics,
            optimal_batch_size=optimal_batch_size,
            optimal_throughput=optimal_throughput,
            concurrent_requests=self.client.max_concurrent_requests,
            gpu_memory_mb=gpu_memory,
            total_vectors_generated=len(documents),
            generation_time_seconds=generation_time,
            generation_throughput=generation_throughput,
            extrapolation=extrapolation
        )
        
        logger.info(f"✓ {model_name} async benchmark completed")
        logger.info(f"  Throughput: {generation_throughput:.2f} docs/s")
        logger.info(f"  GPU peak: {gpu_memory['peak_mb']:.2f} MB")
        
        return result
    
    async def run_serial_benchmark_async(
        self,
        models: List[Dict[str, Any]],
        test_texts: List[str],
        documents: List[Dict[str, str]],
        cache_dir: str,
        auto_tune_batch_size: bool = True,
        pause_between_models: int = 5
    ):
        """
        串行运行所有模型的异步基准测试
        
        Args:
            models: 模型配置列表
            test_texts: 测试文本列表
            documents: 完整文档列表
            cache_dir: 缓存目录
            auto_tune_batch_size: 是否自动调优 batch size
            pause_between_models: 模型间暂停秒数
        """
        logger.info(f"Starting async serial benchmark for {len(models)} models")
        
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        for i, model_config in enumerate(models):
            logger.info(f"\n{'='*80}")
            logger.info(f"Model {i+1}/{len(models)}: {model_config['name']}")
            logger.info(f"{'='*80}\n")
            
            # 运行基准测试
            result = await self.benchmark_model_async(
                model_config,
                test_texts,
                documents,
                cache_dir,
                auto_tune_batch_size
            )
            
            self.results.append(result)
            
            # 保存中间结果
            self.save_results()
            
            # 模型间暂停
            if i < len(models) - 1:
                if pause_between_models > 0:
                    logger.info(f"Pausing for {pause_between_models} seconds...")
                    await asyncio.sleep(pause_between_models)
        
        logger.info("\n" + "="*80)
        logger.info("✓ All models benchmarked successfully (async)!")
        logger.info("="*80)
    
    def save_results(self, filename: str = "async_benchmark_results.json"):
        """
        保存测试结果
        
        Args:
            filename: 输出文件名
        """
        output_file = self.output_dir / filename
        
        results_dict = {
            "mode": "async",
            "concurrent_requests": self.client.max_concurrent_requests,
            "models": [asdict(r) for r in self.results],
            "summary": self.get_summary()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Async results saved to {output_file}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取测试摘要
        
        Returns:
            摘要字典
        """
        if not self.results:
            return {}
        
        summary = {
            "total_models": len(self.results),
            "mode": "async",
            "concurrent_requests": self.client.max_concurrent_requests,
            "models": []
        }
        
        for result in self.results:
            summary["models"].append({
                "name": result.model_name,
                "throughput_docs_per_sec": result.generation_throughput,
                "single_latency_p99_ms": result.single_latency_ms.get("p99_latency_ms", 0),
                "optimal_batch_size": result.optimal_batch_size,
                "concurrent_requests": result.concurrent_requests,
                "gpu_peak_memory_mb": result.gpu_memory_mb["peak_mb"],
                "time_for_3m_vectors_hours": result.generation_time_seconds / 3600,
                "time_for_100m_vectors_hours": result.extrapolation.get(100000000, {}).get("hours", 0),
                "speedup_factor": result.speedup_factor
            })
        
        return summary


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("Async Inference Benchmark Test")
    print("This module requires Xinference running on 192.168.1.51:9997")
