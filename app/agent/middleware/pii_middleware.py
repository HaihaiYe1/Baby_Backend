import re
from typing import Dict, Any
from .base import AgentMiddleware
from app.agent.state import BabyAgentState


class PIIMiddleware(AgentMiddleware):
    """
    PII（个人身份信息）过滤中间件
    
    检测并处理敏感信息：
    - 手机号
    - 邮箱
    - 身份证号
    - 银行卡号
    """
    
    # PII检测模式
    PII_PATTERNS = {
        "phone": r'1[3-9]\d{9}',
        "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        "id_card": r'\d{17}[\dXx]',
        "bank_card": r'\d{16,19}'
    }
    
    def __init__(self, strategy: str = "mask"):
        """
        初始化PII中间件
        
        Args:
            strategy: 处理策略
                - "redact": 完全删除
                - "mask": 部分遮挡
                - "block": 阻止请求
        """
        self.strategy = strategy
    
    async def before_model(self, state: BabyAgentState) -> BabyAgentState:
        """检测PII并处理"""
        messages = state.get("messages", [])
        if not messages:
            return state
        
        # 检查最后一条消息
        last_message = messages[-1]
        content = last_message.content if hasattr(last_message, 'content') else ""
        
        # 检测PII
        pii_found = self._detect_pii(content)
        
        if pii_found:
            # 根据策略处理
            if self.strategy == "block":
                # 阻止请求，添加警告消息
                state["messages"] = messages[:-1] + [
                    type(last_message)(content="检测到敏感信息，请勿在对话中包含个人身份信息。")
                ]
            elif self.strategy == "mask":
                # 遮挡敏感信息
                masked_content = self._mask_pii(content)
                state["messages"] = messages[:-1] + [
                    type(last_message)(content=masked_content)
                ]
            elif self.strategy == "redact":
                # 删除敏感信息
                redacted_content = self._redact_pii(content)
                state["messages"] = messages[:-1] + [
                    type(last_message)(content=redacted_content)
                ]
        
        return state
    
    async def after_model(self, state: BabyAgentState, response: str) -> str:
        """处理模型响应中的PII"""
        # 检查响应中是否包含PII
        pii_found = self._detect_pii(response)
        
        if pii_found:
            # 遮挡响应中的PII
            return self._mask_pii(response)
        
        return response
    
    def _detect_pii(self, text: str) -> Dict[str, list]:
        """检测文本中的PII"""
        found = {}
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                found[pii_type] = matches
        return found
    
    def _mask_pii(self, text: str) -> str:
        """遮挡PII"""
        # 遮挡手机号
        text = re.sub(
            r'(1[3-9]\d)(\d{4})(\d{4})',
            r'\1****\3',
            text
        )
        
        # 遮挡邮箱
        text = re.sub(
            r'([a-zA-Z0-9._%+-]+)(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'****\2',
            text
        )
        
        # 遮挡身份证号
        text = re.sub(
            r'(\d{6})\d{8}(\d{3}[\dXx])',
            r'\1********\2',
            text
        )
        
        # 遮挡银行卡号
        text = re.sub(
            r'(\d{4})\d{8,12}(\d{4})',
            r'\1********\2',
            text
        )
        
        return text
    
    def _redact_pii(self, text: str) -> str:
        """删除PII"""
        for pii_type, pattern in self.PII_PATTERNS.items():
            text = re.sub(pattern, f'[{pii_type}]', text)
        return text
