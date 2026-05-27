import pytest
from fastapi.testclient import TestClient


class TestSmartHome:
    """智能家居模块测试"""
    
    def test_get_smart_home_status(self, authenticated_client: TestClient):
        """测试获取智能家居状态"""
        response = authenticated_client.get("/smart-home/status")
        assert response.status_code in [200, 401]
    
    def test_control_speaker(self, authenticated_client: TestClient):
        """测试控制音箱"""
        response = authenticated_client.post(
            "/smart-home/speaker/control?action=play&content=whitenoise&volume=50"
        )
        assert response.status_code in [200, 401]
    
    def test_control_light(self, authenticated_client: TestClient):
        """测试控制灯光"""
        response = authenticated_client.post(
            "/smart-home/light/control?action=on&brightness=100"
        )
        assert response.status_code in [200, 401]
    
    def test_activate_scene(self, authenticated_client: TestClient):
        """测试激活场景"""
        response = authenticated_client.post(
            "/smart-home/scene/activate?scene=sleep"
        )
        assert response.status_code in [200, 401]
    
    def test_get_available_scenes(self, authenticated_client: TestClient):
        """测试获取可用场景"""
        response = authenticated_client.get("/smart-home/scenes")
        assert response.status_code in [200, 401]
    
    def test_quick_sleep_mode(self, authenticated_client: TestClient):
        """测试快速睡眠模式"""
        response = authenticated_client.post("/smart-home/quick/sleep?duration=60")
        assert response.status_code in [200, 401]
    
    def test_quick_comfort_mode(self, authenticated_client: TestClient):
        """测试快速安抚模式"""
        response = authenticated_client.post(
            "/smart-home/quick/comfort?intensity=medium"
        )
        assert response.status_code in [200, 401]
    
    def test_quick_alert_mode(self, authenticated_client: TestClient):
        """测试快速警报模式"""
        response = authenticated_client.post("/smart-home/quick/alert")
        assert response.status_code in [200, 401]
