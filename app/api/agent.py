from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.utils.security import get_current_user
from app.models import User
from app.agent.baby_agent import agent_manager
from typing import Dict, Any, Optional

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
    model_name: str = Query("gpt-4o", description="使用的模型名称"),
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
            use_agent_mode=use_agent_mode,
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
        agent.reset_memory()
        
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
        agent = agent_manager.get_or_create_agent(
            db=None,
            user_id=current_user.id
        )
        agent.update_preferences(preferences)
        
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
        agent = agent_manager.get_or_create_agent(
            db=None,
            user_id=current_user.id
        )
        
        return {
            "success": True,
            "memory_summary": agent.memory.get_detection_summary(),
            "context_summary": agent.memory.get_context_summary(last_n=10)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    与Agent进行对话
    """
    try:
        agent = agent_manager.get_or_create_agent(
            db=db,
            user_id=current_user.id
        )
        
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
        
        # 使用Agent处理消息（简化版本，实际应该调用Agent的对话功能）
        # 这里暂时返回一个简单的响应
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
