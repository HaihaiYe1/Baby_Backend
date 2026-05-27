from typing import Dict, Any, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import cv2
import numpy as np


class DetectionInput(BaseModel):
    """检测工具输入参数"""
    frame_data: str = Field(description="Base64编码的视频帧数据")
    detection_types: list = Field(
        default=["danger", "suffocation", "action"],
        description="检测类型列表：danger, suffocation, action"
    )


class DetectionTool(BaseTool):
    """视频检测工具，封装YOLOv8和MediaPipe检测"""
    name: str = "video_detection"
    description: str = "分析视频帧，检测婴儿周围的危险物品、窒息风险和异常姿态"
    args_schema: Type[BaseModel] = DetectionInput
    
    _detector: Any = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from app.detection.multi_detector import MultiDetector
        self._detector = MultiDetector()
    
    def _run(
        self,
        frame_data: str,
        detection_types: list = ["danger", "suffocation", "action"]
    ) -> Dict[str, Any]:
        """执行检测"""
        try:
            # 解码Base64图像数据
            import base64
            frame_bytes = base64.b64decode(frame_data)
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {"error": "无法解码图像数据", "overall_level": "unknown"}
            
            # 执行多模态检测
            result = self._detector.detect(frame)
            return result
            
        except Exception as e:
            return {"error": f"检测失败: {str(e)}", "overall_level": "unknown"}
    
    async def _arun(self, frame_data: str, detection_types: list = None) -> Dict[str, Any]:
        """异步执行检测（暂不支持，调用同步版本）"""
        return self._run(frame_data, detection_types or ["danger", "suffocation", "action"])
