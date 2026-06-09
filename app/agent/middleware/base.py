from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.agent.state import BabyAgentState


class AgentMiddleware(ABC):
    """Agent中间件基类"""
    
    @abstractmethod
    async def before_model(self, state: BabyAgentState) -> BabyAgentState:
        """
        模型调用前处理
        
        Args:
            state: 当前Agent状态
            
        Returns:
            处理后的状态
        """
        pass
    
    @abstractmethod
    async def after_model(self, state: BabyAgentState, response: str) -> str:
        """
        模型调用后处理
        
        Args:
            state: 当前Agent状态
            response: 模型响应
            
        Returns:
            处理后的响应
        """
        pass
    
    async def process(self, state: BabyAgentState) -> Dict[str, Any]:
        """
        处理状态（用于LangGraph节点）
        
        Args:
            state: 当前Agent状态
            
        Returns:
            更新的状态
        """
        # 前置处理
        processed_state = await self.before_model(state)
        
        # 返回状态更新
        return {
            k: v for k, v in processed_state.items() 
            if k in state and state[k] != v
        }
