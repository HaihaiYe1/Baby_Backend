import time
from typing import Optional
import cv2


def get_video_capture(source: str) -> cv2.VideoCapture:
    """获取视频捕获对象"""
    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        raise ValueError(f"无法打开视频源: {source}")
    
    return cap


def read_frame(
    cap: cv2.VideoCapture,
    min_interval: float = 0.2,
    last_time: Optional[list] = None
) -> Optional[cv2.typing.MatLike]:
    """
    读取视频帧
    
    Args:
        cap: 视频捕获对象
        min_interval: 最小帧间隔（秒），默认0.2表示每秒5帧
        last_time: 上次读取时间（内部使用）
    
    Returns:
        视频帧或None
    """
    if last_time is None:
        last_time = [0.0]
    
    now = time.time()
    if now - last_time[0] < min_interval:
        return None
    
    ret, frame = cap.read()
    if not ret:
        return None
    
    last_time[0] = now
    return frame
