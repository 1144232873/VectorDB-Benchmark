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
    
    def get_available_model_ids(self) -> List[str]:
        """
        获取所有可用模型的ID列表
        
        Returns:
            模型ID列表
        """
        models = self.list_models()
        model_ids = []
        for model in models:
            # 尝试多种可能的字段名
            model_id = (
                model.get('id') or 
                model.get('model_id') or 
                model.get('name') or
                model.get('uid')
            )
            if model_id:
                model_ids.append(str(model_id))
        return model_ids
    
    def check_model_exists(self, model_name: str) -> tuple[bool, Optional[str]]:
        """
        检查模型是否存在，如果不存在则尝试找到匹配的模型
        
        Args:
            model_name: 要检查的模型名称
            
        Returns:
            (是否存在, 实际模型ID或None)
        """
        available_models = self.get_available_model_ids()
        
        # 精确匹配
        if model_name in available_models:
            return True, model_name
        
        # 尝试模糊匹配（不区分大小写，忽略斜杠）
        model_name_lower = model_name.lower().replace('/', '-')
        for available_id in available_models:
            available_lower = available_id.lower().replace('/', '-')
            if model_name_lower == available_lower:
                logger.warning(f"Model name mismatch: config uses '{model_name}', but Xinference has '{available_id}'")
                return True, available_id
        
        # 尝试部分匹配（包含关键词）
        keywords = model_name.lower().replace('/', ' ').replace('-', ' ').split()
        for available_id in available_models:
            available_lower = available_id.lower()
            if all(keyword in available_lower for keyword in keywords if len(keyword) > 2):
                logger.warning(f"Found similar model: '{available_id}' (config uses '{model_name}')")
                return True, available_id
        
        # 尝试更宽松的匹配：提取模型的核心名称（去掉组织名和版本号）
        # 例如：BAAI/bge-m3 -> bge-m3, Qwen3-Embedding-0.6B -> qwen-embedding-0.6b
        def extract_core_name(name: str) -> str:
            # 去掉组织名（如 BAAI/, Qwen/）
            parts = name.lower().split('/')
            if len(parts) > 1:
                name = parts[-1]
            # 统一版本号：qwen2.5 和 qwen3 都视为 qwen（向后兼容）
            name = name.replace('qwen2.5', 'qwen').replace('qwen3', 'qwen')
            # 提取关键部分：模型类型和大小
            # 例如：qwen-embedding-0.6b, bge-m3
            return name
        
        config_core = extract_core_name(model_name)
        for available_id in available_models:
            available_core = extract_core_name(available_id)
            # 如果核心名称匹配（允许版本号差异，如 qwen2.5 和 qwen3，向后兼容）
            if config_core == available_core:
                logger.warning(f"Found matching model by core name: '{available_id}' (config uses '{model_name}')")
                return True, available_id
            
            # 特殊处理：如果都是embedding模型，且大小匹配
            if 'embedding' in config_core and 'embedding' in available_core:
                # 提取大小标识（0.6b, 4b, 8b, m3等）
                config_sizes = [s for s in ['0.6b', '4b', '8b', 'm3'] if s in config_core]
                available_sizes = [s for s in ['0.6b', '4b', '8b', 'm3'] if s in available_core]
                if config_sizes and available_sizes and config_sizes[0] == available_sizes[0]:
                    logger.warning(f"Found matching embedding model by size: '{available_id}' (config uses '{model_name}')")
                    return True, available_id
        
        return False, None
    
    def embed_single(self, text: str, model: str) -> Optional[np.ndarray]:
        """
        生成单个文本的向量
        
        Args:
            text: 输入文本
            model: 模型名称
            
        Returns:
            向量数组，失败返回None
        """
        # 检查模型是否存在
        exists, actual_model_id = self.check_model_exists(model)
        if not exists:
            available_models = self.get_available_model_ids()
            error_msg = (
                f"Model '{model}' not found in Xinference.\n"
                f"Available models: {', '.join(available_models[:10])}"
            )
            logger.error(error_msg)
            return None
        
        # 使用实际模型ID
        actual_model = actual_model_id if actual_model_id else model
        
        try:
            response = self.client.embeddings.create(
                model=actual_model,
                input=[text]
            )
            embedding = response.data[0].embedding
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            error_detail = str(e)
            if "not found" in error_detail.lower() or "400" in error_detail:
                available_models = self.get_available_model_ids()
                logger.error(
                    f"Failed to embed single text with model '{model}': {error_detail}\n"
                    f"Available models: {', '.join(available_models[:10])}"
                )
            else:
                logger.error(f"Failed to embed single text: {error_detail}")
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
        
        # 检查模型是否存在
        exists, actual_model_id = self.check_model_exists(model)
        if not exists:
            available_models = self.get_available_model_ids()
            error_msg = (
                f"Model '{model}' not found in Xinference.\n"
                f"Available models ({len(available_models)}):\n"
            )
            for m in available_models:
                error_msg += f"  - {m}\n"
            logger.error(error_msg)
            return None
        
        # 使用实际模型ID
        actual_model = actual_model_id if actual_model_id else model
        
        try:
            # 分批处理
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                response = self.client.embeddings.create(
                    model=actual_model,
                    input=batch
                )
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return np.array(all_embeddings, dtype=np.float32)
        except Exception as e:
            error_detail = str(e)
            # 如果是模型未找到错误，提供更详细的信息
            if "not found" in error_detail.lower() or "400" in error_detail:
                available_models = self.get_available_model_ids()
                logger.error(
                    f"Failed to embed batch with model '{model}': {error_detail}\n"
                    f"Available models: {', '.join(available_models[:10])}"
                    + (f" (and {len(available_models) - 10} more)" if len(available_models) > 10 else "")
                )
            else:
                logger.error(f"Failed to embed batch: {error_detail}")
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
