import os
import base64
import json
from typing import Dict, Any, Optional, List
import httpx


class VLMService:
    """视觉语言模型服务，使用小米MiMo进行图像分析"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "MiMo-V2.5-Pro"
    ):
        """
        初始化VLM服务
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
        """
        self.api_key = api_key or os.getenv(
            "MIMO_API_KEY",
            "sk-cky9npvg2kk9c2m8iv7n0ycgnxggfqq73nmvt7sdx9efouwj"
        )
        self.base_url = base_url or os.getenv(
            "MIMO_BASE_URL",
            "https://api.mimo.xiaomi.com/v1"
        )
        self.model = model
        
        # 验证配置
        if not self.api_key:
            raise ValueError("API密钥未设置")
    
    async def analyze_image(
        self,
        image_data: str,
        prompt: str,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """
        分析图像并生成描述
        
        Args:
            image_data: Base64编码的图像数据
            prompt: 分析提示词
            max_tokens: 最大生成token数
            
        Returns:
            分析结果
        """
        try:
            # 准备请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 准备请求体
            # 小米MiMo Vision API格式（假设兼容OpenAI Vision API）
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": max_tokens
            }
            
            # 发送请求
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"API请求失败: {response.status_code}",
                        "details": response.text
                    }
                
                result = response.json()
                
                # 解析响应
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    return {
                        "success": True,
                        "analysis": content,
                        "usage": result.get("usage", {})
                    }
                else:
                    return {
                        "success": False,
                        "error": "API响应格式错误",
                        "response": result
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"VLM分析失败: {str(e)}"
            }
    
    async def analyze_scene(
        self,
        image_data: str,
        detection_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析场景，结合检测结果进行深度推理
        
        Args:
            image_data: Base64编码的图像数据
            detection_results: YOLO/MediaPipe检测结果
            
        Returns:
            场景分析结果
        """
        # 构建提示词
        prompt = self._build_scene_analysis_prompt(detection_results)
        
        # 调用VLM分析
        vlm_result = await self.analyze_image(image_data, prompt)
        
        if not vlm_result["success"]:
            return vlm_result
        
        # 解析VLM输出
        analysis = vlm_result["analysis"]
        
        # 提取关键信息
        scene_analysis = self._parse_scene_analysis(analysis)
        
        return {
            "success": True,
            "vlm_analysis": analysis,
            "scene_analysis": scene_analysis,
            "detection_results": detection_results
        }
    
    def _build_scene_analysis_prompt(
        self,
        detection_results: Dict[str, Any]
    ) -> str:
        """构建场景分析提示词"""
        
        # 提取检测信息
        overall_level = detection_results.get("overall_level", "unknown")
        causes = detection_results.get("causes", [])
        details = detection_results.get("details", {})
        
        cause_text = ""
        if causes:
            cause_text = "检测到的风险:\n"
            for cause in causes[:5]:  # 最多显示5个
                cause_text += f"- {cause.get('reason', '未知风险')} (级别: {cause.get('level', 'unknown')})\n"
        
        prompt = f"""你是一个专业的婴儿安全分析专家。请分析这张婴儿监控图像。

当前自动检测结果:
- 整体安全级别: {overall_level}
{cause_text}

请仔细观察图像，并回答以下问题:
1. 图像中婴儿的状态如何?(睡眠/清醒/活动)
2. 周围环境是否存在潜在危险?
3. 自动检测结果是否准确?是否有误报或漏报?
4. 如果存在风险，请评估实际危险程度(低/中/高)
5. 给出具体的应对建议

请用结构化的方式回答，包含以下JSON格式:
{{
  "baby_status": "sleeping/awake/active",
  "environment_assessment": "safe/caution/dangerous",
  "detection_accuracy": "accurate/false_positive/false_negative",
  "actual_risk_level": "low/medium/high",
  "risk_details": ["风险1", "风险2"],
  "recommendations": ["建议1", "建议2"],
  "confidence": 0.95
}}"""
        
        return prompt
    
    def _parse_scene_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """解析VLM输出的场景分析"""
        try:
            # 尝试从文本中提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', analysis_text)
            
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                return {
                    "parsed": True,
                    "data": result
                }
            else:
                # 如果没有找到JSON，返回原始文本
                return {
                    "parsed": False,
                    "raw_text": analysis_text
                }
                
        except json.JSONDecodeError:
            return {
                "parsed": False,
                "raw_text": analysis_text
            }
    
    async def generate_notification_message(
        self,
        detection_type: str,
        risk_level: str,
        details: str
    ) -> Dict[str, Any]:
        """
        生成通知消息
        
        Args:
            detection_type: 检测类型
            risk_level: 风险级别
            details: 详细信息
            
        Returns:
            生成的通知消息
        """
        prompt = f"""请根据以下检测信息生成家长通知:

检测类型: {detection_type}
风险级别: {risk_level}
详细信息: {details}

要求:
1. 通知标题简洁明了
2. 通知内容包含具体风险描述
3. 提供简要的应对建议
4. 语气专业但温和，避免引起过度恐慌

请生成通知内容:"""
        
        result = await self.analyze_image("", prompt)  # 无图像分析
        
        if result["success"]:
            return {
                "success": True,
                "notification_message": result["analysis"]
            }
        else:
            return result


# 全局VLM服务实例
vlm_service = VLMService()
