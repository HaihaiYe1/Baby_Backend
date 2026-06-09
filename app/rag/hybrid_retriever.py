from typing import List, Dict, Any, Optional, Tuple
from .bm25_retriever import BM25Retriever
from app.config import settings


class HybridRetriever:
    """
    混合检索器
    
    结合稠密向量检索和BM25稀疏检索，使用RRF (Reciprocal Rank Fusion) 融合结果
    """
    
    def __init__(
        self,
        dense_retriever: Any = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        k: int = None
    ):
        """
        初始化混合检索器
        
        Args:
            dense_retriever: 稠密向量检索器
            bm25_retriever: BM25稀疏检索器
            k: RRF常数（默认从配置读取）
        """
        self.dense = dense_retriever
        self.bm25 = bm25_retriever or BM25Retriever()
        self.k = k or settings.RAG_RRF_K
    
    def _rrf_fusion(
        self,
        dense_results: List[Tuple[int, float]],
        bm25_results: List[Tuple[int, float]],
        top_k: int = 10
    ) -> List[int]:
        """
        RRF (Reciprocal Rank Fusion) 融合算法
        
        Args:
            dense_results: 稠密检索结果 (index, score)
            bm25_results: BM25检索结果 (index, score)
            top_k: 返回前k个结果
            
        Returns:
            融合后的文档索引列表
        """
        scores: Dict[int, float] = {}
        
        # 处理稠密检索结果
        for rank, (idx, _) in enumerate(dense_results):
            scores[idx] = scores.get(idx, 0) + 1 / (self.k + rank + 1)
        
        # 处理BM25检索结果
        for rank, (idx, _) in enumerate(bm25_results):
            scores[idx] = scores.get(idx, 0) + 1 / (self.k + rank + 1)
        
        # 按融合分数排序
        sorted_indices = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        return sorted_indices[:top_k]
    
    async def retrieve(
        self,
        query: str,
        top_k: int = None,
        use_dense: bool = True,
        use_bm25: bool = True
    ) -> List[Dict[str, Any]]:
        """
        混合检索
        
        Args:
            query: 查询文本
            top_k: 返回前k个结果
            use_dense: 是否使用稠密检索
            use_bm25: 是否使用BM25检索
            
        Returns:
            检索结果列表
        """
        top_k = top_k or settings.RAG_TOP_K
        
        dense_results = []
        bm25_results = []
        
        # 稠密向量检索
        if use_dense and self.dense:
            try:
                if hasattr(self.dense, 'aretrieve'):
                    dense_results = await self.dense.aretrieve(query, top_k * 2)
                else:
                    dense_results = self.dense.retrieve(query, top_k * 2)
            except Exception as e:
                print(f"Dense retrieval error: {e}")
        
        # BM25稀疏检索
        if use_bm25 and self.bm25:
            try:
                bm25_results = self.bm25.retrieve(query, top_k * 2)
            except Exception as e:
                print(f"BM25 retrieval error: {e}")
        
        # 如果只有一种检索方式可用
        if not dense_results:
            results = [(idx, score) for idx, score in bm25_results[:top_k]]
        elif not bm25_results:
            results = [(idx, score) for idx, score in dense_results[:top_k]]
        else:
            # RRF融合
            fused_indices = self._rrf_fusion(dense_results, bm25_results, top_k)
            
            # 构建结果，保留原始分数
            dense_dict = dict(dense_results)
            bm25_dict = dict(bm25_results)
            
            results = []
            for idx in fused_indices:
                dense_score = dense_dict.get(idx, 0)
                bm25_score = bm25_dict.get(idx, 0)
                results.append((idx, max(dense_score, bm25_score)))
        
        # 构建详细结果
        detailed_results = []
        for idx, score in results:
            detailed_results.append({
                "index": idx,
                "score": score,
                "source": self._get_source(idx, dense_results, bm25_results)
            })
        
        return detailed_results
    
    def _get_source(
        self,
        idx: int,
        dense_results: List[Tuple[int, float]],
        bm25_results: List[Tuple[int, float]]
    ) -> str:
        """判断结果来源"""
        in_dense = any(i == idx for i, _ in dense_results)
        in_bm25 = any(i == idx for i, _ in bm25_results)
        
        if in_dense and in_bm25:
            return "both"
        elif in_dense:
            return "dense"
        else:
            return "bm25"
    
    def update_documents(self, documents: List[str]) -> None:
        """更新文档库"""
        if self.bm25:
            self.bm25.add_documents(documents)
        # 稠密检索器的更新需要根据具体实现


# 全局混合检索器实例
hybrid_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever() -> HybridRetriever:
    """获取混合检索器实例"""
    global hybrid_retriever
    if hybrid_retriever is None:
        from .bm25_retriever import get_bm25_retriever
        hybrid_retriever = HybridRetriever(bm25_retriever=get_bm25_retriever())
    return hybrid_retriever


def initialize_hybrid_retriever(
    dense_retriever: Any = None,
    documents: List[str] = None
) -> HybridRetriever:
    """初始化混合检索器"""
    global hybrid_retriever
    
    from .bm25_retriever import BM25Retriever
    bm25 = BM25Retriever(documents) if documents else BM25Retriever()
    
    hybrid_retriever = HybridRetriever(
        dense_retriever=dense_retriever,
        bm25_retriever=bm25
    )
    return hybrid_retriever
