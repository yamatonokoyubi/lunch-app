"""
店舗情報アクセス・操作権限テスト

Owner/Manager/Staffの役割に基づいた店舗情報へのアクセスと操作権限を検証
"""

import pytest
from fastapi import status

from auth import get_password_hash
from models import Store, User, UserRole


@pytest.fixture
def store_c(db_session):
    """テスト用店舗C"""
    from datetime import time

    store = Store(
        name="テスト店舗C",
        address="東京都世田谷区7-8-9",
        phone_number="03-5555-6666",
        email="storec@test.com",
        opening_time=time(11, 0),
        closing_time=time(23, 0),
        description="テスト用の店舗Cです",
        is_active=True,
    )
    db_session.add(store)
    db_session.commit()
    db_session.refresh(store)
    return store


@pytest.fixture
def owner_user_no_store(db_session, roles):
    """店舗に所属していないOwnerユーザー（全店舗管理用）"""
    user = User(
        username="owner_no_store",
        email="owner_nostore@test.com",
        full_name="全店舗管理オーナー",
        hashed_password=get_password_hash("password123"),
        role="store",
        store_id=None,  # 店舗に所属しない
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    user_role = UserRole(user_id=user.id, role_id=roles["owner"].id)
    db_session.add(user_role)
    db_session.commit()

    return user


@pytest.fixture
def staff_user_store_a(db_session, roles, store_a):
    """店舗AのStaffユーザー"""
    user = User(
        username="staff_store_a",
        email="staff_a@test.com",
        full_name="店舗Aスタッフ",
        hashed_password=get_password_hash("password123"),
        role="store",
        store_id=store_a.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    user_role = UserRole(user_id=user.id, role_id=roles["staff"].id)
    db_session.add(user_role)
    db_session.commit()

    return user


@pytest.fixture
def auth_headers_owner_no_store(client, owner_user_no_store):
    """店舗なしOwnerユーザーの認証ヘッダー"""
    response = client.post(
        "/api/auth/login",
        json={"username": "owner_no_store", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_staff_a(client, staff_user_store_a):
    """店舗AスタッフユーザーのHTTPヘッダー"""
    response = client.post(
        "/api/auth/login",
        json={"username": "staff_store_a", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestStoresListAPI:
    """GET /api/store/stores - 全店舗一覧取得API"""

    def test_owner_can_get_all_stores(
        self,
        client,
        auth_headers_owner_no_store,
        store_a,
        store_b,
        store_c,
    ):
        """Ownerは全店舗一覧を取得できる"""
        response = client.get(
            "/api/store/stores",
            headers=auth_headers_owner_no_store,
        )

        assert response.status_code == 200
        data = response.json()

        assert "stores" in data
        assert "total" in data
        assert data["total"] >= 3  # 最低3店舗

        # 店舗情報の確認
        store_names = [s["name"] for s in data["stores"]]
        assert "テスト店舗A" in store_names
        assert "テスト店舗B" in store_names
        assert "テスト店舗C" in store_names

    def test_manager_cannot_access_stores_list(
        self,
        client,
        auth_headers_manager_store_a,
    ):
        """Managerは全店舗一覧にアクセスできない"""
        response = client.get(
            "/api/store/stores",
            headers=auth_headers_manager_store_a,
        )

        assert response.status_code == 403

    def test_staff_cannot_access_stores_list(
        self,
        client,
        auth_headers_staff_a,
    ):
        """Staffは全店舗一覧にアクセスできない"""
        response = client.get(
            "/api/store/stores",
            headers=auth_headers_staff_a,
        )

        assert response.status_code == 403


class TestStoreProfileGetAPI:
    """GET /api/store/profile - 店舗情報取得API"""

    def test_owner_can_get_any_store_with_store_id(
        self,
        client,
        auth_headers_owner_no_store,
        store_a,
        store_b,
    ):
        """Ownerはstore_idを指定して任意の店舗情報を取得できる"""
        # 店舗Aの取得
        response_a = client.get(
            f"/api/store/profile?store_id={store_a.id}",
            headers=auth_headers_owner_no_store,
        )
        assert response_a.status_code == 200
        data_a = response_a.json()
        assert data_a["id"] == store_a.id
        assert data_a["name"] == "テスト店舗A"

        # 店舗Bの取得
        response_b = client.get(
            f"/api/store/profile?store_id={store_b.id}",
            headers=auth_headers_owner_no_store,
        )
        assert response_b.status_code == 200
        data_b = response_b.json()
        assert data_b["id"] == store_b.id
        assert data_b["name"] == "テスト店舗B"

    def test_owner_must_specify_store_id(
        self,
        client,
        auth_headers_owner_no_store,
    ):
        """Ownerはstore_idを指定しない場合エラー"""
        response = client.get(
            "/api/store/profile",
            headers=auth_headers_owner_no_store,
        )

        assert response.status_code == 400
        assert "must specify store_id" in response.json()["detail"]

    def test_manager_can_get_own_store(
        self,
        client,
        auth_headers_manager_store_a,
        store_a,
    ):
        """Managerは自店舗の情報を取得できる"""
        response = client.get(
            "/api/store/profile",
            headers=auth_headers_manager_store_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == store_a.id
        assert data["name"] == "テスト店舗A"

    def test_manager_can_get_own_store_with_explicit_store_id(
        self,
        client,
        auth_headers_manager_store_a,
        store_a,
    ):
        """Managerは自店舗のstore_idを明示的に指定して取得できる"""
        response = client.get(
            f"/api/store/profile?store_id={store_a.id}",
            headers=auth_headers_manager_store_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == store_a.id

    def test_manager_cannot_access_other_store(
        self,
        client,
        auth_headers_manager_store_a,
        store_b,
    ):
        """Managerは他店舗の情報を取得できない"""
        response = client.get(
            f"/api/store/profile?store_id={store_b.id}",
            headers=auth_headers_manager_store_a,
        )

        assert response.status_code == 403
        assert "only access your own store" in response.json()["detail"]

    def test_staff_can_get_own_store(
        self,
        client,
        auth_headers_staff_a,
        store_a,
    ):
        """Staffは自店舗の情報を取得できる"""
        response = client.get(
            "/api/store/profile",
            headers=auth_headers_staff_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == store_a.id

    def test_staff_cannot_access_other_store(
        self,
        client,
        auth_headers_staff_a,
        store_b,
    ):
        """Staffは他店舗の情報を取得できない"""
        response = client.get(
            f"/api/store/profile?store_id={store_b.id}",
            headers=auth_headers_staff_a,
        )

        assert response.status_code == 403


class TestStoreProfileUpdateAPI:
    """PUT /api/store/profile - 店舗情報更新API"""

    def test_owner_can_update_any_store_with_store_id(
        self,
        client,
        auth_headers_owner_no_store,
        store_a,
        store_b,
    ):
        """Ownerはstore_idを指定して任意の店舗を更新できる"""
        # 店舗Aの更新
        response_a = client.put(
            "/api/store/profile",
            headers=auth_headers_owner_no_store,
            json={
                "store_id": store_a.id,
                "name": "更新された店舗A",
                "description": "Owner by updated",
            },
        )
        assert response_a.status_code == 200
        data_a = response_a.json()
        assert data_a["name"] == "更新された店舗A"
        assert data_a["description"] == "Owner by updated"

        # 店舗Bの更新
        response_b = client.put(
            "/api/store/profile",
            headers=auth_headers_owner_no_store,
            json={
                "store_id": store_b.id,
                "name": "更新された店舗B",
            },
        )
        assert response_b.status_code == 200
        data_b = response_b.json()
        assert data_b["name"] == "更新された店舗B"

    def test_owner_must_specify_store_id_for_update(
        self,
        client,
        auth_headers_owner_no_store,
    ):
        """Ownerはstore_idを指定しない場合更新できない"""
        response = client.put(
            "/api/store/profile",
            headers=auth_headers_owner_no_store,
            json={"name": "新しい名前"},
        )

        assert response.status_code == 400
        assert "must specify store_id" in response.json()["detail"]

    def test_manager_can_update_own_store(
        self,
        client,
        auth_headers_manager_store_a,
        store_a,
    ):
        """Managerは自店舗を更新できる"""
        response = client.put(
            "/api/store/profile",
            headers=auth_headers_manager_store_a,
            json={
                "name": "Managerが更新した店舗A",
                "description": "Manager updated",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Managerが更新した店舗A"
        assert data["description"] == "Manager updated"

    def test_manager_can_update_own_store_with_explicit_store_id(
        self,
        client,
        auth_headers_manager_store_a,
        store_a,
    ):
        """Managerは自店舗のstore_idを明示的に指定して更新できる"""
        response = client.put(
            "/api/store/profile",
            headers=auth_headers_manager_store_a,
            json={
                "store_id": store_a.id,
                "description": "自店舗ID指定で更新",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "自店舗ID指定で更新"

    def test_manager_cannot_update_other_store(
        self,
        client,
        auth_headers_manager_store_a,
        store_b,
    ):
        """Managerは他店舗を更新できない"""
        response = client.put(
            "/api/store/profile",
            headers=auth_headers_manager_store_a,
            json={
                "store_id": store_b.id,
                "name": "不正な更新",
            },
        )

        assert response.status_code == 403
        assert "only update your own store" in response.json()["detail"]

    def test_staff_cannot_update_store(
        self,
        client,
        auth_headers_staff_a,
    ):
        """Staffは店舗情報を更新できない（403 Forbidden）"""
        response = client.put(
            "/api/store/profile",
            headers=auth_headers_staff_a,
            json={"name": "Staffによる不正な更新"},
        )

        assert response.status_code == 403

    def test_staff_cannot_update_store_even_with_store_id(
        self,
        client,
        auth_headers_staff_a,
        store_a,
    ):
        """Staffはstore_idを指定しても更新できない"""
        response = client.put(
            "/api/store/profile",
            headers=auth_headers_staff_a,
            json={
                "store_id": store_a.id,
                "name": "Staffによる不正な更新",
            },
        )

        assert response.status_code == 403


class TestStoreAccessIntegration:
    """統合テスト: 複数ロールでの店舗情報アクセス"""

    def test_all_roles_access_pattern(
        self,
        client,
        auth_headers_owner_no_store,
        auth_headers_manager_store_a,
        auth_headers_manager_store_b,
        auth_headers_staff_a,
        store_a,
        store_b,
    ):
        """全ロールでのアクセスパターンを統合テスト"""
        # Owner: 全店舗一覧を取得
        stores_response = client.get(
            "/api/store/stores",
            headers=auth_headers_owner_no_store,
        )
        assert stores_response.status_code == 200
        assert stores_response.json()["total"] >= 2

        # Owner: 店舗Aを取得
        owner_get_a = client.get(
            f"/api/store/profile?store_id={store_a.id}",
            headers=auth_headers_owner_no_store,
        )
        assert owner_get_a.status_code == 200
        assert owner_get_a.json()["id"] == store_a.id

        # Owner: 店舗Bを更新
        owner_update_b = client.put(
            "/api/store/profile",
            headers=auth_headers_owner_no_store,
            json={"store_id": store_b.id, "description": "Owner integrated test"},
        )
        assert owner_update_b.status_code == 200

        # Manager A: 自店舗Aを取得
        manager_a_get = client.get(
            "/api/store/profile",
            headers=auth_headers_manager_store_a,
        )
        assert manager_a_get.status_code == 200
        assert manager_a_get.json()["id"] == store_a.id

        # Manager A: 店舗Bへのアクセス拒否
        manager_a_get_b = client.get(
            f"/api/store/profile?store_id={store_b.id}",
            headers=auth_headers_manager_store_a,
        )
        assert manager_a_get_b.status_code == 403

        # Manager B: 店舗Bを更新
        manager_b_update = client.put(
            "/api/store/profile",
            headers=auth_headers_manager_store_b,
            json={"description": "Manager B updated"},
        )
        assert manager_b_update.status_code == 200

        # Staff A: 自店舗Aを取得
        staff_get = client.get(
            "/api/store/profile",
            headers=auth_headers_staff_a,
        )
        assert staff_get.status_code == 200

        # Staff A: 更新は拒否
        staff_update = client.put(
            "/api/store/profile",
            headers=auth_headers_staff_a,
            json={"name": "Staff attempt"},
        )
        assert staff_update.status_code == 403
