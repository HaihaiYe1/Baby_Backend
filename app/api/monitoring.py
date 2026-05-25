from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, Optional
from app.utils.security import get_current_user
from app.models import User
from app.services.websocket_manager import ws_manager
from app.services.audio_service import audio_service
import time

router = APIRouter()


@router.get("/stats")
async def get_system_stats(
    current_user: User = Depends(get_current_user)
):
    """
    获取系统性能统计
    """
    try:
        ws_stats = ws_manager.get_stats()
        audio_stats = audio_service.get_stats()
        
        return {
            "success": True,
            "timestamp": time.time(),
            "websocket": ws_stats,
            "audio": audio_stats,
            "system": {
                "uptime_seconds": time.time() - ws_stats.get("start_time", time.time()),
                "memory_usage": "N/A",  # 可以集成psutil获取
                "cpu_usage": "N/A"
            }
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/connections")
async def get_connections(
    client_type: Optional[str] = Query(None, description="客户端类型过滤"),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有连接信息
    """
    try:
        connections = ws_manager.get_all_connections()
        
        # 按类型过滤
        if client_type:
            connections = [
                conn for conn in connections
                if conn and conn.get("client_type") == client_type
            ]
        
        return {
            "success": True,
            "total": len(connections),
            "connections": connections
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/connection/{client_id}")
async def get_connection_info(
    client_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取指定连接信息
    """
    try:
        conn_info = ws_manager.get_connection_info(client_id)
        
        if conn_info:
            return {
                "success": True,
                "connection": conn_info
            }
        else:
            return {
                "success": False,
                "error": f"连接 {client_id} 不存在"
            }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/device-subscriptions")
async def get_device_subscriptions(
    current_user: User = Depends(get_current_user)
):
    """
    获取设备订阅关系
    """
    try:
        subscriptions = {}
        for device_id, client_ids in ws_manager.device_subscriptions.items():
            subscriptions[str(device_id)] = {
                "subscriber_count": len(client_ids),
                "subscribers": list(client_ids)
            }
        
        return {
            "success": True,
            "total_devices": len(subscriptions),
            "subscriptions": subscriptions
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/audio-stats")
async def get_audio_stats(
    current_user: User = Depends(get_current_user)
):
    """
    获取音频服务统计
    """
    try:
        stats = audio_service.get_stats()
        
        return {
            "success": True,
            "audio_stats": stats
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/broadcast")
async def broadcast_message(
    message: str = Query(..., description="广播消息"),
    client_type: Optional[str] = Query(None, description="客户端类型过滤"),
    current_user: User = Depends(get_current_user)
):
    """
    广播消息给所有客户端
    """
    try:
        import json
        
        broadcast_data = {
            "type": "broadcast",
            "data": {
                "message": message,
                "from": "system",
                "timestamp": time.time()
            }
        }
        
        success_count = await ws_manager.broadcast(broadcast_data, client_type)
        
        return {
            "success": True,
            "sent_to": success_count,
            "message": message
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/send-to-device/{device_id}")
async def send_to_device(
    device_id: int,
    message: str = Query(..., description="消息内容"),
    current_user: User = Depends(get_current_user)
):
    """
    发送消息给指定设备的订阅者
    """
    try:
        import json
        
        device_message = {
            "type": "device_message",
            "data": {
                "device_id": device_id,
                "message": message,
                "from": "system",
                "timestamp": time.time()
            }
        }
        
        success_count = await ws_manager.send_to_device(device_id, device_message)
        
        return {
            "success": True,
            "device_id": device_id,
            "sent_to": success_count,
            "message": message
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/reset-stats")
async def reset_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    重置性能统计
    """
    try:
        ws_manager.stats = ws_manager.stats.__class__()
        
        return {
            "success": True,
            "message": "统计已重置"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
