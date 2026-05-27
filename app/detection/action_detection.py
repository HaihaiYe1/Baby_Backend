# detection/action_detection.py
import cv2
import numpy as np
from typing import List, Dict, Any

try:
    import mediapipe as mp
    
    # 尝试新版本API
    if hasattr(mp, 'solutions'):
        MP_AVAILABLE = True
    else:
        MP_AVAILABLE = False
except ImportError:
    MP_AVAILABLE = False


class ActionDetector:
    """姿态检测器"""
    
    def __init__(self, detection_confidence=0.5):
        self.mp_pose = None
        self.pose = None
        self.mp_drawing = None
        
        if MP_AVAILABLE:
            try:
                self.mp_pose = mp.solutions.pose
                self.pose = self.mp_pose.Pose(
                    static_image_mode=False,
                    model_complexity=1,
                    enable_segmentation=False,
                    min_detection_confidence=detection_confidence
                )
                self.mp_drawing = mp.solutions.drawing_utils
            except Exception as e:
                print(f"MediaPipe初始化失败: {e}")

    def detect(self, frame) -> List[Dict[str, Any]]:
        """检测姿态"""
        if self.pose is None:
            return [{"level": "safe", "reason": "mediapipe_not_available"}]
        
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)

            if not results.pose_landmarks:
                return [{"level": "danger", "reason": "no_pose_detected"}]

            landmarks = results.pose_landmarks.landmark

            # 关键点索引
            NOSE = 0
            LEFT_SHOULDER = 11
            RIGHT_SHOULDER = 12
            LEFT_HIP = 23
            RIGHT_HIP = 24

            # 获取关键点坐标
            nose_y = landmarks[NOSE].y
            shoulder_y = (landmarks[LEFT_SHOULDER].y + landmarks[RIGHT_SHOULDER].y) / 2
            hip_y = (landmarks[LEFT_HIP].y + landmarks[RIGHT_HIP].y) / 2

            # 逻辑判断
            if nose_y > hip_y + 0.05:
                return [{"level": "danger", "reason": "fall_detected"}]
            elif nose_y > shoulder_y:
                return [{"level": "warning", "reason": "face_down"}]
            else:
                return [{"level": "safe", "reason": "normal"}]
                
        except Exception as e:
            return [{"level": "safe", "reason": f"detection_error: {str(e)}"}]
