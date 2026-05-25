from typing import Dict, Any, Optional, List
import cv2
import numpy as np
import base64

from app.detection.multi_detector import MultiDetector
from app.services.vlm_service import vlm_service


class SceneAnalyzer:
    """场景分析器，整合传统CV和VLM的双层感知"""
    
    def __init__(self):
        """初始化场景分析器"""
        self.cv_detector = MultiDetector()
        self.use_vlm = True  # 是否使用VLM
    
    async def analyze_frame(
        self,
        frame: np.ndarray,
        frame_id: int = 0,
        device_id: int = 0
    ) -> Dict[str, Any]:
        """
        分析视频帧
        
        Args:
            frame: OpenCV图像帧
            frame_id: 帧ID
            device_id: 设备ID
            
        Returns:
            分析结果
        """
        # 第一层：传统CV检测
        cv_results = self.cv_detector.detect(frame)
        
        # 初始化结果
        analysis_result = {
            "frame_id": frame_id,
            "device_id": device_id,
            "cv_detection": cv_results,
            "vlm_analysis": None,
            "combined_analysis": None,
            "final_assessment": None
        }
        
        # 第二层：VLM深度推理（如果启用）
        if self.use_vlm:
            try:
                # 将帧编码为Base64
                _, buffer = cv2.imencode('.jpg', frame)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # VLM分析
                vlm_result = await vlm_service.analyze_scene(
                    frame_base64,
                    cv_results
                )
                
                analysis_result["vlm_analysis"] = vlm_result
                
                # 合并分析结果
                combined = self._combine_analyses(cv_results, vlm_result)
                analysis_result["combined_analysis"] = combined
                
                # 最终评估
                final = self._make_final_assessment(cv_results, combined)
                analysis_result["final_assessment"] = final
                
            except Exception as e:
                print(f"VLM分析失败: {e}")
                # 降级到仅CV结果
                analysis_result["vlm_analysis"] = {"success": False, "error": str(e)}
                analysis_result["combined_analysis"] = cv_results
                analysis_result["final_assessment"] = self._make_cv_only_assessment(cv_results)
        else:
            # 仅使用CV结果
            analysis_result["combined_analysis"] = cv_results
            analysis_result["final_assessment"] = self._make_cv_only_assessment(cv_results)
        
        return analysis_result
    
    def _combine_analyses(
        self,
        cv_results: Dict[str, Any],
        vlm_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并CV和VLM分析结果
        """
        if not vlm_results.get("success", False):
            return cv_results
        
        scene_analysis = vlm_results.get("scene_analysis", {})
        
        if not scene_analysis.get("parsed", False):
            return cv_results
        
        vlm_data = scene_analysis.get("data", {})
        
        # 提取VLM分析结果
        baby_status = vlm_data.get("baby_status", "unknown")
        environment_assessment = vlm_data.get("environment_assessment", "unknown")
        detection_accuracy = vlm_data.get("detection_accuracy", "unknown")
        actual_risk_level = vlm_data.get("actual_risk_level", "unknown")
        risk_details = vlm_data.get("risk_details", [])
        recommendations = vlm_data.get("recommendations", [])
        confidence = vlm_data.get("confidence", 0.5)
        
        # 构建合并结果
        combined = {
            "overall_level": self._determine_overall_level(
                cv_results.get("overall_level", "safe"),
                actual_risk_level
            ),
            "baby_status": baby_status,
            "environment_assessment": environment_assessment,
            "cv_detection_accuracy": detection_accuracy,
            "risk_details": risk_details,
            "recommendations": recommendations,
            "confidence": confidence,
            "cv_level": cv_results.get("overall_level", "safe"),
            "vlm_level": actual_risk_level,
            "causes": cv_results.get("causes", [])
        }
        
        return combined
    
    def _determine_overall_level(
        self,
        cv_level: str,
        vlm_level: str
    ) -> str:
        """
        确定整体安全级别
        """
        level_priority = {"safe": 0, "warning": 1, "danger": 2}
        
        cv_priority = level_priority.get(cv_level, 0)
        vlm_priority = level_priority.get(vlm_level, 0)
        
        # 取更高的风险级别
        max_priority = max(cv_priority, vlm_priority)
        
        for level, priority in level_priority.items():
            if priority == max_priority:
                return level
        
        return "safe"
    
    def _make_final_assessment(
        self,
        cv_results: Dict[str, Any],
        combined_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        做出最终评估
        """
        overall_level = combined_results.get("overall_level", "safe")
        confidence = combined_results.get("confidence", 0.5)
        cv_level = combined_results.get("cv_level", "safe")
        vlm_level = combined_results.get("vlm_level", "safe")
        
        # 判断是否需要通知
        should_notify = overall_level in ["warning", "danger"]
        
        # 判断是否为误报
        is_false_positive = (
            cv_level in ["warning", "danger"] and
            vlm_level == "safe" and
            combined_results.get("cv_detection_accuracy") == "false_positive"
        )
        
        # 生成通知消息
        notification_message = None
        if should_notify and not is_false_positive:
            risk_details = combined_results.get("risk_details", [])
            recommendations = combined_results.get("recommendations", [])
            
            if risk_details:
                notification_message = f"检测到风险: {', '.join(risk_details[:3])}"
            else:
                notification_message = f"检测到{overall_level}级别风险"
            
            if recommendations:
                notification_message += f"。建议: {', '.join(recommendations[:2])}"
        
        return {
            "overall_level": overall_level,
            "should_notify": should_notify,
            "is_false_positive": is_false_positive,
            "confidence": confidence,
            "notification_message": notification_message,
            "baby_status": combined_results.get("baby_status", "unknown"),
            "environment_assessment": combined_results.get("environment_assessment", "unknown")
        }
    
    def _make_cv_only_assessment(
        self,
        cv_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        仅基于CV结果的评估
        """
        overall_level = cv_results.get("overall_level", "safe")
        causes = cv_results.get("cause", [])
        
        should_notify = overall_level in ["warning", "danger"]
        
        notification_message = None
        if should_notify:
            if causes:
                cause_messages = [c.get("reason", "") for c in causes[:3]]
                notification_message = f"检测到风险: {', '.join(cause_messages)}"
            else:
                notification_message = f"检测到{overall_level}级别风险"
        
        return {
            "overall_level": overall_level,
            "should_notify": should_notify,
            "is_false_positive": False,
            "confidence": 0.7,  # CV结果置信度
            "notification_message": notification_message,
            "baby_status": "unknown",
            "environment_assessment": "unknown"
        }
    
    def enable_vlm(self, enable: bool = True):
        """启用/禁用VLM分析"""
        self.use_vlm = enable
    
    async def generate_notification(
        self,
        detection_type: str,
        risk_level: str,
        details: str
    ) -> Dict[str, Any]:
        """
        生成通知消息
        """
        return await vlm_service.generate_notification_message(
            detection_type,
            risk_level,
            details
        )


# 全局场景分析器实例
scene_analyzer = SceneAnalyzer()
