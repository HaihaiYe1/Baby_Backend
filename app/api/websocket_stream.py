from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import asyncio
import json
import time

from app.services.websocket_manager import ws_manager, MessageType
from app.services.audio_service import audio_service
from app.utils.security import get_current_user

router = APIRouter()


@router.websocket("/video-stream/{device_id}")
async def video_stream_websocket(
    websocket: WebSocket,
    device_id: int,
    client_id: str = Query(..., description="客户端ID"),
    token: Optional[str] = Query(None, description="认证token")
):
    """
    视频流WebSocket端点
    
    支持：
    - 实时视频帧传输
    - 设备订阅管理
    - 心跳检测
    """
    # 连接
    success = await ws_manager.connect(
        websocket=websocket,
        client_id=client_id,
        client_type="video_viewer",
        device_id=device_id
    )
    
    if not success:
        return
    
    try:
        # 主循环：接收和处理消息
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60  # 60秒超时
                )
                
                # 处理消息
                await ws_manager.handle_client_message(client_id, message)
                
            except asyncio.TimeoutError:
                # 发送心跳
                await ws_manager.send_to_client(client_id, {
                    "type": MessageType.HEARTBEAT,
                    "data": {"timestamp": time.time()}
                })
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)
    except Exception as e:
        print(f"视频流WebSocket异常: {e}")
        await ws_manager.disconnect(client_id)


@router.websocket("/audio-stream/{device_id}")
async def audio_stream_websocket(
    websocket: WebSocket,
    device_id: int,
    client_id: str = Query(..., description="客户端ID"),
    sample_rate: int = Query(16000, description="采样率"),
    channels: int = Query(1, description="声道数")
):
    """
    音频流WebSocket端点
    
    支持：
    - 实时音频数据传输
    - 双向语音对讲
    - 音频缓冲
    """
    # 连接
    success = await ws_manager.connect(
        websocket=websocket,
        client_id=client_id,
        client_type="audio_device",
        device_id=device_id
    )
    
    if not success:
        return
    
    # 开始流式传输
    audio_service.start_streaming(device_id)
    
    try:
        # 主循环：接收和处理音频数据
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30  # 30秒超时
                )
                
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type == MessageType.AUDIO_DATA:
                    # 处理接收到的音频数据
                    audio_data = data.get("audio", "")
                    if audio_data:
                        processed_chunk = await audio_service.process_audio_data(
                            device_id=device_id,
                            audio_data=audio_data,
                            sample_rate=data.get("sample_rate", sample_rate),
                            channels=data.get("channels", channels)
                        )
                        
                        # 转发给其他订阅该设备的客户端
                        await ws_manager.send_to_device(device_id, {
                            "type": MessageType.AUDIO_DATA,
                            "data": {
                                "device_id": device_id,
                                "audio": audio_data,
                                "sample_rate": processed_chunk.sample_rate,
                                "channels": processed_chunk.channels,
                                "timestamp": processed_chunk.timestamp,
                                "source": client_id
                            }
                        })
                
                elif message_type == MessageType.HEARTBEAT:
                    # 心跳
                    await ws_manager.handle_client_message(client_id, message)
                
                elif message_type == MessageType.CONTROL:
                    # 控制命令
                    action = data.get("action")
                    if action == "start_stream":
                        audio_service.start_streaming(device_id)
                    elif action == "stop_stream":
                        audio_service.stop_streaming(device_id)
                    elif action == "clear_buffer":
                        audio_service.clear_buffer(device_id)
                    
                    await ws_manager.handle_client_message(client_id, message)
                    
            except asyncio.TimeoutError:
                # 超时，发送心跳
                await ws_manager.send_to_client(client_id, {
                    "type": MessageType.HEARTBEAT,
                    "data": {"timestamp": time.time()}
                })
                
    except WebSocketDisconnect:
        audio_service.stop_streaming(device_id)
        await ws_manager.disconnect(client_id)
    except Exception as e:
        print(f"音频流WebSocket异常: {e}")
        audio_service.stop_streaming(device_id)
        await ws_manager.disconnect(client_id)


@router.websocket("/intercom/{device_id}")
async def intercom_websocket(
    websocket: WebSocket,
    device_id: int,
    client_id: str = Query(..., description="客户端ID"),
    role: str = Query("speaker", description="角色: speaker(说话者), listener(听者)")
):
    """
    双向语音对讲WebSocket端点
    
    支持：
    - 实时语音传输
    - 角色管理（说话者/听者）
    - 音频混合
    """
    # 连接
    client_type = f"intercom_{role}"
    success = await ws_manager.connect(
        websocket=websocket,
        client_id=client_id,
        client_type=client_type,
        device_id=device_id
    )
    
    if not success:
        return
    
    try:
        # 发送连接成功消息
        await ws_manager.send_to_client(client_id, {
            "type": MessageType.STATUS,
            "data": {
                "status": "connected",
                "role": role,
                "device_id": device_id,
                "message": f"已加入设备 {device_id} 的语音对讲"
            }
        })
        
        # 主循环
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30
                )
                
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type == MessageType.AUDIO_DATA:
                    # 处理音频数据
                    audio_data = data.get("audio", "")
                    if audio_data and role == "speaker":
                        # 说话者的音频数据转发给听者
                        await ws_manager.send_to_device(device_id, {
                            "type": MessageType.AUDIO_DATA,
                            "data": {
                                "device_id": device_id,
                                "audio": audio_data,
                                "sample_rate": data.get("sample_rate", 16000),
                                "channels": data.get("channels", 1),
                                "timestamp": time.time(),
                                "source": client_id,
                                "role": role
                            }
                        })
                
                elif message_type == MessageType.CONTROL:
                    # 控制命令
                    action = data.get("action")
                    
                    if action == "switch_role":
                        # 切换角色
                        new_role = "listener" if role == "speaker" else "speaker"
                        role = new_role
                        ws_manager.connections[client_id].client_type = f"intercom_{new_role}"
                        
                        await ws_manager.send_to_client(client_id, {
                            "type": MessageType.STATUS,
                            "data": {
                                "status": "role_switched",
                                "new_role": new_role
                            }
                        })
                    
                    elif action == "mute":
                        # 静音
                        await ws_manager.send_to_client(client_id, {
                            "type": MessageType.STATUS,
                            "data": {"status": "muted"}
                        })
                    
                    elif action == "unmute":
                        # 取消静音
                        await ws_manager.send_to_client(client_id, {
                            "type": MessageType.STATUS,
                            "data": {"status": "unmuted"}
                        })
                
                elif message_type == MessageType.HEARTBEAT:
                    await ws_manager.handle_client_message(client_id, message)
                    
            except asyncio.TimeoutError:
                await ws_manager.send_to_client(client_id, {
                    "type": MessageType.HEARTBEAT,
                    "data": {"timestamp": time.time()}
                })
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)
    except Exception as e:
        print(f"语音对讲WebSocket异常: {e}")
        await ws_manager.disconnect(client_id)


@router.websocket("/agent-stream")
async def agent_stream_websocket(
    websocket: WebSocket,
    client_id: str = Query(..., description="客户端ID"),
    user_id: int = Query(..., description="用户ID")
):
    """
    Agent推理结果流式传输
    
    支持：
    - Agent分析结果实时推送
    - 检测状态更新
    - 通知消息
    """
    # 连接
    success = await ws_manager.connect(
        websocket=websocket,
        client_id=client_id,
        client_type="agent_viewer"
    )
    
    if not success:
        return
    
    try:
        # 主循环
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60
                )
                
                await ws_manager.handle_client_message(client_id, message)
                
            except asyncio.TimeoutError:
                await ws_manager.send_to_client(client_id, {
                    "type": MessageType.HEARTBEAT,
                    "data": {"timestamp": time.time()}
                })
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)
    except Exception as e:
        print(f"Agent流WebSocket异常: {e}")
        await ws_manager.disconnect(client_id)
