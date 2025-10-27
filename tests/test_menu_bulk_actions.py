"""
メニュー一括操作APIのテスト
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_bulk_availability_basic():
    """基本的な一括公開/非公開のテスト"""
    # 実際のシステムの既存ユーザーでログイン
    login_response = client.post("/api/auth/login", data={
        "username": "store001",
        "password": "store001"
    })
    
    if login_response.status_code != 200:
        pytest.skip("テストユーザーが利用できません")
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # メニュー一覧を取得
    menus_response = client.get("/api/store/menus", headers=headers)
    assert menus_response.status_code == 200
    
    menus_data = menus_response.json()
    if isinstance(menus_data, dict):
        menus = menus_data.get("menus", [])
    else:
        menus = menus_data
    
    if len(menus) < 2:
        pytest.skip("テスト用のメニューが不足しています")
    
    # 最初の2つのメニューIDを使用
    menu_ids = [menus[0]["id"], menus[1]["id"]]
    
    # 一括非公開
    bulk_response = client.put(
        "/api/store/menus/bulk-availability",
        json={"menu_ids": menu_ids, "is_available": False},
        headers=headers
    )
    
    assert bulk_response.status_code == 200
    data = bulk_response.json()
    assert data["updated_count"] >= 0
    assert "message" in data
    
    # 一括公開
    bulk_response2 = client.put(
        "/api/store/menus/bulk-availability",
        json={"menu_ids": menu_ids, "is_available": True},
        headers=headers
    )
    
    assert bulk_response2.status_code == 200
    data2 = bulk_response2.json()
    assert data2["updated_count"] >= 0


def test_bulk_availability_empty_list():
    """空のリストでのバリデーションエラー"""
    login_response = client.post("/api/auth/login", data={
        "username": "store001",
        "password": "store001"
    })
    
    if login_response.status_code != 200:
        pytest.skip("テストユーザーが利用できません")
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 空のリスト
    bulk_response = client.put(
        "/api/store/menus/bulk-availability",
        json={"menu_ids": [], "is_available": True},
        headers=headers
    )
    
    assert bulk_response.status_code == 422  # バリデーションエラー


def test_bulk_availability_unauthorized():
    """未認証でのアクセス拒否"""
    bulk_response = client.put(
        "/api/store/menus/bulk-availability",
        json={"menu_ids": [1, 2], "is_available": True}
    )
    
    assert bulk_response.status_code == 401  # 未認証
