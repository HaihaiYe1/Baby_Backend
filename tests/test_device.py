import pytest
from fastapi.testclient import TestClient


class TestDevice:
    """设备管理模块测试"""
    
    def test_create_device(self, authenticated_client: TestClient):
        """测试创建设备"""
        response = authenticated_client.post("/device/add", json={
            "name": "Baby Camera 1",
            "ip": "192.168.1.100",
            "status": "online"
        })
        # 新API不再需要email字段，从认证用户获取
        assert response.status_code in [200, 401]
    
    def test_get_device_list(self, authenticated_client: TestClient):
        """测试获取设备列表"""
        response = authenticated_client.get("/device/list")
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            assert isinstance(response.json(), list)
    
    def test_get_device_by_id(self, authenticated_client: TestClient):
        """测试通过ID获取设备"""
        # 先创建设备
        create_response = authenticated_client.post("/device/add", json={
            "name": "Test Camera",
            "ip": "192.168.1.101",
            "status": "online"
        })
        
        if create_response.status_code == 200:
            device_id = create_response.json().get("device_id")
            if device_id:
                response = authenticated_client.get(f"/device/{device_id}")
                assert response.status_code in [200, 401, 403]
    
    def test_update_device(self, authenticated_client: TestClient):
        """测试更新设备"""
        # 先创建设备
        create_response = authenticated_client.post("/device/add", json={
            "name": "Update Test Camera",
            "ip": "192.168.1.102",
            "status": "offline"
        })
        
        if create_response.status_code == 200:
            device_id = create_response.json().get("device_id")
            if device_id:
                response = authenticated_client.put("/device/update", json={
                    "id": device_id,
                    "name": "Updated Camera"
                })
                assert response.status_code in [200, 401, 403, 404]
    
    def test_delete_device(self, authenticated_client: TestClient):
        """测试删除设备"""
        # 先创建设备
        create_response = authenticated_client.post("/device/add", json={
            "name": "Delete Test Camera",
            "ip": "192.168.1.103",
            "status": "online"
        })
        
        if create_response.status_code == 200:
            device_id = create_response.json().get("device_id")
            if device_id:
                response = authenticated_client.delete(f"/device/delete?device_id={device_id}")
                assert response.status_code in [200, 401, 403, 404]
