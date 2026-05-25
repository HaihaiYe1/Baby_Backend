from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import deque
import json


class ConversationMemory:
    """Agent对话记忆管理"""
    
    def __init__(self, max_history: int = 50, retention_hours: int = 24):
        """
        初始化记忆管理器
        
        Args:
            max_history: 最大历史记录数
            retention_hours: 记忆保留时间（小时）
        """
        self.max_history = max_history
        self.retention_hours = retention_hours
        
        # 对话历史
        self.conversation_history: deque = deque(maxlen=max_history)
        
        # 检测状态记忆
        self.detection_state: Dict[str, Any] = {
            "last_detection_time": None,
            "consecutive_danger_count": 0,
            "last_notification_time": None,
            "active_risks": [],
            "device_status": {}
        }
        
        # 用户偏好记忆
        self.user_preferences: Dict[str, Any] = {
            "notification_cooldown_seconds": 300,  # 5分钟冷却
            "sensitivity_level": "medium",  # low, medium, high
            "auto_notify": True
        }
    
    def add_conversation(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加对话记录"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,  # "user", "agent", "system"
            "content": content,
            "metadata": metadata or {}
        }
        self.conversation_history.append(entry)
        self._cleanup_old_entries()
    
    def add_detection_result(
        self,
        detection_result: Dict[str, Any],
        device_id: int
    ) -> None:
        """添加检测结果到记忆"""
        timestamp = datetime.now()
        
        # 更新检测状态
        self.detection_state["last_detection_time"] = timestamp.isoformat()
        
        # 分析危险级别
        overall_level = detection_result.get("overall_level", "safe")
        
        if overall_level in ["warning", "danger"]:
            self.detection_state["consecutive_danger_count"] += 1
            self.detection_state["active_risks"].append({
                "timestamp": timestamp.isoformat(),
                "level": overall_level,
                "device_id": device_id,
                "causes": detection_result.get("causes", [])
            })
            
            # 只保留最近10个风险记录
            if len(self.detection_state["active_risks"]) > 10:
                self.detection_state["active_risks"] = \
                    self.detection_state["active_risks"][-10:]
        else:
            # 安全状态重置连续危险计数
            self.detection_state["consecutive_danger_count"] = 0
        
        # 更新设备状态
        self.detection_state["device_status"][device_id] = {
            "last_seen": timestamp.isoformat(),
            "status": "online",
            "last_level": overall_level
        }
        
        # 记录到对话历史
        self.add_conversation(
            role="system",
            content=f"检测完成: {overall_level}",
            metadata={
                "type": "detection",
                "device_id": device_id,
                "result": detection_result
            }
        )
    
    def should_send_notification(self, detection_result: Dict[str, Any]) -> bool:
        """判断是否应该发送通知"""
        # 检查通知冷却时间
        if self.detection_state["last_notification_time"]:
            last_notif = datetime.fromisoformat(
                self.detection_state["last_notification_time"]
            )
            cooldown = timedelta(
                seconds=self.user_preferences["notification_cooldown_seconds"]
            )
            if datetime.now() - last_notif < cooldown:
                return False
        
        # 检查危险级别
        overall_level = detection_result.get("overall_level", "safe")
        if overall_level not in ["warning", "danger"]:
            return False
        
        # 检查连续危险次数（避免单次误报）
        consecutive_count = self.detection_state["consecutive_danger_count"]
        sensitivity = self.user_preferences["sensitivity_level"]
        
        threshold_map = {
            "low": 5,      # 连续5次才通知
            "medium": 3,   # 连续3次才通知
            "high": 1      # 立即通知
        }
        
        return consecutive_count >= threshold_map.get(sensitivity, 3)
    
    def mark_notification_sent(self) -> None:
        """标记已发送通知"""
        self.detection_state["last_notification_time"] = \
            datetime.now().isoformat()
    
    def get_context_summary(self, last_n: int = 5) -> str:
        """获取上下文摘要"""
        recent_entries = list(self.conversation_history)[-last_n:]
        
        if not recent_entries:
            return "无历史记录"
        
        summary_parts = []
        for entry in recent_entries:
            timestamp = entry["timestamp"][:19]  # 去掉毫秒
            role = entry["role"]
            content = entry["content"][:100]  # 截断过长内容
            summary_parts.append(f"[{timestamp}] {role}: {content}")
        
        return "\n".join(summary_parts)
    
    def get_detection_summary(self) -> Dict[str, Any]:
        """获取检测状态摘要"""
        return {
            "last_detection": self.detection_state["last_detection_time"],
            "consecutive_danger_count": \
                self.detection_state["consecutive_danger_count"],
            "active_risks_count": \
                len(self.detection_state["active_risks"]),
            "active_devices": \
                list(self.detection_state["device_status"].keys()),
            "user_sensitivity": \
                self.user_preferences["sensitivity_level"]
        }
    
    def update_user_preferences(
        self,
        preferences: Dict[str, Any]
    ) -> None:
        """更新用户偏好设置"""
        self.user_preferences.update(preferences)
    
    def _cleanup_old_entries(self):
        """清理过期的记忆条目"""
        if not self.conversation_history:
            return
        
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        cutoff_str = cutoff_time.isoformat()
        
        # 清理过期的风险记录
        self.detection_state["active_risks"] = [
            risk for risk in self.detection_state["active_risks"]
            if risk["timestamp"] > cutoff_str
        ]
    
    def reset(self) -> None:
        """重置记忆"""
        self.conversation_history.clear()
        self.detection_state = {
            "last_detection_time": None,
            "consecutive_danger_count": 0,
            "last_notification_time": None,
            "active_risks": [],
            "device_status": {}
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """导出记忆状态为字典"""
        return {
            "conversation_history": list(self.conversation_history),
            "detection_state": self.detection_state,
            "user_preferences": self.user_preferences
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        """从字典恢复记忆状态"""
        memory = cls()
        memory.conversation_history = deque(
            data.get("conversation_history", []),
            maxlen=memory.max_history
        )
        memory.detection_state = data.get("detection_state", {})
        memory.user_preferences = data.get("user_preferences", {})
        return memory
