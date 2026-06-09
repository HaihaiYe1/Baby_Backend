from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings


def create_checkpointer():
    """
    创建LangGraph checkpointer
    
    根据配置选择不同的后端:
    - memory: 内存存储（开发/测试用）
    - sqlite: SQLite存储
    - mysql: MySQL存储（生产环境推荐）
    """
    backend = settings.LANGGRAPH_CHECKPOINT_BACKEND
    
    if backend == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    
    elif backend == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver
        db_url = settings.LANGGRAPH_CHECKPOINT_URL or "sqlite:///checkpoints.db"
        return SqliteSaver.from_conn_string(db_url)
    
    elif backend == "mysql":
        from langgraph.checkpoint.sqlalchemy import SQLAlchemySaver
        db_url = settings.LANGGRAPH_CHECKPOINT_URL or settings.DATABASE_URL
        if not db_url:
            raise ValueError("MySQL checkpointer requires DATABASE_URL or LANGGRAPH_CHECKPOINT_URL")
        return SQLAlchemySaver.from_conn_string(db_url)
    
    else:
        raise ValueError(f"Unsupported checkpoint backend: {backend}")


def create_async_checkpointer():
    """创建异步checkpointer"""
    backend = settings.LANGGRAPH_CHECKPOINT_BACKEND
    
    if backend == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    
    elif backend == "mysql":
        from langgraph.checkpoint.sqlalchemy.aio import AsyncSQLAlchemySaver
        db_url = settings.LANGGRAPH_CHECKPOINT_URL or settings.DATABASE_URL
        return AsyncSQLAlchemySaver.from_conn_string(db_url)
    
    else:
        # 回退到同步版本
        return create_checkpointer()
