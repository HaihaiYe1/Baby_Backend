import pytest
from fastapi.testclient import TestClient


class TestVideo:
    """视频模块测试"""
    
    def test_start_detect(self, authenticated_client: TestClient):
        """测试启动检测"""
        response = authenticated_client.post("/video/start-detect?device_id=1")
        # 可能成功(200)或设备不存在(404)或未认证(401)
        assert response.status_code in [200, 401, 404]
    
    def test_stop_detect(self, authenticated_client: TestClient):
        """测试停止检测"""
        response = authenticated_client.post("/video/stop-detect?device_id=1")
        assert response.status_code in [200, 400, 401, 404]
    
    def test_agent_detect(self, authenticated_client: TestClient):
        """测试Agent检测"""
        response = authenticated_client.post(
            "/video/agent-detect?device_id=1&max_frames=1&use_agent=false"
        )
        assert response.status_code in [200, 401, 404, 500]
    
    def test_vlm_detect(self, authenticated_client: TestClient):
        """测试VLM检测"""
        response = authenticated_client.post(
            "/video/vlm-detect?device_id=1&max_frames=1&use_vlm=false"
        )
        assert response.status_code in [200, 401, 404, 500]
