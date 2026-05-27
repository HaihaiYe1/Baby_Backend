import logging
from typing import Dict, Any, Optional, List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.models import Device

logger = logging.getLogger(__name__)


class DeviceQueryInput(BaseModel):
    """设备查询输入参数"""
    user_id: int = Field(description="用户ID")
    device_id: Optional[int] = Field(default=None, description="设备ID（可选）")


class DeviceControlInput(BaseModel):
    """设备控制输入参数"""
    device_id: int = Field(description="设备ID")
    action: str = Field(description="控制动作：status, start_detect, stop_detect")
    parameters: Optional[Dict] = Field(default=None, description="额外参数")


class DeviceTool(BaseTool):
    """设备管理工具，用于查询和控制设备"""
    name: str = "device_management"
    description: str = "管理监控设备，包括查询设备状态、启动/停止检测等"
    args_schema: Type[BaseModel] = DeviceControlInput
    
    _db: Any = None
    
    def __init__(self, db: Session, **kwargs):
        super().__init__(**kwargs)
        self._db = db
    
    def _run(
        self,
        device_id: int,
        action: str,
        parameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """执行设备操作"""
        try:
            # 查询设备
            device = self._db.query(Device).filter(Device.id == device_id).first()
            if not device:
                return {"success": False, "error": f"设备 {device_id} 不存在"}
            
            if action == "status":
                return {
                    "success": True,
                    "device_id": device.id,
                    "name": device.name,
                    "ip": device.ip,
                    "status": device.status,
                    "rtsp_url": device.rtsp_url
                }
            
            elif action == "start_detect":
                return {
                    "success": True,
                    "device_id": device_id,
                    "action": "start_detect",
                    "message": f"已启动设备 {device.name} 的检测"
                }
            
            elif action == "stop_detect":
                return {
                    "success": True,
                    "device_id": device_id,
                    "action": "stop_detect",
                    "message": f"已停止设备 {device.name} 的检测"
                }
            
            else:
                return {"success": False, "error": f"不支持的操作: {action}"}
                
        except Exception as e:
            logger.error(f"设备操作失败: {e}", exc_info=True)
            return {"success": False, "error": f"设备操作失败: {str(e)}"}
    
    async def _arun(
        self,
        device_id: int,
        action: str,
        parameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """异步执行设备操作"""
        return self._run(device_id, action, parameters)


class DeviceQueryTool(BaseTool):
    """设备查询工具"""
    name: str = "query_devices"
    description: str = "查询用户的所有设备或特定设备信息"
    args_schema: Type[BaseModel] = DeviceQueryInput
    
    _db: Any = None
    
    def __init__(self, db: Session, **kwargs):
        super().__init__(**kwargs)
        self._db = db
    
    def _run(
        self,
        user_id: int,
        device_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """查询设备"""
        try:
            if device_id:
                device = self._db.query(Device).filter(
                    Device.id == device_id
                ).first()
                if device:
                    return {
                        "success": True,
                        "device": {
                            "id": device.id,
                            "name": device.name,
                            "ip": device.ip,
                            "status": device.status,
                            "rtsp_url": device.rtsp_url
                        }
                    }
                else:
                    return {"success": False, "error": f"设备 {device_id} 不存在"}
            else:
                devices = self._db.query(Device).filter(
                    Device.email == user_id
                ).all()
                
                device_list = [
                    {
                        "id": d.id,
                        "name": d.name,
                        "ip": d.ip,
                        "status": d.status,
                        "rtsp_url": d.rtsp_url
                    }
                    for d in devices
                ]
                
                return {"success": True, "devices": device_list}
                
        except Exception as e:
            logger.error(f"查询设备失败: {e}", exc_info=True)
            return {"success": False, "error": f"查询设备失败: {str(e)}"}
    
    async def _arun(
        self,
        user_id: int,
        device_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """异步查询设备"""
        return self._run(user_id, device_id)
