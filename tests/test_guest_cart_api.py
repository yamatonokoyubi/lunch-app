"""
ゲストカートAPI テスト

ゲストセッションに紐づくカート操作（追加・取得・更新・削除）のテスト
"""

import pytest
from fastapi.testclient import TestClient

from models import GuestCartItem, GuestSession, Menu, Store, User


class TestGuestCartAPI:
    """ゲストカートAPI テストクラス"""

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

        from datetime import time

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

        # OwnerとStoreを紐付け
        owner.store_id = store.id
        db_session.commit()

        return store

    @pytest.fixture
    def test_menus(self, db_session, test_store):
        """テスト用メニューを作成"""
        menu1 = Menu(
            name="唐揚げ弁当",
            description="人気の唐揚げ弁当",
            price=600,
            store_id=test_store.id,
            is_available=True,
        )
        menu2 = Menu(
            name="のり弁当",
            description="定番ののり弁当",
            price=500,
            store_id=test_store.id,
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

    @pytest.fixture
    def another_store(self, db_session):
        """別の店舗を作成（他店舗チェック用）"""
        owner = User(
            username="another_owner",
            email="another@example.com",
            hashed_password="hashed",
            role="store_owner",
        )
        db_session.add(owner)
        db_session.flush()

        from datetime import time

        store = Store(
            name="別の店舗",
            address="神奈川県横浜市",
            phone_number="045-1234-5678",
            email="anotherstore@example.com",
            opening_time=time(10, 0),
            closing_time=time(20, 0),
            is_active=True,
        )
        db_session.add(store)
        db_session.commit()
        db_session.refresh(store)

        # OwnerとStoreを紐付け
        owner.store_id = store.id
        db_session.commit()

        return store

    @pytest.fixture
    def another_store_menu(self, db_session, another_store):
        """別店舗のメニュー"""
        menu = Menu(
            name="他店の弁当",
            description="他店のメニュー",
            price=700,
            store_id=another_store.id,
            is_available=True,
        )
        db_session.add(menu)
        db_session.commit()
        db_session.refresh(menu)
        return menu

    @pytest.fixture
    def guest_with_store(self, db_session, test_store):
        """店舗が選択されたゲストセッション"""
        from datetime import datetime, timedelta

        session = GuestSession(
            session_id="test-session-id-12345",
            selected_store_id=test_store.id,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session

    @pytest.fixture
    def guest_without_store(self, db_session):
        """店舗が選択されていないゲストセッション"""
        from datetime import datetime, timedelta

        session = GuestSession(
            session_id="test-no-store-12345",
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session

    def test_add_to_cart_success(
        self,
        client: TestClient,
        db_session,
        guest_with_store,
        test_menus,
    ):
        """カートに商品を追加できることを確認"""
        client.cookies.set("guest_session_id", guest_with_store.session_id)

        # メニューを追加
        response = client.post(
            "/api/guest/cart/add",
            json={
                "menu_id": test_menus["available1"].id,
                "quantity": 2,
            },
        )

        assert response.status_code == 201
        data = response.json()

        # レスポンス検証
        assert data["session_id"] == guest_with_store.session_id
        assert len(data["items"]) == 1
        assert data["items"][0]["menu_id"] == test_menus["available1"].id
        assert data["items"][0]["quantity"] == 2
        assert data["total_items"] == 2
        assert data["total_amount"] == 600 * 2

    def test_add_increment_quantity(
        self,
        client: TestClient,
        db_session,
        guest_with_store,
        test_menus,
    ):
        """同じ商品を追加すると数量が加算される"""
        client.cookies.set("guest_session_id", guest_with_store.session_id)

        # 1回目の追加
        client.post(
            "/api/guest/cart/add",
            json={
                "menu_id": test_menus["available1"].id,
                "quantity": 1,
            },
        )

        # 2回目の追加（同じメニュー）
        response = client.post(
            "/api/guest/cart/add",
            json={
                "menu_id": test_menus["available1"].id,
                "quantity": 3,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["items"][0]["quantity"] == 4  # 1 + 3

    def test_add_without_store(
        self, client: TestClient, guest_without_store, test_menus
    ):
        """店舗を選択していない場合はエラー"""
        client.cookies.set("guest_session_id", guest_without_store.session_id)

        response = client.post(
            "/api/guest/cart/add",
            json={
                "menu_id": test_menus["available1"].id,
                "quantity": 1,
            },
        )

        assert response.status_code == 400
        assert "店舗を選択してください" in response.json()["detail"]

    def test_add_menu_not_found(self, client: TestClient, guest_with_store):
        """存在しないメニューを追加しようとするとエラー"""
        client.cookies.set("guest_session_id", guest_with_store.session_id)

        response = client.post(
            "/api/guest/cart/add",
            json={"menu_id": 99999, "quantity": 1},
        )

        assert response.status_code == 404

    def test_add_different_store_menu(
        self,
        client: TestClient,
        guest_with_store,
        another_store_menu,
    ):
        """選択店舗と異なる店舗のメニューはエラー"""
        client.cookies.set("guest_session_id", guest_with_store.session_id)

        response = client.post(
            "/api/guest/cart/add",
            json={"menu_id": another_store_menu.id, "quantity": 1},
        )

        assert response.status_code == 400

    def test_add_unavailable_menu(
        self, client: TestClient, guest_with_store, test_menus
    ):
        """在庫切れメニューはエラー"""
        client.cookies.set("guest_session_id", guest_with_store.session_id)

        response = client.post(
            "/api/guest/cart/add",
            json={
                "menu_id": test_menus["unavailable"].id,
                "quantity": 1,
            },
        )

        assert response.status_code == 400

    def test_get_cart_empty(self, client: TestClient, guest_with_store):
        """空のカートを取得"""
        client.cookies.set("guest_session_id", guest_with_store.session_id)

        response = client.get("/api/guest/cart")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0
        assert data["total_items"] == 0

    def test_get_cart_with_items(
        self,
        client: TestClient,
        db_session,
        guest_with_store,
        test_menus,
    ):
        """商品が入っているカートを取得"""
        cart_item1 = GuestCartItem(
            session_id=guest_with_store.session_id,
            menu_id=test_menus["available1"].id,
            quantity=2,
        )
        cart_item2 = GuestCartItem(
            session_id=guest_with_store.session_id,
            menu_id=test_menus["available2"].id,
            quantity=1,
        )
        db_session.add_all([cart_item1, cart_item2])
        db_session.commit()

        client.cookies.set("guest_session_id", guest_with_store.session_id)

        response = client.get("/api/guest/cart")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total_items"] == 3

    def test_update_cart_item(
        self,
        client: TestClient,
        db_session,
        guest_with_store,
        test_menus,
    ):
        """カートアイテムの数量を更新"""
        cart_item = GuestCartItem(
            session_id=guest_with_store.session_id,
            menu_id=test_menus["available1"].id,
            quantity=2,
        )
        db_session.add(cart_item)
        db_session.commit()
        db_session.refresh(cart_item)

        client.cookies.set("guest_session_id", guest_with_store.session_id)

        response = client.put(
            f"/api/guest/cart/item/{cart_item.id}",
            json={"quantity": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["quantity"] == 5

    def test_update_item_not_found(self, client: TestClient, guest_with_store):
        """存在しないカートアイテムの更新はエラー"""
        client.cookies.set("guest_session_id", guest_with_store.session_id)

        response = client.put(
            "/api/guest/cart/item/99999",
            json={"quantity": 5},
        )

        assert response.status_code == 404

    def test_update_wrong_session(
        self,
        client: TestClient,
        db_session,
        guest_with_store,
        test_menus,
    ):
        """他のセッションのアイテムは更新不可"""
        from datetime import datetime, timedelta

        other_session = GuestSession(
            session_id="other-session-id",
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db_session.add(other_session)
        db_session.commit()

        cart_item = GuestCartItem(
            session_id=other_session.session_id,
            menu_id=test_menus["available1"].id,
            quantity=2,
        )
        db_session.add(cart_item)
        db_session.commit()
        db_session.refresh(cart_item)

        client.cookies.set("guest_session_id", guest_with_store.session_id)

        response = client.put(
            f"/api/guest/cart/item/{cart_item.id}",
            json={"quantity": 5},
        )

        assert response.status_code == 403

    def test_delete_cart_item(
        self,
        client: TestClient,
        db_session,
        guest_with_store,
        test_menus,
    ):
        """カートからアイテムを削除"""
        cart_item = GuestCartItem(
            session_id=guest_with_store.session_id,
            menu_id=test_menus["available1"].id,
            quantity=2,
        )
        db_session.add(cart_item)
        db_session.commit()
        db_session.refresh(cart_item)

        client.cookies.set("guest_session_id", guest_with_store.session_id)

        response = client.delete(f"/api/guest/cart/item/{cart_item.id}")

        assert response.status_code == 200
        assert len(response.json()["items"]) == 0

    def test_delete_item_not_found(self, client: TestClient, guest_with_store):
        """存在しないアイテムの削除はエラー"""
        client.cookies.set("guest_session_id", guest_with_store.session_id)

        response = client.delete("/api/guest/cart/item/99999")

        assert response.status_code == 404

    def test_delete_wrong_session(
        self,
        client: TestClient,
        db_session,
        guest_with_store,
        test_menus,
    ):
        """他のセッションのアイテムは削除不可"""
        from datetime import datetime, timedelta

        other_session = GuestSession(
            session_id="other-session",
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db_session.add(other_session)
        db_session.commit()

        cart_item = GuestCartItem(
            session_id=other_session.session_id,
            menu_id=test_menus["available1"].id,
            quantity=2,
        )
        db_session.add(cart_item)
        db_session.commit()
        db_session.refresh(cart_item)

        client.cookies.set("guest_session_id", guest_with_store.session_id)

        response = client.delete(f"/api/guest/cart/item/{cart_item.id}")

        assert response.status_code == 403
