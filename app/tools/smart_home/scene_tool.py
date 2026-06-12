from typing import Dict, Any, Optional, List, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from .mqtt_client import mqtt_client


class SceneInput(BaseModel):
    """场景模式输入参数"""
    scene: str = Field(description="场景模式: sleep, wake, comfort, alert, calm")
    duration: Optional[int] = Field(default=None, description="持续时长（分钟）")
    intensity: Optional[str] = Field(default=None, description="强度: low, medium, high")


class SceneTool(BaseTool):
    """场景模式工具"""
    name: str = "smart_scene"
    description: str = "控制智能家居场景模式，一键调节多个设备"
    args_schema: Type[BaseModel] = SceneInput
    
    # MQTT主题
    TOPIC_COMMAND: str = "baby/scene/command"
    TOPIC_STATUS: str = "baby/scene/status"
    
    # 场景配置
    SCENE_CONFIG: Dict[str, Dict] = {
        "sleep": {
            "name": "睡眠模式",
            "description": "营造安静舒适的睡眠环境",
            "actions": [
                {"tool": "light", "action": "mode", "params": {"mode": "sleep"}},
                {"tool": "speaker", "action": "play", "params": {"content": "whitenoise", "volume": 30, "duration": 60}}
            ]
        },
        "wake": {
            "name": "唤醒模式",
            "description": "温柔唤醒婴儿",
            "actions": [
                {"tool": "light", "action": "mode", "params": {"mode": "normal"}},
                {"tool": "speaker", "action": "play", "params": {"content": "bird", "volume": 40, "duration": 15}}
            ]
        },
        "comfort": {
            "name": "安抚模式",
            "description": "安抚哭闹的婴儿",
            "actions": [
                {"tool": "light", "action": "color", "params": {"color": "soft", "brightness": 30}},
                {"tool": "speaker", "action": "play", "params": {"content": "lullaby", "volume": 50, "duration": 30}}
            ]
        },
        "alert": {
            "name": "警报模式",
            "description": "检测到危险时的应急响应",
            "actions": [
                {"tool": "light", "action": "on", "params": {"brightness": 100, "color": "warm"}},
                {"tool": "speaker", "action": "play", "params": {"content": "whitenoise", "volume": 70}}
            ]
        },
        "calm": {
            "name": "平静模式",
            "description": "帮助婴儿平静下来",
            "actions": [
                {"tool": "light", "action": "dim", "params": {"brightness": 20, "color": "warm"}},
                {"tool": "speaker", "action": "play", "params": {"content": "ocean", "volume": 40, "duration": 45}}
            ]
        }
    }
    
    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True
    
    def __init__(self, **kwargs):
        """初始化场景工具"""
        super().__init__(**kwargs)
        # 使用object.__setattr__绕过Pydantic的限制
        from .speaker_tool import SpeakerTool
        from .light_tool import LightTool
        object.__setattr__(self, '_speaker_tool', SpeakerTool())
        object.__setattr__(self, '_light_tool', LightTool())
    
    def _run(
        self,
        scene: str,
        duration: Optional[int] = None,
        intensity: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行场景模式"""
        try:
            if scene not in self.SCENE_CONFIG:
                return {
                    "success": False,
                    "error": f"不支持的场景: {scene}",
                    "supported_scenes": list(self.SCENE_CONFIG.keys())
                }
            
            scene_config = self.SCENE_CONFIG[scene]
            results = []
            
            # 执行场景中的所有动作
            for action in scene_config["actions"]:
                tool_name = action["tool"]
                action_name = action["action"]
                params = action["params"].copy()
                
                # 应用强度调整
                if intensity:
                    params = self._apply_intensity(params, intensity)
                
                # 应用持续时长
                if duration and "duration" in params:
                    params["duration"] = duration
                
                # 执行动作
                if tool_name == "light":
                    result = self._light_tool._run(action=action_name, **params)
                elif tool_name == "speaker":
                    result = self._speaker_tool._run(action=action_name, **params)
                else:
                    result = {"success": False, "error": f"未知工具: {tool_name}"}
                
                results.append({
                    "tool": tool_name,
                    "action": action_name,
                    "result": result
                })
            
            # 发送场景命令到MQTT
            scene_command = {
                "scene": scene,
                "scene_name": scene_config["name"],
                "duration": duration,
                "intensity": intensity
            }
            mqtt_client.publish(self.TOPIC_COMMAND, scene_command)
            
            # 统计成功和失败
            success_count = sum(1 for r in results if r["result"].get("success", False))
            total_count = len(results)
            
            return {
                "success": success_count > 0,
                "scene": scene,
                "scene_name": scene_config["name"],
                "description": scene_config["description"],
                "actions_executed": total_count,
                "actions_succeeded": success_count,
                "results": results,
                "message": f"已执行{scene_config['name']}，{success_count}/{total_count}个动作成功"
            }
            
        except Exception as e:
            return {"success": False, "error": f"场景执行失败: {str(e)}"}
    
    def _apply_intensity(self, params: Dict[str, Any], intensity: str) -> Dict[str, Any]:
        """应用强度调整"""
        intensity_multiplier = {
            "low": 0.5,
            "medium": 1.0,
            "high": 1.5
        }
        
        multiplier = intensity_multiplier.get(intensity, 1.0)
        
        adjusted_params = params.copy()
        
        if "volume" in adjusted_params:
            adjusted_params["volume"] = min(100, int(adjusted_params["volume"] * multiplier))
        
        if "brightness" in adjusted_params:
            adjusted_params["brightness"] = min(100, int(adjusted_params["brightness"] * multiplier))
        
        return adjusted_params
    
    async def _arun(self, **kwargs) -> Dict[str, Any]:
        """异步执行"""
        return self._run(**kwargs)
    
    def sleep_mode(self, duration: int = 60) -> Dict[str, Any]:
        """睡眠模式"""
        return self._run(scene="sleep", duration=duration)
    
    def comfort_mode(self, intensity: str = "medium") -> Dict[str, Any]:
        """安抚模式"""
        return self._run(scene="comfort", intensity=intensity)
    
    def alert_mode(self) -> Dict[str, Any]:
        """警报模式"""
        return self._run(scene="alert", intensity="high")
    
    def calm_mode(self, duration: int = 30) -> Dict[str, Any]:
        """平静模式"""
        return self._run(scene="calm", duration=duration)
