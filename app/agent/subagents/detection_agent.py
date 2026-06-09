from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings


class DetectionAgent:
    """
    视频检测子Agent
    
    专门负责视频帧分析和安全检测
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(
            model=settings.MIMO_MODEL,
            api_key=settings.MIMO_API_KEY,
            base_url=settings.MIMO_BASE_URL,
            temperature=0.1,
            max_tokens=1024
        )
        
        self.system_prompt = """你是婴儿安全检测专家。

职责：
1. 分析视频帧，识别潜在危险
2. 评估风险级别（safe/warning/danger）
3. 提供简要的安全建议

检测重点：
- 婴儿睡姿安全（俯卧、被子遮盖面部等）
- 窒息风险（枕头、玩具、塑料袋等）
- 跌落风险（床边、高处等）
- 异物窒息风险（小物件、食物等）

请用专业但易懂的语言回复。"""
    
    async def analyze(
        self,
        detection_results: Dict[str, Any],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析检测结果
        
        Args:
            detection_results: 视频检测结果
            context: 额外上下文信息
            
        Returns:
            分析结果
        """
        # 构建分析请求
        request = f"""请分析以下视频检测结果：

检测结果：
{self._format_detection_results(detection_results)}

{f'上下文信息：{context}' if context else ''}

请提供：
1. 风险评估（safe/warning/danger）
2. 具体风险点分析
3. 建议措施"""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=request)
            ])
            
            # 解析响应
            analysis = response.content
            
            # 提取风险级别
            risk_level = self._extract_risk_level(analysis)
            
            return {
                "success": True,
                "risk_level": risk_level,
                "analysis": analysis,
                "detection_results": detection_results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "risk_level": "unknown",
                "detection_results": detection_results
            }
    
    def _format_detection_results(self, results: Dict[str, Any]) -> str:
        """格式化检测结果"""
        lines = []
        
        overall_level = results.get("overall_level", "unknown")
        lines.append(f"整体风险级别: {overall_level}")
        
        causes = results.get("causes", [])
        if causes:
            lines.append("检测到的问题：")
            for i, cause in enumerate(causes, 1):
                reason = cause.get("reason", "")
                confidence = cause.get("confidence", 0)
                lines.append(f"  {i}. {reason} (置信度: {confidence:.2f})")
        
        objects = results.get("objects", [])
        if objects:
            lines.append("检测到的物体：")
            for obj in objects[:5]:  # 最多显示5个
                name = obj.get("name", "")
                confidence = obj.get("confidence", 0)
                lines.append(f"  - {name} ({confidence:.2f})")
        
        return "\n".join(lines)
    
    def _extract_risk_level(self, analysis: str) -> str:
        """从分析文本中提取风险级别"""
        analysis_lower = analysis.lower()
        
        if "danger" in analysis_lower or "危险" in analysis_lower:
            return "danger"
        elif "warning" in analysis_lower or "警告" in analysis_lower or "注意" in analysis_lower:
            return "warning"
        else:
            return "safe"


# 全局检测Agent实例
detection_agent = DetectionAgent()
