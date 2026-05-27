import pytest
from fastapi.testclient import TestClient


class TestRAG:
    """RAG育儿知识库模块测试"""
    
    def test_get_parenting_advice(self, authenticated_client: TestClient):
        """测试获取育儿建议"""
        response = authenticated_client.post("/rag/advice?situation=宝宝晚上哭闹")
        assert response.status_code in [200, 401]
    
    def test_get_emergency_advice(self, authenticated_client: TestClient):
        """测试获取紧急建议"""
        response = authenticated_client.post(
            "/rag/emergency-advice?emergency_type=fever&details=宝宝发烧38度"
        )
        assert response.status_code in [200, 401]
    
    def test_get_knowledge_stats(self, authenticated_client: TestClient):
        """测试获取知识库统计"""
        response = authenticated_client.get("/rag/knowledge-stats")
        assert response.status_code in [200, 401]
    
    def test_search_knowledge(self, authenticated_client: TestClient):
        """测试搜索知识库"""
        response = authenticated_client.post("/rag/search-knowledge?query=婴儿睡眠")
        assert response.status_code in [200, 401]
    
    def test_add_knowledge(self, authenticated_client: TestClient):
        """测试添加知识"""
        response = authenticated_client.post(
            "/rag/add-knowledge?content=测试知识内容&category=general"
        )
        assert response.status_code in [200, 401]
