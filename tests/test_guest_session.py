"""
ゲストセッション管理APIのユニットテスト

セッションの生成、取得、更新、削除の動作を検証
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import GuestSession, Store

# テスト用データベース設定
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_guest_session.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """テスト用データベースセッション"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """各テスト前にデータベースをセットアップ"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_store(setup_database):
    """テスト用の店舗を作成"""
    from datetime import time as dt_time

    db = TestingSessionLocal()
    store = Store(
        name="テスト店舗",
        address="東京都渋谷区1-2-3",
        phone_number="03-1234-5678",
        email="test@example.com",
        opening_time=dt_time(9, 0, 0),  # time オブジェクトを使用
        closing_time=dt_time(21, 0, 0),  # time オブジェクトを使用
        is_active=True,
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    db.close()
    return store


class TestGuestSessionCreation:
    """ゲストセッション作成のテスト"""

    def test_create_new_session(self, setup_database):
        """新しいセッションを作成できることを検証"""
        response = client.post("/api/guest/session")

        assert response.status_code == 201
        data = response.json()

        # レスポンスの検証
        assert "session_id" in data
        assert len(data["session_id"]) == 64  # 64文字のセッションID
        assert "created_at" in data
        assert "expires_at" in data
        assert "last_accessed_at" in data
        assert data["selected_store_id"] is None

        # Cookieが設定されていることを確認
        assert "guest_session_id" in response.cookies

    def test_session_id_is_unique(self, setup_database):
        """各セッションIDが一意であることを検証"""
        # 新しいクライアントインスタンスを使用して完全に独立したセッションを作成
        with TestClient(app) as client1:
            response1 = client1.post("/api/guest/session")

        with TestClient(app) as client2:
            response2 = client2.post("/api/guest/session")

        session_id_1 = response1.json()["session_id"]
        session_id_2 = response2.json()["session_id"]

        assert session_id_1 != session_id_2

    def test_existing_session_returns_same_session(self, setup_database):
        """既存のセッションがある場合、同じセッションを返すことを検証"""
        # 最初のセッション作成
        response1 = client.post("/api/guest/session")
        session_id_1 = response1.json()["session_id"]
        cookie = response1.cookies["guest_session_id"]

        # 同じCookieで再度リクエスト
        response2 = client.post(
            "/api/guest/session", cookies={"guest_session_id": cookie}
        )
        session_id_2 = response2.json()["session_id"]

        assert session_id_1 == session_id_2

    def test_session_expiry_is_24_hours(self, setup_database):
        """セッションの有効期限が24時間後に設定されることを検証"""
        response = client.post("/api/guest/session")
        data = response.json()

        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))

        time_diff = expires_at - created_at
        expected_diff = timedelta(hours=24)

        # 1分の誤差を許容
        assert abs(time_diff - expected_diff) < timedelta(minutes=1)


class TestGuestSessionRetrieval:
    """ゲストセッション取得のテスト"""

    def test_get_current_session(self, setup_database):
        """現在のセッション情報を取得できることを検証"""
        # セッション作成
        create_response = client.post("/api/guest/session")
        cookie = create_response.cookies["guest_session_id"]

        # セッション取得
        response = client.get(
            "/api/guest/session", cookies={"guest_session_id": cookie}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == create_response.json()["session_id"]

    def test_get_session_without_cookie_fails(self, setup_database):
        """Cookieなしでセッション取得すると401エラーになることを検証"""
        response = client.get("/api/guest/session")

        assert response.status_code == 401
        assert "guest session required" in response.json()["detail"].lower()

    def test_get_session_with_invalid_cookie_fails(self, setup_database):
        """無効なCookieでセッション取得すると401エラーになることを検証"""
        response = client.get(
            "/api/guest/session", cookies={"guest_session_id": "invalid_id"}
        )

        assert response.status_code == 401


class TestStoreSelection:
    """店舗選択のテスト"""

    def test_update_selected_store(self, test_store):
        """店舗選択情報を保存できることを検証"""
        # セッション作成
        create_response = client.post("/api/guest/session")
        cookie = create_response.cookies["guest_session_id"]

        # 店舗選択
        response = client.post(
            "/api/guest/session/store",
            json={"store_id": test_store.id},
            cookies={"guest_session_id": cookie},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["selected_store_id"] == test_store.id

        # セッション取得で確認
        get_response = client.get(
            "/api/guest/session", cookies={"guest_session_id": cookie}
        )
        assert get_response.json()["selected_store_id"] == test_store.id

    def test_update_store_without_session_fails(self, test_store):
        """セッションなしで店舗選択すると401エラーになることを検証"""
        response = client.post(
            "/api/guest/session/store", json={"store_id": test_store.id}
        )

        assert response.status_code == 401

    def test_update_nonexistent_store_fails(self, setup_database):
        """存在しない店舗を選択すると404エラーになることを検証"""
        # セッション作成
        create_response = client.post("/api/guest/session")
        cookie = create_response.cookies["guest_session_id"]

        # 存在しない店舗ID
        response = client.post(
            "/api/guest/session/store",
            json={"store_id": 99999},
            cookies={"guest_session_id": cookie},
        )

        assert response.status_code == 404

    def test_update_store_multiple_times(self, test_store):
        """店舗選択を複数回更新できることを検証"""
        from datetime import time as dt_time

        # 2つ目の店舗を作成
        db = TestingSessionLocal()
        store2 = Store(
            name="テスト店舗2",
            address="東京都新宿区4-5-6",
            phone_number="03-9876-5432",
            email="test2@example.com",
            opening_time=dt_time(9, 0, 0),
            closing_time=dt_time(21, 0, 0),
            is_active=True,
        )
        db.add(store2)
        db.commit()
        db.refresh(store2)
        db.close()

        # セッション作成
        create_response = client.post("/api/guest/session")
        cookie = create_response.cookies["guest_session_id"]

        # 1つ目の店舗を選択
        response1 = client.post(
            "/api/guest/session/store",
            json={"store_id": test_store.id},
            cookies={"guest_session_id": cookie},
        )
        assert response1.json()["selected_store_id"] == test_store.id

        # 2つ目の店舗を選択（上書き）
        response2 = client.post(
            "/api/guest/session/store",
            json={"store_id": store2.id},
            cookies={"guest_session_id": cookie},
        )
        assert response2.json()["selected_store_id"] == store2.id


class TestSessionDeletion:
    """セッション削除のテスト"""

    def test_delete_session(self, setup_database):
        """セッションを削除できることを検証"""
        # セッション作成
        create_response = client.post("/api/guest/session")
        cookie = create_response.cookies["guest_session_id"]

        # セッション削除
        response = client.delete(
            "/api/guest/session", cookies={"guest_session_id": cookie}
        )

        assert response.status_code == 204

        # 削除後に取得すると401エラー
        get_response = client.get(
            "/api/guest/session", cookies={"guest_session_id": cookie}
        )
        assert get_response.status_code == 401

    def test_delete_session_removes_cookie(self, setup_database):
        """セッション削除時にCookieも削除されることを検証"""
        # セッション作成
        create_response = client.post("/api/guest/session")
        cookie = create_response.cookies["guest_session_id"]

        # セッション削除
        response = client.delete(
            "/api/guest/session", cookies={"guest_session_id": cookie}
        )

        # Cookieが削除されている（空文字列または不在）
        assert (
            response.cookies.get("guest_session_id") == ""
            or "guest_session_id" not in response.cookies
        )


class TestMultipleTabsScenario:
    """複数タブでの動作テスト"""

    def test_same_session_across_multiple_requests(self, setup_database):
        """同一ブラウザ（同一Cookie）で複数タブを開いても同じセッションを共有することを検証"""
        # セッション作成
        create_response = client.post("/api/guest/session")
        cookie = create_response.cookies["guest_session_id"]
        session_id = create_response.json()["session_id"]

        # タブ1でセッション取得
        tab1_response = client.get(
            "/api/guest/session", cookies={"guest_session_id": cookie}
        )

        # タブ2でセッション取得
        tab2_response = client.get(
            "/api/guest/session", cookies={"guest_session_id": cookie}
        )

        # 両方とも同じセッションID
        assert tab1_response.json()["session_id"] == session_id
        assert tab2_response.json()["session_id"] == session_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
