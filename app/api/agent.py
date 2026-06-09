from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.utils.security import get_current_user
from app.models import User
from app.agent.baby_agent import agent_manager
from app.config import settings
from typing import Dict, Any, Optional
import json

router = APIRouter()


@router.get("/status")
async def get_agent_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的Agent状态
    """
    try:
        agent = agent_manager.get_or_create_agent(
            db=None,
            user_id=current_user.id
        )
        return {
            "success": True,
            "user_id": current_user.id,
            "agent_status": agent.get_status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Agent状态失败: {str(e)}")


@router.post("/initialize")
async def initialize_agent(
    use_agent_mode: bool = Query(True, description="是否使用Agent模式"),
    use_langgraph: Optional[bool] = Query(None, description="是否使用LangGraph"),
    model_name: str = Query("MiMo-V2.5-Pro", description="使用的模型名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    初始化或重新初始化Agent
    """
    try:
        # 移除现有Agent（如果存在）
        agent_manager.remove_agent(current_user.id)
        
        # 创建新Agent
        agent = agent_manager.get_or_create_agent(
            db=db,
            user_id=current_user.id,
            use_langgraph=use_langgraph,
            model_name=model_name
        )
        
        return {
            "success": True,
            "message": "Agent初始化成功",
            "agent_status": agent.get_status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化Agent失败: {str(e)}")


@router.post("/reset-memory")
async def reset_agent_memory(
    current_user: User = Depends(get_current_user)
):
    """
    重置Agent的记忆
    """
    try:
        agent = agent_manager.get_or_create_agent(
            db=None,
            user_id=current_user.id
        )
        
        # 检查是否是LangGraph Agent
        if hasattr(agent, 'reset_memory'):
            agent.reset_memory()
        else:
            # LangGraph Agent使用不同的方式重置
            pass
        
        return {
            "success": True,
            "message": "Agent记忆已重置"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置记忆失败: {str(e)}")


@router.put("/preferences")
async def update_agent_preferences(
    preferences: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    更新Agent的用户偏好设置
    """
    try:
        # 更新到Store
        from app.agent.store import user_preference_store
        user_preference_store.save_preferences(current_user.id, preferences)
        
        return {
            "success": True,
            "message": "偏好设置已更新",
            "preferences": preferences
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新偏好失败: {str(e)}")


@router.get("/memory-summary")
async def get_memory_summary(
    current_user: User = Depends(get_current_user)
):
    """
    获取Agent的记忆摘要
    """
    try:
        from app.agent.store import user_preference_store, conversation_store
        
        preferences = user_preference_store.get_preferences(current_user.id)
        threads = conversation_store.get_threads(current_user.id)
        
        return {
            "success": True,
            "preferences": preferences,
            "threads": threads,
            "threads_count": len(threads)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记忆摘要失败: {str(e)}")


@router.get("/all-agents")
async def get_all_agents_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取所有Agent的状态（管理员功能）
    """
    # 注意：这里应该添加管理员权限检查
    try:
        all_status = agent_manager.get_all_agents_status()
        
        return {
            "success": True,
            "agents_count": len(all_status),
            "agents_status": all_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取所有Agent状态失败: {str(e)}")


@router.delete("/remove")
async def remove_agent(
    current_user: User = Depends(get_current_user)
):
    """
    移除当前用户的Agent
    """
    try:
        agent_manager.remove_agent(current_user.id)
        
        return {
            "success": True,
            "message": "Agent已移除"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"移除Agent失败: {str(e)}")


@router.post("/chat")
async def chat_with_agent(
    message: str = Query(..., description="用户消息"),
    device_id: Optional[int] = Query(None, description="相关设备ID（可选）"),
    thread_id: Optional[str] = Query(None, description="线程ID（可选）"),
    use_langgraph: Optional[bool] = Query(None, description="是否使用LangGraph"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    与Agent进行对话
    """
    try:
        agent = agent_manager.get_or_create_agent(
            db=db,
            user_id=current_user.id,
            use_langgraph=use_langgraph
        )
        
        # LangGraph Agent
        if hasattr(agent, 'chat'):
            result = await agent.chat(message, thread_id)
            
            # 保存到对话历史
            from app.agent.store import conversation_store
            if thread_id:
                conversation_store.save_message(
                    current_user.id, thread_id, "user", message
                )
                conversation_store.save_message(
                    current_user.id, thread_id, "agent", result.get("response", "")
                )
            
            return {
                "success": result.get("success", True),
                "user_message": message,
                "agent_response": result.get("response", ""),
                "thread_id": result.get("thread_id", thread_id)
            }
        
        # 传统Agent
        else:
            # 记录用户消息
            agent.memory.add_conversation(
                role="user",
                content=message,
                metadata={"device_id": device_id}
            )
            
            # 如果有设备ID，可以结合设备上下文
            if device_id:
                context = f"用户正在询问关于设备 {device_id} 的问题"
            else:
                context = "用户正在询问一般性问题"
            
            # 使用Agent处理消息
            response = f"收到您的消息: {message}。Agent正在处理中..."
            
            # 记录Agent响应
            agent.memory.add_conversation(
                role="agent",
                content=response,
                metadata={"device_id": device_id}
            )
            
            return {
                "success": True,
                "user_message": message,
                "agent_response": response,
                "context": context
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"与Agent对话失败: {str(e)}")


@router.post("/chat/stream")
async def stream_chat_with_agent(
    message: str = Query(..., description="用户消息"),
    thread_id: Optional[str] = Query(None, description="线程ID（可选）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    流式与Agent对话（仅支持LangGraph）
    """
    try:
        agent = agent_manager.get_or_create_agent(
            db=db,
            user_id=current_user.id,
            use_langgraph=True
        )
        
        if not hasattr(agent, 'stream_chat'):
            raise HTTPException(
                status_code=400,
                detail="流式对话仅支持LangGraph Agent"
            )
        
        async def generate():
            async for chunk in agent.stream_chat(message, thread_id):
                yield f"data: {json.dumps(chunk)}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流式对话失败: {str(e)}")


@router.get("/threads")
async def list_threads(
    current_user: User = Depends(get_current_user)
):
    """
    列出用户的对话线程
    """
    try:
        from app.agent.store import conversation_store
        threads = conversation_store.get_threads(current_user.id)
        
        return {
            "success": True,
            "threads": threads,
            "count": len(threads)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取线程列表失败: {str(e)}")


@router.get("/threads/{thread_id}/history")
async def get_thread_history(
    thread_id: str,
    limit: int = Query(50, description="返回消息数量"),
    current_user: User = Depends(get_current_user)
):
    """
    获取线程对话历史
    """
    try:
        from app.agent.store import conversation_store
        messages = conversation_store.get_messages(
            current_user.id, thread_id, limit
        )
        
        return {
            "success": True,
            "thread_id": thread_id,
            "messages": messages,
            "count": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    删除对话线程
    """
    try:
        from app.agent.store import conversation_store
        success = conversation_store.delete_thread(current_user.id, thread_id)
        
        return {
            "success": success,
            "message": "线程已删除" if success else "线程不存在"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除线程失败: {str(e)}")


@router.get("/config")
async def get_agent_config(
    current_user: User = Depends(get_current_user)
):
    """
    获取Agent配置
    """
    return {
        "success": True,
        "config": {
            "use_langgraph": settings.USE_LANGGRAPH,
            "checkpoint_backend": settings.LANGGRAPH_CHECKPOINT_BACKEND,
            "rag_use_bm25": settings.RAG_USE_BM25,
            "rag_use_reranker": settings.RAG_USE_RERANKER,
            "model": settings.MIMO_MODEL
        }
    }
