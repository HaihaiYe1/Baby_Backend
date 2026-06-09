from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings
from app.rag.retriever import RAGRetriever


class AdviceAgent:
    """
    育儿建议子Agent
    
    专门负责提供育儿知识和建议
    """
    
    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        retriever: Optional[RAGRetriever] = None
    ):
        self.llm = llm or ChatOpenAI(
            model=settings.MIMO_MODEL,
            api_key=settings.MIMO_API_KEY,
            base_url=settings.MIMO_BASE_URL,
            temperature=0.3,
            max_tokens=1024
        )
        
        self.retriever = retriever or RAGRetriever()
        
        self.system_prompt = """你是专业的育儿顾问。

职责：
1. 回答育儿相关问题
2. 提供专业的育儿建议
3. 解释婴儿行为和发育特点

回答原则：
- 基于科学的育儿知识
- 语言温和、易于理解
- 考虑婴儿月龄因素
- 提供实用的建议

请用温暖专业的语气回答。"""
    
    async def get_advice(
        self,
        question: str,
        baby_age_months: Optional[int] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取育儿建议
        
        Args:
            question: 用户问题
            baby_age_months: 婴儿月龄
            context: 额外上下文
            
        Returns:
            建议结果
        """
        # 检索相关知识
        knowledge_context = ""
        try:
            if self.retriever:
                results = await self.retriever.retrieve(
                    question,
                    top_k=3,
                    optimize_query=True
                )
                if results:
                    knowledge_context = "\n\n参考知识：\n"
                    for i, result in enumerate(results[:3], 1):
                        content = result.get("content", "")
                        knowledge_context += f"{i}. {content[:200]}...\n"
        except Exception as e:
            print(f"Knowledge retrieval error: {e}")
        
        # 构建请求
        request = f"""请回答以下育儿问题：

问题：{question}

{f'婴儿月龄：{baby_age_months}个月' if baby_age_months else ''}
{f'上下文：{context}' if context else ''}
{knowledge_context}

请提供专业、实用的建议。"""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=request)
            ])
            
            return {
                "success": True,
                "advice": response.content,
                "has_knowledge_base": bool(knowledge_context)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "advice": "抱歉，暂时无法提供建议。请稍后再试。"
            }
    
    async def explain_detection(
        self,
        detection_results: Dict[str, Any],
        baby_age_months: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        解释检测结果
        
        Args:
            detection_results: 检测结果
            baby_age_months: 婴儿月龄
            
        Returns:
            解释结果
        """
        # 构建解释请求
        risk_level = detection_results.get("overall_level", "unknown")
        causes = detection_results.get("causes", [])
        
        causes_text = ""
        if causes:
            causes_text = "检测到的问题：\n"
            for cause in causes[:3]:
                reason = cause.get("reason", "")
                causes_text += f"- {reason}\n"
        
        request = f"""请解释以下婴儿安全检测结果：

风险级别：{risk_level}
{causes_text}
{f'婴儿月龄：{baby_age_months}个月' if baby_age_months else ''}

请解释：
1. 这些风险意味着什么
2. 为什么需要注意
3. 如何预防和处理"""
        
        try:
            # 检索相关知识
            knowledge_context = ""
            if self.retriever:
                try:
                    search_query = f"{risk_level}风险 婴儿安全"
                    results = await self.retriever.retrieve(search_query, top_k=2)
                    if results:
                        knowledge_context = "\n\n相关知识：\n"
                        for result in results[:2]:
                            content = result.get("content", "")
                            knowledge_context += f"- {content[:150]}...\n"
                except Exception:
                    pass
            
            request += knowledge_context
            
            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=request)
            ])
            
            return {
                "success": True,
                "explanation": response.content,
                "risk_level": risk_level
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# 全局育儿建议Agent实例
advice_agent = AdviceAgent()
