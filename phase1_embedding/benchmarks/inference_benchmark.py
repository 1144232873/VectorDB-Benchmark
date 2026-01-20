"""
推理性能基准测试 - 串行测试5个模型的推理性能
"""

import time
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import numpy as np
from tqdm import tqdm

from ..models.xinference_client import XinferenceClient
from ..cache.vector_cache import VectorCache
from .gpu_monitor import GPUMonitor

logger = logging.getLogger(__name__)


@dataclass
class ModelBenchmarkResult:
    """单个模型的基准测试结果"""
    model_name: str
    model_full_name: str
    vector_dim: int
    
    # 单样本延迟测试
    single_latency_ms: Dict[str, float]  # avg, std, p50, p90, p95, p99
    
    # 批处理吞吐量测试
    batch_throughput: Dict[int, Dict[str, float]]  # {batch_size: {throughput, latency}}
    optimal_batch_size: int
    optimal_throughput: float
    
    # 显存使用
    gpu_memory_mb: Dict[str, float]  # peak, average
    
    # 向量生成统计
    total_vectors_generated: int
    generation_time_seconds: float
    generation_throughput: float  # vectors/second
    
    # 推算
    extrapolation: Dict[int, Dict[str, float]]  # {target_size: {hours, ...}}
    

class InferenceBenchmark:
    """推理性能基准测试"""
    
    def __init__(
        self,
        xinference_client: XinferenceClient,
        output_dir: str = "phase1_results"
    ):
        """
        初始化基准测试
        
        Args:
            xinference_client: Xinference客户端
            output_dir: 输出目录
        """
        self.client = xinference_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.results: List[ModelBenchmarkResult] = []
        
        logger.info("Inference benchmark initialized")
    
    def test_single_latency(
        self,
        model_name: str,
        texts: List[str],
        num_samples: int = 1000,
        warmup: int = 10
    ) -> Dict[str, float]:
        """
        测试单样本推理延迟
        
        Args:
            model_name: 模型名称
            texts: 测试文本列表
            num_samples: 测试样本数
            warmup: 预热次数
            
        Returns:
            延迟统计
        """
        logger.info(f"Testing single latency for {model_name}")
        return self.client.test_single_latency(texts, model_name, num_samples, warmup)
    
    def test_batch_throughput(
        self,
        model_name: str,
        texts: List[str],
        batch_sizes: List[int],
        num_iterations: int = 10
    ) -> Dict[int, Dict[str, float]]:
        """
        测试批处理吞吐量
        
        Args:
            model_name: 模型名称
            texts: 测试文本列表
            batch_sizes: 要测试的batch size列表
            num_iterations: 每个batch size的迭代次数
            
        Returns:
            {batch_size: {throughput, latency, ...}}
        """
        logger.info(f"Testing batch throughput for {model_name}")
        
        results = {}
        for batch_size in batch_sizes:
            logger.info(f"  Testing batch_size={batch_size}")
            metrics = self.client.test_throughput(
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
    
    def generate_vectors_with_monitoring(
        self,
        model_name: str,
        documents: List[Dict[str, str]],
        cache_file: str,
        batch_size: int = 32
    ) -> tuple[float, Dict[str, float]]:
        """
        生成向量并监控GPU
        
        Args:
            model_name: 模型名称
            documents: 文档列表 [{id, text}]
            cache_file: 缓存文件路径
            batch_size: 批处理大小
            
        Returns:
            (生成时间, GPU峰值显存)
        """
        logger.info(f"Generating vectors for {model_name}")
        logger.info(f"  Total documents: {len(documents)}")
        logger.info(f"  Cache file: {cache_file}")
        
        # 启动GPU监控
        gpu_monitor = GPUMonitor(interval=1.0)
        gpu_monitor.start()
        
        start_time = time.time()
        
        try:
            # 批量生成向量
            current_idx = 0
            pbar = tqdm(total=len(documents), desc=f"Generating {model_name}")
            
            while current_idx < len(documents):
                batch_docs = documents[current_idx:current_idx + batch_size]
                batch_texts = [doc["text"] for doc in batch_docs]
                
                # 生成向量
                embeddings = self.client.embed_batch(batch_texts, model_name, batch_size)
                
                if embeddings is None:
                    logger.error(f"Failed to generate embeddings at index {current_idx}")
                    break
                
                # 写入缓存
                # 注意：这里需要在调用前已创建cache文件
                # 实际写入逻辑在generate_and_cache_vectors中处理
                
                current_idx += len(batch_docs)
                pbar.update(len(batch_docs))
            
            pbar.close()
        finally:
            # 停止GPU监控
            gpu_monitor.stop()
        
        generation_time = time.time() - start_time
        
        # 获取GPU峰值显存
        gpu_summary = gpu_monitor.get_summary()
        peak_memory = gpu_summary.get("peak_memory_mb", {})
        avg_memory = gpu_summary.get("average_memory_mb", {})
        
        gpu_memory = {
            "peak_mb": max(peak_memory.values()) if peak_memory else 0,
            "average_mb": max(avg_memory.values()) if avg_memory else 0
        }
        
        logger.info(f"Vector generation completed in {generation_time:.2f}s")
        logger.info(f"GPU peak memory: {gpu_memory['peak_mb']:.2f} MB")
        
        return generation_time, gpu_memory
    
    def generate_and_cache_vectors(
        self,
        model_name: str,
        model_config: Dict[str, Any],
        documents: List[Dict[str, str]],
        cache_file: str,
        batch_size: int = 32
    ) -> tuple[float, Dict[str, float]]:
        """
        生成向量并保存到缓存
        
        Args:
            model_name: 模型名称
            model_config: 模型配置
            documents: 文档列表
            cache_file: 缓存文件路径
            batch_size: 批处理大小
            
        Returns:
            (生成时间, GPU显存统计)
        """
        vector_dim = model_config["dimensions"]
        
        # 创建缓存文件
        cache = VectorCache(cache_file, mode="w")
        cache.create(
            total_vectors=len(documents),
            vector_dim=vector_dim,
            metadata={
                "model_name": model_name,
                "model_full_name": model_config.get("model_name", model_name),
                "vector_dim": vector_dim
            }
        )
        
        # 启动GPU监控
        gpu_monitor = GPUMonitor(interval=1.0)
        gpu_monitor.start()
        
        start_time = time.time()
        current_idx = 0
        
        try:
            pbar = tqdm(total=len(documents), desc=f"Generating {model_name}")
            
            while current_idx < len(documents):
                batch_docs = documents[current_idx:current_idx + batch_size]
                batch_texts = [doc["text"] for doc in batch_docs]
                batch_ids = [doc["id"] for doc in batch_docs]
                
                # 生成向量
                embeddings = self.client.embed_batch(batch_texts, model_config["model_name"], batch_size)
                
                if embeddings is None:
                    logger.error(f"Failed to generate embeddings at index {current_idx}")
                    break
                
                # 写入缓存
                cache.write_batch(embeddings, batch_ids, current_idx)
                
                current_idx += len(batch_docs)
                pbar.update(len(batch_docs))
            
            pbar.close()
        finally:
            cache.close()
            gpu_monitor.stop()
        
        generation_time = time.time() - start_time
        
        # 获取GPU统计
        gpu_summary = gpu_monitor.get_summary()
        peak_memory = gpu_summary.get("peak_memory_mb", {})
        avg_memory = gpu_summary.get("average_memory_mb", {})
        
        gpu_memory = {
            "peak_mb": max(peak_memory.values()) if peak_memory else 0,
            "average_mb": max(avg_memory.values()) if avg_memory else 0
        }
        
        logger.info(f"✓ {model_name}: Generated {current_idx} vectors in {generation_time:.2f}s")
        logger.info(f"  GPU peak memory: {gpu_memory['peak_mb']:.2f} MB")
        
        return generation_time, gpu_memory
    
    def benchmark_model(
        self,
        model_config: Dict[str, Any],
        test_texts: List[str],
        documents: List[Dict[str, str]],
        cache_dir: str
    ) -> ModelBenchmarkResult:
        """
        对单个模型进行完整基准测试
        
        Args:
            model_config: 模型配置
            test_texts: 用于性能测试的文本列表
            documents: 用于向量生成的完整文档列表
            cache_dir: 向量缓存目录
            
        Returns:
            测试结果
        """
        model_name = model_config["name"]
        model_full_name = model_config["model_name"]
        
        logger.info("="*80)
        logger.info(f"Benchmarking model: {model_name}")
        logger.info("="*80)
        
        # 1. 单样本延迟测试
        logger.info("Step 1: Single latency test")
        latency_metrics = self.test_single_latency(model_full_name, test_texts)
        
        # 2. 批处理吞吐量测试
        logger.info("Step 2: Batch throughput test")
        batch_sizes = model_config.get("batch_sizes", [8, 16, 32, 64])
        throughput_metrics = self.test_batch_throughput(
            model_full_name,
            test_texts,
            batch_sizes
        )
        
        # 找到最优batch size
        optimal_batch = max(throughput_metrics.items(), key=lambda x: x[1]["throughput"])
        optimal_batch_size = optimal_batch[0]
        optimal_throughput = optimal_batch[1]["throughput"]
        
        # 3. 向量生成测试
        logger.info("Step 3: Vector generation with GPU monitoring")
        cache_file = Path(cache_dir) / f"{model_name}.h5"
        generation_time, gpu_memory = self.generate_and_cache_vectors(
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
        result = ModelBenchmarkResult(
            model_name=model_name,
            model_full_name=model_full_name,
            vector_dim=model_config["dimensions"],
            single_latency_ms=latency_metrics,
            batch_throughput=throughput_metrics,
            optimal_batch_size=optimal_batch_size,
            optimal_throughput=optimal_throughput,
            gpu_memory_mb=gpu_memory,
            total_vectors_generated=len(documents),
            generation_time_seconds=generation_time,
            generation_throughput=generation_throughput,
            extrapolation=extrapolation
        )
        
        logger.info(f"✓ {model_name} benchmark completed")
        logger.info(f"  Throughput: {generation_throughput:.2f} docs/s")
        logger.info(f"  GPU peak: {gpu_memory['peak_mb']:.2f} MB")
        
        return result
    
    def run_serial_benchmark(
        self,
        models: List[Dict[str, Any]],
        test_texts: List[str],
        documents: List[Dict[str, str]],
        cache_dir: str,
        cleanup_between_models: bool = True,
        pause_between_models: int = 5
    ):
        """
        串行运行所有模型的基准测试
        
        Args:
            models: 模型配置列表
            test_texts: 测试文本列表
            documents: 完整文档列表
            cache_dir: 缓存目录
            cleanup_between_models: 模型间是否清理显存
            pause_between_models: 模型间暂停秒数
        """
        logger.info(f"Starting serial benchmark for {len(models)} models")
        
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        for i, model_config in enumerate(models):
            logger.info(f"\n{'='*80}")
            logger.info(f"Model {i+1}/{len(models)}: {model_config['name']}")
            logger.info(f"{'='*80}\n")
            
            # 运行基准测试
            result = self.benchmark_model(
                model_config,
                test_texts,
                documents,
                cache_dir
            )
            
            self.results.append(result)
            
            # 保存中间结果
            self.save_results()
            
            # 模型间暂停
            if i < len(models) - 1:  # 不是最后一个模型
                if cleanup_between_models:
                    logger.info("Cleaning up GPU memory...")
                    # 在Python中，通常依赖垃圾回收
                    # Xinference server端会管理模型加载/卸载
                
                if pause_between_models > 0:
                    logger.info(f"Pausing for {pause_between_models} seconds...")
                    time.sleep(pause_between_models)
        
        logger.info("\n" + "="*80)
        logger.info("✓ All models benchmarked successfully!")
        logger.info("="*80)
    
    def save_results(self, filename: str = "benchmark_results.json"):
        """
        保存测试结果
        
        Args:
            filename: 输出文件名
        """
        output_file = self.output_dir / filename
        
        results_dict = {
            "models": [asdict(r) for r in self.results],
            "summary": self.get_summary()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_file}")
    
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
            "models": []
        }
        
        for result in self.results:
            summary["models"].append({
                "name": result.model_name,
                "throughput_docs_per_sec": result.generation_throughput,
                "single_latency_p99_ms": result.single_latency_ms.get("p99_latency_ms", 0),
                "optimal_batch_size": result.optimal_batch_size,
                "gpu_peak_memory_mb": result.gpu_memory_mb["peak_mb"],
                "time_for_3m_vectors_hours": result.generation_time_seconds / 3600,
                "time_for_100m_vectors_hours": result.extrapolation.get(100000000, {}).get("hours", 0)
            })
        
        return summary


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("Inference Benchmark Test")
    print("This module requires Xinference running on 192.168.1.51:9997")
