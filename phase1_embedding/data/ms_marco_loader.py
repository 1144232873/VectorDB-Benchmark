"""
MS MARCO数据集下载和加载
"""

import os
import logging
import requests
import tarfile
import gzip
from pathlib import Path
from typing import List, Dict, Optional, Iterator
from tqdm import tqdm
import random
import json

logger = logging.getLogger(__name__)


class MSMARCOLoader:
    """MS MARCO数据集加载器"""
    
    # 官方下载链接
    COLLECTION_URL = "https://msmarco.blob.core.windows.net/msmarcoranking/collection.tar.gz"
    QUERIES_URL = "https://msmarco.blob.core.windows.net/msmarcoranking/queries.tar.gz"
    
    # 备用链接（Hugging Face）
    HF_COLLECTION_URL = "https://huggingface.co/datasets/microsoft/ms_marco/resolve/main/collection.tsv"
    
    def __init__(self, data_dir: str = "data/ms_marco"):
        """
        初始化加载器
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.collection_file = self.data_dir / "collection.tsv"
        self.queries_file = self.data_dir / "queries.dev.small.tsv"
        
        logger.info(f"MS MARCO loader initialized: {self.data_dir}")
    
    def download_file(self, url: str, output_path: Path, chunk_size: int = 8192) -> bool:
        """
        下载文件并显示进度
        
        Args:
            url: 下载URL
            output_path: 输出文件路径
            chunk_size: 下载块大小
            
        Returns:
            是否下载成功
        """
        try:
            logger.info(f"Downloading from {url}")
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f, tqdm(
                total=total_size,
                unit='iB',
                unit_scale=True,
                desc=output_path.name
            ) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            logger.info(f"Downloaded successfully: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False
    
    def extract_tar_gz(self, tar_path: Path, extract_to: Path) -> bool:
        """
        解压tar.gz文件
        
        Args:
            tar_path: tar.gz文件路径
            extract_to: 解压目标目录
            
        Returns:
            是否解压成功
        """
        try:
            logger.info(f"Extracting {tar_path}")
            with tarfile.open(tar_path, 'r:gz') as tar:
                tar.extractall(path=extract_to)
            logger.info(f"Extracted successfully to {extract_to}")
            return True
        except Exception as e:
            logger.error(f"Failed to extract {tar_path}: {e}")
            return False
    
    def download_collection(self, force: bool = False) -> bool:
        """
        下载collection数据集
        
        Args:
            force: 是否强制重新下载
            
        Returns:
            是否下载成功
        """
        if self.collection_file.exists() and not force:
            logger.info(f"Collection file already exists: {self.collection_file}")
            return True
        
        # 尝试下载官方链接
        tar_file = self.data_dir / "collection.tar.gz"
        if self.download_file(self.COLLECTION_URL, tar_file):
            if self.extract_tar_gz(tar_file, self.data_dir):
                tar_file.unlink()  # 删除压缩文件
                return True
        
        # 尝试备用链接
        logger.info("Trying alternative download source (Hugging Face)")
        return self.download_file(self.HF_COLLECTION_URL, self.collection_file)
    
    def download_queries(self, force: bool = False) -> bool:
        """
        下载queries数据集
        
        Args:
            force: 是否强制重新下载
            
        Returns:
            是否下载成功
        """
        if self.queries_file.exists() and not force:
            logger.info(f"Queries file already exists: {self.queries_file}")
            return True
        
        tar_file = self.data_dir / "queries.tar.gz"
        if self.download_file(self.QUERIES_URL, tar_file):
            if self.extract_tar_gz(tar_file, self.data_dir):
                tar_file.unlink()
                return True
        
        return False
    
    def load_collection(
        self,
        max_samples: Optional[int] = None,
        min_length: int = 10,
        max_length: int = 512,
        seed: int = 42
    ) -> List[Dict[str, str]]:
        """
        加载collection数据集
        
        Args:
            max_samples: 最大样本数（None表示加载全部）
            min_length: 最小文本长度
            max_length: 最大文本长度
            seed: 随机种子
            
        Returns:
            文档列表，每个文档包含 {id, text}
        """
        if not self.collection_file.exists():
            raise FileNotFoundError(f"Collection file not found: {self.collection_file}")
        
        logger.info(f"Loading collection from {self.collection_file}")
        
        documents = []
        with open(self.collection_file, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc="Loading collection"):
                parts = line.strip().split('\t')
                if len(parts) != 2:
                    continue
                
                doc_id, text = parts
                text_len = len(text)
                
                # 过滤太短或太长的文本
                if text_len < min_length or text_len > max_length:
                    continue
                
                documents.append({
                    "id": doc_id,
                    "text": text
                })
                
                # 如果达到max_samples，停止加载
                if max_samples and len(documents) >= max_samples:
                    break
        
        # 如果需要采样，进行随机打乱
        if max_samples and len(documents) > max_samples:
            random.seed(seed)
            random.shuffle(documents)
            documents = documents[:max_samples]
        
        logger.info(f"Loaded {len(documents)} documents")
        return documents
    
    def load_collection_iter(
        self,
        min_length: int = 10,
        max_length: int = 512
    ) -> Iterator[Dict[str, str]]:
        """
        迭代器方式加载collection（节省内存）
        
        Args:
            min_length: 最小文本长度
            max_length: 最大文本长度
            
        Yields:
            文档字典 {id, text}
        """
        if not self.collection_file.exists():
            raise FileNotFoundError(f"Collection file not found: {self.collection_file}")
        
        with open(self.collection_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) != 2:
                    continue
                
                doc_id, text = parts
                text_len = len(text)
                
                if min_length <= text_len <= max_length:
                    yield {
                        "id": doc_id,
                        "text": text
                    }
    
    def sample_documents(
        self,
        num_samples: int = 3000000,
        seed: int = 42
    ) -> List[Dict[str, str]]:
        """
        采样指定数量的文档（适用于大规模测试）
        
        Args:
            num_samples: 采样数量
            seed: 随机种子
            
        Returns:
            采样后的文档列表
        """
        logger.info(f"Sampling {num_samples} documents")
        
        # 首先统计总文档数
        total_docs = sum(1 for _ in self.load_collection_iter())
        logger.info(f"Total documents in collection: {total_docs}")
        
        if num_samples >= total_docs:
            # 如果需要的样本数大于总数，直接加载全部
            return self.load_collection()
        
        # 使用reservoir sampling进行采样
        random.seed(seed)
        sampled = []
        
        for i, doc in enumerate(self.load_collection_iter()):
            if len(sampled) < num_samples:
                sampled.append(doc)
            else:
                # Reservoir sampling
                j = random.randint(0, i)
                if j < num_samples:
                    sampled[j] = doc
        
        logger.info(f"Sampled {len(sampled)} documents")
        return sampled
    
    def prepare_dataset(
        self,
        num_samples: int = 3000000,
        output_file: Optional[str] = None,
        force: bool = False
    ) -> List[Dict[str, str]]:
        """
        准备完整的测试数据集
        
        Args:
            num_samples: 样本数量
            output_file: 输出文件（可选，用于缓存）
            force: 是否强制重新生成
            
        Returns:
            文档列表
        """
        # 检查是否有缓存
        if output_file and Path(output_file).exists() and not force:
            logger.info(f"Loading cached dataset from {output_file}")
            with open(output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 下载数据集
        if not self.download_collection():
            raise RuntimeError("Failed to download collection")
        
        # 采样文档
        documents = self.sample_documents(num_samples)
        
        # 保存缓存
        if output_file:
            logger.info(f"Saving dataset to {output_file}")
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
        
        return documents


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    loader = MSMARCOLoader()
    
    # 下载数据集
    print("Downloading MS MARCO collection...")
    if loader.download_collection():
        print("✓ Collection downloaded successfully")
        
        # 加载少量样本测试
        print("\nLoading 1000 sample documents...")
        docs = loader.load_collection(max_samples=1000)
        print(f"✓ Loaded {len(docs)} documents")
        
        if docs:
            print(f"\nFirst document:")
            print(f"  ID: {docs[0]['id']}")
            print(f"  Text: {docs[0]['text'][:100]}...")
    else:
        print("✗ Failed to download collection")
