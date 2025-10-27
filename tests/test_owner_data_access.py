"""
Owner ロールの全店舗データアクセステスト

Ownerは全店舗のデータを、Manager/Staffは自店舗のみのデータをアクセスできることを確認する
対象API:
- GET /api/store/dashboard - ダッシュボードサマリー
- GET /api/store/dashboard/weekly-sales - 週次売上
- GET /api/store/reports/sales - 売上レポート
"""

from datetime import date, datetime, timedelta

import pytest

from models import Menu, Order


@pytest.fixture
def manager_user_store_a(db_session, roles, store_a):
    """店舗Aのマネージャーユーザー"""
    from auth import get_password_hash
    from models import User, UserRole

    user = User(
        username="manager_store_a",
        email="manager_a@test.com",
        full_name="店舗Aマネージャー",
        hashed_password=get_password_hash("password123"),
        role="store",
        store_id=store_a.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    user_role = UserRole(user_id=user.id, role_id=roles["manager"].id)
    db_session.add(user_role)
    db_session.commit()

    return user


@pytest.fixture
def manager_user_store_b(db_session, roles, store_b):
    """店舗Bのマネージャーユーザー"""
    from auth import get_password_hash
    from models import User, UserRole

    user = User(
        username="manager_store_b",
        email="manager_b@test.com",
        full_name="店舗Bマネージャー",
        hashed_password=get_password_hash("password123"),
        role="store",
        store_id=store_b.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    user_role = UserRole(user_id=user.id, role_id=roles["manager"].id)
    db_session.add(user_role)
    db_session.commit()

    return user


@pytest.fixture
def menu_store_a(db_session, store_a):
    """店舗Aのメニュー"""
    menu = Menu(
        name="店舗A弁当",
        price=1000,
        description="店舗Aのテスト弁当",
        is_available=True,
        store_id=store_a.id,
    )
    db_session.add(menu)
    db_session.commit()
    db_session.refresh(menu)
    return menu


@pytest.fixture
def menu_store_b(db_session, store_b):
    """店舗Bのメニュー"""
    menu = Menu(
        name="店舗B弁当",
        price=1500,
        description="店舗Bのテスト弁当",
        is_available=True,
        store_id=store_b.id,
    )
    db_session.add(menu)
    db_session.commit()
    db_session.refresh(menu)
    return menu


@pytest.fixture
def orders_multi_store(
    db_session, customer_user_a, menu_store_a, menu_store_b, store_a, store_b
):
    """複数店舗の注文データを作成"""
    # 今日の日付で時刻のみ変える
    today = date.today()

    # 店舗Aの注文（3件）- すべて今日
    orders_a = []
    for i in range(3):
        order = Order(
            user_id=customer_user_a.id,
            menu_id=menu_store_a.id,
            store_id=store_a.id,
            quantity=1,
            total_price=menu_store_a.price,
            status="completed",
            ordered_at=datetime.combine(today, datetime.min.time())
            + timedelta(hours=10 + i),
        )
        db_session.add(order)
        orders_a.append(order)

    # 店舗Bの注文（2件）- すべて今日
    orders_b = []
    for i in range(2):
        order = Order(
            user_id=customer_user_a.id,
            menu_id=menu_store_b.id,
            store_id=store_b.id,
            quantity=1,
            total_price=menu_store_b.price,
            status="completed",
            ordered_at=datetime.combine(today, datetime.min.time())
            + timedelta(hours=12 + i),
        )
        db_session.add(order)
        orders_b.append(order)

    db_session.commit()
    return {"store_a": orders_a, "store_b": orders_b}


@pytest.fixture
def auth_headers_owner(client, owner_user):
    """Ownerユーザーの認証ヘッダー"""
    response = client.post(
        "/api/auth/login",
        json={"username": "owner_user", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_manager_a(client, manager_user_store_a):
    """店舗Aマネージャーの認証ヘッダー"""
    response = client.post(
        "/api/auth/login",
        json={"username": "manager_store_a", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_manager_b(client, manager_user_store_b):
    """店舗Bマネージャーの認証ヘッダー"""
    response = client.post(
        "/api/auth/login",
        json={"username": "manager_store_b", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestDashboardDataAccess:
    """ダッシュボードAPI (/api/store/dashboard) のデータアクセステスト"""

    def test_owner_sees_all_stores_data(
        self,
        client,
        auth_headers_owner,
        orders_multi_store,
        menu_store_a,
        menu_store_b,
    ):
        """Ownerは全店舗のデータ（店舗A 3件 + 店舗B 2件 = 計5件）を取得する"""
        response = client.get("/api/store/dashboard", headers=auth_headers_owner)

        assert response.status_code == 200
        data = response.json()

        # 全店舗の注文数
        assert data["total_orders"] == 5

        # 全店舗の売上 = 店舗A(1000 * 3) + 店舗B(1500 * 2)
        expected_sales = (menu_store_a.price * 3) + (menu_store_b.price * 2)
        assert data["total_sales"] == expected_sales

    def test_manager_sees_only_own_store_data(
        self,
        client,
        auth_headers_manager_a,
        orders_multi_store,
        menu_store_a,
    ):
        """店舗Aマネージャーは店舗Aのデータ（3件）のみを取得する"""
        response = client.get("/api/store/dashboard", headers=auth_headers_manager_a)

        assert response.status_code == 200
        data = response.json()

        # 店舗Aの注文数のみ
        assert data["total_orders"] == 3

        # 店舗Aの売上のみ
        expected_sales = menu_store_a.price * 3
        assert data["total_sales"] == expected_sales

    def test_different_managers_see_different_data(
        self,
        client,
        auth_headers_manager_a,
        auth_headers_manager_b,
        orders_multi_store,
        menu_store_a,
        menu_store_b,
    ):
        """異なる店舗のマネージャーは異なるデータを取得する"""
        # 店舗Aマネージャー
        response_a = client.get("/api/store/dashboard", headers=auth_headers_manager_a)
        assert response_a.status_code == 200
        data_a = response_a.json()

        # 店舗Bマネージャー
        response_b = client.get("/api/store/dashboard", headers=auth_headers_manager_b)
        assert response_b.status_code == 200
        data_b = response_b.json()

        # 注文数が異なる
        assert data_a["total_orders"] == 3
        assert data_b["total_orders"] == 2

        # 売上が異なる
        assert data_a["total_sales"] == menu_store_a.price * 3
        assert data_b["total_sales"] == menu_store_b.price * 2


class TestWeeklySalesDataAccess:
    """週次売上API (/api/store/dashboard/weekly-sales) のデータアクセステスト"""

    def test_owner_sees_all_stores_weekly_sales(
        self,
        client,
        auth_headers_owner,
        orders_multi_store,
        menu_store_a,
        menu_store_b,
    ):
        """Ownerは全店舗の週次売上を取得する"""
        response = client.get(
            "/api/store/dashboard/weekly-sales", headers=auth_headers_owner
        )

        assert response.status_code == 200
        data = response.json()

        # レスポンスにlabelsとdataがある
        assert "labels" in data
        assert "data" in data
        assert len(data["labels"]) == 7  # 7日分
        assert len(data["data"]) == 7

        # 今日のデータが含まれている
        today = date.today().isoformat()
        assert today in data["labels"]

        # 今日のインデックスを取得
        today_index = data["labels"].index(today)
        today_revenue = data["data"][today_index]

        # 全店舗の売上
        expected_sales = (menu_store_a.price * 3) + (menu_store_b.price * 2)
        assert today_revenue == expected_sales

    def test_manager_sees_only_own_store_weekly_sales(
        self,
        client,
        auth_headers_manager_a,
        orders_multi_store,
        menu_store_a,
    ):
        """店舗Aマネージャーは店舗Aの週次売上のみを取得する"""
        response = client.get(
            "/api/store/dashboard/weekly-sales", headers=auth_headers_manager_a
        )

        assert response.status_code == 200
        data = response.json()

        # レスポンスにlabelsとdataがある
        assert "labels" in data
        assert "data" in data

        # 今日のデータが含まれている
        today = date.today().isoformat()
        assert today in data["labels"]

        # 今日のインデックスを取得
        today_index = data["labels"].index(today)
        today_revenue = data["data"][today_index]

        # 店舗Aの売上のみ
        expected_sales = menu_store_a.price * 3
        assert today_revenue == expected_sales


class TestSalesReportDataAccess:
    """売上レポートAPI (/api/store/reports/sales) のデータアクセステスト"""

    def test_owner_sees_all_stores_sales_report(
        self,
        client,
        auth_headers_owner,
        orders_multi_store,
        menu_store_a,
        menu_store_b,
    ):
        """Ownerは全店舗の売上レポートを取得する"""
        today = date.today().isoformat()

        response = client.get(
            "/api/store/reports/sales",
            params={"start_date": today, "end_date": today},
            headers=auth_headers_owner,
        )

        assert response.status_code == 200
        data = response.json()

        # 全店舗の注文数
        assert data["total_orders"] == 5

        # 全店舗の売上
        expected_sales = (menu_store_a.price * 3) + (menu_store_b.price * 2)
        assert data["total_sales"] == expected_sales

        # 日次データ
        assert len(data["daily_reports"]) == 1
        assert data["daily_reports"][0]["total_orders"] == 5

    def test_manager_sees_only_own_store_sales_report(
        self,
        client,
        auth_headers_manager_a,
        orders_multi_store,
        menu_store_a,
    ):
        """店舗Aマネージャーは店舗Aの売上レポートのみを取得する"""
        today = date.today().isoformat()

        response = client.get(
            "/api/store/reports/sales",
            params={"start_date": today, "end_date": today},
            headers=auth_headers_manager_a,
        )

        assert response.status_code == 200
        data = response.json()

        # 店舗Aの注文数のみ
        assert data["total_orders"] == 3

        # 店舗Aの売上のみ
        expected_sales = menu_store_a.price * 3
        assert data["total_sales"] == expected_sales

        # 日次データ
        assert len(data["daily_reports"]) == 1
        assert data["daily_reports"][0]["total_orders"] == 3

    def test_owner_menu_report_includes_all_stores(
        self,
        client,
        auth_headers_owner,
        orders_multi_store,
        menu_store_a,
        menu_store_b,
    ):
        """Ownerのメニューレポートには全店舗のメニューが含まれる"""
        today = date.today().isoformat()

        response = client.get(
            "/api/store/reports/sales",
            params={"start_date": today, "end_date": today},
            headers=auth_headers_owner,
        )

        assert response.status_code == 200
        data = response.json()

        # メニューレポートに2つのメニュー（店舗A・B）が含まれる
        menu_reports = data["menu_reports"]
        assert len(menu_reports) == 2

        # メニューIDでソート
        menu_reports_sorted = sorted(menu_reports, key=lambda x: x["menu_id"])

        # 店舗Aのメニュー
        assert menu_reports_sorted[0]["menu_name"] == "店舗A弁当"
        assert menu_reports_sorted[0]["total_quantity"] == 3

        # 店舗Bのメニュー
        assert menu_reports_sorted[1]["menu_name"] == "店舗B弁当"
        assert menu_reports_sorted[1]["total_quantity"] == 2

    def test_manager_menu_report_only_own_store(
        self,
        client,
        auth_headers_manager_a,
        orders_multi_store,
        menu_store_a,
    ):
        """マネージャーのメニューレポートには自店舗のメニューのみ含まれる"""
        today = date.today().isoformat()

        response = client.get(
            "/api/store/reports/sales",
            params={"start_date": today, "end_date": today},
            headers=auth_headers_manager_a,
        )

        assert response.status_code == 200
        data = response.json()

        # メニューレポートに1つのメニュー（店舗Aのみ）が含まれる
        menu_reports = data["menu_reports"]
        assert len(menu_reports) == 1
        assert menu_reports[0]["menu_name"] == "店舗A弁当"
        assert menu_reports[0]["total_quantity"] == 3
