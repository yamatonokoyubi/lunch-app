"""
公開メニューAPI テスト

認証不要で店舗のメニュー一覧を取得するAPIのテスト
"""

from datetime import time

import pytest
from fastapi.testclient import TestClient

from models import Menu, MenuCategory, Store, User


class TestPublicMenuAPI:
    """公開メニューAPI テストクラス"""

    @pytest.fixture
    def test_store(self, db_session):
        """テスト用店舗を作成"""
        owner = User(
            username="store_owner",
            email="store@example.com",
            hashed_password="hashed",
            role="store_owner",
        )
        db_session.add(owner)
        db_session.flush()

        store = Store(
            name="テスト店舗",
            address="東京都渋谷区1-1-1",
            phone_number="03-1234-5678",
            email="teststore@example.com",
            opening_time=time(9, 0),
            closing_time=time(21, 0),
            is_active=True,
        )
        db_session.add(store)
        db_session.commit()
        db_session.refresh(store)

        owner.store_id = store.id
        db_session.commit()

        return store

    @pytest.fixture
    def test_category(self, db_session, test_store):
        """テスト用カテゴリを作成"""
        category = MenuCategory(
            name="定番",
            display_order=1,
            store_id=test_store.id,
        )
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)
        return category

    @pytest.fixture
    def test_menus(self, db_session, test_store, test_category):
        """テスト用メニューを作成"""
        menu1 = Menu(
            name="唐揚げ弁当",
            description="人気の唐揚げ弁当",
            price=600,
            store_id=test_store.id,
            category_id=test_category.id,
            is_available=True,
        )
        menu2 = Menu(
            name="のり弁当",
            description="定番ののり弁当",
            price=500,
            store_id=test_store.id,
            category_id=test_category.id,
            is_available=True,
        )
        menu3 = Menu(
            name="在庫切れ弁当",
            description="在庫切れ",
            price=550,
            store_id=test_store.id,
            is_available=False,
        )
        db_session.add_all([menu1, menu2, menu3])
        db_session.commit()
        db_session.refresh(menu1)
        db_session.refresh(menu2)
        db_session.refresh(menu3)
        return {
            "available1": menu1,
            "available2": menu2,
            "unavailable": menu3,
        }

    def test_get_store_menus_success(self, client: TestClient, test_store, test_menus):
        """店舗メニュー一覧の取得成功"""
        response = client.get(f"/api/public/stores/{test_store.id}/menus")

        assert response.status_code == 200
        data = response.json()

        # 販売可能なメニューのみ返される
        assert len(data) == 2
        menu_names = [menu["name"] for menu in data]
        assert "唐揚げ弁当" in menu_names
        assert "のり弁当" in menu_names
        assert "在庫切れ弁当" not in menu_names

    def test_get_store_menus_with_unavailable(
        self, client: TestClient, test_store, test_menus
    ):
        """在庫切れメニューも含めて取得"""
        response = client.get(
            f"/api/public/stores/{test_store.id}/menus?is_available=false"
        )

        assert response.status_code == 200
        data = response.json()

        # すべてのメニューが返される
        assert len(data) == 3

    def test_get_store_menus_by_category(
        self, client: TestClient, test_store, test_category, test_menus
    ):
        """カテゴリでフィルタ"""
        response = client.get(
            f"/api/public/stores/{test_store.id}/menus"
            f"?category_id={test_category.id}"
        )

        assert response.status_code == 200
        data = response.json()

        # カテゴリに属するメニューのみ
        assert len(data) == 2
        for menu in data:
            assert menu["category"]["id"] == test_category.id

    def test_get_store_menus_store_not_found(self, client: TestClient):
        """存在しない店舗はエラー"""
        response = client.get("/api/public/stores/99999/menus")

        assert response.status_code == 404
        assert "見つかりません" in response.json()["detail"]

    def test_menu_response_structure(self, client: TestClient, test_store, test_menus):
        """メニューレスポンスの構造を確認"""
        response = client.get(f"/api/public/stores/{test_store.id}/menus")

        assert response.status_code == 200
        data = response.json()

        # 最初のメニューの構造を確認
        menu = data[0]
        assert "id" in menu
        assert "name" in menu
        assert "description" in menu
        assert "price" in menu
        assert "is_available" in menu
        assert "store_id" in menu
        assert menu["store_id"] == test_store.id

    def test_menu_includes_category(
        self, client: TestClient, test_store, test_category, test_menus
    ):
        """メニューにカテゴリ情報が含まれる"""
        response = client.get(f"/api/public/stores/{test_store.id}/menus")

        assert response.status_code == 200
        data = response.json()

        # カテゴリ情報を持つメニューを確認
        menu_with_category = next((m for m in data if m.get("category")), None)
        assert menu_with_category is not None
        assert menu_with_category["category"]["name"] == "定番"
