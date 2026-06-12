import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.utils.database import get_db, SessionLocal
from app.models import Device
from app.detection.multi_detector import MultiDetector
from app.utils.video_utils import get_video_capture, read_frame
import time
import os
import threading
import base64
import cv2

from app.schemas import NotificationCreate
from app.crud import create_notification
from app.api.websocket import send_alert_message
from app.utils.security import get_current_user
from app.models import User
from app.agent import BabyAgent
from app.agent.baby_agent import agent_manager
from app.services.scene_analyzer import scene_analyzer

logger = logging.getLogger(__name__)

router = APIRouter()
multi_detector = MultiDetector()

# 从配置读取冷却时间
COOL_DOWN_TIME = int(os.getenv("DETECTION_COOLDOWN_SECONDS", "5"))
DETECTION_THREADS = {}
STOP_FLAGS = {}
_threads_lock = threading.Lock()


# 启动持续检测
@router.post("/start-detect")
def start_detect(
        device_id: int = Query(..., description="设备 ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    with _threads_lock:
        if device_id in DETECTION_THREADS:
            raise HTTPException(status_code=400, detail="检测已在运行")

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device or not device.rtsp_url:
        raise HTTPException(status_code=404, detail="设备不存在或未配置 RTSP 流地址")

    stop_flag = threading.Event()
    
    with _threads_lock:
        STOP_FLAGS[device_id] = stop_flag

    def detection_loop():
        """检测循环 - 在独立线程中运行"""
        cap = None
        db_session = None
        try:
            cap = get_video_capture(device.rtsp_url)
            # 在线程中创建新的数据库会话
            db_session = SessionLocal()
            notified_messages = {}
            
            # 获取事件循环用于异步调用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            while not stop_flag.is_set():
                frame = read_frame(cap)
                if frame is None:
                    continue

                detection = multi_detector.detect(frame)

                if isinstance(detection, dict):
                    causes = detection.get("causes", [])
                    for cause in causes:
                        level = cause.get("level")
                        message = cause.get("reason")

                        if level in ["warning", "danger"]:
                            current_time = time.time()
                            if message not in notified_messages or current_time - notified_messages.get(message, 0) >= COOL_DOWN_TIME:
                                try:
                                    notification_data = NotificationCreate(
                                        device_id=device_id,
                                        level=level,
                                        message=message
                                    )
                                    notification = create_notification(db_session, notification_data, user_id=current_user.id)

                                    # 使用事件循环执行异步操作
                                    loop.run_until_complete(
                                        send_alert_message(level=level, message=message, alert_id=notification.id)
                                    )

                                    notified_messages[message] = current_time
                                except Exception as e:
                                    logger.error(f"创建通知失败: {e}")

                time.sleep(0.1)
            
            loop.close()
            
        except Exception as e:
            logger.error(f"检测循环异常: {e}")
        finally:
            if cap is not None:
                cap.release()
            if db_session is not None:
                db_session.close()

    t = threading.Thread(target=detection_loop, daemon=True)
    with _threads_lock:
        DETECTION_THREADS[device_id] = t
    t.start()

    return {"message": f"已启动设备 {device.name} 的持续检测"}


# 停止持续检测
@router.post("/stop-detect")
def stop_detect(
        device_id: int = Query(..., description="设备 ID"),
):
    with _threads_lock:
        if device_id not in DETECTION_THREADS:
            raise HTTPException(status_code=400, detail="该设备未在检测中")

        STOP_FLAGS[device_id].set()
        thread = DETECTION_THREADS[device_id]

    thread.join(timeout=5)

    with _threads_lock:
        del DETECTION_THREADS[device_id]
        del STOP_FLAGS[device_id]

    return {"message": f"已停止设备 {device_id} 的检测"}


# Agent模式检测接口
@router.post("/agent-detect")
async def agent_detect(
        device_id: int = Query(..., description="设备 ID"),
        max_frames: int = Query(5, description="最多处理多少帧"),
        use_agent: bool = Query(True, description="是否使用Agent模式"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    使用AI Agent进行视频分析
    """
    # 获取设备信息
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device or not device.rtsp_url:
        raise HTTPException(status_code=404, detail="设备不存在或未配置 RTSP 流地址")
    
    # 获取或创建Agent
    agent = agent_manager.get_or_create_agent(
        db=db,
        user_id=current_user.id,
        use_agent_mode=use_agent
    )
    
    # 打开视频流
    cap = get_video_capture(device.rtsp_url)
    if not cap.isOpened():
        raise HTTPException(status_code=500, detail="无法打开视频流")
    
    results = []
    count = 0
    
    try:
        while count < max_frames:
            frame = read_frame(cap)
            if frame is None:
                break
            
            # 将帧转换为Base64
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # 使用Agent分析
            analysis_result = await agent.analyze_frame(
                frame_data=frame_base64,
                device_id=device_id,
                context=f"设备名称: {device.name}"
            )
            
            results.append({
                "frame_index": count,
                "timestamp": time.time(),
                "analysis": analysis_result
            })
            
            count += 1
            await asyncio.sleep(0.1)
    
    finally:
        cap.release()
    
    return {
        "device_name": device.name,
        "video_source": device.rtsp_url,
        "frames_processed": count,
        "agent_mode": use_agent,
        "results": results,
        "agent_status": agent.get_status()
    }


# 获取Agent状态
@router.get("/agent-status")
async def get_agent_status(
        current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的Agent状态
    """
    agent = agent_manager.get_or_create_agent(
        db=None,  # 不需要数据库
        user_id=current_user.id
    )
    return agent.get_status()


# 更新Agent偏好设置
@router.put("/agent-preferences")
async def update_agent_preferences(
        preferences: dict,
        current_user: User = Depends(get_current_user)
):
    """
    更新Agent的用户偏好设置
    """
    agent = agent_manager.get_or_create_agent(
        db=None,
        user_id=current_user.id
    )
    agent.update_preferences(preferences)
    return {"message": "偏好设置已更新", "preferences": preferences}


# 没有用的接口，还不知道怎么用
@router.get("/detect")
async def detect_video_source(
        device_id: int = Query(None, description="设备 ID（用于从数据库获取 RTSP 地址）"),
        video_path: str = Query(None, description="本地测试视频路径（如传入则优先使用）"),
        max_frames: int = Query(10, description="最多处理多少帧"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)  # ✅ 获取当前登录用户
):

    # 检测接口：支持本地视频或设备 ID 对应的 RTSP 流。
    # 优先使用本地视频路径，如未提供则使用数据库中设备的 RTSP 地址。

    # 优先使用本地视频路径
    if video_path:
        if not os.path.exists(video_path):
            raise HTTPException(status_code=400, detail="本地视频文件不存在")

        cap = get_video_capture(video_path)
        source_info = video_path  # 视频路径作为源信息
        device_name = "LocalTest"
        device_id = None  # 本地视频测试时没有设备 ID，设为 None
    elif device_id is not None:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="设备不存在")
        if not device.rtsp_url:
            raise HTTPException(status_code=400, detail="设备未配置 RTSP 流地址")

        cap = get_video_capture(device.rtsp_url)
        source_info = device.rtsp_url
        device_name = device.name

    else:
        raise HTTPException(status_code=400, detail="请提供 device_id 或 video_path")

    # 帧检测循环
    results = []
    count = 0
    notified_messages = {}  # 用于记录已经通知的 (frame_index, message) 和通知时间

    while count < max_frames:
        frame = read_frame(cap)
        if frame is None:
            break

        # 执行检测
        detection = multi_detector.detect(frame)

        # 遍历检测结果并根据危险级别创建通知 + 推送
        if isinstance(detection, dict):  # ensure detection is valid
            overall_level = detection.get("overall_level")
            causes = detection.get("causes", [])

            for cause in causes:
                level = cause.get("level")  # 修改为 level
                message = cause.get("reason")  # 修改为 message

                # 只处理 level 为 'warning' 或 'danger' 的情况
                if level in ['warning', 'danger']:
                    current_time = time.time()
                    # 检查是否已经通知过该消息，且冷却时间是否到
                    if message not in notified_messages or current_time - notified_messages[message] >= COOL_DOWN_TIME:
                        if level and message:
                            # 本地视频测试时 device_id 传入 None 或虚拟 ID
                            notification_data = NotificationCreate(
                                device_id=device_id or 1,  # 本地视频时传入 1 或其他虚拟值
                                level=level,
                                message=message
                            )

                            notification = create_notification(
                                db, notification_data,
                                user_id=current_user.id  # 只传 user_id, 因为 level 和 message 已经在 NotificationCreate 中
                            )

                            # ✅ 异步推送 WebSocket 通知
                            await send_alert_message(  # 使用 await
                                level=level,  # 修改为 level
                                message=message,  # 修改为 message
                                alert_id=notification.id
                            )

                            # 更新通知时间
                            notified_messages[message] = current_time

        results.append({
            "frame_index": count,
            "detection": detection
        })

        count += 1
        await asyncio.sleep(0.1)

    cap.release()

    return {
        "device_name": device_name,
        "video_source": source_info,
        "frames_processed": count,
        "results": results
    }


# VLM增强检测接口
@router.post("/vlm-detect")
async def vlm_detect(
        device_id: int = Query(..., description="设备 ID"),
        max_frames: int = Query(3, description="最多处理多少帧"),
        use_vlm: bool = Query(True, description="是否使用VLM分析"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    使用VLM增强的视频分析（双层感知）
    """
    # 获取设备信息
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device or not device.rtsp_url:
        raise HTTPException(status_code=404, detail="设备不存在或未配置 RTSP 流地址")
    
    # 配置场景分析器
    scene_analyzer.enable_vlm(use_vlm)
    
    # 打开视频流
    cap = get_video_capture(device.rtsp_url)
    if not cap.isOpened():
        raise HTTPException(status_code=500, detail="无法打开视频流")
    
    results = []
    count = 0
    
    try:
        while count < max_frames:
            frame = read_frame(cap)
            if frame is None:
                break
            
            # 使用场景分析器分析帧
            analysis = await scene_analyzer.analyze_frame(
                frame=frame,
                frame_id=count,
                device_id=device_id
            )
            
            # 检查是否需要发送通知
            final_assessment = analysis.get("final_assessment", {})
            if final_assessment.get("should_notify", False):
                # 发送通知
                notification_message = final_assessment.get("notification_message", "检测到风险")
                overall_level = final_assessment.get("overall_level", "warning")
                
                # 创建通知
                notification_data = NotificationCreate(
                    device_id=device_id,
                    level=overall_level,
                    message=notification_message
                )
                
                try:
                    notification = create_notification(
                        db, notification_data,
                        user_id=current_user.id
                    )
                    
                    # WebSocket推送
                    await send_alert_message(
                        level=overall_level,
                        message=notification_message,
                        alert_id=notification.id
                    )
                    
                    analysis["notification_sent"] = True
                    analysis["notification_id"] = notification.id
                    
                except Exception as e:
                    print(f"发送通知失败: {e}")
                    analysis["notification_sent"] = False
                    analysis["notification_error"] = str(e)
            
            results.append({
                "frame_index": count,
                "timestamp": time.time(),
                "analysis": analysis
            })
            
            count += 1
            await asyncio.sleep(0.1)
    
    finally:
        cap.release()
    
    # 生成摘要
    summary = {
        "total_frames": count,
        "notifications_sent": sum(1 for r in results if r.get("analysis", {}).get("notification_sent", False)),
        "risk_levels": [r.get("analysis", {}).get("final_assessment", {}).get("overall_level", "safe") for r in results]
    }
    
    return {
        "device_name": device.name,
        "video_source": device.rtsp_url,
        "frames_processed": count,
        "use_vlm": use_vlm,
        "results": results,
        "summary": summary
    }
