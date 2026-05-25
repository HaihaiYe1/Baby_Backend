from typing import Dict, Any, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.crud import create_notification
from app.schemas import NotificationCreate
from app.api.websocket import send_alert_message
import asyncio


class NotificationInput(BaseModel):
    """通知工具输入参数"""
    user_id: int = Field(description="用户ID")
    device_id: int = Field(description="设备ID")
    level: str = Field(description="通知级别：safe, warning, danger")
    message: str = Field(description="通知消息内容")


class NotificationTool(BaseTool):
    """通知工具，用于发送报警通知"""
    name = "send_notification"
    description = "向用户发送报警通知，支持WebSocket实时推送"
    args_schema = NotificationInput
    
    def __init__(self, db: Session):
        super().__init__()
        self._db = db
    
    def _run(
        self,
        user_id: int,
        device_id: int,
        level: str,
        message: str
    ) -> Dict[str, Any]:
        """发送通知"""
        try:
            # 创建通知数据
            notification_data = NotificationCreate(
                device_id=device_id,
                level=level,
                message=message
            )
            
            # 保存到数据库
            notification = create_notification(
                self._db,
                notification_data,
                user_id=user_id
            )
            
            # 通过WebSocket推送
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(
                        send_alert_message(
                            level=level,
                            message=message,
                            alert_id=notification.id
                        )
                    )
                else:
                    loop.run_until_complete(
                        send_alert_message(
                            level=level,
                            message=message,
                            alert_id=notification.id
                        )
                    )
            except Exception as ws_error:
                print(f"WebSocket推送失败: {ws_error}")
            
            return {
                "success": True,
                "notification_id": notification.id,
                "level": level,
                "message": message
            }
            
        except Exception as e:
            return {"success": False, "error": f"发送通知失败: {str(e)}"}
    
    async def _arun(
        self,
        user_id: int,
        device_id: int,
        level: str,
        message: str
    ) -> Dict[str, Any]:
        """异步发送通知"""
        return self._run(user_id, device_id, level, message)
