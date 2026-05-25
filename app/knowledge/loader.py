import os
from typing import List, Optional
from pathlib import Path


class DocumentLoader:
    """文档加载器"""
    
    def __init__(self):
        """初始化文档加载器"""
        self.supported_extensions = {
            '.txt': self._load_text,
            '.pdf': self._load_pdf,
            '.docx': self._load_docx,
            '.md': self._load_markdown
        }
    
    def load(self, file_path: str) -> str:
        """
        加载文档
        
        Args:
            file_path: 文件路径
            
        Returns:
            文档内容
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        extension = path.suffix.lower()
        
        if extension not in self.supported_extensions:
            raise ValueError(f"不支持的文件格式: {extension}")
        
        loader_func = self.supported_extensions[extension]
        return loader_func(file_path)
    
    def load_and_split(
        self,
        file_path: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        加载并分割文档
        
        Args:
            file_path: 文件路径
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            
        Returns:
            文档分块列表
        """
        content = self.load(file_path)
        return self._split_text(content, chunk_size, chunk_overlap)
    
    def _load_text(self, file_path: str) -> str:
        """加载文本文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _load_pdf(self, file_path: str) -> str:
        """加载PDF文件"""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text_parts = []
                
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                
                return '\n\n'.join(text_parts)
                
        except ImportError:
            raise ImportError("请安装PyPDF2: pip install pypdf2")
    
    def _load_docx(self, file_path: str) -> str:
        """加载Word文档"""
        try:
            from docx import Document
            
            doc = Document(file_path)
            paragraphs = []
            
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            
            return '\n\n'.join(paragraphs)
            
        except ImportError:
            raise ImportError("请安装python-docx: pip install python-docx")
    
    def _load_markdown(self, file_path: str) -> str:
        """加载Markdown文件"""
        # Markdown本质上是文本文件
        return self._load_text(file_path)
    
    def _split_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        分割文本
        
        Args:
            text: 文本内容
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            
        Returns:
            文本分块列表
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # 如果不是最后一块，尝试在句子边界分割
            if end < len(text):
                # 查找最近的句子结束符
                for i in range(end, max(start + chunk_size // 2, end - 100), -1):
                    if text[i] in '。！？.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 移动起始位置
            start = end - chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def load_directory(
        self,
        directory_path: str,
        recursive: bool = True
    ) -> List[str]:
        """
        加载目录中的所有文档
        
        Args:
            directory_path: 目录路径
            recursive: 是否递归加载
            
        Returns:
            文档内容列表
        """
        path = Path(directory_path)
        
        if not path.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        documents = []
        
        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'
        
        for file_path in path.glob(pattern):
            if file_path.is_file():
                extension = file_path.suffix.lower()
                if extension in self.supported_extensions:
                    try:
                        content = self.load(str(file_path))
                        documents.append(content)
                    except Exception as e:
                        print(f"加载文件 {file_path} 失败: {e}")
        
        return documents
    
    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的文件扩展名
        
        Returns:
            支持的扩展名列表
        """
        return list(self.supported_extensions.keys())


# 全局文档加载器实例
document_loader = DocumentLoader()
