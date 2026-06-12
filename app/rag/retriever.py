from typing import List, Dict, Any, Optional
from app.rag.knowledge_base import knowledge_base
from app.config import settings


class RAGRetriever:
    """RAG检索器（支持混合检索）"""
    
    def __init__(
        self,
        knowledge_base_instance=None,
        use_hybrid: bool = None,
        use_reranker: bool = None
    ):
        """
        初始化检索器
        
        Args:
            knowledge_base_instance: 知识库实例
            use_hybrid: 是否使用混合检索
            use_reranker: 是否使用重排序
        """
        self.kb = knowledge_base_instance or knowledge_base
        self.use_hybrid = use_hybrid if use_hybrid is not None else settings.RAG_USE_BM25
        self.use_reranker = use_reranker if use_reranker is not None else settings.RAG_USE_RERANKER
        
        # 延迟初始化组件
        self._hybrid_retriever = None
        self._reranker = None
        self._query_optimizer = None
    
    @property
    def hybrid_retriever(self):
        """获取混合检索器"""
        if self._hybrid_retriever is None and self.use_hybrid:
            from .hybrid_retriever import get_hybrid_retriever
            self._hybrid_retriever = get_hybrid_retriever()
        return self._hybrid_retriever
    
    @property
    def reranker(self):
        """获取重排序器"""
        if self._reranker is None and self.use_reranker:
            from .reranker import get_reranker
            self._reranker = get_reranker()
        return self._reranker
    
    @property
    def query_optimizer(self):
        """获取查询优化器"""
        if self._query_optimizer is None:
            from .query_optimizer import get_query_optimizer
            self._query_optimizer = get_query_optimizer()
        return self._query_optimizer
    
    async def retrieve(
        self,
        query: str,
        top_k: int = None,
        category: Optional[str] = None,
        use_hybrid: Optional[bool] = None,
        use_reranker: Optional[bool] = None,
        optimize_query: bool = False
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            category: 知识类别过滤
            use_hybrid: 是否使用混合检索
            use_reranker: 是否使用重排序
            optimize_query: 是否优化查询
            
        Returns:
            检索结果列表
        """
        top_k = top_k or settings.RAG_TOP_K
        use_hybrid = use_hybrid if use_hybrid is not None else self.use_hybrid
        use_reranker = use_reranker if use_reranker is not None else self.use_reranker
        
        # 查询优化
        original_query = query
        if optimize_query:
            try:
                query = await self.query_optimizer.rewrite_query(query)
            except Exception as e:
                print(f"Query optimization error: {e}")
        
        # 混合检索
        if use_hybrid and self.hybrid_retriever:
            results = await self._hybrid_retrieve(query, top_k * 2 if use_reranker else top_k, category)
        else:
            results = await self._dense_retrieve(query, top_k * 2 if use_reranker else top_k, category)
        
        # 重排序
        if use_reranker and self.reranker and len(results) > top_k:
            results = await self._rerank_results(original_query, results, top_k)
        
        return results[:top_k]
    
    async def _dense_retrieve(
        self,
        query: str,
        top_k: int,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """稠密向量检索"""
        if category:
            results = self.kb.search_by_category(category, query, top_k)
        else:
            results = self.kb.query(query, top_k)
        
        # 格式化结果
        formatted_results = []
        for i in range(len(results["documents"])):
            formatted_results.append({
                "content": results["documents"][i],
                "metadata": results["metadatas"][i],
                "score": 1 - results["distances"][i] if results["distances"] else 0,
                "id": results["ids"][i],
                "source": "dense"
            })
        
        return formatted_results
    
    async def _hybrid_retrieve(
        self,
        query: str,
        top_k: int,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """混合检索"""
        # 获取稠密检索结果
        dense_results = await self._dense_retrieve(query, top_k, category)
        
        # 如果混合检索器可用，使用RRF融合
        if self.hybrid_retriever:
            try:
                # 提取文档内容用于BM25检索
                documents = [r["content"] for r in dense_results]
                
                # 更新BM25索引
                if self.hybrid_retriever.bm25:
                    self.hybrid_retriever.bm25.add_documents(documents)
                
                # 执行混合检索
                hybrid_results = await self.hybrid_retriever.retrieve(query, top_k)
                
                # 转换结果格式
                formatted_results = []
                for result in hybrid_results:
                    idx = result["index"]
                    if idx < len(dense_results):
                        formatted_results.append({
                            **dense_results[idx],
                            "score": result["score"],
                            "source": result.get("source", "hybrid")
                        })
                
                return formatted_results
                
            except Exception as e:
                print(f"Hybrid retrieval error: {e}")
                return dense_results
        
        return dense_results
    
    async def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """重排序结果"""
        if not self.reranker or not results:
            return results
        
        try:
            # 提取文档内容
            documents = [r["content"] for r in results]
            
            # 执行重排序
            reranked = self.reranker.rerank_with_details(query, documents, top_k)
            
            # 转换结果格式
            formatted_results = []
            for item in reranked:
                idx = item["index"]
                if idx < len(results):
                    formatted_results.append({
                        **results[idx],
                        "rerank_score": item["score"]
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"Reranking error: {e}")
            return results
    
    def retrieve(
        self,
        query: str,
        n_results: int = 3,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            category: 知识类别过滤
            
        Returns:
            检索结果列表
        """
        if category:
            results = self.kb.search_by_category(category, query, n_results)
        else:
            results = self.kb.query(query, n_results)
        
        # 格式化结果
        formatted_results = []
        for i in range(len(results["documents"])):
            formatted_results.append({
                "content": results["documents"][i],
                "metadata": results["metadatas"][i],
                "score": 1 - results["distances"][i] if results["distances"] else 0,
                "id": results["ids"][i]
            })
        
        return formatted_results
    
    def retrieve_with_context(
        self,
        query: str,
        context: str,
        n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        结合上下文检索
        
        Args:
            query: 查询文本
            context: 上下文信息
            n_results: 返回结果数量
            
        Returns:
            检索结果
        """
        # 组合查询和上下文
        combined_query = f"{context} {query}"
        return self.retrieve(combined_query, n_results)
    
    def retrieve_for_situation(
        self,
        situation: str,
        baby_age_months: Optional[int] = None,
        n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        针对特定情况检索
        
        Args:
            situation: 情况描述
            baby_age_months: 婴儿月龄
            n_results: 返回结果数量
            
        Returns:
            检索结果
        """
        # 构建查询
        query_parts = [situation]
        
        if baby_age_months is not None:
            age_context = self._get_age_context(baby_age_months)
            query_parts.append(age_context)
        
        query = " ".join(query_parts)
        return self.retrieve(query, n_results)
    
    def _get_age_context(self, age_months: int) -> str:
        """
        根据月龄获取上下文
        
        Args:
            age_months: 月龄
            
        Returns:
            年龄上下文描述
        """
        if age_months <= 3:
            return "新生儿0-3个月"
        elif age_months <= 6:
            return "婴儿4-6个月"
        elif age_months <= 9:
            return "婴儿7-9个月"
        elif age_months <= 12:
            return "婴儿10-12个月"
        elif age_months <= 18:
            return "幼儿13-18个月"
        elif age_months <= 24:
            return "幼儿19-24个月"
        else:
            return f"{age_months}个月大的婴儿"
    
    def retrieve_by_category(
        self,
        category: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        按类别检索
        
        Args:
            category: 知识类别
            n_results: 返回结果数量
            
        Returns:
            检索结果
        """
        # 使用空查询获取该类别下的所有文档
        # 这里可能需要调整，因为ChromaDB可能不支持空查询
        # 可以使用通用查询词
        query = f"{category}相关知识"
        return self.kb.search_by_category(category, query, n_results)
    
    def get_relevant_categories(self, query: str) -> List[str]:
        """
        获取相关类别
        
        Args:
            query: 查询文本
            
        Returns:
            相关类别列表
        """
        # 先检索一些文档
        results = self.retrieve(query, n_results=10)
        
        # 提取类别
        categories = set()
        for result in results:
            metadata = result.get("metadata", {})
            category = metadata.get("category")
            if category:
                categories.add(category)
        
        return list(categories)


# 全局检索器实例
rag_retriever = RAGRetriever()
