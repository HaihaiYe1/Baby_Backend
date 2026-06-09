from typing import Dict, Any, List, Optional
from .base import AgentMiddleware
from app.agent.state import BabyAgentState


class HITLMiddleware(AgentMiddleware):
    """
    Human-In-The-Loop中间件
    
    用于敏感操作的人工审核：
    - 发送通知
    - 控制智能家居设备
    - 执行危险操作
    """
    
    # 需要人工审核的工具
    INTERRUPT_TOOLS = [
        "send_notification",
        "smart_scene",
        "control_speaker",
        "control_light"
    ]
    
    def __init__(self, auto_approve_safe: bool = True):
        """
        初始化HITL中间件
        
        Args:
            auto_approve_safe: 是否自动批准安全操作
        """
        self.auto_approve_safe = auto_approve_safe
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
    
    async def before_model(self, state: BabyAgentState) -> BabyAgentState:
        """检查是否需要人工审核"""
        # 检查是否有待审批的操作
        if state.get("pending_approval"):
            return state
        
        return state
    
    async def after_model(self, state: BabyAgentState, response: str) -> str:
        """处理模型响应"""
        return response
    
    def should_interrupt(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """
        判断是否需要中断进行人工审核
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            
        Returns:
            是否需要中断
        """
        # 检查是否在需要审核的工具列表中
        if tool_name not in self.INTERRUPT_TOOLS:
            return False
        
        # 如果启用了自动批准安全操作
        if self.auto_approve_safe:
            # 检查操作是否安全
            if self._is_safe_operation(tool_name, tool_args):
                return False
        
        return True
    
    def _is_safe_operation(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """判断操作是否安全"""
        # 通知操作
        if tool_name == "send_notification":
            level = tool_args.get("level", "safe")
            # 安全级别通知不需要审核
            return level == "safe"
        
        # 灯光操作
        if tool_name == "control_light":
            action = tool_args.get("action", "")
            # 关灯操作不需要审核
            return action == "off"
        
        # 音箱操作
        if tool_name == "control_speaker":
            action = tool_args.get("action", "")
            # 播放白噪音等安全操作不需要审核
            return action in ["play_white_noise", "stop"]
        
        return False
    
    def create_approval_request(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        user_id: int,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建审批请求
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            user_id: 用户ID
            context: 上下文信息
            
        Returns:
            审批请求
        """
        request_id = f"{user_id}_{tool_name}_{id(tool_args)}"
        
        request = {
            "request_id": request_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "user_id": user_id,
            "context": context,
            "status": "pending"
        }
        
        self.pending_approvals[request_id] = request
        return request
    
    def approve_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """批准请求"""
        if request_id in self.pending_approvals:
            self.pending_approvals[request_id]["status"] = "approved"
            return self.pending_approvals.pop(request_id)
        return None
    
    def reject_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """拒绝请求"""
        if request_id in self.pending_approvals:
            self.pending_approvals[request_id]["status"] = "rejected"
            return self.pending_approvals.pop(request_id)
        return None
    
    def get_pending_requests(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取待审批请求"""
        requests = list(self.pending_approvals.values())
        
        if user_id is not None:
            requests = [r for r in requests if r["user_id"] == user_id]
        
        return requests
