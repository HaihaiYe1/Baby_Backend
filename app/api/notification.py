import logging
import asyncio
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.models import Notification, User
from app.schemas import NotificationCreate, NotificationUpdate
from app.crud import create_notification
from app.utils.database import get_db
from app.api.websocket import send_alert_message
from app.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_class=JSONResponse)
def list_notifications(
    skip: int = Query(0, description="跳过前 N 条记录"),
    limit: int = Query(20, description="返回的最大记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取通知列表"""
    try:
        notifications = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.deleted == False
        ).order_by(
            Notification.pinned.desc(),
            Notification.timestamp.desc()
        ).offset(skip).limit(limit).all()

        result = [n.to_dict() for n in notifications]
        return JSONResponse(content=jsonable_encoder(result), media_type="application/json")
    except Exception as e:
        logger.error(f"获取通知列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching notifications")


@router.post("")
async def add_notification(
    notification: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新通知"""
    try:
        if not notification.message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        if notification.level not in ["safe", "warning", "danger"]:
            raise HTTPException(status_code=400, detail="Invalid level")

        new_notification = create_notification(
            db=db,
            notification_data=notification,
            user_id=current_user.id
        )

        # 异步WebSocket推送
        message = f"New alert: {notification.level} - {notification.message}"
        asyncio.create_task(send_alert_message(notification.level, message, new_notification.id))

        logger.info(f"用户 {current_user.email} 创建通知: {new_notification.id}")
        return {
            "message": "Notification created successfully",
            "data": new_notification.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建通知失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating notification")


@router.put("/{notification_id}")
def update_notification(
    notification_id: int,
    updated_data: NotificationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新通知"""
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        # 按需更新字段
        if updated_data.message is not None:
            notification.message = updated_data.message
        if updated_data.level is not None:
            notification.level = updated_data.level
        if updated_data.pinned is not None:
            notification.pinned = updated_data.pinned
        if updated_data.deleted is not None:
            notification.deleted = updated_data.deleted
        if updated_data.device_id is not None:
            notification.device_id = updated_data.device_id

        db.commit()
        db.refresh(notification)

        logger.info(f"用户 {current_user.email} 更新通知: {notification_id}")
        return {"message": "Notification updated", "data": notification.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新通知失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating notification")


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除单条通知（软删除）"""
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        notification.deleted = True
        db.commit()
        
        logger.info(f"用户 {current_user.email} 删除通知: {notification_id}")
        return {"message": "Notification deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除通知失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting notification")


@router.post("/{notification_id}/pin")
def toggle_pin_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """置顶/取消置顶通知"""
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        notification.pinned = not notification.pinned
        db.commit()
        db.refresh(notification)

        logger.info(f"用户 {current_user.email} 切换通知置顶: {notification_id} -> {notification.pinned}")
        return {
            "message": "Notification pin state updated",
            "pinned": notification.pinned
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新置顶状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating pin status")


@router.delete("/clear")
def clear_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """清空通知（批量软删除）"""
    try:
        count = db.query(Notification).filter(
            Notification.user_id == current_user.id
        ).update({Notification.deleted: True})
        db.commit()
        
        logger.info(f"用户 {current_user.email} 清空通知: {count} 条")
        return {"message": "All notifications cleared", "count": count}
    except Exception as e:
        logger.error(f"清空通知失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error clearing notifications")
