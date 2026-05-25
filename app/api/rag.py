from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.utils.security import get_current_user
from app.models import User
from app.rag.advisor import parenting_advisor
from typing import Dict, Any, Optional

router = APIRouter()


@router.post("/advice")
async def get_parenting_advice(
    situation: str = Query(..., description="情况描述"),
    baby_age_months: Optional[int] = Query(None, description="婴儿月龄"),
    context: Optional[str] = Query(None, description="额外上下文"),
    current_user: User = Depends(get_current_user)
):
    """
    获取育儿建议
    """
    try:
        result = await parenting_advisor.get_advice(
            situation=situation,
            baby_age_months=baby_age_months,
            context=context
        )
        
        return {
            "success": True,
            "user_id": current_user.id,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取建议失败: {str(e)}")


@router.post("/emergency-advice")
async def get_emergency_advice(
    emergency_type: str = Query(..., description="紧急情况类型"),
    details: str = Query(..., description="详细信息"),
    current_user: User = Depends(get_current_user)
):
    """
    获取紧急情况建议
    """
    try:
        result = await parenting_advisor.get_emergency_advice(
            emergency_type=emergency_type,
            details=details
        )
        
        return {
            "success": True,
            "user_id": current_user.id,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取紧急建议失败: {str(e)}")


@router.get("/knowledge-stats")
async def get_knowledge_stats(
    current_user: User = Depends(get_current_user)
):
    """
    获取知识库统计信息
    """
    try:
        from app.rag.knowledge_base import knowledge_base
        
        stats = knowledge_base.get_collection_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/search-knowledge")
async def search_knowledge(
    query: str = Query(..., description="查询内容"),
    n_results: int = Query(5, description="返回结果数量"),
    category: Optional[str] = Query(None, description="知识类别"),
    current_user: User = Depends(get_current_user)
):
    """
    搜索知识库
    """
    try:
        from app.rag.retriever import rag_retriever
        
        results = rag_retriever.retrieve(
            query=query,
            n_results=n_results,
            category=category
        )
        
        return {
            "success": True,
            "query": query,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/add-knowledge")
async def add_knowledge(
    content: str = Query(..., description="知识内容"),
    category: str = Query("general", description="知识类别"),
    source: Optional[str] = Query(None, description="来源"),
    current_user: User = Depends(get_current_user)
):
    """
    添加知识到知识库
    """
    try:
        from app.rag.knowledge_base import knowledge_base
        
        metadata = {
            "category": category,
            "added_by": current_user.id,
            "source": source or "user_input"
        }
        
        ids = knowledge_base.add_documents(
            documents=[content],
            metadatas=[metadata]
        )
        
        return {
            "success": True,
            "message": "知识添加成功",
            "document_id": ids[0] if ids else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加知识失败: {str(e)}")
