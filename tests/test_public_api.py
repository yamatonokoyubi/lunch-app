"""
公開APIのテスト

認証不要の店舗一覧APIをテスト
"""

from datetime import time as dt_time

import pytest

from models import Store


@pytest.fixture
def test_stores(db_session):
    """テスト用店舗データの作成"""
    # 既存データをクリア（念のため）
    db_session.query(Store).delete()
    db_session.commit()

    stores = [
        Store(
            name="渋谷弁当店",
            address="東京都渋谷区1-1-1",
            phone_number="03-1234-5678",
            email="shibuya@example.com",
            opening_time=dt_time(9, 0, 0),
            closing_time=dt_time(21, 0, 0),
            description="渋谷駅近くの人気弁当店",
            is_active=True,
        ),
        Store(
            name="新宿弁当店",
            address="東京都新宿区2-2-2",
            phone_number="03-2345-6789",
            email="shinjuku@example.com",
            opening_time=dt_time(10, 0, 0),
            closing_time=dt_time(20, 0, 0),
            description="新宿の美味しい弁当",
            is_active=True,
        ),
        Store(
            name="横浜弁当店",
            address="神奈川県横浜市3-3-3",
            phone_number="045-1234-5678",
            email="yokohama@example.com",
            opening_time=dt_time(8, 0, 0),
            closing_time=dt_time(22, 0, 0),
            description="横浜の老舗弁当店",
            is_active=False,  # 営業時間外
        ),
    ]

    for store in stores:
        db_session.add(store)
    db_session.commit()

    yield stores


class TestPublicStoresAPI:
    """公開店舗一覧APIのテスト"""

    def test_get_all_active_stores(self, client, test_stores):
        """すべての営業中店舗を取得"""
        response = client.get("/api/public/stores")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2  # 営業中の店舗のみ
        assert data[0]["name"] == "新宿弁当店"  # 名前順
        assert data[1]["name"] == "渋谷弁当店"

    def test_get_all_stores_including_inactive(self, client, test_stores):
        """営業時間外を含むすべての店舗を取得"""
        response = client.get("/api/public/stores?is_active=false")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # すべての店舗

    def test_search_by_name(self, client, test_stores):
        """店舗名で検索"""
        response = client.get("/api/public/stores?search=渋谷")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "渋谷弁当店"

    def test_search_by_address(self, client, test_stores):
        """住所で検索"""
        response = client.get("/api/public/stores?search=神奈川")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # 営業時間外の店舗は除外

        # 営業時間外も含めて検索
        response = client.get("/api/public/stores?search=神奈川&is_active=false")
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "横浜弁当店"

    def test_search_no_results(self, client, test_stores):
        """検索結果が0件"""
        response = client.get("/api/public/stores?search=大阪")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_store_response_structure(self, client, test_stores):
        """レスポンス構造のチェック"""
        response = client.get("/api/public/stores")

        assert response.status_code == 200
        data = response.json()
        store = data[0]

        # 必須フィールド
        assert "id" in store
        assert "name" in store
        assert "address" in store
        assert "phone_number" in store
        assert "email" in store
        assert "opening_time" in store
        assert "closing_time" in store
        assert "is_active" in store

        # オプショナルフィールド
        assert "description" in store
        assert "image_url" in store

        # created_at, updated_atは含まれない（公開API）
        assert "created_at" not in store
        assert "updated_at" not in store
        assert "created_at" not in store
        assert "updated_at" not in store
