"""
Xinference客户端 - 连接到远程192.168.1.51:9997的Xinference服务
"""

import time
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
import numpy as np

logger = logging.getLogger(__name__)


class XinferenceClient:
    """Xinference客户端，使用OpenAI兼容的API"""
    
    def __init__(self, host: str = "192.168.1.51", port: int = 9997, timeout: int = 300):
        """
        初始化Xinference客户端
        
        Args:
            host: Xinference服务器地址
            port: Xinference服务器端口
            timeout: 请求超时时间（秒）
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/v1"
        self.timeout = timeout
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            base_url=self.base_url,
            api_key="dummy",  # Xinference不需要真实的API key
            timeout=timeout
        )
        
        logger.info(f"Xinference client initialized: {self.base_url}")
        
    def list_models(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的模型
        
        Returns:
            模型列表
        """
        try:
            models = self.client.models.list()
            return [model.model_dump() for model in models.data]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    def check_health(self) -> bool:
        """
        检查Xinference服务是否健康
        
        Returns:
            是否健康
        """
        try:
            models = self.list_models()
            logger.info(f"Xinference service is healthy, {len(models)} models available")
            return True
        except Exception as e:
            logger.error(f"Xinference service health check failed: {e}")
            return False
    
    def embed_single(self, text: str, model: str) -> Optional[np.ndarray]:
        """
        生成单个文本的向量
        
        Args:
            text: 输入文本
            model: 模型名称
            
        Returns:
            向量数组，失败返回None
        """
        try:
            response = self.client.embeddings.create(
                model=model,
                input=[text]
            )
            embedding = response.data[0].embedding
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to embed single text: {e}")
            return None
    
    def embed_batch(self, texts: List[str], model: str, batch_size: int = 32) -> Optional[np.ndarray]:
        """
        批量生成文本向量
        
        Args:
            texts: 输入文本列表
            model: 模型名称
            batch_size: 批处理大小
            
        Returns:
            向量数组，形状为 (len(texts), embedding_dim)，失败返回None
        """
        if not texts:
            return None
        
        try:
            # 分批处理
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                response = self.client.embeddings.create(
                    model=model,
                    input=batch
                )
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return np.array(all_embeddings, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to embed batch: {e}")
            return None
    
    def embed_batch_with_timing(
        self,
        texts: List[str],
        model: str,
        batch_size: int = 32
    ) -> tuple[Optional[np.ndarray], float]:
        """
        批量生成文本向量，并返回耗时
        
        Args:
            texts: 输入文本列表
            model: 模型名称
            batch_size: 批处理大小
            
        Returns:
            (向量数组, 耗时秒数)
        """
        start_time = time.time()
        embeddings = self.embed_batch(texts, model, batch_size)
        elapsed = time.time() - start_time
        return embeddings, elapsed
    
    def test_throughput(
        self,
        texts: List[str],
        model: str,
        batch_size: int = 32,
        num_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        测试模型吞吐量
        
        Args:
            texts: 测试文本列表
            model: 模型名称
            batch_size: 批处理大小
            num_iterations: 迭代次数
            
        Returns:
            性能指标字典
        """
        logger.info(f"Testing throughput for {model} with batch_size={batch_size}")
        
        latencies = []
        for i in range(num_iterations):
            _, latency = self.embed_batch_with_timing(texts[:batch_size], model, batch_size)
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
        
        logger.info(f"Throughput test results: {throughput:.2f} docs/s (avg latency: {avg_latency:.4f}s)")
        return metrics
    
    def test_single_latency(
        self,
        texts: List[str],
        model: str,
        num_samples: int = 1000,
        warmup: int = 10
    ) -> Dict[str, Any]:
        """
        测试单样本推理延迟
        
        Args:
            texts: 测试文本列表
            model: 模型名称
            num_samples: 测试样本数
            warmup: 预热次数
            
        Returns:
            延迟指标字典
        """
        logger.info(f"Testing single latency for {model}")
        
        # 预热
        for i in range(warmup):
            self.embed_single(texts[i % len(texts)], model)
        
        # 测试
        latencies = []
        for i in range(num_samples):
            text = texts[i % len(texts)]
            start_time = time.time()
            self.embed_single(text, model)
            latency = time.time() - start_time
            latencies.append(latency)
        
        latencies_ms = np.array(latencies) * 1000  # 转换为毫秒
        
        metrics = {
            "model": model,
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
        
        logger.info(f"Single latency test results: avg={metrics['avg_latency_ms']:.2f}ms, p99={metrics['p99_latency_ms']:.2f}ms")
        return metrics
    
    def close(self):
        """关闭客户端连接"""
        # OpenAI客户端不需要显式关闭
        logger.info("Xinference client closed")


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    client = XinferenceClient()
    
    # 检查健康状态
    if client.check_health():
        print("✓ Xinference service is healthy")
        
        # 列出模型
        models = client.list_models()
        print(f"\n✓ Available models: {len(models)}")
        for model in models[:5]:  # 只显示前5个
            print(f"  - {model.get('id', 'unknown')}")
    else:
        print("✗ Xinference service is not available")
