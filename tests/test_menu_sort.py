"""
メニューソート機能のテスト
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from tests.conftest import client, test_db, test_user_store1, auth_headers_store1


class TestMenuSort:
    """メニューソート機能のテスト"""

    def setup_test_menus(self, client, auth_headers_store1):
        """テスト用のメニューを作成"""
        menus_data = [
            {"name": "唐揚げ弁当", "price": 500, "is_available": True},
            {"name": "幕の内弁当", "price": 800, "is_available": True},
            {"name": "のり弁当", "price": 350, "is_available": False},
            {"name": "ハンバーグ弁当", "price": 650, "is_available": True},
            {"name": "焼き魚弁当", "price": 700, "is_available": True},
        ]
        
        created_menus = []
        for menu_data in menus_data:
            response = client.post("/api/store/menus", json=menu_data, headers=auth_headers_store1)
            assert response.status_code == 200
            created_menus.append(response.json())
        
        return created_menus

    def test_sort_by_name_asc(self, client, test_db, auth_headers_store1):
        """正常系: 名前の昇順ソート"""
        self.setup_test_menus(client, auth_headers_store1)
        
        response = client.get(
            "/api/store/menus?sort_by=name&sort_order=asc",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        menus = data["menus"]
        
        # 名前が昇順になっているか確認
        menu_names = [menu["name"] for menu in menus]
        assert menu_names == sorted(menu_names)

    def test_sort_by_name_desc(self, client, test_db, auth_headers_store1):
        """正常系: 名前の降順ソート"""
        self.setup_test_menus(client, auth_headers_store1)
        
        response = client.get(
            "/api/store/menus?sort_by=name&sort_order=desc",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        menus = data["menus"]
        
        # 名前が降順になっているか確認
        menu_names = [menu["name"] for menu in menus]
        assert menu_names == sorted(menu_names, reverse=True)

    def test_sort_by_price_asc(self, client, test_db, auth_headers_store1):
        """正常系: 価格の昇順ソート"""
        self.setup_test_menus(client, auth_headers_store1)
        
        response = client.get(
            "/api/store/menus?sort_by=price&sort_order=asc",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        menus = data["menus"]
        
        # 価格が昇順になっているか確認
        prices = [menu["price"] for menu in menus]
        assert prices == sorted(prices)

    def test_sort_by_price_desc(self, client, test_db, auth_headers_store1):
        """正常系: 価格の降順ソート"""
        self.setup_test_menus(client, auth_headers_store1)
        
        response = client.get(
            "/api/store/menus?sort_by=price&sort_order=desc",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        menus = data["menus"]
        
        # 価格が降順になっているか確認
        prices = [menu["price"] for menu in menus]
        assert prices == sorted(prices, reverse=True)

    def test_sort_by_created_at_asc(self, client, test_db, auth_headers_store1):
        """正常系: 作成日時の昇順ソート"""
        self.setup_test_menus(client, auth_headers_store1)
        
        response = client.get(
            "/api/store/menus?sort_by=created_at&sort_order=asc",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        menus = data["menus"]
        
        # 作成日時が昇順になっているか確認
        created_ats = [menu["created_at"] for menu in menus]
        assert created_ats == sorted(created_ats)

    def test_sort_by_updated_at_desc(self, client, test_db, auth_headers_store1):
        """正常系: 更新日時の降順ソート"""
        self.setup_test_menus(client, auth_headers_store1)
        
        response = client.get(
            "/api/store/menus?sort_by=updated_at&sort_order=desc",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        menus = data["menus"]
        
        # 更新日時が降順になっているか確認
        updated_ats = [menu["updated_at"] for menu in menus]
        assert updated_ats == sorted(updated_ats, reverse=True)

    def test_default_sort(self, client, test_db, auth_headers_store1):
        """正常系: デフォルトソート（更新日時の降順）"""
        self.setup_test_menus(client, auth_headers_store1)
        
        response = client.get(
            "/api/store/menus",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        menus = data["menus"]
        
        # デフォルトで更新日時の降順になっているか確認
        updated_ats = [menu["updated_at"] for menu in menus]
        assert updated_ats == sorted(updated_ats, reverse=True)

    def test_sort_with_filter(self, client, test_db, auth_headers_store1):
        """正常系: フィルタとソートの組み合わせ"""
        self.setup_test_menus(client, auth_headers_store1)
        
        response = client.get(
            "/api/store/menus?is_available=true&sort_by=price&sort_order=asc",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 200
        data = response.json()
        menus = data["menus"]
        
        # すべてのメニューが利用可能であることを確認
        assert all(menu["is_available"] for menu in menus)
        
        # 価格が昇順になっているか確認
        prices = [menu["price"] for menu in menus]
        assert prices == sorted(prices)

    def test_invalid_sort_by(self, client, test_db, auth_headers_store1):
        """異常系: 無効なソートカラム"""
        response = client.get(
            "/api/store/menus?sort_by=invalid_column",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 400
        assert "Invalid sort_by parameter" in response.json()["detail"]

    def test_invalid_sort_order(self, client, test_db, auth_headers_store1):
        """異常系: 無効なソート順序"""
        response = client.get(
            "/api/store/menus?sort_by=name&sort_order=invalid",
            headers=auth_headers_store1
        )
        
        assert response.status_code == 400
        assert "Invalid sort_order parameter" in response.json()["detail"]

    def test_sort_unauthorized(self, client, test_db):
        """異常系: 未認証ユーザー"""
        response = client.get("/api/store/menus?sort_by=name&sort_order=asc")
        assert response.status_code == 401
