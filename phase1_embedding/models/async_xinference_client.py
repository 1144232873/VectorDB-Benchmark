"""
异步 Xinference 客户端 - 支持高并发推理请求

使用 httpx 异步 HTTP 客户端实现并发请求，显著提升 GPU 利用率
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
import numpy as np
import httpx
from tqdm.asyncio import tqdm as async_tqdm

logger = logging.getLogger(__name__)


class AsyncXinferenceClient:
    """异步 Xinference 客户端，支持高并发请求"""
    
    def __init__(
        self,
        host: str = "192.168.1.51",
        port: int = 9997,
        timeout: int = 300,
        max_concurrent_requests: int = 8,
        connection_pool_size: int = 32
    ):
        """
        初始化异步 Xinference 客户端
        
        Args:
            host: Xinference 服务器地址
            port: Xinference 服务器端口
            timeout: 请求超时时间（秒）
            max_concurrent_requests: 最大并发请求数
            connection_pool_size: 连接池大小
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/v1"
        self.timeout = timeout
        self.max_concurrent_requests = max_concurrent_requests
        
        # 配置连接池和超时
        limits = httpx.Limits(
            max_keepalive_connections=connection_pool_size,
            max_connections=connection_pool_size * 2,
            keepalive_expiry=300
        )
        
        timeout_config = httpx.Timeout(
            timeout=timeout,
            connect=10.0,
            read=timeout,
            write=timeout
        )
        
        # 创建异步 HTTP 客户端
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            limits=limits,
            timeout=timeout_config,
            http2=True  # 启用 HTTP/2 以提升性能
        )
        
        # 信号量控制并发数
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        logger.info(
            f"Async Xinference client initialized: {self.base_url}, "
            f"max_concurrent={max_concurrent_requests}, pool_size={connection_pool_size}"
        )
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的模型
        
        Returns:
            模型列表
        """
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def check_health(self) -> bool:
        """
        检查 Xinference 服务是否健康
        
        Returns:
            是否健康
        """
        try:
            models = await self.list_models()
            logger.info(f"Xinference service is healthy, {len(models)} models available")
            return True
        except Exception as e:
            logger.error(f"Xinference service health check failed: {e}")
            return False
    
    async def get_available_model_ids(self) -> List[str]:
        """
        获取所有可用模型的 ID 列表
        
        Returns:
            模型 ID 列表
        """
        models = await self.list_models()
        model_ids = []
        for model in models:
            model_id = (
                model.get('id') or 
                model.get('model_id') or 
                model.get('name') or
                model.get('uid')
            )
            if model_id:
                model_ids.append(str(model_id))
        return model_ids
    
    async def embed_batch_async(
        self,
        texts: List[str],
        model: str
    ) -> Optional[np.ndarray]:
        """
        异步批量生成文本向量（单次请求）
        
        Args:
            texts: 输入文本列表
            model: 模型名称
            
        Returns:
            向量数组，形状为 (len(texts), embedding_dim)，失败返回 None
        """
        if not texts:
            return None
        
        try:
            # 使用信号量控制并发
            async with self.semaphore:
                response = await self.client.post(
                    "/embeddings",
                    json={
                        "model": model,
                        "input": texts
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                embeddings = [item["embedding"] for item in data["data"]]
                return np.array(embeddings, dtype=np.float32)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error embedding batch: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Failed to embed batch: {e}")
            return None
    
    async def embed_batch_with_timing(
        self,
        texts: List[str],
        model: str
    ) -> tuple[Optional[np.ndarray], float]:
        """
        异步批量生成文本向量，并返回耗时
        
        Args:
            texts: 输入文本列表
            model: 模型名称
            
        Returns:
            (向量数组, 耗时秒数)
        """
        start_time = time.time()
        embeddings = await self.embed_batch_async(texts, model)
        elapsed = time.time() - start_time
        return embeddings, elapsed
    
    async def embed_concurrent(
        self,
        all_texts: List[str],
        model: str,
        batch_size: int = 128,
        show_progress: bool = True
    ) -> Optional[np.ndarray]:
        """
        并发处理大量文本的向量生成
        
        Args:
            all_texts: 所有文本列表
            model: 模型名称
            batch_size: 每个批次的大小
            show_progress: 是否显示进度条
            
        Returns:
            所有向量数组，形状为 (len(all_texts), embedding_dim)
        """
        if not all_texts:
            return None
        
        # 将文本分成多个批次
        batches = []
        for i in range(0, len(all_texts), batch_size):
            batch = all_texts[i:i+batch_size]
            batches.append(batch)
        
        logger.info(
            f"Processing {len(all_texts)} texts in {len(batches)} batches "
            f"(batch_size={batch_size}, concurrent={self.max_concurrent_requests})"
        )
        
        # 并发发送所有批次
        tasks = [self.embed_batch_async(batch, model) for batch in batches]
        
        if show_progress:
            # 使用异步进度条
            results = []
            for coro in async_tqdm(
                asyncio.as_completed(tasks),
                total=len(tasks),
                desc=f"Embedding {model}"
            ):
                result = await coro
                results.append(result)
        else:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查是否有失败的批次
        failed_batches = []
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch {i} failed: {result}")
                failed_batches.append(i)
            elif result is None:
                logger.error(f"Batch {i} returned None")
                failed_batches.append(i)
            else:
                valid_results.append(result)
        
        if failed_batches:
            logger.error(f"Failed batches: {len(failed_batches)}/{len(batches)}")
            return None
        
        # 合并所有结果
        all_embeddings = np.vstack(valid_results)
        logger.info(f"✓ Generated {len(all_embeddings)} embeddings")
        
        return all_embeddings
    
    async def test_throughput_async(
        self,
        texts: List[str],
        model: str,
        batch_size: int = 128,
        num_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        异步测试模型吞吐量
        
        Args:
            texts: 测试文本列表
            model: 模型名称
            batch_size: 批处理大小
            num_iterations: 迭代次数
            
        Returns:
            性能指标字典
        """
        logger.info(f"Testing async throughput for {model} with batch_size={batch_size}")
        
        latencies = []
        test_batch = texts[:batch_size]
        
        for i in range(num_iterations):
            _, latency = await self.embed_batch_with_timing(test_batch, model)
            latencies.append(latency)
            logger.debug(f"Iteration {i+1}/{num_iterations}: {latency:.4f}s")
        
        avg_latency = np.mean(latencies)
        std_latency = np.std(latencies)
        throughput = batch_size / avg_latency  # docs/s
        
        metrics = {
            "model": model,
            "batch_size": batch_size,
            "num_iterations": num_iterations,
            "avg_latency": avg_latency,
            "std_latency": std_latency,
            "min_latency": min(latencies),
            "max_latency": max(latencies),
            "throughput": throughput,
            "throughput_unit": "docs/s"
        }
        
        logger.info(
            f"Async throughput test results: {throughput:.2f} docs/s "
            f"(avg latency: {avg_latency:.4f}s)"
        )
        return metrics
    
    async def find_optimal_batch_size(
        self,
        texts: List[str],
        model: str,
        start_size: int = 64,
        max_size: int = 2048,
        test_iterations: int = 3
    ) -> tuple[int, float]:
        """
        自动寻找最优批次大小
        
        Args:
            texts: 测试文本列表
            model: 模型名称
            start_size: 起始批次大小
            max_size: 最大批次大小
            test_iterations: 每个批次大小的测试迭代次数
            
        Returns:
            (最优批次大小, 最优吞吐量)
        """
        logger.info(f"Finding optimal batch size for {model} (start={start_size}, max={max_size})")
        
        batch_size = start_size
        best_batch_size = start_size
        best_throughput = 0.0
        previous_throughput = 0.0
        
        while batch_size <= max_size and batch_size <= len(texts):
            try:
                metrics = await self.test_throughput_async(
                    texts,
                    model,
                    batch_size,
                    test_iterations
                )
                
                throughput = metrics["throughput"]
                logger.info(f"  batch_size={batch_size}: {throughput:.2f} docs/s")
                
                # 如果吞吐量下降超过 10%，停止测试
                if previous_throughput > 0 and throughput < previous_throughput * 0.9:
                    logger.info(f"  Throughput degraded, stopping at batch_size={batch_size}")
                    break
                
                if throughput > best_throughput:
                    best_throughput = throughput
                    best_batch_size = batch_size
                
                previous_throughput = throughput
                batch_size *= 2  # 翻倍测试
                
            except Exception as e:
                logger.error(f"  batch_size={batch_size} failed: {e}")
                # 可能是 OOM，停止测试
                break
        
        logger.info(
            f"✓ Optimal batch size for {model}: {best_batch_size} "
            f"({best_throughput:.2f} docs/s)"
        )
        return best_batch_size, best_throughput
    
    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()
        logger.info("Async Xinference client closed")
    
    async def __aenter__(self):
        """异步上下文管理器：进入"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器：退出"""
        await self.close()


# 同步包装器，用于向后兼容
class AsyncXinferenceClientSync:
    """同步包装器，允许在同步代码中使用异步客户端"""
    
    def __init__(self, *args, **kwargs):
        self.async_client = AsyncXinferenceClient(*args, **kwargs)
        self.loop = asyncio.new_event_loop()
    
    def embed_concurrent(self, *args, **kwargs):
        """同步调用异步并发方法"""
        return self.loop.run_until_complete(
            self.async_client.embed_concurrent(*args, **kwargs)
        )
    
    def find_optimal_batch_size(self, *args, **kwargs):
        """同步调用异步寻找最优批次大小"""
        return self.loop.run_until_complete(
            self.async_client.find_optimal_batch_size(*args, **kwargs)
        )
    
    def close(self):
        """关闭客户端"""
        self.loop.run_until_complete(self.async_client.close())
        self.loop.close()


if __name__ == "__main__":
    # 测试代码
    async def test():
        logging.basicConfig(level=logging.INFO)
        
        async with AsyncXinferenceClient(max_concurrent_requests=8) as client:
            # 检查健康状态
            if await client.check_health():
                print("✓ Xinference service is healthy")
                
                # 列出模型
                models = await client.list_models()
                print(f"\n✓ Available models: {len(models)}")
                for model in models[:3]:
                    print(f"  - {model.get('id', 'unknown')}")
                
                # 测试并发嵌入（如果有模型）
                if models:
                    model_id = models[0].get('id')
                    test_texts = ["测试文本 " + str(i) for i in range(100)]
                    
                    print(f"\n测试并发嵌入（100个文本，batch_size=32）")
                    embeddings = await client.embed_concurrent(
                        test_texts,
                        model_id,
                        batch_size=32
                    )
                    
                    if embeddings is not None:
                        print(f"✓ 生成向量形状: {embeddings.shape}")
            else:
                print("✗ Xinference service is not available")
    
    asyncio.run(test())
