import asyncio
import json
import time
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict
from enum import Enum


class MessageType(str, Enum):
    """消息类型枚举"""
    ALERT = "alert"
    VIDEO_FRAME = "video_frame"
    AUDIO_DATA = "audio_data"
    CONTROL = "control"
    STATUS = "status"
    HEARTBEAT = "heartbeat"


@dataclass
class ConnectionInfo:
    """连接信息"""
    client_id: str
    websocket: WebSocket
    connected_at: float
    last_heartbeat: float
    client_type: str  # "mobile", "web", "audio_device"
    device_id: Optional[int] = None
    subscriptions: Set[str] = None
    
    def __post_init__(self):
        if self.subscriptions is None:
            self.subscriptions = set()


@dataclass
class PerformanceStats:
    """性能统计"""
    total_connections: int = 0
    active_connections: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors: int = 0
    avg_latency_ms: float = 0.0


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        """初始化WebSocket管理器"""
        # 活跃连接
        self.connections: Dict[str, ConnectionInfo] = {}
        
        # 设备订阅关系
        self.device_subscriptions: Dict[int, Set[str]] = {}
        
        # 性能统计
        self.stats = PerformanceStats()
        
        # 心跳超时时间（秒）
        self.heartbeat_timeout = 30
        
        # 消息队列
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # 启动后台任务
        self._background_tasks: List[asyncio.Task] = []
    
    async def start(self):
        """启动管理器"""
        # 启动心跳检测
        self._background_tasks.append(
            asyncio.create_task(self._heartbeat_checker())
        )
        # 启动消息处理
        self._background_tasks.append(
            asyncio.create_task(self._message_processor())
        )
        print("WebSocket管理器已启动")
    
    async def stop(self):
        """停止管理器"""
        for task in self._background_tasks:
            task.cancel()
        self._background_tasks.clear()
        print("WebSocket管理器已停止")
    
    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        client_type: str = "mobile",
        device_id: Optional[int] = None
    ) -> bool:
        """
        处理新连接
        
        Args:
            websocket: WebSocket连接
            client_id: 客户端ID
            client_type: 客户端类型
            device_id: 关联的设备ID
            
        Returns:
            是否连接成功
        """
        try:
            await websocket.accept()
            
            # 创建连接信息
            conn_info = ConnectionInfo(
                client_id=client_id,
                websocket=websocket,
                connected_at=time.time(),
                last_heartbeat=time.time(),
                client_type=client_type,
                device_id=device_id
            )
            
            # 保存连接
            self.connections[client_id] = conn_info
            
            # 更新设备订阅
            if device_id is not None:
                if device_id not in self.device_subscriptions:
                    self.device_subscriptions[device_id] = set()
                self.device_subscriptions[device_id].add(client_id)
            
            # 更新统计
            self.stats.total_connections += 1
            self.stats.active_connections = len(self.connections)
            
            print(f"客户端连接: {client_id} (类型: {client_type}, 设备: {device_id})")
            
            # 发送欢迎消息
            await self.send_to_client(client_id, {
                "type": MessageType.STATUS,
                "data": {
                    "status": "connected",
                    "client_id": client_id,
                    "server_time": time.time()
                }
            })
            
            return True
            
        except Exception as e:
            print(f"连接失败: {e}")
            self.stats.errors += 1
            return False
    
    async def disconnect(self, client_id: str):
        """
        处理断开连接
        
        Args:
            client_id: 客户端ID
        """
        if client_id not in self.connections:
            return
        
        conn_info = self.connections[client_id]
        
        # 从设备订阅中移除
        if conn_info.device_id is not None:
            device_subs = self.device_subscriptions.get(conn_info.device_id)
            if device_subs:
                device_subs.discard(client_id)
                if not device_subs:
                    del self.device_subscriptions[conn_info.device_id]
        
        # 移除连接
        del self.connections[client_id]
        
        # 更新统计
        self.stats.active_connections = len(self.connections)
        
        print(f"客户端断开: {client_id}")
    
    async def send_to_client(
        self,
        client_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """
        发送消息给指定客户端
        
        Args:
            client_id: 客户端ID
            message: 消息内容
            
        Returns:
            是否发送成功
        """
        if client_id not in self.connections:
            return False
        
        conn_info = self.connections[client_id]
        
        try:
            json_data = json.dumps(message)
            await conn_info.websocket.send_text(json_data)
            
            # 更新统计
            self.stats.messages_sent += 1
            self.stats.bytes_sent += len(json_data)
            
            return True
            
        except Exception as e:
            print(f"发送失败: {e}")
            self.stats.errors += 1
            await self.disconnect(client_id)
            return False
    
    async def send_to_device(
        self,
        device_id: int,
        message: Dict[str, Any]
    ) -> int:
        """
        发送消息给订阅指定设备的所有客户端
        
        Args:
            device_id: 设备ID
            message: 消息内容
            
        Returns:
            成功发送的客户端数量
        """
        subscribers = self.device_subscriptions.get(device_id, set())
        
        if not subscribers:
            return 0
        
        success_count = 0
        for client_id in list(subscribers):
            if await self.send_to_client(client_id, message):
                success_count += 1
        
        return success_count
    
    async def broadcast(
        self,
        message: Dict[str, Any],
        client_type: Optional[str] = None
    ) -> int:
        """
        广播消息
        
        Args:
            message: 消息内容
            client_type: 客户端类型过滤
            
        Returns:
            成功发送的客户端数量
        """
        success_count = 0
        
        for client_id, conn_info in list(self.connections.items()):
            if client_type and conn_info.client_type != client_type:
                continue
            
            if await self.send_to_client(client_id, message):
                success_count += 1
        
        return success_count
    
    async def send_alert(
        self,
        level: str,
        message: str,
        alert_id: int,
        device_id: Optional[int] = None
    ) -> int:
        """
        发送警报消息
        
        Args:
            level: 警报级别
            message: 警报内容
            alert_id: 警报ID
            device_id: 设备ID
            
        Returns:
            成功发送的客户端数量
        """
        alert_data = {
            "type": MessageType.ALERT,
            "data": {
                "id": alert_id,
                "level": level,
                "message": message,
                "timestamp": time.time()
            }
        }
        
        if device_id is not None:
            return await self.send_to_device(device_id, alert_data)
        else:
            return await self.broadcast(alert_data)
    
    async def send_video_frame(
        self,
        device_id: int,
        frame_data: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        发送视频帧
        
        Args:
            device_id: 设备ID
            frame_data: Base64编码的帧数据
            metadata: 帧元数据
            
        Returns:
            成功发送的客户端数量
        """
        frame_message = {
            "type": MessageType.VIDEO_FRAME,
            "data": {
                "device_id": device_id,
                "frame": frame_data,
                "timestamp": time.time(),
                "metadata": metadata or {}
            }
        }
        
        return await self.send_to_device(device_id, frame_message)
    
    async def send_audio_data(
        self,
        device_id: int,
        audio_data: str,
        sample_rate: int = 16000,
        channels: int = 1
    ) -> int:
        """
        发送音频数据
        
        Args:
            device_id: 设备ID
            audio_data: Base64编码的音频数据
            sample_rate: 采样率
            channels: 声道数
            
        Returns:
            成功发送的客户端数量
        """
        audio_message = {
            "type": MessageType.AUDIO_DATA,
            "data": {
                "device_id": device_id,
                "audio": audio_data,
                "sample_rate": sample_rate,
                "channels": channels,
                "timestamp": time.time()
            }
        }
        
        return await self.send_to_device(device_id, audio_message)
    
    async def handle_client_message(
        self,
        client_id: str,
        message: str
    ):
        """
        处理客户端消息
        
        Args:
            client_id: 客户端ID
            message: 消息内容
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            # 更新统计
            self.stats.messages_received += 1
            self.stats.bytes_received += len(message)
            
            # 处理心跳
            if message_type == MessageType.HEARTBEAT:
                if client_id in self.connections:
                    self.connections[client_id].last_heartbeat = time.time()
                return
            
            # 处理订阅请求
            if message_type == "subscribe":
                device_id = data.get("device_id")
                if device_id and client_id in self.connections:
                    self.connections[client_id].subscriptions.add(str(device_id))
                    if device_id not in self.device_subscriptions:
                        self.device_subscriptions[device_id] = set()
                    self.device_subscriptions[device_id].add(client_id)
                return
            
            # 处理取消订阅
            if message_type == "unsubscribe":
                device_id = data.get("device_id")
                if device_id and client_id in self.connections:
                    self.connections[client_id].subscriptions.discard(str(device_id))
                    device_subs = self.device_subscriptions.get(device_id)
                    if device_subs:
                        device_subs.discard(client_id)
                return
            
            # 处理音频数据（双向语音对讲）
            if message_type == MessageType.AUDIO_DATA:
                device_id = data.get("device_id")
                if device_id:
                    # 转发给对应设备的其他客户端
                    await self.send_to_device(device_id, data)
                return
            
            # 处理控制命令
            if message_type == MessageType.CONTROL:
                # 可以在这里处理各种控制命令
                print(f"收到控制命令: {data}")
                return
                
        except json.JSONDecodeError:
            print(f"无法解析消息: {message}")
        except Exception as e:
            print(f"处理消息失败: {e}")
            self.stats.errors += 1
    
    async def _heartbeat_checker(self):
        """心跳检测后台任务"""
        while True:
            try:
                current_time = time.time()
                disconnected_clients = []
                
                for client_id, conn_info in self.connections.items():
                    if current_time - conn_info.last_heartbeat > self.heartbeat_timeout:
                        disconnected_clients.append(client_id)
                
                for client_id in disconnected_clients:
                    print(f"心跳超时，断开连接: {client_id}")
                    await self.disconnect(client_id)
                
                await asyncio.sleep(10)  # 每10秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"心跳检测异常: {e}")
                await asyncio.sleep(5)
    
    async def _message_processor(self):
        """消息处理后台任务"""
        while True:
            try:
                # 从队列获取消息并处理
                client_id, message = await self.message_queue.get()
                await self.handle_client_message(client_id, message)
                self.message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"消息处理异常: {e}")
                await asyncio.sleep(1)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取性能统计
        
        Returns:
            统计信息
        """
        return {
            "total_connections": self.stats.total_connections,
            "active_connections": self.stats.active_connections,
            "messages_sent": self.stats.messages_sent,
            "messages_received": self.stats.messages_received,
            "bytes_sent": self.stats.bytes_sent,
            "bytes_received": self.stats.bytes_received,
            "errors": self.stats.errors,
            "avg_latency_ms": self.stats.avg_latency_ms,
            "device_subscriptions": {
                str(device_id): len(subs) 
                for device_id, subs in self.device_subscriptions.items()
            }
        }
    
    def get_connection_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        获取连接信息
        
        Args:
            client_id: 客户端ID
            
        Returns:
            连接信息
        """
        if client_id not in self.connections:
            return None
        
        conn_info = self.connections[client_id]
        return {
            "client_id": conn_info.client_id,
            "connected_at": conn_info.connected_at,
            "last_heartbeat": conn_info.last_heartbeat,
            "client_type": conn_info.client_type,
            "device_id": conn_info.device_id,
            "subscriptions": list(conn_info.subscriptions)
        }
    
    def get_all_connections(self) -> List[Dict[str, Any]]:
        """
        获取所有连接信息
        
        Returns:
            连接信息列表
        """
        return [
            self.get_connection_info(client_id)
            for client_id in self.connections.keys()
        ]


# 全局WebSocket管理器实例
ws_manager = WebSocketManager()
