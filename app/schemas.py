from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


# ==================== 用户相关 ====================

class UserCreate(BaseModel):
    """用户注册请求"""
    email: EmailStr
    password: str
    username: str


class UserLogin(BaseModel):
    """用户登录请求"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """修改用户名请求"""
    username: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str


# ==================== 设备相关 ====================

class DeviceCreate(BaseModel):
    """创建设备请求"""
    name: str
    ip: str
    status: str = "offline"


class DeviceUpdate(BaseModel):
    """更新设备请求"""
    id: int
    name: Optional[str] = None
    ip: Optional[str] = None
    status: Optional[str] = None
    rtsp_url: Optional[str] = None


# ==================== 通知相关 ====================

class NotificationBase(BaseModel):
    """通知基础模型"""
    message: str
    level: str
    pinned: Optional[bool] = False
    deleted: Optional[bool] = False
    device_id: Optional[int] = None


class NotificationCreate(NotificationBase):
    """创建通知请求"""
    device_id: int


class Notification(NotificationBase):
    """通知响应模型"""
    id: int
    user_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationUpdate(BaseModel):
    """更新通知请求"""
    message: Optional[str] = None
    level: Optional[str] = None
    pinned: Optional[bool] = None
    deleted: Optional[bool] = None
    device_id: Optional[int] = None


# ==================== 其他 ====================

class HTTPValidationError(BaseModel):
    """错误响应"""
    detail: list
