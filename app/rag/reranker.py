from typing import List, Tuple, Dict, Any, Optional
from app.config import settings


class CrossEncoderReranker:
    """
    Cross-Encoder重排序器
    
    使用Cross-Encoder模型对检索结果进行重排序
    """
    
    def __init__(self, model_name: str = None):
        """
        初始化重排序器
        
        Args:
            model_name: Cross-Encoder模型名称
        """
        self.model_name = model_name or settings.RAG_RERANKER_MODEL
        self.model = None
        self._initialized = False
    
    def _initialize(self) -> None:
        """延迟初始化模型"""
        if self._initialized:
            return
        
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            self._initialized = True
        except ImportError:
            print("sentence-transformers not installed, reranker disabled")
        except Exception as e:
            print(f"Failed to initialize reranker: {e}")
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = None
    ) -> List[Tuple[int, float]]:
        """
        重排序文档
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回前k个结果
            
        Returns:
            (文档索引, 分数) 列表
        """
        top_k = top_k or settings.RAG_RERANK_TOP_K
        
        self._initialize()
        
        if not self.model or not documents:
            # 如果模型未初始化或无文档，返回原始顺序
            return [(i, 1.0) for i in range(min(top_k, len(documents)))]
        
        try:
            # 构建查询-文档对
            pairs = [(query, doc) for doc in documents]
            
            # 计算相关性分数
            scores = self.model.predict(pairs)
            
            # 按分数排序
            ranked = sorted(
                enumerate(scores),
                key=lambda x: x[1],
                reverse=True
            )
            
            return ranked[:top_k]
            
        except Exception as e:
            print(f"Reranking error: {e}")
            return [(i, 1.0) for i in range(min(top_k, len(documents)))]
    
    async def arerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = None
    ) -> List[Tuple[int, float]]:
        """
        异步重排序（目前使用同步实现）
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回前k个结果
            
        Returns:
            (文档索引, 分数) 列表
        """
        return self.rerank(query, documents, top_k)
    
    def rerank_with_details(
        self,
        query: str,
        documents: List[str],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        重排序文档（带详细信息）
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回前k个结果
            
        Returns:
            包含文档内容和分数的结果列表
        """
        results = self.rerank(query, documents, top_k)
        
        detailed_results = []
        for idx, score in results:
            detailed_results.append({
                "index": idx,
                "document": documents[idx],
                "score": float(score)
            })
        
        return detailed_results


class SimpleReranker:
    """
    简单重排序器（不依赖外部模型）
    
    使用文本匹配特征进行重排序
    """
    
    def __init__(self):
        pass
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        简单重排序
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回前k个结果
            
        Returns:
            (文档索引, 分数) 列表
        """
        if not documents:
            return []
        
        query_lower = query.lower()
        query_tokens = set(query_lower.split())
        
        scores = []
        for idx, doc in enumerate(documents):
            doc_lower = doc.lower()
            doc_tokens = set(doc_lower.split())
            
            # 计算多种匹配特征
            score = 0.0
            
            # 1. 查询词覆盖率
            if query_tokens:
                coverage = len(query_tokens & doc_tokens) / len(query_tokens)
                score += coverage * 0.4
            
            # 2. 查询作为子串出现
            if query_lower in doc_lower:
                score += 0.3
            
            # 3. 文档长度惩罚（避免过长文档）
            length_penalty = min(1.0, 100 / max(len(doc), 1))
            score += length_penalty * 0.1
            
            # 4. 关键词密度
            if doc_tokens:
                keyword_density = len(query_tokens & doc_tokens) / len(doc_tokens)
                score += keyword_density * 0.2
            
            scores.append((idx, score))
        
        # 按分数排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]


# 全局重排序器实例
reranker: Optional[CrossEncoderReranker] = None


def get_reranker() -> CrossEncoderReranker:
    """获取重排序器实例"""
    global reranker
    if reranker is None:
        reranker = CrossEncoderReranker()
    return reranker


def get_simple_reranker() -> SimpleReranker:
    """获取简单重排序器实例"""
    return SimpleReranker()
