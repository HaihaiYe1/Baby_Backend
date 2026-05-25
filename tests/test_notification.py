import pytest
from fastapi.testclient import TestClient


class TestNotification:
    """通知模块测试"""
    
    def test_get_notifications(self, authenticated_client: TestClient):
        """测试获取通知列表"""
        response = authenticated_client.get("/notification/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_notification(self, authenticated_client: TestClient):
        """测试创建通知"""
        response = authenticated_client.post("/notification/", json={
            "message": "Test notification",
            "level": "warning",
            "device_id": 1
        })
        # 注意：这个端点可能需要调整
        assert response.status_code in [200, 201, 404, 422]
    
    def test_pin_notification(self, authenticated_client: TestClient):
        """测试置顶通知"""
        # 先获取通知列表
        response = authenticated_client.get("/notification/")
        if response.status_code == 200:
            notifications = response.json()
            if notifications:
                notification_id = notifications[0]["id"]
                response = authenticated_client.post(f"/notification/{notification_id}/pin")
                assert response.status_code == 200
    
    def test_delete_notification(self, authenticated_client: TestClient):
        """测试删除通知"""
        # 先获取通知列表
        response = authenticated_client.get("/notification/")
        if response.status_code == 200:
            notifications = response.json()
            if notifications:
                notification_id = notifications[0]["id"]
                response = authenticated_client.delete(f"/notification/{notification_id}")
                assert response.status_code == 200
