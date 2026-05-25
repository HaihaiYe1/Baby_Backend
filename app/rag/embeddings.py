from typing import List, Optional
import os


class EmbeddingManager:
    """嵌入向量管理器"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化嵌入管理器
        
        Args:
            model_name: 嵌入模型名称
        """
        self.model_name = model_name
        self.model = None
    
    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
                print(f"已加载嵌入模型: {self.model_name}")
            except ImportError:
                print("sentence-transformers未安装，使用默认嵌入函数")
                self.model = None
    
    def embed_text(self, text: str) -> List[float]:
        """
        将文本转换为向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        self._load_model()
        
        if self.model is None:
            # 返回空向量或抛出异常
            raise ValueError("嵌入模型未加载")
        
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        self._load_model()
        
        if self.model is None:
            raise ValueError("嵌入模型未加载")
        
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
    
    def get_embedding_dimension(self) -> int:
        """
        获取嵌入向量维度
        
        Returns:
            向量维度
        """
        self._load_model()
        
        if self.model is None:
            return 0
        
        return self.model.get_sentence_embedding_dimension()
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数 (0-1)
        """
        import numpy as np
        
        embedding1 = self.embed_text(text1)
        embedding2 = self.embed_text(text2)
        
        # 计算余弦相似度
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


# 全局嵌入管理器实例
embedding_manager = EmbeddingManager()
