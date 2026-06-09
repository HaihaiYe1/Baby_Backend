from typing import Dict, Any, List, Optional, Union
import os
import json
from datetime import datetime

try:
    from langchain.agents import AgentExecutor, create_openai_tools_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
    
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from sqlalchemy.orm import Session

from .tools import DetectionTool, NotificationTool, DeviceTool
from .prompts import AgentPrompts
from .memory import ConversationMemory
from app.rag.advisor import parenting_advisor
from app.tools.smart_home import SpeakerTool, LightTool, SceneTool
from app.config import settings


class BabyAgent:
    """婴儿看护AI Agent核心类"""
    
    def __init__(
        self,
        db: Session,
        user_id: int,
        openai_api_key: Optional[str] = None,
        model_name: str = "MiMo-V2.5-Pro",
        use_agent_mode: bool = True
    ):
        """
        初始化BabyAgent
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            openai_api_key: OpenAI API密钥（可选，默认从环境变量读取）
            model_name: 使用的模型名称
            use_agent_mode: 是否使用Agent模式（False则使用传统规则模式）
        """
        self.db = db
        self.user_id = user_id
        self.use_agent_mode = use_agent_mode
        
        # 初始化记忆
        self.memory = ConversationMemory()
        
        # 初始化工具
        self.tools = self._initialize_tools()
        
        # 初始化育儿顾问
        self.advisor = parenting_advisor
        
        # 初始化LLM（如果使用Agent模式）
        if use_agent_mode:
            # 小米MiMo API配置 - 从环境变量读取
            api_key = openai_api_key or os.getenv("MIMO_API_KEY")
            base_url = os.getenv("MIMO_BASE_URL", "https://api.mimo.xiaomi.com/v1")
            
            if not api_key:
                print("警告: 未设置MIMO_API_KEY，将使用传统模式")
                self.use_agent_mode = False
            else:
                self.llm = ChatOpenAI(
                    model=model_name,
                    api_key=api_key,
                    base_url=base_url,
                    temperature=0.1,  # 低温度，更确定性的响应
                    max_tokens=1024
                )
                self.agent_executor = self._create_agent_executor()
    
    def _initialize_tools(self) -> List[Any]:
        """初始化Agent工具集"""
        return [
            DetectionTool(),
            NotificationTool(db=self.db),
            DeviceTool(db=self.db),
            SpeakerTool(),
            LightTool(),
            SceneTool()
        ]
    
    def _create_agent_executor(self) -> AgentExecutor:
        """创建Agent执行器"""
        # 创建提示词模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", AgentPrompts.get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # 创建Agent
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # 创建Agent执行器
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            early_stopping_method="generate"
        )
    
    async def analyze_frame(
        self,
        frame_data: str,
        device_id: int,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析视频帧
        
        Args:
            frame_data: Base64编码的视频帧
            device_id: 设备ID
            context: 额外上下文信息
            
        Returns:
            分析结果，包含检测结果和Agent决策
        """
        timestamp = datetime.now().isoformat()
        
        if self.use_agent_mode:
            return await self._analyze_with_agent(
                frame_data, device_id, timestamp, context
            )
        else:
            return await self._analyze_with_rules(
                frame_data, device_id, timestamp
            )
    
    async def _analyze_with_agent(
        self,
        frame_data: str,
        device_id: int,
        timestamp: str,
        context: Optional[str]
    ) -> Dict[str, Any]:
        """使用Agent模式分析"""
        # 构建输入
        input_text = f"""请分析来自设备 {device_id} 的视频帧（时间：{timestamp}）。
        
任务：
1. 使用video_detection工具分析视频帧
2. 评估检测结果的安全级别
3. 如果存在风险，决定是否需要发送通知
4. 提供简要的分析说明

{f'上下文信息：{context}' if context else ''}

请开始分析。"""
        
        try:
            # 执行Agent
            result = await self.agent_executor.ainvoke({
                "input": input_text,
                "chat_history": self._get_chat_history()
            })
            
            # 解析Agent输出
            agent_output = result.get("output", "")
            
            # 记录到记忆
            self.memory.add_conversation(
                role="agent",
                content=agent_output,
                metadata={"device_id": device_id, "timestamp": timestamp}
            )
            
            return {
                "mode": "agent",
                "timestamp": timestamp,
                "device_id": device_id,
                "agent_output": agent_output,
                "success": True
            }
            
        except Exception as e:
            error_msg = f"Agent分析失败: {str(e)}"
            print(error_msg)
            
            # 降级到规则模式
            return await self._analyze_with_rules(
                frame_data, device_id, timestamp
            )
    
    async def _analyze_with_rules(
        self,
        frame_data: str,
        device_id: int,
        timestamp: str
    ) -> Dict[str, Any]:
        """使用传统规则模式分析（降级方案）"""
        # 使用检测工具
        detection_tool = self.tools[0]  # DetectionTool
        detection_result = detection_tool._run(frame_data)
        
        # 记录检测结果
        self.memory.add_detection_result(detection_result, device_id)
        
        # 判断是否需要通知
        should_notify = self.memory.should_send_notification(detection_result)
        
        notification_sent = False
        if should_notify:
            # 使用通知工具
            notification_tool = self.tools[1]  # NotificationTool
            overall_level = detection_result.get("overall_level", "safe")
            causes = detection_result.get("causes", [])
            
            # 构建通知消息
            if causes:
                cause_messages = [c.get("reason", "") for c in causes[:3]]
                message = f"检测到风险: {', '.join(cause_messages)}"
            else:
                message = f"检测到{overall_level}级别风险"
            
            notif_result = notification_tool._run(
                user_id=self.user_id,
                device_id=device_id,
                level=overall_level,
                message=message
            )
            
            notification_sent = notif_result.get("success", False)
            if notification_sent:
                self.memory.mark_notification_sent()
        
        return {
            "mode": "rules",
            "timestamp": timestamp,
            "device_id": device_id,
            "detection_result": detection_result,
            "should_notify": should_notify,
            "notification_sent": notification_sent,
            "success": True
        }
    
    def _get_chat_history(self) -> List[Any]:
        """获取聊天历史（LangChain格式）"""
        history = []
        for entry in list(self.memory.conversation_history)[-10:]:  # 最近10条
            role = entry["role"]
            content = entry["content"]
            
            if role == "user":
                history.append(HumanMessage(content=content))
            elif role == "agent":
                history.append(AIMessage(content=content))
        
        return history
    
    def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "mode": "agent" if self.use_agent_mode else "rules",
            "user_id": self.user_id,
            "memory_summary": self.memory.get_detection_summary(),
            "tools_available": [t.name for t in self.tools]
        }
    
    def update_preferences(self, preferences: Dict[str, Any]) -> None:
        """更新用户偏好"""
        self.memory.update_user_preferences(preferences)
    
    def reset_memory(self) -> None:
        """重置记忆"""
        self.memory.reset()


class BabyAgentManager:
    """BabyAgent管理器，管理多个用户的Agent实例"""
    
    def __init__(self):
        self._agents: Dict[int, Union[BabyAgent, Any]] = {}  # BabyAgent or LangGraphBabyAgent
        self._langgraph_agents: Dict[int, Any] = {}  # LangGraphBabyAgent instances
    
    def get_or_create_agent(
        self,
        db: Session,
        user_id: int,
        use_langgraph: Optional[bool] = None,
        **kwargs
    ) -> Union[BabyAgent, Any]:
        """
        获取或创建用户的Agent
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            use_langgraph: 是否使用LangGraph（None则从配置读取）
            **kwargs: 其他参数
            
        Returns:
            BabyAgent或LangGraphBabyAgent实例
        """
        if use_langgraph is None:
            use_langgraph = settings.USE_LANGGRAPH
        
        if use_langgraph:
            return self._get_or_create_langgraph_agent(db, user_id, **kwargs)
        else:
            return self._get_or_create_legacy_agent(db, user_id, **kwargs)
    
    def _get_or_create_legacy_agent(
        self,
        db: Session,
        user_id: int,
        **kwargs
    ) -> BabyAgent:
        """获取或创建传统Agent"""
        if user_id not in self._agents:
            self._agents[user_id] = BabyAgent(
                db=db,
                user_id=user_id,
                **kwargs
            )
        return self._agents[user_id]
    
    def _get_or_create_langgraph_agent(
        self,
        db: Session,
        user_id: int,
        **kwargs
    ) -> Any:
        """获取或创建LangGraph Agent"""
        from .langgraph_agent import LangGraphBabyAgent
        
        if user_id not in self._langgraph_agents:
            self._langgraph_agents[user_id] = LangGraphBabyAgent(
                db=db,
                user_id=user_id,
                **kwargs
            )
        return self._langgraph_agents[user_id]
    
    def remove_agent(self, user_id: int) -> None:
        """移除用户的Agent"""
        if user_id in self._agents:
            del self._agents[user_id]
        if user_id in self._langgraph_agents:
            del self._langgraph_agents[user_id]
    
    def get_all_agents_status(self) -> Dict[int, Dict[str, Any]]:
        """获取所有Agent的状态"""
        status = {}
        
        # 传统Agent状态
        for user_id, agent in self._agents.items():
            status[user_id] = agent.get_status()
        
        # LangGraph Agent状态
        for user_id, agent in self._langgraph_agents.items():
            status[user_id] = agent.get_status()
        
        return status


# 全局Agent管理器实例
agent_manager = BabyAgentManager()
