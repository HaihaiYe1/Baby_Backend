import os
import pytest
import asyncio
from typing import Generator

# 设置测试环境变量 - 必须在导入app之前
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["DATABASE_HOST"] = "localhost"
os.environ["DATABASE_PORT"] = "3306"
os.environ["DATABASE_USER"] = "test"
os.environ["DATABASE_PASSWORD"] = "test"
os.environ["DATABASE_NAME"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["MIMO_API_KEY"] = "test-key"
os.environ["DEBUG"] = "true"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.utils.database import Base, get_db

# 创建测试数据库引擎
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db() -> Generator[Session, None, None]:
    """覆盖数据库依赖"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    """创建测试客户端"""
    # 在导入app之前覆盖数据库依赖
    from app.main import app
    app.dependency_overrides[get_db] = override_get_db
    
    Base.metadata.create_all(bind=test_engine)
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_client(client: TestClient) -> TestClient:
    """创建已认证的测试客户端"""
    # 注册用户
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123",
        "username": "testuser"
    })
    
    # 登录获取token
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("token")
        if token:
            client.headers = {"Authorization": f"Bearer {token}"}
    
    return client
