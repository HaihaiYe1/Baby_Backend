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
    volume: Optional[int] = Query(None, description="音量: 0-100"),
    duration: Optional[int] = Query(None, description="播放时长（分钟）"),
    current_user: User = Depends(get_current_user)
):
    """
    控制智能音箱
    """
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
    brightness: Optional[int] = Query(None, description="亮度: 0-100"),
    color: Optional[str] = Query(None, description="颜色: warm, cool, night, soft"),
    mode: Optional[str] = Query(None, description="模式: normal, night, reading, sleep"),
    current_user: User = Depends(get_current_user)
):
    """
    控制智能灯光
    """
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
    duration: Optional[int] = Query(None, description="持续时长（分钟）"),
    intensity: Optional[str] = Query(None, description="强度: low, medium, high"),
    current_user: User = Depends(get_current_user)
):
    """
    激活场景模式
    """
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
    limit: int = Query(50, description="返回数量"),
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
    duration: int = Query(60, description="持续时长（分钟）"),
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
