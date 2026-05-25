import pytest
from fastapi.testclient import TestClient


class TestDevice:
    """设备管理模块测试"""
    
    def test_create_device(self, authenticated_client: TestClient):
        """测试创建设备"""
        response = authenticated_client.post("/device/create", json={
            "email": "test@example.com",
            "name": "Baby Camera 1",
            "ip": "192.168.1.100",
            "status": "online"
        })
        assert response.status_code == 200
    
    def test_get_device_list(self, authenticated_client: TestClient):
        """测试获取设备列表"""
        response = authenticated_client.get("/device/list")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_device_by_id(self, authenticated_client: TestClient):
        """测试通过ID获取设备"""
        # 先创建设备
        create_response = authenticated_client.post("/device/create", json={
            "email": "test@example.com",
            "name": "Test Camera",
            "ip": "192.168.1.101",
            "status": "online"
        })
        
        if create_response.status_code == 200:
            device_id = create_response.json().get("id")
            if device_id:
                response = authenticated_client.get(f"/device/{device_id}")
                assert response.status_code == 200
    
    def test_update_device(self, authenticated_client: TestClient):
        """测试更新设备"""
        # 先创建设备
        create_response = authenticated_client.post("/device/create", json={
            "email": "test@example.com",
            "name": "Update Test Camera",
            "ip": "192.168.1.102",
            "status": "offline"
        })
        
        if create_response.status_code == 200:
            device_id = create_response.json().get("id")
            if device_id:
                response = authenticated_client.put(f"/device/{device_id}", json={
                    "id": device_id,
                    "name": "Updated Camera",
                    "email": "test@example.com"
                })
                assert response.status_code == 200
    
    def test_delete_device(self, authenticated_client: TestClient):
        """测试删除设备"""
        # 先创建设备
        create_response = authenticated_client.post("/device/create", json={
            "email": "test@example.com",
            "name": "Delete Test Camera",
            "ip": "192.168.1.103",
            "status": "online"
        })
        
        if create_response.status_code == 200:
            device_id = create_response.json().get("id")
            if device_id:
                response = authenticated_client.delete(f"/device/{device_id}")
                assert response.status_code == 200
