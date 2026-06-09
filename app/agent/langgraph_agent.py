from typing import Dict, Any, List, Optional, Annotated
import os
import json
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import BaseTool

from sqlalchemy.orm import Session

from .state import BabyAgentState
from .checkpointer import create_checkpointer
from .tools import DetectionTool, NotificationTool, DeviceTool
from .prompts import AgentPrompts
from app.rag.advisor import parenting_advisor
from app.rag.retriever import RAGRetriever
from app.tools.smart_home import SpeakerTool, LightTool, SceneTool
from app.config import settings


class LangGraphBabyAgent:
    """基于LangGraph的婴儿看护AI Agent"""
    
    def __init__(
        self,
        db: Session,
        user_id: int,
        openai_api_key: Optional[str] = None,
        model_name: str = "MiMo-V2.5-Pro"
    ):
        self.db = db
        self.user_id = user_id
        
        # 初始化LLM
        api_key = openai_api_key or settings.MIMO_API_KEY
        base_url = settings.MIMO_BASE_URL
        
        if not api_key:
            raise ValueError("MIMO_API_KEY is required for LangGraph agent")
        
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.1,
            max_tokens=1024
        )
        
        # 初始化工具
        self.tools = self._initialize_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # 绑定工具到LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # 初始化RAG检索器
        self.retriever = RAGRetriever()
        
        # 初始化checkpointer
        self.checkpointer = create_checkpointer()
        
        # 构建图
        self.graph = self._build_graph()
    
    def _initialize_tools(self) -> List[BaseTool]:
        """初始化Agent工具集"""
        return [
            DetectionTool(),
            NotificationTool(db=self.db),
            DeviceTool(db=self.db),
            SpeakerTool(),
            LightTool(),
            SceneTool()
        ]
    
    def _build_graph(self) -> StateGraph:
        """构建LangGraph状态图"""
        graph = StateGraph(BabyAgentState)
        
        # 添加节点
        graph.add_node("llm", self._llm_node)
        graph.add_node("tools", ToolNode(self.tools))
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("assess_risk", self._assess_risk_node)
        graph.add_node("notify", self._notify_node)
        graph.add_node("rules_mode", self._rules_mode_node)
        
        # 定义边
        graph.add_edge(START, "llm")
        graph.add_conditional_edges("llm", self._should_continue, {
            "tools": "tools",
            "retrieve": "retrieve",
            "end": END
        })
        graph.add_edge("tools", "assess_risk")
        graph.add_edge("retrieve", "assess_risk")
        graph.add_conditional_edges("assess_risk", self._should_notify, {
            "notify": "notify",
            "end": END
        })
        graph.add_edge("notify", END)
        
        # 编译图
        return graph.compile(checkpointer=self.checkpointer)
    
    async def _llm_node(self, state: BabyAgentState) -> Dict[str, Any]:
        """LLM节点 - 调用MiMo LLM"""
        messages = state.get("messages", [])
        
        # 添加系统提示
        system_prompt = AgentPrompts.get_system_prompt()
        full_messages = [SystemMessage(content=system_prompt)] + messages
        
        # 调用LLM
        response = await self.llm_with_tools.ainvoke(full_messages)
        
        return {"messages": [response]}
    
    async def _retrieve_node(self, state: BabyAgentState) -> Dict[str, Any]:
        """RAG检索节点"""
        messages = state.get("messages", [])
        if not messages:
            return {"retrieved_knowledge": []}
        
        # 获取最后一条用户消息
        last_message = messages[-1]
        query = last_message.content if isinstance(last_message, HumanMessage) else ""
        
        if not query:
            return {"retrieved_knowledge": []}
        
        # 检索相关知识
        try:
            results = await self.retriever.retrieve(query, top_k=5)
            return {"retrieved_knowledge": results}
        except Exception as e:
            print(f"RAG retrieval error: {e}")
            return {"retrieved_knowledge": []}
    
    async def _assess_risk_node(self, state: BabyAgentState) -> Dict[str, Any]:
        """风险评估节点"""
        detection_results = state.get("detection_results", {})
        
        if not detection_results:
            return {"risk_level": "safe", "should_notify": False}
        
        # 评估风险级别
        overall_level = detection_results.get("overall_level", "safe")
        consecutive_danger = state.get("consecutive_danger_count", 0)
        
        # 更新连续危险计数
        if overall_level == "danger":
            consecutive_danger += 1
        else:
            consecutive_danger = 0
        
        # 决定是否通知
        should_notify = (
            overall_level == "danger" or
            (overall_level == "warning" and consecutive_danger >= 3)
        )
        
        return {
            "risk_level": overall_level,
            "consecutive_danger_count": consecutive_danger,
            "should_notify": should_notify
        }
    
    async def _notify_node(self, state: BabyAgentState) -> Dict[str, Any]:
        """通知节点"""
        risk_level = state.get("risk_level", "safe")
        detection_results = state.get("detection_results", {})
        user_id = state.get("user_id", self.user_id)
        device_id = state.get("device_id", "unknown")
        
        # 构建通知消息
        causes = detection_results.get("causes", [])
        if causes:
            cause_messages = [c.get("reason", "") for c in causes[:3]]
            message = f"检测到风险: {', '.join(cause_messages)}"
        else:
            message = f"检测到{risk_level}级别风险"
        
        # 发送通知
        notification_tool = self.tool_map.get("send_notification")
        if notification_tool:
            try:
                result = await notification_tool.ainvoke({
                    "user_id": user_id,
                    "device_id": device_id,
                    "level": risk_level,
                    "message": message
                })
                return {"notification_sent": True, "notification_level": risk_level}
            except Exception as e:
                print(f"Notification error: {e}")
        
        return {"notification_sent": False}
    
    async def _rules_mode_node(self, state: BabyAgentState) -> Dict[str, Any]:
        """规则模式降级节点"""
        # 当LLM失败时，使用规则模式处理
        return {"use_rules_mode": True}
    
    def _should_continue(self, state: BabyAgentState) -> str:
        """决定下一步：调用工具、检索或结束"""
        messages = state.get("messages", [])
        if not messages:
            return "end"
        
        last_message = messages[-1]
        
        # 检查是否有工具调用
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            # 检查是否需要RAG检索
            for tool_call in last_message.tool_calls:
                if tool_call["name"] == "search_knowledge":
                    return "retrieve"
            return "tools"
        
        return "end"
    
    def _should_notify(self, state: BabyAgentState) -> str:
        """决定是否发送通知"""
        if state.get("should_notify", False):
            return "notify"
        return "end"
    
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
            分析结果
        """
        timestamp = datetime.now().isoformat()
        
        # 构建输入消息
        input_text = f"""请分析来自设备 {device_id} 的视频帧（时间：{timestamp}）。
        
任务：
1. 使用video_detection工具分析视频帧
2. 评估检测结果的安全级别
3. 如果存在风险，决定是否需要发送通知
4. 提供简要的分析说明

{f'上下文信息：{context}' if context else ''}

请开始分析。"""
        
        # 配置thread_id
        thread_id = f"user_{self.user_id}_device_{device_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # 执行图
            result = await self.graph.ainvoke(
                {
                    "messages": [HumanMessage(content=input_text)],
                    "user_id": self.user_id,
                    "device_id": str(device_id)
                },
                config=config
            )
            
            # 提取输出
            messages = result.get("messages", [])
            agent_output = messages[-1].content if messages else ""
            
            return {
                "mode": "langgraph",
                "timestamp": timestamp,
                "device_id": device_id,
                "agent_output": agent_output,
                "risk_level": result.get("risk_level", "safe"),
                "notification_sent": result.get("notification_sent", False),
                "success": True
            }
            
        except Exception as e:
            error_msg = f"LangGraph分析失败: {str(e)}"
            print(error_msg)
            
            # 降级到规则模式
            return await self._fallback_rules_mode(frame_data, device_id, timestamp)
    
    async def _fallback_rules_mode(
        self,
        frame_data: str,
        device_id: int,
        timestamp: str
    ) -> Dict[str, Any]:
        """降级到规则模式"""
        detection_tool = self.tool_map.get("video_detection")
        if not detection_tool:
            return {"mode": "fallback", "success": False, "error": "No detection tool"}
        
        try:
            detection_result = await detection_tool.ainvoke({"frame_data": frame_data})
            
            return {
                "mode": "rules_fallback",
                "timestamp": timestamp,
                "device_id": device_id,
                "detection_result": detection_result,
                "success": True
            }
        except Exception as e:
            return {"mode": "fallback", "success": False, "error": str(e)}
    
    async def chat(
        self,
        message: str,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        与Agent对话
        
        Args:
            message: 用户消息
            thread_id: 线程ID（可选）
            
        Returns:
            对话结果
        """
        if not thread_id:
            thread_id = f"user_{self.user_id}_chat"
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            result = await self.graph.ainvoke(
                {
                    "messages": [HumanMessage(content=message)],
                    "user_id": self.user_id
                },
                config=config
            )
            
            messages = result.get("messages", [])
            response = messages[-1].content if messages else ""
            
            return {
                "response": response,
                "thread_id": thread_id,
                "success": True
            }
            
        except Exception as e:
            return {
                "response": f"处理消息时出错: {str(e)}",
                "thread_id": thread_id,
                "success": False
            }
    
    async def stream_chat(
        self,
        message: str,
        thread_id: Optional[str] = None
    ):
        """
        流式对话
        
        Args:
            message: 用户消息
            thread_id: 线程ID（可选）
            
        Yields:
            流式响应片段
        """
        if not thread_id:
            thread_id = f"user_{self.user_id}_chat"
        
        config = {"configurable": {"thread_id": thread_id}}
        
        async for event in self.graph.astream_events(
            {
                "messages": [HumanMessage(content=message)],
                "user_id": self.user_id
            },
            config=config,
            version="v2"
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield {"type": "content", "data": chunk.content}
            elif event["event"] == "on_tool_end":
                yield {"type": "tool_result", "data": event["data"]}
    
    def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "mode": "langgraph",
            "user_id": self.user_id,
            "tools_available": [t.name for t in self.tools],
            "checkpoint_backend": settings.LANGGRAPH_CHECKPOINT_BACKEND
        }
