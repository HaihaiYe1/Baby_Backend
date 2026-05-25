from typing import Dict, Any, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from .mqtt_client import mqtt_client


class SpeakerInput(BaseModel):
    """音箱控制输入参数"""
    action: str = Field(description="操作: play, stop, pause, resume, set_volume")
    content: Optional[str] = Field(default=None, description="播放内容: whitenoise, lullaby, ocean, rain")
    volume: Optional[int] = Field(default=None, description="音量: 0-100")
    duration: Optional[int] = Field(default=None, description="播放时长（分钟）")


class SpeakerTool(BaseTool):
    """智能音箱控制工具"""
    name = "smart_speaker"
    description = "控制智能音箱播放白噪音、摇篮曲等，用于安抚婴儿"
    args_schema = SpeakerInput
    
    # MQTT主题
    TOPIC_COMMAND = "baby/speaker/command"
    TOPIC_STATUS = "baby/speaker/status"
    
    # 预设内容
    CONTENT_MAP = {
        "whitenoise": "白噪音",
        "lullaby": "摇篮曲",
        "ocean": "海浪声",
        "rain": "雨声",
        "heartbeat": "心跳声",
        "bird": "鸟鸣声"
    }
    
    def _run(
        self,
        action: str,
        content: Optional[str] = None,
        volume: Optional[int] = None,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """执行音箱控制"""
        try:
            # 构建命令
            command = {
                "action": action,
                "device_type": "speaker"
            }
            
            if content:
                if content not in self.CONTENT_MAP:
                    return {
                        "success": False,
                        "error": f"不支持的内容: {content}",
                        "supported_content": list(self.CONTENT_MAP.keys())
                    }
                command["content"] = content
                command["content_name"] = self.CONTENT_MAP[content]
            
            if volume is not None:
                if not 0 <= volume <= 100:
                    return {"success": False, "error": "音量必须在0-100之间"}
                command["volume"] = volume
            
            if duration is not None:
                if duration <= 0:
                    return {"success": False, "error": "播放时长必须大于0"}
                command["duration"] = duration
            
            # 发送MQTT命令
            success = mqtt_client.publish(self.TOPIC_COMMAND, command)
            
            if success:
                return {
                    "success": True,
                    "action": action,
                    "content": content,
                    "content_name": self.CONTENT_MAP.get(content) if content else None,
                    "volume": volume,
                    "duration": duration,
                    "message": f"已发送{action}命令到智能音箱"
                }
            else:
                return {
                    "success": False,
                    "error": "MQTT发送失败，请检查连接"
                }
                
        except Exception as e:
            return {"success": False, "error": f"音箱控制失败: {str(e)}"}
    
    async def _arun(self, **kwargs) -> Dict[str, Any]:
        """异步执行"""
        return self._run(**kwargs)
    
    def play_white_noise(self, duration: int = 30) -> Dict[str, Any]:
        """播放白噪音"""
        return self._run(action="play", content="whitenoise", duration=duration)
    
    def play_lullaby(self, volume: int = 50) -> Dict[str, Any]:
        """播放摇篮曲"""
        return self._run(action="play", content="lullaby", volume=volume)
    
    def stop(self) -> Dict[str, Any]:
        """停止播放"""
        return self._run(action="stop")
    
    def set_volume(self, volume: int) -> Dict[str, Any]:
        """设置音量"""
        return self._run(action="set_volume", volume=volume)
