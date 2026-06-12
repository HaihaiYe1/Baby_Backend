from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.utils.security import get_current_user
from app.models import User
from app.tools.smart_home import SpeakerTool, LightTool, SceneTool
from app.tools.smart_home.mqtt_client import mqtt_client
from typing import Dict, Any, Optional

router = APIRouter()

# 初始化工具
speaker_tool = SpeakerTool()
light_tool = LightTool()
scene_tool = SceneTool()


@router.get("/status")
async def get_smart_home_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取智能家居系统状态
    """
    try:
        mqtt_status = mqtt_client.get_status()
        
        return {
            "success": True,
            "mqtt": mqtt_status,
            "tools": {
                "speaker": "available",
                "light": "available",
                "scene": "available"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/speaker/control")
async def control_speaker(
    action: str = Query(..., description="操作: play, stop, pause, resume, set_volume"),
    content: Optional[str] = Query(None, description="播放内容: whitenoise, lullaby, ocean, rain"),
    volume: Optional[int] = Query(None, ge=0, le=100, description="音量: 0-100"),
    duration: Optional[int] = Query(None, ge=1, le=1440, description="播放时长（分钟）: 1-1440"),
    current_user: User = Depends(get_current_user)
):
    """
    控制智能音箱
    """
    # 验证action参数
    valid_actions = ["play", "stop", "pause", "resume", "set_volume"]
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"无效的操作: {action}，有效操作: {valid_actions}")
    
    # 验证content参数
    if content and action == "play":
        valid_contents = ["whitenoise", "lullaby", "ocean", "rain"]
        if content not in valid_contents:
            raise HTTPException(status_code=400, detail=f"无效的播放内容: {content}，有效内容: {valid_contents}")
    
    try:
        result = speaker_tool._run(
            action=action,
            content=content,
            volume=volume,
            duration=duration
        )
        
        return {
            "success": result.get("success", False),
            "user_id": current_user.id,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音箱控制失败: {str(e)}")


@router.post("/light/control")
async def control_light(
    action: str = Query(..., description="操作: on, off, dim, color, mode"),
    brightness: Optional[int] = Query(None, ge=0, le=100, description="亮度: 0-100"),
    color: Optional[str] = Query(None, description="颜色: warm, cool, night, soft"),
    mode: Optional[str] = Query(None, description="模式: normal, night, reading, sleep"),
    current_user: User = Depends(get_current_user)
):
    """
    控制智能灯光
    """
    # 验证action参数
    valid_actions = ["on", "off", "dim", "color", "mode"]
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"无效的操作: {action}，有效操作: {valid_actions}")
    
    # 验证color参数
    if color and action == "color":
        valid_colors = ["warm", "cool", "night", "soft"]
        if color not in valid_colors:
            raise HTTPException(status_code=400, detail=f"无效的颜色: {color}，有效颜色: {valid_colors}")
    
    # 验证mode参数
    if mode and action == "mode":
        valid_modes = ["normal", "night", "reading", "sleep"]
        if mode not in valid_modes:
            raise HTTPException(status_code=400, detail=f"无效的模式: {mode}，有效模式: {valid_modes}")
    
    try:
        result = light_tool._run(
            action=action,
            brightness=brightness,
            color=color,
            mode=mode
        )
        
        return {
            "success": result.get("success", False),
            "user_id": current_user.id,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"灯光控制失败: {str(e)}")


@router.post("/scene/activate")
async def activate_scene(
    scene: str = Query(..., description="场景模式: sleep, wake, comfort, alert, calm"),
    duration: Optional[int] = Query(None, ge=1, le=1440, description="持续时长（分钟）: 1-1440"),
    intensity: Optional[str] = Query(None, description="强度: low, medium, high"),
    current_user: User = Depends(get_current_user)
):
    """
    激活场景模式
    """
    # 验证scene参数
    valid_scenes = ["sleep", "wake", "comfort", "alert", "calm"]
    if scene not in valid_scenes:
        raise HTTPException(status_code=400, detail=f"无效的场景: {scene}，有效场景: {valid_scenes}")
    
    # 验证intensity参数
    if intensity:
        valid_intensities = ["low", "medium", "high"]
        if intensity not in valid_intensities:
            raise HTTPException(status_code=400, detail=f"无效的强度: {intensity}，有效强度: {valid_intensities}")
    
    try:
        result = scene_tool._run(
            scene=scene,
            duration=duration,
            intensity=intensity
        )
        
        return {
            "success": result.get("success", False),
            "user_id": current_user.id,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"场景激活失败: {str(e)}")


@router.get("/scenes")
async def get_available_scenes(
    current_user: User = Depends(get_current_user)
):
    """
    获取可用场景列表
    """
    try:
        scenes = scene_tool.SCENE_CONFIG
        
        return {
            "success": True,
            "scenes": {
                name: {
                    "name": config["name"],
                    "description": config["description"]
                }
                for name, config in scenes.items()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取场景列表失败: {str(e)}")


@router.get("/mqtt/history")
async def get_mqtt_history(
    topic: Optional[str] = Query(None, description="过滤主题"),
    limit: int = Query(50, ge=1, le=1000, description="返回数量: 1-1000"),
    current_user: User = Depends(get_current_user)
):
    """
    获取MQTT消息历史
    """
    try:
        history = mqtt_client.get_message_history(topic=topic, limit=limit)
        
        return {
            "success": True,
            "history": history,
            "total": len(history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.post("/quick/sleep")
async def quick_sleep_mode(
    duration: int = Query(60, ge=1, le=1440, description="持续时长（分钟）: 1-1440"),
    current_user: User = Depends(get_current_user)
):
    """
    快速启动睡眠模式
    """
    try:
        result = scene_tool.sleep_mode(duration=duration)
        
        return {
            "success": result.get("success", False),
            "user_id": current_user.id,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动睡眠模式失败: {str(e)}")


@router.post("/quick/comfort")
async def quick_comfort_mode(
    intensity: str = Query("medium", description="强度: low, medium, high"),
    current_user: User = Depends(get_current_user)
):
    """
    快速启动安抚模式
    """
    # 验证intensity参数
    valid_intensities = ["low", "medium", "high"]
    if intensity not in valid_intensities:
        raise HTTPException(status_code=400, detail=f"无效的强度: {intensity}，有效强度: {valid_intensities}")
    
    try:
        result = scene_tool.comfort_mode(intensity=intensity)
        
        return {
            "success": result.get("success", False),
            "user_id": current_user.id,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动安抚模式失败: {str(e)}")


@router.post("/quick/alert")
async def quick_alert_mode(
    current_user: User = Depends(get_current_user)
):
    """
    快速启动警报模式
    """
    try:
        result = scene_tool.alert_mode()
        
        return {
            "success": result.get("success", False),
            "user_id": current_user.id,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动警报模式失败: {str(e)}")
