"""
メニューカテゴリ機能のテスト
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_menu_categories():
    """カテゴリ一覧取得のテスト"""
    # ログイン
    login_response = client.post("/api/auth/login", data={
        "username": "store001",
        "password": "store001"
    })
    
    if login_response.status_code != 200:
        pytest.skip("テストユーザーが利用できません")
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # カテゴリ一覧を取得
    response = client.get("/api/store/menu-categories", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "categories" in data
    assert "total" in data
    assert isinstance(data["categories"], list)


def test_create_menu_category():
    """カテゴリ作成のテスト"""
    login_response = client.post("/api/auth/login", data={
        "username": "store001",
        "password": "store001"
    })
    
    if login_response.status_code != 200:
        pytest.skip("テストユーザーが利用できません")
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 一意な名前を生成
    import time
    category_name = f"テストカテゴリ_{int(time.time())}"
    
    # カテゴリを作成
    response = client.post(
        "/api/store/menu-categories",
        json={
            "name": category_name,
            "description": "テスト用のカテゴリ",
            "display_order": 1,
            "is_active": True
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == category_name
    assert data["description"] == "テスト用のカテゴリ"
    assert "id" in data


def test_update_menu_category():
    """カテゴリ更新のテスト"""
    login_response = client.post("/api/auth/login", data={
        "username": "store001",
        "password": "store001"
    })
    
    if login_response.status_code != 200:
        pytest.skip("テストユーザーが利用できません")
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # まずカテゴリを作成
    import time
    category_name = f"更新テスト_{int(time.time())}"
    
    create_response = client.post(
        "/api/store/menu-categories",
        json={
            "name": category_name,
            "description": "更新前",
            "display_order": 1,
            "is_active": True
        },
        headers=headers
    )
    
    if create_response.status_code != 200:
        pytest.skip("カテゴリの作成に失敗しました")
    
    category_id = create_response.json()["id"]
    
    # カテゴリを更新
    update_response = client.put(
        f"/api/store/menu-categories/{category_id}",
        json={
            "description": "更新後",
            "display_order": 2
        },
        headers=headers
    )
    
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["description"] == "更新後"
    assert data["display_order"] == 2


def test_delete_menu_category():
    """カテゴリ削除のテスト"""
    login_response = client.post("/api/auth/login", data={
        "username": "store001",
        "password": "store001"
    })
    
    if login_response.status_code != 200:
        pytest.skip("テストユーザーが利用できません")
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # まずカテゴリを作成
    import time
    category_name = f"削除テスト_{int(time.time())}"
    
    create_response = client.post(
        "/api/store/menu-categories",
        json={
            "name": category_name,
            "description": "削除テスト用",
            "display_order": 1,
            "is_active": True
        },
        headers=headers
    )
    
    if create_response.status_code != 200:
        pytest.skip("カテゴリの作成に失敗しました")
    
    category_id = create_response.json()["id"]
    
    # カテゴリを削除
    delete_response = client.delete(
        f"/api/store/menu-categories/{category_id}",
        headers=headers
    )
    
    assert delete_response.status_code == 200
    data = delete_response.json()
    assert "message" in data


def test_filter_menus_by_category():
    """カテゴリでメニューをフィルタするテスト"""
    login_response = client.post("/api/auth/login", data={
        "username": "store001",
        "password": "store001"
    })
    
    if login_response.status_code != 200:
        pytest.skip("テストユーザーが利用できません")
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # カテゴリなしのメニューを取得
    response = client.get("/api/store/menus?category_id=0", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "menus" in data or isinstance(data, list)


def test_unauthorized_category_access():
    """未認証でのカテゴリアクセスのテスト"""
    response = client.get("/api/store/menu-categories")
    assert response.status_code == 401
