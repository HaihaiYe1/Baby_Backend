from typing import List, Dict, Any, Optional
from app.rag.knowledge_base import knowledge_base


class RAGRetriever:
    """RAG检索器"""
    
    def __init__(self, knowledge_base_instance=None):
        """
        初始化检索器
        
        Args:
            knowledge_base_instance: 知识库实例
        """
        self.kb = knowledge_base_instance or knowledge_base
    
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
