"""
メニュー変更履歴（監査ログ）機能のテスト
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from models import Menu, MenuChangeLog, Store, User


class TestMenuAuditLog:
    """メニュー監査ログ機能のテスト"""

    def test_menu_create_logs_change(
        self, client: TestClient, db_session: Session, owner_token: str
    ):
        """メニュー作成時に変更履歴が記録されること"""
        # メニューを作成
        menu_data = {
            "name": "テスト弁当",
            "price": 500,
            "description": "テスト用の弁当",
            "is_available": True,
        }

        response = client.post(
            "/store/menus",
            json=menu_data,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 200
        menu_id = response.json()["id"]

        # 変更履歴が記録されているか確認
        logs = (
            db_session.query(MenuChangeLog)
            .filter(MenuChangeLog.menu_id == menu_id, MenuChangeLog.action == "create")
            .all()
        )

        assert len(logs) > 0
        log = logs[0]
        assert log.action == "create"
        assert log.menu_id == menu_id
        assert log.user_id is not None

    def test_menu_update_logs_change(
        self, client: TestClient, db_session: Session, owner_token: str, test_menu: Menu
    ):
        """メニュー更新時に変更履歴が記録されること"""
        # メニューを更新
        update_data = {"name": "更新後の弁当", "price": 600}

        response = client.put(
            f"/store/menus/{test_menu.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 200

        # 変更履歴が記録されているか確認
        logs = (
            db_session.query(MenuChangeLog)
            .filter(
                MenuChangeLog.menu_id == test_menu.id, MenuChangeLog.action == "update"
            )
            .all()
        )

        assert len(logs) > 0
        # 個別フィールドの変更ログを確認
        name_log = next((log for log in logs if log.field_name == "name"), None)
        assert name_log is not None
        assert name_log.new_value == "更新後の弁当"

        price_log = next((log for log in logs if log.field_name == "price"), None)
        assert price_log is not None
        assert price_log.new_value == "600"

    def test_menu_delete_logs_change(
        self, client: TestClient, db_session: Session, owner_token: str, test_menu: Menu
    ):
        """メニュー削除時に変更履歴が記録されること"""
        menu_id = test_menu.id

        # メニューを削除
        response = client.delete(
            f"/store/menus/{menu_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 200

        # 変更履歴が記録されているか確認
        logs = (
            db_session.query(MenuChangeLog)
            .filter(MenuChangeLog.menu_id == menu_id, MenuChangeLog.action == "delete")
            .all()
        )

        assert len(logs) > 0
        log = logs[0]
        assert log.action == "delete"
        assert log.changes is not None

    def test_get_menu_change_logs(
        self, client: TestClient, db_session: Session, owner_token: str, test_menu: Menu
    ):
        """特定メニューの変更履歴を取得できること"""
        # いくつか変更履歴を作成
        for i in range(3):
            client.put(
                f"/store/menus/{test_menu.id}",
                json={"price": 500 + i * 100},
                headers={"Authorization": f"Bearer {owner_token}"},
            )

        # 変更履歴を取得
        response = client.get(
            f"/store/menus/{test_menu.id}/change-logs",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "logs" in data
        assert "total" in data
        assert data["total"] > 0
        assert len(data["logs"]) > 0

        # 最新の変更が最初に来ることを確認（降順）
        logs = data["logs"]
        for i in range(len(logs) - 1):
            log1_time = datetime.fromisoformat(
                logs[i]["changed_at"].replace("Z", "+00:00")
            )
            log2_time = datetime.fromisoformat(
                logs[i + 1]["changed_at"].replace("Z", "+00:00")
            )
            assert log1_time >= log2_time

    def test_get_menu_change_logs_with_action_filter(
        self, client: TestClient, db_session: Session, owner_token: str, test_menu: Menu
    ):
        """アクションでフィルターして変更履歴を取得できること"""
        # メニューを更新
        client.put(
            f"/store/menus/{test_menu.id}",
            json={"price": 999},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        # updateアクションのみ取得
        response = client.get(
            f"/store/menus/{test_menu.id}/change-logs?action=update",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # すべてのログがupdateアクションであることを確認
        for log in data["logs"]:
            assert log["action"] == "update"

    def test_get_store_change_logs(
        self, client: TestClient, db_session: Session, owner_token: str, test_menu: Menu
    ):
        """店舗全体の変更履歴を取得できること"""
        # メニューを作成
        client.post(
            "/store/menus",
            json={"name": "新しい弁当", "price": 800, "is_available": True},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        # 店舗全体の変更履歴を取得
        response = client.get(
            "/store/change-logs", headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        assert "logs" in data
        assert "total" in data
        assert data["total"] > 0

    def test_get_store_change_logs_with_menu_filter(
        self, client: TestClient, db_session: Session, owner_token: str, test_menu: Menu
    ):
        """メニューIDでフィルターして店舗の変更履歴を取得できること"""
        # メニューを更新
        client.put(
            f"/store/menus/{test_menu.id}",
            json={"price": 777},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        # 特定メニューの変更履歴のみ取得
        response = client.get(
            f"/store/change-logs?menu_id={test_menu.id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # すべてのログが指定したメニューのものであることを確認
        for log in data["logs"]:
            assert log["menu_id"] == test_menu.id

    def test_change_logs_pagination(
        self, client: TestClient, db_session: Session, owner_token: str, test_menu: Menu
    ):
        """変更履歴のページネーションが正しく動作すること"""
        # 複数の変更を作成
        for i in range(15):
            client.put(
                f"/store/menus/{test_menu.id}",
                json={"price": 500 + i},
                headers={"Authorization": f"Bearer {owner_token}"},
            )

        # 1ページ目を取得（5件ずつ）
        response1 = client.get(
            f"/store/menus/{test_menu.id}/change-logs?page=1&per_page=5",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # 2ページ目を取得
        response2 = client.get(
            f"/store/menus/{test_menu.id}/change-logs?page=2&per_page=5",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response2.status_code == 200
        data2 = response2.json()

        assert len(data1["logs"]) == 5
        assert len(data2["logs"]) == 5
        # ページが異なることを確認
        assert data1["logs"][0]["id"] != data2["logs"][0]["id"]

    def test_change_logs_require_owner_permission(
        self, client: TestClient, db_session: Session, manager_token: str
    ):
        """変更履歴の閲覧にはowner権限が必要であること"""
        # managerトークンで変更履歴を取得しようとする
        response = client.get(
            "/store/change-logs", headers={"Authorization": f"Bearer {manager_token}"}
        )
        # ownerのみアクセス可能なので403エラー
        assert response.status_code == 403

    def test_change_logs_isolation(
        self, client: TestClient, db_session: Session, owner_token: str, other_store_menu: Menu
    ):
        """他店舗のメニュー変更履歴は閲覧できないこと"""
        # 他店舗のメニューIDで変更履歴を取得しようとする
        response = client.get(
            f"/store/menus/{other_store_menu.id}/change-logs",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        # 404エラーになることを確認（存在しないように見える）
        assert response.status_code == 404

    def test_change_logs_performance(
        self, client: TestClient, db_session: Session, owner_token: str, test_menu: Menu
    ):
        """大量の変更履歴があってもパフォーマンスが劣化しないこと"""
        import time

        # 100件の変更履歴を作成
        for i in range(100):
            client.put(
                f"/store/menus/{test_menu.id}",
                json={"price": 500 + i},
                headers={"Authorization": f"Bearer {owner_token}"},
            )

        # 変更履歴取得のパフォーマンスを測定
        start_time = time.time()
        response = client.get(
            f"/store/menus/{test_menu.id}/change-logs?per_page=20",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        end_time = time.time()

        assert response.status_code == 200
        # 1秒以内に完了することを確認
        assert (end_time - start_time) < 1.0
