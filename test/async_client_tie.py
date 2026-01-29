"""
异步 Text Embeddings Inference (TIE/TEI) 客户端
用于调用 Hugging Face TEI 的 /embed 接口，与 async_client.py (Xinference) 对比测试
"""

import asyncio
import time
import logging
from typing import List, Optional, Dict
import numpy as np
import httpx
logger = logging.getLogger(__name__)

# Qwen3-Embedding 推荐的指令模板（可配置覆盖）
DEFAULT_INSTRUCTION_TEMPLATE = (
    "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: {text}"
)


class AsyncTIEClient:
    """异步 Text Embeddings Inference 客户端（/embed 接口）"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8088,
        timeout: int = 300,
        max_concurrent_requests: int = 16,
        connection_pool_size: int = 32,
        instruction_template: Optional[str] = None,
    ):
        """
        Args:
            host: TIE 服务地址
            port: TIE 服务端口（docker -p 8088:80 时使用 8088）
            timeout: 请求超时（秒）
            max_concurrent_requests: 最大并发请求数
            connection_pool_size: 连接池大小
            instruction_template: 指令模板，{text} 会被替换为原文。None 则使用 Qwen 默认模板；空字符串表示不包装。
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.embed_url = f"{self.base_url}/embed"
        self.timeout = timeout
        self.max_concurrent_requests = max_concurrent_requests
        self.instruction_template = (
            instruction_template
            if instruction_template is not None
            else DEFAULT_INSTRUCTION_TEMPLATE
        )

        limits = httpx.Limits(
            max_keepalive_connections=connection_pool_size,
            max_connections=connection_pool_size * 2,
            keepalive_expiry=300,
        )
        timeout_config = httpx.Timeout(
            timeout=timeout,
            connect=10.0,
            read=timeout,
            write=timeout,
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            limits=limits,
            timeout=timeout_config,
            http2=True,
        )
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

        logger.info(
            f"Async TIE client initialized: {self.embed_url}, "
            f"max_concurrent={max_concurrent_requests}, "
            f"instruction_template={'<custom>' if self.instruction_template else 'none'}"
        )

    def _wrap_inputs(self, texts: List[str]) -> List[str]:
        """按指令模板包装输入（适用于 Qwen3-Embedding 等）"""
        if not self.instruction_template:
            return texts
        return [self.instruction_template.format(text=t) for t in texts]

    async def health(self) -> bool:
        """检查 TIE 服务是否可用（/health 或 /embed 可选用）"""
        try:
            # TEI 可能提供 /health，若无则用 HEAD /
            r = await self.client.get("/")
            return r.status_code in (200, 404)
        except Exception as e:
            logger.debug(f"TIE health check failed: {e}")
            return False

    async def embed_batch_async(
        self,
        texts: List[str],
        model: str = "text-embeddings-inference",
    ) -> Optional[np.ndarray]:
        """异步批量调用 /embed 生成向量（model 参数在 TEI 中通常忽略，保留接口兼容）"""
        if not texts:
            return None
        inputs = self._wrap_inputs(texts)
        try:
            async with self.semaphore:
                response = await self.client.post(
                    "/embed",
                    json={"inputs": inputs if len(inputs) > 1 else inputs[0]},
                )
                response.raise_for_status()
                data = response.json()

                # TEI 返回格式：可能是 [[...], [...]] 或 {"embeddings": [[...], [...]]}
                if isinstance(data, list):
                    embeddings = data
                else:
                    embeddings = data.get("embeddings", data)
                if not embeddings:
                    return None
                return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            logger.error(f"TIE embed_batch_async failed: {e}")
            return None

    async def embed_concurrent(
        self,
        all_texts: List[str],
        model: str = "text-embeddings-inference",
        batch_size: int = 128,
        show_progress: bool = True,
    ) -> Optional[np.ndarray]:
        """并发批量向量化"""
        if not all_texts:
            return None
        batches = [
            all_texts[i : i + batch_size]
            for i in range(0, len(all_texts), batch_size)
        ]
        logger.info(
            f"TIE: Processing {len(all_texts)} texts in {len(batches)} batches "
            f"(batch_size={batch_size}, concurrent={self.max_concurrent_requests})"
        )
        tasks = [self.embed_batch_async(b, model) for b in batches]
        # 使用 gather 并发且保证结果顺序与 batches 一致
        results = await asyncio.gather(*tasks, return_exceptions=True)

        failed = [i for i, r in enumerate(results) if not isinstance(r, np.ndarray)]
        if failed:
            logger.error(f"TIE failed batches: {len(failed)}/{len(batches)}")
            return None
        all_embeddings = np.vstack([r for r in results if r is not None])
        logger.info(f"✓ TIE generated {len(all_embeddings)} embeddings")
        return all_embeddings

    async def find_optimal_batch_size(
        self,
        texts: List[str],
        model: str = "text-embeddings-inference",
        start_size: int = 64,
        max_size: int = 2048,
        test_iterations: int = 3,
    ) -> tuple[int, float]:
        """自动寻找最优 batch size"""
        logger.info(f"TIE: Finding optimal batch size (model={model})")
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
                    logger.info("  Throughput degraded, stopping")
                    break
                if throughput > best_throughput:
                    best_throughput = throughput
                    best_batch_size = batch_size
                previous_throughput = throughput
                batch_size *= 2
            except Exception as e:
                logger.error(f"  batch_size={batch_size} failed: {e}")
                break
        logger.info(f"✓ TIE optimal batch size: {best_batch_size} ({best_throughput:.2f} docs/s)")
        return best_batch_size, best_throughput

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
