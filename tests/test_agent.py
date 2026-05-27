import pytest
from fastapi.testclient import TestClient


class TestAgent:
    """Agent模块测试"""
    
    def test_get_agent_status(self, authenticated_client: TestClient):
        """测试获取Agent状态"""
        response = authenticated_client.get("/agent/status")
        assert response.status_code in [200, 401]
    
    def test_initialize_agent(self, authenticated_client: TestClient):
        """测试初始化Agent"""
        response = authenticated_client.post("/agent/initialize?use_agent_mode=false")
        assert response.status_code in [200, 401]
    
    def test_chat_with_agent(self, authenticated_client: TestClient):
        """测试与Agent对话"""
        response = authenticated_client.post("/agent/chat?message=你好")
        assert response.status_code in [200, 401]
    
    def test_reset_agent_memory(self, authenticated_client: TestClient):
        """测试重置Agent记忆"""
        response = authenticated_client.post("/agent/reset-memory")
        assert response.status_code in [200, 401]
    
    def test_get_agent_memory_summary(self, authenticated_client: TestClient):
        """测试获取Agent记忆摘要"""
        response = authenticated_client.get("/agent/memory-summary")
        assert response.status_code in [200, 401]
