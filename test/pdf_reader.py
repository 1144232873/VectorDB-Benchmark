"""
PDF文本提取模块
支持批量处理PDF文件，提取文本并进行分块处理
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
import pdfplumber

logger = logging.getLogger(__name__)


class PDFReader:
    """PDF文本提取器"""
    
    def __init__(
        self,
        chunk_size: int = 512,
        min_length: int = 10,
        max_length: int = 512,
        overlap: int = 50
    ):
        """
        初始化PDF读取器
        
        Args:
            chunk_size: 文本分块大小（字符数）
            min_length: 最小文本长度
            max_length: 最大文本长度
            overlap: 分块重叠字符数
        """
        self.chunk_size = chunk_size
        self.min_length = min_length
        self.max_length = max_length
        self.overlap = overlap
    
    def clean_text(self, text: str) -> str:
        """
        清理文本
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 去除特殊字符（保留中文、英文、数字、基本标点）
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？；：、""''（）【】《》]', '', text)
        return text.strip()
    
    def chunk_text(self, text: str) -> List[str]:
        """
        将文本分块
        
        Args:
            text: 原始文本
            
        Returns:
            文本块列表
        """
        chunks = []
        
        # 先按段落分割
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果当前块加上新段落不超过最大长度，则合并
            if len(current_chunk) + len(para) + 1 <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n" + para
                else:
                    current_chunk = para
            else:
                # 保存当前块
                if current_chunk and len(current_chunk) >= self.min_length:
                    chunks.append(current_chunk[:self.max_length])
                
                # 如果段落本身就很长，需要进一步分割
                if len(para) > self.chunk_size:
                    # 按句子分割
                    sentences = re.split(r'[。！？\n]', para)
                    current_chunk = ""
                    for sent in sentences:
                        sent = sent.strip()
                        if not sent:
                            continue
                        
                        if len(current_chunk) + len(sent) + 1 <= self.chunk_size:
                            if current_chunk:
                                current_chunk += " " + sent
                            else:
                                current_chunk = sent
                        else:
                            if current_chunk and len(current_chunk) >= self.min_length:
                                chunks.append(current_chunk[:self.max_length])
                            current_chunk = sent
                else:
                    current_chunk = para
        
        # 添加最后一个块
        if current_chunk and len(current_chunk) >= self.min_length:
            chunks.append(current_chunk[:self.max_length])
        
        return chunks
    
    def extract_text_from_pdf(self, pdf_path: Path) -> List[str]:
        """
        从单个PDF文件提取文本
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            文本块列表
        """
        chunks = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n\n"
                
                # 清理文本
                full_text = self.clean_text(full_text)
                
                # 分块
                if full_text:
                    chunks = self.chunk_text(full_text)
                
                logger.info(f"Extracted {len(chunks)} chunks from {pdf_path.name}")
                
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
        
        return chunks
    
    def extract_from_directory(
        self,
        directory: Path,
        pattern: str = "*.pdf"
    ) -> List[Dict[str, any]]:
        """
        从目录中批量提取PDF文本
        
        Args:
            directory: PDF目录路径
            pattern: 文件匹配模式
            
        Returns:
            文档列表，每个文档包含 {id, text, source_file, chunk_id}
        """
        pdf_dir = Path(directory)
        if not pdf_dir.exists():
            logger.error(f"Directory not found: {pdf_dir}")
            return []
        
        documents = []
        pdf_files = list(pdf_dir.glob(pattern))
        pdf_files.extend(pdf_dir.glob(pattern.upper()))  # 也匹配大写扩展名
        
        logger.info(f"Found {len(pdf_files)} PDF files in {pdf_dir}")
        
        for pdf_file in pdf_files:
            chunks = self.extract_text_from_pdf(pdf_file)
            
            for chunk_id, chunk_text in enumerate(chunks, 1):
                doc_id = f"{pdf_file.stem}_chunk_{chunk_id}"
                documents.append({
                    "id": doc_id,
                    "text": chunk_text,
                    "source_file": pdf_file.name,
                    "chunk_id": chunk_id
                })
        
        logger.info(f"Total extracted {len(documents)} text chunks from {len(pdf_files)} PDFs")
        return documents


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    reader = PDFReader(chunk_size=512, min_length=10, max_length=512)
    
    # 测试提取
    test_dir = Path("向量测试文档")
    if test_dir.exists():
        docs = reader.extract_from_directory(test_dir)
        print(f"\n提取了 {len(docs)} 个文本块")
        if docs:
            print(f"\n第一个文本块示例：\n{docs[0]['text'][:200]}...")
    else:
        print(f"测试目录不存在: {test_dir}")
