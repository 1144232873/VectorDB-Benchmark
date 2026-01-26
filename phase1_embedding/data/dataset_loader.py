"""
数据集加载器 - 通用TSV格式数据集加载
"""

import logging
import random
from pathlib import Path
from typing import List, Dict, Iterator
from tqdm import tqdm

logger = logging.getLogger(__name__)


class DatasetLoader:
    """通用数据集加载器（TSV格式）"""
    
    def __init__(self, data_dir: str = "data/dataset"):
        """
        初始化加载器
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.collection_file = self.data_dir / "collection.tsv"
        logger.info(f"Dataset loader initialized: {self.data_dir}")
    
    def check_dataset(self) -> bool:
        """检查数据集是否存在"""
        if self.collection_file.exists():
            logger.info(f"Dataset found: {self.collection_file}")
            return True
        else:
            logger.error(f"Dataset not found: {self.collection_file}")
            logger.error("Please generate dataset first:")
            logger.error("  cd datasets/scripts && ./quick_start.sh 100000")
            logger.error("Or rename existing file:")
            logger.error(f"  mv {self.data_dir}/quick-test.tsv {self.collection_file}")
            return False
    
    def load_collection_iter(
        self,
        min_length: int = 10,
        max_length: int = 512
    ) -> Iterator[Dict[str, str]]:
        """
        迭代器方式加载数据集（节省内存）
        
        Args:
            min_length: 最小文本长度
            max_length: 最大文本长度
            
        Yields:
            文档字典 {id, text}
        """
        if not self.collection_file.exists():
            # 检查是否有旧的临时文件
            quick_test_file = self.data_dir / "quick-test.tsv"
            if quick_test_file.exists():
                raise FileNotFoundError(
                    f"Dataset file not found: {self.collection_file}\n"
                    f"Found old temporary file: {quick_test_file}\n"
                    f"Please rename it: mv {quick_test_file} {self.collection_file}"
                )
            else:
                raise FileNotFoundError(
                    f"Dataset file not found: {self.collection_file}\n"
                    f"Please generate dataset: cd datasets/scripts && ./quick_start.sh 100000"
                )
        
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
    
    def load_collection(
        self,
        max_samples: int = None,
        min_length: int = 10,
        max_length: int = 512,
        seed: int = 42
    ) -> List[Dict[str, str]]:
        """
        加载数据集
        
        Args:
            max_samples: 最大样本数（None表示加载全部）
            min_length: 最小文本长度
            max_length: 最大文本长度
            seed: 随机种子
            
        Returns:
            文档列表
        """
        logger.info(f"Loading dataset from {self.collection_file}")
        
        documents = []
        for doc in tqdm(self.load_collection_iter(min_length, max_length), desc="Loading dataset"):
            documents.append(doc)
            
            if max_samples and len(documents) >= max_samples:
                break
        
        # 打乱顺序
        if max_samples and len(documents) > max_samples:
            random.seed(seed)
            random.shuffle(documents)
            documents = documents[:max_samples]
        
        logger.info(f"Loaded {len(documents)} documents")
        return documents
    
    def sample_documents(
        self,
        num_samples: int = 3000000,
        seed: int = 42
    ) -> List[Dict[str, str]]:
        """
        采样指定数量的文档
        
        Args:
            num_samples: 采样数量
            seed: 随机种子
            
        Returns:
            采样后的文档列表
        """
        logger.info(f"Sampling {num_samples} documents")
        
        # 统计总文档数
        total_docs = sum(1 for _ in self.load_collection_iter())
        logger.info(f"Total documents in dataset: {total_docs:,}")
        
        if num_samples >= total_docs:
            # 样本数大于总数，加载全部
            logger.info(f"Using all {total_docs:,} documents")
            return self.load_collection()
        
        # 使用 reservoir sampling 进行采样
        logger.info(f"Sampling {num_samples:,} from {total_docs:,} documents")
        random.seed(seed)
        sampled = []
        
        for i, doc in enumerate(tqdm(self.load_collection_iter(), total=total_docs, desc="Sampling")):
            if len(sampled) < num_samples:
                sampled.append(doc)
            else:
                # Reservoir sampling
                j = random.randint(0, i)
                if j < num_samples:
                    sampled[j] = doc
        
        logger.info(f"Sampled {len(sampled):,} documents")
        return sampled


if __name__ == "__main__":
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    loader = DatasetLoader()
    
    if loader.check_dataset():
        print("✓ Dataset exists")
        
        # 加载少量样本测试
        print("\nLoading 10 sample documents...")
        docs = loader.load_collection(max_samples=10)
        print(f"✓ Loaded {len(docs)} documents")
        
        if docs:
            print(f"\nFirst document:")
            print(f"  ID: {docs[0]['id']}")
            print(f"  Text: {docs[0]['text'][:100]}...")
    else:
        print("✗ Dataset not found")
        print("Run: cd datasets/scripts && ./quick_start.sh 100000")
