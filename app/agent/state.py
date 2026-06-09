from typing import TypedDict, Annotated, NotRequired, Optional
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class BabyAgentState(TypedDict):
    """BabyAgent状态定义"""
    
    # 消息历史（自动累加）
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 检测状态
    detection_results: NotRequired[dict]
    risk_level: NotRequired[str]  # safe | warning | danger
    consecutive_danger_count: NotRequired[int]
    
    # 用户上下文
    user_id: NotRequired[int]
    device_id: NotRequired[str]
    baby_age_months: NotRequired[int]
    
    # RAG上下文
    retrieved_knowledge: NotRequired[list[dict]]
    query_rewrite: NotRequired[str]
    
    # 控制流
    should_notify: NotRequired[bool]
    should_control_device: NotRequired[bool]
    use_rules_mode: NotRequired[bool]
    
    # 通知状态
    notification_sent: NotRequired[bool]
    notification_level: NotRequired[str]
    
    # 设备状态
    device_action: NotRequired[str]
    device_params: NotRequired[dict]
