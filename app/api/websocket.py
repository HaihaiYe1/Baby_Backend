import logging
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import List
import json

logger = logging.getLogger(__name__)

router = APIRouter()

connected_clients: List[WebSocket] = []


@router.websocket("/alerts")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info("新客户端连接 WebSocket")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info("客户端断开 WebSocket")


async def send_alert_message(level: str, message: str, alert_id: int = 1):
    """推送警报消息"""
    data = {
        "id": alert_id,
        "level": level,
        "message": message
    }
    json_data = json.dumps(data, ensure_ascii=False)

    logger.info(f"推送消息给 {len(connected_clients)} 个客户端: {message}")

    disconnected_clients = []
    for client in connected_clients:
        try:
            await client.send_text(json_data)
        except Exception as e:
            logger.warning(f"WebSocket 推送失败: {e}")
            disconnected_clients.append(client)

    for client in disconnected_clients:
        connected_clients.remove(client)
        logger.info("移除断开连接的客户端")
