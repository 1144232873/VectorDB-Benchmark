"""
简化的异步Xinference客户端
用于test目录下的PDF向量化脚本
"""

import asyncio
import time
import logging
from typing import List, Optional, Dict
import numpy as np
import httpx
from tqdm.asyncio import tqdm as async_tqdm

logger = logging.getLogger(__name__)


class AsyncXinferenceClient:
    """异步Xinference客户端"""
    
    def __init__(
        self,
        host: str = "192.168.1.51",
        port: int = 9997,
        timeout: int = 300,
        max_concurrent_requests: int = 16,
        connection_pool_size: int = 32
    ):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/v1"
        self.timeout = timeout
        self.max_concurrent_requests = max_concurrent_requests
        
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
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            limits=limits,
            timeout=timeout_config,
            http2=True
        )
        
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        logger.info(
            f"Async Xinference client initialized: {self.base_url}, "
            f"max_concurrent={max_concurrent_requests}"
        )
    
    async def list_models(self) -> List[Dict]:
        """列出所有可用的模型"""
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def embed_batch_async(
        self,
        texts: List[str],
        model: str
    ) -> Optional[np.ndarray]:
        """异步批量生成文本向量"""
        if not texts:
            return None
        
        try:
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
                
        except Exception as e:
            logger.error(f"Failed to embed batch: {e}")
            return None
    
    async def embed_concurrent(
        self,
        all_texts: List[str],
        model: str,
        batch_size: int = 128,
        show_progress: bool = True
    ) -> Optional[np.ndarray]:
        """并发处理大量文本的向量生成"""
        if not all_texts:
            return None
        
        batches = []
        for i in range(0, len(all_texts), batch_size):
            batch = all_texts[i:i+batch_size]
            batches.append(batch)
        
        logger.info(
            f"Processing {len(all_texts)} texts in {len(batches)} batches "
            f"(batch_size={batch_size}, concurrent={self.max_concurrent_requests})"
        )
        
        tasks = [self.embed_batch_async(batch, model) for batch in batches]
        
        if show_progress:
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
        
        all_embeddings = np.vstack(valid_results)
        logger.info(f"✓ Generated {len(all_embeddings)} embeddings")
        
        return all_embeddings
    
    async def find_optimal_batch_size(
        self,
        texts: List[str],
        model: str,
        start_size: int = 64,
        max_size: int = 2048,
        test_iterations: int = 3
    ) -> tuple[int, float]:
        """自动寻找最优批次大小"""
        logger.info(f"Finding optimal batch size for {model}")
        
        batch_size = start_size
        best_batch_size = start_size
        best_throughput = 0.0
        previous_throughput = 0.0
        
        while batch_size <= max_size and batch_size <= len(texts):
            try:
                test_batch = texts[:batch_size]
                latencies = []
                
                for _ in range(test_iterations):
                    start_time = time.time()
                    result = await self.embed_batch_async(test_batch, model)
                    if result is not None:
                        latencies.append(time.time() - start_time)
                
                if not latencies:
                    break
                
                avg_latency = np.mean(latencies)
                throughput = batch_size / avg_latency
                
                logger.info(f"  batch_size={batch_size}: {throughput:.2f} docs/s")
                
                if previous_throughput > 0 and throughput < previous_throughput * 0.9:
                    logger.info(f"  Throughput degraded, stopping")
                    break
                
                if throughput > best_throughput:
                    best_throughput = throughput
                    best_batch_size = batch_size
                
                previous_throughput = throughput
                batch_size *= 2
                
            except Exception as e:
                logger.error(f"  batch_size={batch_size} failed: {e}")
                break
        
        logger.info(f"✓ Optimal batch size: {best_batch_size} ({best_throughput:.2f} docs/s)")
        return best_batch_size, best_throughput
    
    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
