from typing import Dict, Any, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from .mqtt_client import mqtt_client


class LightInput(BaseModel):
    """灯光控制输入参数"""
    action: str = Field(description="操作: on, off, dim, color, mode")
    brightness: Optional[int] = Field(default=None, description="亮度: 0-100")
    color: Optional[str] = Field(default=None, description="颜色: warm, cool, night, soft")
    mode: Optional[str] = Field(default=None, description="模式: normal, night, reading, sleep")


class LightTool(BaseTool):
    """智能灯光控制工具"""
    name = "smart_light"
    description = "控制婴儿房灯光，调节亮度和颜色，营造舒适环境"
    args_schema = LightInput
    
    # MQTT主题
    TOPIC_COMMAND = "baby/light/command"
    TOPIC_STATUS = "baby/light/status"
    
    # 颜色配置
    COLOR_MAP = {
        "warm": {"r": 255, "g": 180, "b": 100, "name": "暖光"},
        "cool": {"r": 200, "g": 220, "b": 255, "name": "冷光"},
        "night": {"r": 255, "g": 100, "b": 50, "name": "夜灯"},
        "soft": {"r": 255, "g": 200, "b": 150, "name": "柔光"}
    }
    
    # 模式配置
    MODE_MAP = {
        "normal": {"brightness": 100, "color": "warm", "name": "普通模式"},
        "night": {"brightness": 10, "color": "night", "name": "夜灯模式"},
        "reading": {"brightness": 80, "color": "cool", "name": "阅读模式"},
        "sleep": {"brightness": 5, "color": "soft", "name": "睡眠模式"}
    }
    
    def _run(
        self,
        action: str,
        brightness: Optional[int] = None,
        color: Optional[str] = None,
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行灯光控制"""
        try:
            # 构建命令
            command = {
                "action": action,
                "device_type": "light"
            }
            
            if brightness is not None:
                if not 0 <= brightness <= 100:
                    return {"success": False, "error": "亮度必须在0-100之间"}
                command["brightness"] = brightness
            
            if color:
                if color not in self.COLOR_MAP:
                    return {
                        "success": False,
                        "error": f"不支持的颜色: {color}",
                        "supported_colors": list(self.COLOR_MAP.keys())
                    }
                command["color"] = self.COLOR_MAP[color]
                command["color_name"] = color
            
            if mode:
                if mode not in self.MODE_MAP:
                    return {
                        "success": False,
                        "error": f"不支持的模式: {mode}",
                        "supported_modes": list(self.MODE_MAP.keys())
                    }
                command["mode"] = mode
                command["mode_config"] = self.MODE_MAP[mode]
            
            # 发送MQTT命令
            success = mqtt_client.publish(self.TOPIC_COMMAND, command)
            
            if success:
                return {
                    "success": True,
                    "action": action,
                    "brightness": brightness,
                    "color": color,
                    "mode": mode,
                    "message": f"已发送{action}命令到智能灯光"
                }
            else:
                return {
                    "success": False,
                    "error": "MQTT发送失败，请检查连接"
                }
                
        except Exception as e:
            return {"success": False, "error": f"灯光控制失败: {str(e)}"}
    
    async def _arun(self, **kwargs) -> Dict[str, Any]:
        """异步执行"""
        return self._run(**kwargs)
    
    def turn_on(self, brightness: int = 100) -> Dict[str, Any]:
        """开灯"""
        return self._run(action="on", brightness=brightness)
    
    def turn_off(self) -> Dict[str, Any]:
        """关灯"""
        return self._run(action="off")
    
    def dim(self, brightness: int) -> Dict[str, Any]:
        """调节亮度"""
        return self._run(action="dim", brightness=brightness)
    
    def set_night_mode(self) -> Dict[str, Any]:
        """设置夜灯模式"""
        return self._run(action="mode", mode="night")
    
    def set_sleep_mode(self) -> Dict[str, Any]:
        """设置睡眠模式"""
        return self._run(action="mode", mode="sleep")
    
    def set_soft_light(self) -> Dict[str, Any]:
        """设置柔光"""
        return self._run(action="color", color="soft", brightness=50)
