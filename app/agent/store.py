from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class InMemoryStore:
    """
    内存存储（开发/测试用）
    
    生产环境应使用Redis或数据库存储
    """
    
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
    
    def put(self, namespace: tuple, key: str, value: Dict[str, Any]) -> None:
        """存储数据"""
        ns_str = ":".join(str(n) for n in namespace)
        if ns_str not in self._storage:
            self._storage[ns_str] = {}
        self._storage[ns_str][key] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
    
    def get(self, namespace: tuple, key: str) -> Optional[Dict[str, Any]]:
        """获取数据"""
        ns_str = ":".join(str(n) for n in namespace)
        if ns_str in self._storage and key in self._storage[ns_str]:
            return self._storage[ns_str][key]["value"]
        return None
    
    def delete(self, namespace: tuple, key: str) -> bool:
        """删除数据"""
        ns_str = ":".join(str(n) for n in namespace)
        if ns_str in self._storage and key in self._storage[ns_str]:
            del self._storage[ns_str][key]
            return True
        return False
    
    def list_keys(self, namespace: tuple) -> List[str]:
        """列出命名空间下的所有键"""
        ns_str = ":".join(str(n) for n in namespace)
        if ns_str in self._storage:
            return list(self._storage[ns_str].keys())
        return []
    
    def search(self, namespace: tuple, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索数据（简单文本匹配）"""
        ns_str = ":".join(str(n) for n in namespace)
        results = []
        
        if ns_str in self._storage:
            for key, data in self._storage[ns_str].items():
                value = data["value"]
                # 简单的文本匹配搜索
                value_str = json.dumps(value, ensure_ascii=False).lower()
                if query.lower() in value_str or query.lower() in key.lower():
                    results.append({
                        "key": key,
                        "value": value,
                        "timestamp": data["timestamp"]
                    })
                    
                    if len(results) >= limit:
                        break
        
        return results


class UserPreferenceStore:
    """用户偏好存储"""
    
    def __init__(self, store: Optional[InMemoryStore] = None):
        self.store = store or InMemoryStore()
    
    def save_preferences(self, user_id: int, preferences: Dict[str, Any]) -> None:
        """保存用户偏好"""
        self.store.put(
            ("user_prefs", str(user_id)),
            "preferences",
            {
                **preferences,
                "updated_at": datetime.now().isoformat()
            }
        )
    
    def get_preferences(self, user_id: int) -> Dict[str, Any]:
        """获取用户偏好"""
        prefs = self.store.get(("user_prefs", str(user_id)), "preferences")
        return prefs or self._get_default_preferences()
    
    def update_preference(self, user_id: int, key: str, value: Any) -> None:
        """更新单个偏好"""
        prefs = self.get_preferences(user_id)
        prefs[key] = value
        self.save_preferences(user_id, prefs)
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """获取默认偏好"""
        return {
            "notification_level": "warning",  # safe | warning | danger
            "notification_methods": ["app_push"],
            "quiet_hours": {
                "enabled": False,
                "start": "22:00",
                "end": "07:00"
            },
            "baby_age_months": None,
            "preferred_scenes": ["sleep", "comfort"],
            "language": "zh-CN"
        }


class ConversationStore:
    """对话历史存储"""
    
    def __init__(self, store: Optional[InMemoryStore] = None):
        self.store = store or InMemoryStore()
    
    def save_message(
        self,
        user_id: int,
        thread_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """保存消息"""
        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # 获取现有消息
        messages = self.get_messages(user_id, thread_id)
        messages.append(message)
        
        # 只保留最近100条消息
        if len(messages) > 100:
            messages = messages[-100:]
        
        self.store.put(
            ("conversations", str(user_id)),
            thread_id,
            {"messages": messages}
        )
    
    def get_messages(
        self,
        user_id: int,
        thread_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取消息历史"""
        data = self.store.get(("conversations", str(user_id)), thread_id)
        if data:
            messages = data.get("messages", [])
            return messages[-limit:]
        return []
    
    def get_threads(self, user_id: int) -> List[str]:
        """获取用户的所有线程"""
        return self.store.list_keys(("conversations", str(user_id)))
    
    def delete_thread(self, user_id: int, thread_id: str) -> bool:
        """删除线程"""
        return self.store.delete(("conversations", str(user_id)), thread_id)


# 全局存储实例
store = InMemoryStore()
user_preference_store = UserPreferenceStore(store)
conversation_store = ConversationStore(store)
