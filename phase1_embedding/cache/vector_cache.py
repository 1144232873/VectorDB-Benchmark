"""
向量缓存管理 - 使用HDF5格式存储大规模向量
"""

import logging
import h5py
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any
from tqdm import tqdm

logger = logging.getLogger(__name__)


class VectorCache:
    """向量缓存管理器，使用HDF5格式"""
    
    def __init__(
        self,
        cache_file: str,
        mode: str = "r",
        compression: str = "gzip",
        compression_level: int = 4
    ):
        """
        初始化向量缓存
        
        Args:
            cache_file: HDF5文件路径
            mode: 文件打开模式 ('r', 'w', 'a')
            compression: 压缩算法 ('gzip', 'lzf', None)
            compression_level: 压缩级别 (0-9, 仅gzip)
        """
        self.cache_file = Path(cache_file)
        self.mode = mode
        self.compression = compression
        self.compression_level = compression_level if compression == "gzip" else None
        self.h5file: Optional[h5py.File] = None
        
        logger.info(f"Vector cache initialized: {self.cache_file}")
    
    def create(
        self,
        total_vectors: int,
        vector_dim: int,
        dtype: str = "float32",
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 10000
    ):
        """
        创建新的向量缓存文件
        
        Args:
            total_vectors: 总向量数
            vector_dim: 向量维度
            dtype: 数据类型
            metadata: 元数据
            chunk_size: HDF5 chunk大小
        """
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.h5file = h5py.File(self.cache_file, 'w')
        
        # 创建向量数据集
        self.h5file.create_dataset(
            "vectors",
            shape=(total_vectors, vector_dim),
            dtype=dtype,
            chunks=(chunk_size, vector_dim),
            compression=self.compression,
            compression_opts=self.compression_level
        )
        
        # 创建ID数据集
        self.h5file.create_dataset(
            "ids",
            shape=(total_vectors,),
            dtype="S64",  # 字符串ID，最长64字节
            compression=self.compression
        )
        
        # 保存元数据
        if metadata:
            for key, value in metadata.items():
                self.h5file.attrs[key] = value
        
        self.h5file.attrs["total_vectors"] = total_vectors
        self.h5file.attrs["vector_dim"] = vector_dim
        self.h5file.attrs["dtype"] = dtype
        
        logger.info(f"Created vector cache: {total_vectors} vectors, dim={vector_dim}")
    
    def open(self, mode: str = None):
        """
        打开现有的缓存文件
        
        Args:
            mode: 打开模式，None使用初始化时的模式
        """
        if mode:
            self.mode = mode
        
        self.h5file = h5py.File(self.cache_file, self.mode)
        logger.info(f"Opened vector cache: {self.cache_file} (mode: {self.mode})")
    
    def write_batch(
        self,
        vectors: np.ndarray,
        ids: List[str],
        start_idx: int = 0
    ):
        """
        批量写入向量
        
        Args:
            vectors: 向量数组，形状 (batch_size, vector_dim)
            ids: ID列表
            start_idx: 起始索引
        """
        if self.h5file is None:
            raise RuntimeError("Cache file not opened")
        
        batch_size = len(vectors)
        end_idx = start_idx + batch_size
        
        # 写入向量
        self.h5file["vectors"][start_idx:end_idx] = vectors
        
        # 写入ID（转换为字节）
        id_bytes = [id_str.encode('utf-8') for id_str in ids]
        self.h5file["ids"][start_idx:end_idx] = id_bytes
        
        # 确保写入磁盘
        self.h5file.flush()
    
    def write_vectors_iter(
        self,
        vectors_iter,
        ids_iter,
        total_vectors: int,
        batch_size: int = 10000,
        show_progress: bool = True
    ):
        """
        从迭代器写入向量（节省内存）
        
        Args:
            vectors_iter: 向量迭代器
            ids_iter: ID迭代器
            total_vectors: 总向量数
            batch_size: 批处理大小
            show_progress: 是否显示进度条
        """
        if self.h5file is None:
            raise RuntimeError("Cache file not opened")
        
        current_idx = 0
        vectors_batch = []
        ids_batch = []
        
        pbar = tqdm(total=total_vectors, disable=not show_progress, desc="Writing vectors")
        
        for vector, vec_id in zip(vectors_iter, ids_iter):
            vectors_batch.append(vector)
            ids_batch.append(vec_id)
            
            if len(vectors_batch) >= batch_size:
                # 写入批次
                self.write_batch(
                    np.array(vectors_batch),
                    ids_batch,
                    current_idx
                )
                current_idx += len(vectors_batch)
                pbar.update(len(vectors_batch))
                
                vectors_batch.clear()
                ids_batch.clear()
        
        # 写入剩余数据
        if vectors_batch:
            self.write_batch(
                np.array(vectors_batch),
                ids_batch,
                current_idx
            )
            pbar.update(len(vectors_batch))
        
        pbar.close()
        logger.info(f"Wrote {current_idx + len(vectors_batch)} vectors to cache")
    
    def read_vectors(
        self,
        start_idx: int = 0,
        end_idx: Optional[int] = None
    ) -> np.ndarray:
        """
        读取向量
        
        Args:
            start_idx: 起始索引
            end_idx: 结束索引（None表示读取到末尾）
            
        Returns:
            向量数组
        """
        if self.h5file is None:
            raise RuntimeError("Cache file not opened")
        
        if end_idx is None:
            return self.h5file["vectors"][start_idx:]
        else:
            return self.h5file["vectors"][start_idx:end_idx]
    
    def read_ids(
        self,
        start_idx: int = 0,
        end_idx: Optional[int] = None
    ) -> List[str]:
        """
        读取ID
        
        Args:
            start_idx: 起始索引
            end_idx: 结束索引
            
        Returns:
            ID列表
        """
        if self.h5file is None:
            raise RuntimeError("Cache file not opened")
        
        if end_idx is None:
            id_bytes = self.h5file["ids"][start_idx:]
        else:
            id_bytes = self.h5file["ids"][start_idx:end_idx]
        
        return [id_b.decode('utf-8') for id_b in id_bytes]
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取元数据
        
        Returns:
            元数据字典
        """
        if self.h5file is None:
            raise RuntimeError("Cache file not opened")
        
        return dict(self.h5file.attrs)
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取缓存信息
        
        Returns:
            信息字典
        """
        if self.h5file is None:
            self.open("r")
        
        metadata = self.get_metadata()
        file_size_mb = self.cache_file.stat().st_size / 1024**2
        
        info = {
            "file_path": str(self.cache_file),
            "file_size_mb": file_size_mb,
            "total_vectors": metadata.get("total_vectors", "unknown"),
            "vector_dim": metadata.get("vector_dim", "unknown"),
            "dtype": metadata.get("dtype", "unknown"),
            "metadata": metadata
        }
        
        return info
    
    def close(self):
        """关闭缓存文件"""
        if self.h5file is not None:
            self.h5file.close()
            self.h5file = None
            logger.info("Vector cache closed")
    
    def __enter__(self):
        """上下文管理器：进入"""
        if self.h5file is None:
            self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器：退出"""
        self.close()
    
    @staticmethod
    def estimate_size(
        total_vectors: int,
        vector_dim: int,
        dtype: str = "float32",
        compression_ratio: float = 0.7
    ) -> float:
        """
        估算缓存文件大小
        
        Args:
            total_vectors: 总向量数
            vector_dim: 向量维度
            dtype: 数据类型
            compression_ratio: 压缩比（压缩后/原始大小）
            
        Returns:
            估算大小（MB）
        """
        dtype_sizes = {
            "float32": 4,
            "float16": 2,
            "float64": 8
        }
        
        bytes_per_element = dtype_sizes.get(dtype, 4)
        raw_size_mb = (total_vectors * vector_dim * bytes_per_element) / 1024**2
        compressed_size_mb = raw_size_mb * compression_ratio
        
        return compressed_size_mb


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    test_file = "test_cache.h5"
    
    # 测试创建和写入
    print("Testing vector cache creation and write...")
    cache = VectorCache(test_file, mode="w")
    cache.create(total_vectors=1000, vector_dim=768)
    
    # 生成测试数据
    test_vectors = np.random.randn(1000, 768).astype(np.float32)
    test_ids = [f"doc_{i}" for i in range(1000)]
    
    # 批量写入
    cache.write_batch(test_vectors[:500], test_ids[:500], start_idx=0)
    cache.write_batch(test_vectors[500:], test_ids[500:], start_idx=500)
    cache.close()
    
    print("✓ Write completed")
    
    # 测试读取
    print("\nTesting vector cache read...")
    with VectorCache(test_file, mode="r") as cache:
        info = cache.get_info()
        print(f"✓ Cache info: {info['total_vectors']} vectors, {info['file_size_mb']:.2f} MB")
        
        # 读取部分向量
        vectors = cache.read_vectors(0, 10)
        ids = cache.read_ids(0, 10)
        print(f"✓ Read {len(vectors)} vectors")
        print(f"  First ID: {ids[0]}")
    
    # 清理
    Path(test_file).unlink()
    print("\n✓ Test completed")
