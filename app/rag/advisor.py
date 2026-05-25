from typing import Dict, Any, Optional, List
import os
import json

from app.rag.retriever import rag_retriever
from app.services.vlm_service import vlm_service


class ParentingAdvisor:
    """育儿顾问，基于RAG生成建议"""
    
    def __init__(self, retriever=None):
        """
        初始化育儿顾问
        
        Args:
            retriever: RAG检索器实例
        """
        self.retriever = retriever or rag_retriever
    
    async def get_advice(
        self,
        situation: str,
        baby_age_months: Optional[int] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取育儿建议
        
        Args:
            situation: 情况描述
            baby_age_months: 婴儿月龄
            context: 额外上下文
            
        Returns:
            建议结果
        """
        # 检索相关知识
        retrieved_docs = self.retriever.retrieve_for_situation(
            situation=situation,
            baby_age_months=baby_age_months,
            n_results=3
        )
        
        if not retrieved_docs:
            return {
                "success": False,
                "error": "未找到相关知识",
                "advice": "建议咨询专业儿科医生。"
            }
        
        # 构建上下文
        knowledge_context = self._build_knowledge_context(retrieved_docs)
        
        # 生成建议
        advice_result = await self._generate_advice(
            situation=situation,
            knowledge_context=knowledge_context,
            baby_age_months=baby_age_months,
            context=context
        )
        
        return {
            "success": True,
            "situation": situation,
            "baby_age_months": baby_age_months,
            "retrieved_knowledge": retrieved_docs,
            "advice": advice_result
        }
    
    def _build_knowledge_context(self, docs: List[Dict[str, Any]]) -> str:
        """
        构建知识上下文
        
        Args:
            docs: 检索到的文档
            
        Returns:
            格式化的知识上下文
        """
        context_parts = []
        for i, doc in enumerate(docs, 1):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            source = metadata.get("source", "未知来源")
            
            context_parts.append(f"知识{i} (来源: {source}):\n{content}")
        
        return "\n\n".join(context_parts)
    
    async def _generate_advice(
        self,
        situation: str,
        knowledge_context: str,
        baby_age_months: Optional[int] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成建议
        
        Args:
            situation: 情况描述
            knowledge_context: 知识上下文
            baby_age_months: 婴儿月龄
            context: 额外上下文
            
        Returns:
            生成的建议
        """
        # 构建提示词
        prompt = self._build_advice_prompt(
            situation=situation,
            knowledge_context=knowledge_context,
            baby_age_months=baby_age_months,
            context=context
        )
        
        # 调用VLM服务生成建议
        # 这里使用VLM服务，但实际上可能更适合使用纯文本LLM
        # 为了简化，我们使用VLM服务，但传入空图像
        result = await vlm_service.analyze_image("", prompt)
        
        if result["success"]:
            return {
                "generated_advice": result["analysis"],
                "knowledge_used": len(knowledge_context) > 0
            }
        else:
            # 如果生成失败，返回基于检索的简单建议
            return {
                "generated_advice": self._generate_fallback_advice(situation, knowledge_context),
                "knowledge_used": True,
                "generation_failed": True
            }
    
    def _build_advice_prompt(
        self,
        situation: str,
        knowledge_context: str,
        baby_age_months: Optional[int] = None,
        context: Optional[str] = None
    ) -> str:
        """
        构建建议提示词
        
        Args:
            situation: 情况描述
            knowledge_context: 知识上下文
            baby_age_months: 婴儿月龄
            context: 额外上下文
            
        Returns:
            提示词
        """
        age_info = f"婴儿月龄: {baby_age_months}个月" if baby_age_months else "婴儿月龄: 未知"
        context_info = f"额外上下文: {context}" if context else ""
        
        prompt = f"""你是一个专业的育儿顾问。请根据以下情况和相关知识，提供专业、实用的育儿建议。

情况描述:
{situation}

{age_info}
{context_info}

相关知识库内容:
{knowledge_context}

请提供:
1. 情况分析
2. 具体建议（分步骤）
3. 注意事项
4. 何时需要就医

请用温和、专业的语气回答，避免引起过度恐慌。"""
        
        return prompt
    
    def _generate_fallback_advice(self, situation: str, knowledge_context: str) -> str:
        """
        生成后备建议
        
        Args:
            situation: 情况描述
            knowledge_context: 知识上下文
            
        Returns:
            后备建议
        """
        # 简单提取知识上下文中的关键信息
        if "发烧" in situation or "发热" in situation:
            return "建议监测体温，如持续发热请及时就医。"
        elif "哭闹" in situation:
            return "请检查婴儿是否饥饿、尿布是否需要更换，尝试安抚。"
        elif "睡眠" in situation:
            return "确保睡眠环境安静、舒适，建立规律的睡眠习惯。"
        else:
            return "请仔细观察婴儿状态，如有异常请及时咨询医生。"
    
    async def get_emergency_advice(
        self,
        emergency_type: str,
        details: str
    ) -> Dict[str, Any]:
        """
        获取紧急情况建议
        
        Args:
            emergency_type: 紧急情况类型
            details: 详细信息
            
        Returns:
            紧急建议
        """
        # 紧急情况类别
        emergency_categories = {
            "choking": "窒息",
            "fever": "高烧",
            "fall": "跌落",
            "breathing": "呼吸困难",
            "allergy": "过敏反应"
        }
        
        category = emergency_categories.get(emergency_type, "其他紧急情况")
        
        # 检索相关知识
        retrieved_docs = self.retriever.retrieve(
            query=f"{category} {details}",
            n_results=3
        )
        
        # 生成紧急建议
        advice_result = await self._generate_emergency_advice(
            emergency_type=emergency_type,
            category=category,
            details=details,
            knowledge_docs=retrieved_docs
        )
        
        return {
            "success": True,
            "emergency_type": emergency_type,
            "category": category,
            "details": details,
            "retrieved_knowledge": retrieved_docs,
            "emergency_advice": advice_result
        }
    
    async def _generate_emergency_advice(
        self,
        emergency_type: str,
        category: str,
        details: str,
        knowledge_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成紧急建议
        
        Args:
            emergency_type: 紧急情况类型
            category: 类别
            details: 详细信息
            knowledge_docs: 知识文档
            
        Returns:
            紧急建议
        """
        # 构建知识上下文
        knowledge_context = self._build_knowledge_context(knowledge_docs)
        
        prompt = f"""紧急情况！请提供专业的紧急处理建议。

紧急类型: {category}
详细情况: {details}

相关知识:
{knowledge_context}

请立即提供:
1. 紧急处理步骤（按优先级）
2. 需要避免的错误操作
3. 何时必须立即就医
4. 等待救援时的注意事项

请用清晰、简洁的语言，确保在紧急情况下易于理解。"""
        
        result = await vlm_service.analyze_image("", prompt)
        
        if result["success"]:
            return {
                "advice": result["analysis"],
                "is_emergency": True
            }
        else:
            # 后备紧急建议
            return {
                "advice": self._get_default_emergency_advice(emergency_type),
                "is_emergency": True,
                "generation_failed": True
            }
    
    def _get_default_emergency_advice(self, emergency_type: str) -> str:
        """
        获取默认紧急建议
        
        Args:
            emergency_type: 紧急情况类型
            
        Returns:
            默认建议
        """
        default_advice = {
            "choking": "立即拨打急救电话，尝试海姆立克急救法。",
            "fever": "监测体温，如超过38.5℃请立即就医。",
            "fall": "保持婴儿静止，观察意识状态，立即就医。",
            "breathing": "保持呼吸道通畅，立即拨打急救电话。",
            "allergy": "远离过敏原，如出现呼吸困难立即就医。"
        }
        
        return default_advice.get(emergency_type, "请立即联系急救服务。")


# 全局育儿顾问实例
parenting_advisor = ParentingAdvisor()
