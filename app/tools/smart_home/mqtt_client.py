import os
import json
import time
from typing import Dict, Any, Optional, Callable, List
import paho.mqtt.client as mqtt


class MQTTClient:
    """MQTT客户端封装"""
    
    def __init__(
        self,
        broker_host: Optional[str] = None,
        broker_port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: str = "baby_monitor_agent"
    ):
        """
        初始化MQTT客户端
        
        Args:
            broker_host: MQTT代理地址
            broker_port: MQTT代理端口
            username: 用户名
            password: 密码
            client_id: 客户端ID
        """
        self.broker_host = broker_host or os.getenv("MQTT_BROKER_HOST", "localhost")
        self.broker_port = broker_port or int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.username = username or os.getenv("MQTT_USERNAME")
        self.password = password or os.getenv("MQTT_PASSWORD")
        self.client_id = client_id
        
        # 初始化MQTT客户端
        self.client = mqtt.Client(client_id=self.client_id)
        
        # 设置认证
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        # 设置回调
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # 状态
        self.connected = False
        self.subscriptions: Dict[str, List[Callable]] = {}
        
        # 消息历史
        self.message_history: List[Dict[str, Any]] = []
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.connected = True
            print(f"MQTT连接成功: {self.broker_host}:{self.broker_port}")
            
            # 重新订阅
            for topic in self.subscriptions:
                self.client.subscribe(topic)
        else:
            print(f"MQTT连接失败，错误码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.connected = False
        print(f"MQTT断开连接，错误码: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """消息回调"""
        try:
            payload = json.loads(msg.payload.decode())
            topic = msg.topic
            
            # 记录消息历史
            self.message_history.append({
                "timestamp": time.time(),
                "topic": topic,
                "payload": payload
            })
            
            # 限制历史记录数量
            if len(self.message_history) > 100:
                self.message_history = self.message_history[-100:]
            
            # 调用订阅回调
            if topic in self.subscriptions:
                for callback in self.subscriptions[topic]:
                    try:
                        callback(topic, payload)
                    except Exception as e:
                        print(f"回调执行失败: {e}")
                        
        except json.JSONDecodeError:
            print(f"无法解析消息: {msg.payload}")
    
    def connect(self) -> bool:
        """
        连接到MQTT代理
        
        Returns:
            是否连接成功
        """
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            
            # 等待连接
            timeout = 10
            start_time = time.time()
            while not self.connected and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            return self.connected
            
        except Exception as e:
            print(f"MQTT连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
    
    def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        qos: int = 0
    ) -> bool:
        """
        发布消息
        
        Args:
            topic: 主题
            payload: 消息内容
            qos: 服务质量等级
            
        Returns:
            是否发布成功
        """
        if not self.connected:
            print("MQTT未连接")
            return False
        
        try:
            json_payload = json.dumps(payload)
            result = self.client.publish(topic, json_payload, qos=qos)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # 记录消息历史
                self.message_history.append({
                    "timestamp": time.time(),
                    "topic": topic,
                    "payload": payload,
                    "direction": "out"
                })
                return True
            else:
                print(f"发布失败，错误码: {result.rc}")
                return False
                
        except Exception as e:
            print(f"发布异常: {e}")
            return False
    
    def subscribe(
        self,
        topic: str,
        callback: Optional[Callable] = None,
        qos: int = 0
    ) -> bool:
        """
        订阅主题
        
        Args:
            topic: 主题
            callback: 回调函数
            qos: 服务质量等级
            
        Returns:
            是否订阅成功
        """
        if not self.connected:
            print("MQTT未连接")
            return False
        
        try:
            result, mid = self.client.subscribe(topic, qos=qos)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                # 添加回调
                if topic not in self.subscriptions:
                    self.subscriptions[topic] = []
                
                if callback:
                    self.subscriptions[topic].append(callback)
                
                return True
            else:
                print(f"订阅失败，错误码: {result}")
                return False
                
        except Exception as e:
            print(f"订阅异常: {e}")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """
        取消订阅
        
        Args:
            topic: 主题
            
        Returns:
            是否取消成功
        """
        try:
            result, mid = self.client.unsubscribe(topic)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                # 移除回调
                if topic in self.subscriptions:
                    del self.subscriptions[topic]
                return True
            else:
                return False
                
        except Exception as e:
            print(f"取消订阅异常: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取客户端状态
        
        Returns:
            状态信息
        """
        return {
            "connected": self.connected,
            "broker_host": self.broker_host,
            "broker_port": self.broker_port,
            "client_id": self.client_id,
            "subscriptions": list(self.subscriptions.keys()),
            "message_count": len(self.message_history)
        }
    
    def get_message_history(
        self,
        topic: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取消息历史
        
        Args:
            topic: 过滤主题
            limit: 返回数量限制
            
        Returns:
            消息历史
        """
        history = self.message_history
        
        if topic:
            history = [msg for msg in history if msg.get("topic") == topic]
        
        return history[-limit:]


# 全局MQTT客户端实例
mqtt_client = MQTTClient()
