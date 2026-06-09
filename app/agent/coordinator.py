from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.config import settings
from .subagents import DetectionAgent, SmartHomeAgent, AdviceAgent


class CoordinatorAgent:
    """
    协调器Agent
    
    管理和协调多个子Agent
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(
            model=settings.MIMO_MODEL,
            api_key=settings.MIMO_API_KEY,
            base_url=settings.MIMO_BASE_URL,
            temperature=0.1,
            max_tokens=1024
        )
        
        # 初始化子Agent
        self.detection_agent = DetectionAgent(self.llm)
        self.smart_home_agent = SmartHomeAgent(self.llm)
        self.advice_agent = AdviceAgent(self.llm)
        
        self.system_prompt = """你是婴儿看护AI助手的协调器。

职责：
1. 理解用户意图
2. 将任务分配给合适的子Agent
3. 整合多个Agent的结果
4. 生成最终响应

可用的子Agent：
- detection_agent: 视频检测分析
- smart_home_agent: 智能家居控制
- advice_agent: 育儿建议

请根据用户输入选择合适的Agent处理任务。"""
    
    async def process(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入
            context: 上下文信息（包含检测结果、设备状态等）
            
        Returns:
            处理结果
        """
        # 确定需要调用的Agent
        intent = await self._classify_intent(user_input, context)
        
        results = {}
        
        # 根据意图调用相应Agent
        if intent == "detection" or intent == "both_detection":
            detection_results = context.get("detection_results", {}) if context else {}
            if detection_results:
                results["detection"] = await self.detection_agent.analyze(
                    detection_results,
                    context.get("extra_context") if context else None
                )
        
        if intent == "smart_home" or intent == "both_detection":
            results["smart_home"] = await self.smart_home_agent.control(user_input)
        
        if intent == "advice":
            baby_age = context.get("baby_age_months") if context else None
            results["advice"] = await self.advice_agent.get_advice(
                user_input,
                baby_age
            )
        
        # 如果意图不明确，默认使用育儿建议Agent
        if not results:
            results["advice"] = await self.advice_agent.get_advice(user_input)
        
        # 整合结果
        response = await self._synthesize_response(user_input, results, intent)
        
        return {
            "success": True,
            "intent": intent,
            "results": results,
            "response": response
        }
    
    async def _classify_intent(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """分类用户意图"""
        # 构建分类请求
        has_detection = bool(context and context.get("detection_results"))
        
        request = f"""请分类以下用户输入的意图：

用户输入：{user_input}
{f'当前有检测结果: {has_detection}' if has_detection else ''}

可选意图：
- detection: 询问视频检测结果、安全分析
- smart_home: 控制智能家居设备
- advice: 询问育儿问题、寻求建议
- both_detection: 同时需要检测分析和设备控制

请只返回意图类别，不要添加其他内容。"""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="你是一个意图分类专家。"),
                HumanMessage(content=request)
            ])
            
            intent = response.content.strip().lower()
            
            # 验证意图
            valid_intents = ["detection", "smart_home", "advice", "both_detection"]
            if intent in valid_intents:
                return intent
            
            # 默认返回advice
            return "advice"
            
        except Exception as e:
            print(f"Intent classification error: {e}")
            return "advice"
    
    async def _synthesize_response(
        self,
        user_input: str,
        results: Dict[str, Any],
        intent: str
    ) -> str:
        """整合多个Agent的结果"""
        # 如果只有一个结果，直接返回
        if len(results) == 1:
            key = list(results.keys())[0]
            result = results[key]
            
            if key == "detection":
                return result.get("analysis", "检测分析完成")
            elif key == "smart_home":
                return result.get("raw_response", "设备控制完成")
            elif key == "advice":
                return result.get("advice", "建议生成完成")
        
        # 多个结果需要整合
        synthesis_parts = []
        
        if "detection" in results:
            detection = results["detection"]
            synthesis_parts.append(f"检测分析：\n{detection.get('analysis', '')}")
        
        if "smart_home" in results:
            smart_home = results["smart_home"]
            synthesis_parts.append(f"设备控制：\n{smart_home.get('raw_response', '')}")
        
        if "advice" in results:
            advice = results["advice"]
            synthesis_parts.append(f"育儿建议：\n{advice.get('advice', '')}")
        
        synthesis_request = f"""请整合以下信息，生成简洁的最终回复：

用户问题：{user_input}

各Agent结果：
{chr(10).join(synthesis_parts)}

请生成一个连贯、简洁的回复。"""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="你是一个信息整合专家，擅长将多个信息源整合成简洁的回复。"),
                HumanMessage(content=synthesis_request)
            ])
            
            return response.content
            
        except Exception as e:
            print(f"Response synthesis error: {e}")
            # 回退到简单拼接
            return "\n\n".join(synthesis_parts)
    
    async def analyze_and_respond(
        self,
        detection_results: Dict[str, Any],
        user_message: Optional[str] = None,
        baby_age_months: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        分析检测结果并生成响应
        
        Args:
            detection_results: 检测结果
            user_message: 用户消息（可选）
            baby_age_months: 婴儿月龄
            
        Returns:
            分析结果
        """
        context = {
            "detection_results": detection_results,
            "baby_age_months": baby_age_months
        }
        
        # 如果没有用户消息，自动生成
        if not user_message:
            risk_level = detection_results.get("overall_level", "safe")
            if risk_level == "danger":
                user_message = "检测到危险，请分析并提供建议"
            elif risk_level == "warning":
                user_message = "检测到警告，请分析情况"
            else:
                user_message = "请分析当前情况"
        
        return await self.process(user_message, context)


# 全局协调器Agent实例
coordinator_agent = CoordinatorAgent()
