from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.utils.security import get_current_user
from app.models import User
from app.rag.advisor import parenting_advisor
from app.rag.retriever import RAGRetriever
from app.config import settings
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

router = APIRouter()


class HybridSearchRequest(BaseModel):
    """混合检索请求"""
    query: str
    top_k: int = 10
    use_hybrid: bool = True
    use_reranker: bool = True
    optimize_query: bool = False
    category: Optional[str] = None


class EvaluateRequest(BaseModel):
    """评估请求"""
    test_cases: List[Dict[str, Any]]


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
    搜索知识库（稠密向量检索）
    """
    try:
        retriever = RAGRetriever(use_hybrid=False, use_reranker=False)
        
        results = await retriever.retrieve(
            query=query,
            top_k=n_results,
            category=category
        )
        
        return {
            "success": True,
            "query": query,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/hybrid-search")
async def hybrid_search(
    request: HybridSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    混合检索（BM25 + 向量 + 重排序）
    """
    try:
        retriever = RAGRetriever(
            use_hybrid=request.use_hybrid,
            use_reranker=request.use_reranker
        )
        
        results = await retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            category=request.category,
            optimize_query=request.optimize_query
        )
        
        return {
            "success": True,
            "query": request.query,
            "optimized": request.optimize_query,
            "hybrid": request.use_hybrid,
            "reranked": request.use_reranker,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"混合检索失败: {str(e)}")


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


@router.post("/evaluate")
async def evaluate_rag(
    request: EvaluateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    评估RAG系统质量
    """
    try:
        from app.rag.evaluator import evaluator
        
        results = await evaluator.evaluate(request.test_cases)
        report = evaluator.generate_report(results)
        
        return {
            "success": True,
            "results": results,
            "report": report
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")


@router.get("/config")
async def get_rag_config(
    current_user: User = Depends(get_current_user)
):
    """
    获取RAG配置
    """
    return {
        "success": True,
        "config": {
            "use_bm25": settings.RAG_USE_BM25,
            "use_rrf": settings.RAG_USE_RRF,
            "rrf_k": settings.RAG_RRF_K,
            "use_reranker": settings.RAG_USE_RERANKER,
            "reranker_model": settings.RAG_RERANKER_MODEL,
            "top_k": settings.RAG_TOP_K,
            "rerank_top_k": settings.RAG_RERANK_TOP_K
        }
    }
