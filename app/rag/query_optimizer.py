from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(
            model=settings.MIMO_MODEL,
            api_key=settings.MIMO_API_KEY,
            base_url=settings.MIMO_BASE_URL,
            temperature=0.1,
            max_tokens=512
        )
    
    async def rewrite_query(self, query: str, chat_history: List[dict] = None) -> str:
        """
        LLM重写查询为更易检索的形式
        
        Args:
            query: 原始查询
            chat_history: 聊天历史
            
        Returns:
            重写后的查询
        """
        history_context = ""
        if chat_history:
            recent_history = chat_history[-3:]  # 最近3条
            history_context = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in recent_history
            ])
        
        prompt = f"""请将以下用户问题重写为更适合知识库检索的形式。

要求：
1. 保留原始意图
2. 扩展相关关键词
3. 使问题更完整、更具体
4. 适合向量相似度匹配

{f'聊天历史：{history_context}' if history_context else ''}

原始问题：{query}

重写后的查询："""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="你是一个查询优化专家，擅长将用户问题重写为更适合检索的形式。"),
                HumanMessage(content=prompt)
            ])
            return response.content.strip()
        except Exception as e:
            print(f"Query rewrite error: {e}")
            return query
    
    async def hyde(self, query: str) -> str:
        """
        HyDE (Hypothetical Document Embeddings)
        生成假设性文档用于检索
        
        Args:
            query: 用户查询
            
        Returns:
            假设性文档
        """
        prompt = f"""请生成一个可能包含以下问题答案的文档片段。

要求：
1. 文档应该像是从育儿百科或专家文章中摘录的
2. 包含具体的知识和建议
3. 长度适中（100-200字）
4. 使用专业但易懂的语言

问题：{query}

假设性文档："""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="你是一个育儿知识专家，擅长生成高质量的知识文档。"),
                HumanMessage(content=prompt)
            ])
            return response.content.strip()
        except Exception as e:
            print(f"HyDE error: {e}")
            return query
    
    async def multi_hop(self, query: str) -> List[str]:
        """
        将复杂问题分解为子问题
        
        Args:
            query: 复杂查询
            
        Returns:
            子问题列表
        """
        prompt = f"""请将以下复杂问题分解为2-3个更简单的子问题。

要求：
1. 每个子问题应该独立可回答
2. 子问题的答案组合起来应该能回答原始问题
3. 子问题应该具体明确

原始问题：{query}

请直接返回子问题列表，每行一个："""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="你是一个问题分析专家，擅长将复杂问题分解为简单的子问题。"),
                HumanMessage(content=prompt)
            ])
            
            # 解析子问题
            sub_questions = [
                q.strip() for q in response.content.strip().split('\n')
                if q.strip() and not q.strip().startswith('#')
            ]
            
            return sub_questions if sub_questions else [query]
            
        except Exception as e:
            print(f"Multi-hop error: {e}")
            return [query]
    
    async def extract_keywords(self, query: str) -> List[str]:
        """
        提取查询关键词
        
        Args:
            query: 用户查询
            
        Returns:
            关键词列表
        """
        prompt = f"""请从以下问题中提取3-5个最重要的关键词。

要求：
1. 关键词应该能代表问题的核心主题
2. 包含名词、动词和专业术语
3. 去除停用词

问题：{query}

请直接返回关键词，用逗号分隔："""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="你是一个文本分析专家，擅长提取关键词。"),
                HumanMessage(content=prompt)
            ])
            
            keywords = [
                kw.strip() for kw in response.content.strip().split(',')
                if kw.strip()
            ]
            
            return keywords
            
        except Exception as e:
            print(f"Keyword extraction error: {e}")
            return query.split()[:5]


# 全局查询优化器实例
query_optimizer = QueryOptimizer()
