import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models import Device, User, Notification
from app.schemas import DeviceCreate, DeviceUpdate
from app.utils.database import get_db
from app.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/add")
def add_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加新设备"""
    # 使用当前用户的email
    new_device = Device(
        email=current_user.email,
        name=device.name,
        ip=device.ip,
        status=device.status,
        rtsp_url=device.ip  # 默认使用ip作为rtsp_url
    )
    db.add(new_device)
    try:
        db.commit()
        db.refresh(new_device)
    except Exception as e:
        db.rollback()
        logger.error(f"添加设备失败: {e}")
        raise HTTPException(status_code=500, detail="添加设备失败")
    
    logger.info(f"用户 {current_user.email} 添加设备: {new_device.name}")
    return {"message": "Device added successfully", "device_id": new_device.id}


@router.get("/list")
def get_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的设备列表"""
    devices = db.query(Device).filter(Device.email == current_user.email).all()

    return [
        {
            "id": d.id,
            "name": d.name,
            "email": d.email,
            "ip": d.ip,
            "status": d.status,
            "rtsp_url": d.rtsp_url
        }
        for d in devices
    ]


@router.get("/get_rtsp_url")
def get_rtsp_url(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户设备的RTSP地址"""
    devices = db.query(Device).filter(Device.email == current_user.email).all()
    if not devices:
        raise HTTPException(status_code=404, detail="Devices not found")

    return {"rtspUrl": devices[0].rtsp_url}


@router.put("/update")
def update_device(
    device_update: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新设备信息"""
    device = db.query(Device).filter(Device.id == device_update.id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # 验证设备属于当前用户
    if device.email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to update this device")

    # 仅更新非None字段
    if device_update.name is not None:
        device.name = device_update.name
    if device_update.ip is not None:
        device.ip = device_update.ip
    if device_update.status is not None:
        device.status = device_update.status
    if device_update.rtsp_url is not None:
        device.rtsp_url = device_update.rtsp_url

    try:
        db.commit()
        db.refresh(device)
    except Exception as e:
        db.rollback()
        logger.error(f"更新设备失败: {e}")
        raise HTTPException(status_code=500, detail="更新设备失败")
    
    logger.info(f"用户 {current_user.email} 更新设备: {device.id}")
    return {"message": "Device updated successfully"}


@router.delete("/delete")
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除设备"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # 验证设备属于当前用户
    if device.email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to delete this device")

    try:
        # 先删除关联的通知记录
        deleted_notifications = db.query(Notification).filter(
            Notification.device_id == device_id
        ).delete(synchronize_session=False)
        logger.info(f"删除设备 {device_id} 关联的通知: {deleted_notifications} 条")
        
        # 删除设备
        db.delete(device)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"删除设备失败: {e}")
        raise HTTPException(status_code=500, detail="删除设备失败")
    
    logger.info(f"用户 {current_user.email} 删除设备: {device_id}")
    return {"message": "Device deleted successfully"}


@router.get("/{device_id}")
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定设备信息"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # 验证设备属于当前用户
    if device.email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to access this device")

    return {
        "id": device.id,
        "name": device.name,
        "email": device.email,
        "ip": device.ip,
        "status": device.status,
        "rtsp_url": device.rtsp_url
    }
