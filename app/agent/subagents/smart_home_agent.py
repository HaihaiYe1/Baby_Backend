from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings


class SmartHomeAgent:
    """
    智能家居控制子Agent
    
    专门负责智能家居设备控制
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(
            model=settings.MIMO_MODEL,
            api_key=settings.MIMO_API_KEY,
            base_url=settings.MIMO_BASE_URL,
            temperature=0.1,
            max_tokens=1024
        )
        
        self.system_prompt = """你是智能家居控制专家。

职责：
1. 根据场景需求控制智能设备
2. 优化设备参数设置
3. 确保设备操作安全

可控制的设备：
- 音箱：播放白噪音、摇篮曲、停止播放
- 灯光：开关、调节亮度、切换颜色模式
- 场景：睡眠模式、安抚模式、玩耍模式、喂奶模式

请用简洁的语言回复，直接给出控制指令。"""
    
    async def control(
        self,
        action_request: str,
        current_status: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行智能家居控制
        
        Args:
            action_request: 控制请求描述
            current_status: 当前设备状态
            
        Returns:
            控制结果
        """
        # 构建控制请求
        request = f"""请根据以下需求生成智能家居控制指令：

需求：{action_request}

{f'当前设备状态：{current_status}' if current_status else ''}

请返回JSON格式的控制指令，包含：
- device: 设备类型 (speaker/light/scene)
- action: 操作类型
- params: 参数（可选）"""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=request)
            ])
            
            # 解析响应为控制指令
            commands = self._parse_commands(response.content)
            
            return {
                "success": True,
                "commands": commands,
                "raw_response": response.content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "commands": []
            }
    
    def _parse_commands(self, response: str) -> List[Dict[str, Any]]:
        """解析控制指令"""
        import json
        
        commands = []
        
        # 尝试解析JSON
        try:
            # 查找JSON块
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                if isinstance(parsed, list):
                    commands = parsed
                elif isinstance(parsed, dict):
                    commands = [parsed]
        except json.JSONDecodeError:
            pass
        
        # 如果JSON解析失败，使用默认指令
        if not commands:
            commands = self._extract_default_commands(response)
        
        return commands
    
    def _extract_default_commands(self, response: str) -> List[Dict[str, Any]]:
        """从文本中提取默认控制指令"""
        commands = []
        response_lower = response.lower()
        
        # 检测场景类型
        if "睡眠" in response or "sleep" in response_lower:
            commands.append({
                "device": "scene",
                "action": "execute",
                "params": {"scene_name": "sleep"}
            })
        elif "安抚" in response or "comfort" in response_lower:
            commands.append({
                "device": "scene",
                "action": "execute",
                "params": {"scene_name": "comfort"}
            })
        elif "玩耍" in response or "play" in response_lower:
            commands.append({
                "device": "scene",
                "action": "execute",
                "params": {"scene_name": "play"}
            })
        elif "喂奶" in response or "feeding" in response_lower:
            commands.append({
                "device": "scene",
                "action": "execute",
                "params": {"scene_name": "feeding"}
            })
        
        return commands
    
    async def get_suggestions(
        self,
        situation: str,
        baby_age_months: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取智能家居建议
        
        Args:
            situation: 当前情况描述
            baby_age_months: 婴儿月龄
            
        Returns:
            建议列表
        """
        request = f"""请根据以下情况提供智能家居控制建议：

情况：{situation}
{f'婴儿月龄：{baby_age_months}个月' if baby_age_months else ''}

请提供：
1. 推荐的场景模式
2. 设备参数建议
3. 注意事项"""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=request)
            ])
            
            return {
                "success": True,
                "suggestions": response.content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# 全局智能家居Agent实例
smart_home_agent = SmartHomeAgent()
