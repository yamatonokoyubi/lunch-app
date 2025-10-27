"""
pytest設定とフィクスチャ

テスト用のデータベース、クライアント、ユーザーなどを提供
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth import get_password_hash
from database import Base, get_db
from main import app
from models import Menu, Order, Role, Store, User, UserRole

# テスト用インメモリデータベース
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    テスト用データベースセッションを提供
    各テストごとに新しいデータベースを作成
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    テスト用FastAPIクライアントを提供
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def customer_user_a(db_session):
    """
    テスト用顧客ユーザーA
    """
    user = User(
        username="customer_a",
        email="customer_a@test.com",
        full_name="テスト顧客A",
        hashed_password=get_password_hash("password123"),
        role="customer",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def customer_user_b(db_session):
    """
    テスト用顧客ユーザーB
    """
    user = User(
        username="customer_b",
        email="customer_b@test.com",
        full_name="テスト顧客B",
        hashed_password=get_password_hash("password123"),
        role="customer",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def customer_user_empty(db_session):
    """
    注文履歴がないテスト用顧客ユーザー
    """
    user = User(
        username="customer_empty",
        email="customer_empty@test.com",
        full_name="テスト顧客(履歴なし)",
        hashed_password=get_password_hash("password123"),
        role="customer",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def store_user(db_session, roles, store_a):
    """
    テスト用店舗ユーザー (owner権限付き)
    既存テストとの互換性のため、ownerロールを自動割当
    """
    user = User(
        username="store_user",
        email="store@test.com",
        full_name="テスト店舗",
        hashed_password=get_password_hash("password123"),
        role="store",
        is_active=True,
        store_id=store_a.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 既存テストとの互換性のため、ownerロールを割り当て
    user_role = UserRole(user_id=user.id, role_id=roles["owner"].id)
    db_session.add(user_role)
    db_session.commit()

    return user


@pytest.fixture
def roles(db_session):
    """
    テスト用役割データを作成
    """
    owner_role = Role(name="owner", description="店舗オーナー")
    manager_role = Role(name="manager", description="店舗マネージャー")
    staff_role = Role(name="staff", description="店舗スタッフ")

    db_session.add(owner_role)
    db_session.add(manager_role)
    db_session.add(staff_role)
    db_session.commit()

    db_session.refresh(owner_role)
    db_session.refresh(manager_role)
    db_session.refresh(staff_role)

    return {"owner": owner_role, "manager": manager_role, "staff": staff_role}


@pytest.fixture
def owner_user(db_session, roles):
    """
    テスト用オーナーユーザー
    """
    user = User(
        username="owner_user",
        email="owner@test.com",
        full_name="テストオーナー",
        hashed_password=get_password_hash("password123"),
        role="store",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # ロールを割り当て
    user_role = UserRole(user_id=user.id, role_id=roles["owner"].id)
    db_session.add(user_role)
    db_session.commit()

    return user


@pytest.fixture
def manager_user(db_session, roles):
    """
    テスト用マネージャーユーザー
    """
    user = User(
        username="manager_user",
        email="manager@test.com",
        full_name="テストマネージャー",
        hashed_password=get_password_hash("password123"),
        role="store",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # ロールを割り当て
    user_role = UserRole(user_id=user.id, role_id=roles["manager"].id)
    db_session.add(user_role)
    db_session.commit()

    return user


@pytest.fixture
def staff_user(db_session, roles):
    """
    テスト用スタッフユーザー
    """
    user = User(
        username="staff_user",
        email="staff@test.com",
        full_name="テストスタッフ",
        hashed_password=get_password_hash("password123"),
        role="store",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # ロールを割り当て
    user_role = UserRole(user_id=user.id, role_id=roles["staff"].id)
    db_session.add(user_role)
    db_session.commit()

    return user


@pytest.fixture
def test_menu(db_session, store_a):
    """
    テスト用メニュー
    """
    menu = Menu(
        name="テスト弁当",
        price=800,
        description="テスト用の弁当です",
        image_url="https://example.com/test.jpg",
        is_available=True,
        store_id=store_a.id,
    )
    db_session.add(menu)
    db_session.commit()
    db_session.refresh(menu)
    return menu


@pytest.fixture
def test_menu_2(db_session, store_a):
    """
    テスト用メニュー2
    """
    menu = Menu(
        name="テスト弁当2",
        price=900,
        description="テスト用の弁当2です",
        image_url="https://example.com/test2.jpg",
        is_available=True,
        store_id=store_a.id,
    )
    db_session.add(menu)
    db_session.commit()
    db_session.refresh(menu)
    return menu


@pytest.fixture
def test_menu_unavailable(db_session):
    """
    在庫切れのテスト用メニュー
    """
    menu = Menu(
        name="在庫切れ弁当",
        price=1000,
        description="在庫切れのテスト用弁当です",
        image_url="https://example.com/unavailable.jpg",
        is_available=False,
    )
    db_session.add(menu)
    db_session.commit()
    db_session.refresh(menu)
    return menu


@pytest.fixture
def orders_for_customer_a(db_session, customer_user_a, test_menu, test_menu_2, store_a):
    """
    顧客Aの注文履歴を作成
    """
    # 3つの注文を作成（新しい順にテストするため、異なる日時で作成）
    orders = []

    # 注文1（最古）
    order1 = Order(
        user_id=customer_user_a.id,
        menu_id=test_menu.id,
        store_id=store_a.id,
        quantity=2,
        total_price=test_menu.price * 2,
        status="completed",
        ordered_at=datetime.utcnow() - timedelta(days=2),
        notes="最初の注文",
    )
    db_session.add(order1)
    orders.append(order1)

    # 注文2（中間）
    order2 = Order(
        user_id=customer_user_a.id,
        menu_id=test_menu_2.id,
        store_id=store_a.id,
        quantity=1,
        total_price=test_menu_2.price * 1,
        status="confirmed",
        ordered_at=datetime.utcnow() - timedelta(days=1),
        notes="2番目の注文",
    )
    db_session.add(order2)
    orders.append(order2)

    # 注文3（最新）
    order3 = Order(
        user_id=customer_user_a.id,
        menu_id=test_menu.id,
        store_id=store_a.id,
        quantity=3,
        total_price=test_menu.price * 3,
        status="pending",
        ordered_at=datetime.utcnow(),
        notes="最新の注文",
    )
    db_session.add(order3)
    orders.append(order3)

    db_session.commit()
    for order in orders:
        db_session.refresh(order)

    return orders


@pytest.fixture
def orders_for_customer_b(db_session, customer_user_b, test_menu, store_a):
    """
    顧客Bの注文履歴を作成
    """
    orders = []

    # 注文1
    order1 = Order(
        user_id=customer_user_b.id,
        menu_id=test_menu.id,
        store_id=store_a.id,
        quantity=1,
        total_price=test_menu.price * 1,
        status="pending",
        ordered_at=datetime.utcnow(),
        notes="顧客Bの注文",
    )
    db_session.add(order1)
    orders.append(order1)

    db_session.commit()
    for order in orders:
        db_session.refresh(order)

    return orders


def get_auth_token(client, username: str, password: str) -> str:
    """
    認証トークンを取得するヘルパー関数
    """
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers_customer_a(client, customer_user_a):
    """
    顧客Aの認証ヘッダー
    """
    token = get_auth_token(client, "customer_a", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_customer_b(client, customer_user_b):
    """
    顧客Bの認証ヘッダー
    """
    token = get_auth_token(client, "customer_b", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_customer_empty(client, customer_user_empty):
    """
    注文履歴がない顧客の認証ヘッダー
    """
    token = get_auth_token(client, "customer_empty", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_store(client, store_user):
    """
    店舗ユーザーの認証ヘッダー
    """
    token = get_auth_token(client, "store_user", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_owner(client, owner_user):
    """
    オーナーユーザーの認証ヘッダー
    """
    token = get_auth_token(client, "owner_user", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_manager(client, manager_user):
    """
    マネージャーユーザーの認証ヘッダー
    """
    token = get_auth_token(client, "manager_user", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_staff(client, staff_user):
    """
    スタッフユーザーの認証ヘッダー
    """
    token = get_auth_token(client, "staff_user", "password123")
    return {"Authorization": f"Bearer {token}"}


# ===== 店舗関連フィクスチャ =====


@pytest.fixture
def store_a(db_session):
    """
    テスト用店舗A
    """
    from datetime import time

    store = Store(
        name="テスト店舗A",
        address="東京都渋谷区1-2-3",
        phone_number="03-1234-5678",
        email="storea@test.com",
        opening_time=time(9, 0),
        closing_time=time(21, 0),
        description="テスト用の店舗Aです",
        is_active=True,
    )
    db_session.add(store)
    db_session.commit()
    db_session.refresh(store)
    return store


@pytest.fixture
def store_b(db_session):
    """
    テスト用店舗B
    """
    from datetime import time

    store = Store(
        name="テスト店舗B",
        address="東京都新宿区4-5-6",
        phone_number="03-9876-5432",
        email="storeb@test.com",
        opening_time=time(10, 0),
        closing_time=time(22, 0),
        description="テスト用の店舗Bです",
        is_active=True,
    )
    db_session.add(store)
    db_session.commit()
    db_session.refresh(store)
    return store


@pytest.fixture
def owner_user_store_a(db_session, roles, store_a):
    """
    店舗Aのオーナーユーザー
    """
    user = User(
        username="owner_store_a",
        email="owner_a@test.com",
        full_name="店舗Aオーナー",
        hashed_password=get_password_hash("password123"),
        role="store",
        store_id=store_a.id,
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
def manager_user_store_a(db_session, roles, store_a):
    """
    店舗Aのマネージャーユーザー
    """
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
def staff_user_store_a(db_session, roles, store_a):
    """
    店舗Aのスタッフユーザー
    """
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
def owner_user_store_b(db_session, roles, store_b):
    """
    店舗Bのオーナーユーザー
    """
    user = User(
        username="owner_store_b",
        email="owner_b@test.com",
        full_name="店舗Bオーナー",
        hashed_password=get_password_hash("password123"),
        role="store",
        store_id=store_b.id,
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
def auth_headers_owner_store_a(client, owner_user_store_a):
    """
    店舗Aオーナーの認証ヘッダー
    """
    token = get_auth_token(client, "owner_store_a", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_manager_store_a(client, manager_user_store_a):
    """
    店舗Aマネージャーの認証ヘッダー
    """
    token = get_auth_token(client, "manager_store_a", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_staff_store_a(client, staff_user_store_a):
    """
    店舗Aスタッフの認証ヘッダー
    """
    token = get_auth_token(client, "staff_store_a", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_owner_store_b(client, owner_user_store_b):
    """
    店舗Bオーナーの認証ヘッダー
    """
    token = get_auth_token(client, "owner_store_b", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_user_store_b(db_session, roles, store_b):
    """
    店舗Bのマネージャーユーザー
    """
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
def staff_user_store_b(db_session, roles, store_b):
    """
    店舗Bのスタッフユーザー
    """
    user = User(
        username="staff_store_b",
        email="staff_b@test.com",
        full_name="店舗Bスタッフ",
        hashed_password=get_password_hash("password123"),
        role="store",
        store_id=store_b.id,
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
def auth_headers_manager_store_b(client, manager_user_store_b):
    """
    店舗Bマネージャーの認証ヘッダー
    """
    token = get_auth_token(client, "manager_store_b", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_staff_store_b(client, staff_user_store_b):
    """
    店舗Bスタッフの認証ヘッダー
    """
    token = get_auth_token(client, "staff_store_b", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def menu_store_a(db_session, store_a):
    """
    店舗Aのメニュー
    """
    menu = Menu(
        name="店舗A特製弁当",
        price=850,
        description="店舗A専用のテスト弁当",
        image_url="https://example.com/menu_a.jpg",
        is_available=True,
        store_id=store_a.id,
    )
    db_session.add(menu)
    db_session.commit()
    db_session.refresh(menu)
    return menu


@pytest.fixture
def menu_store_a_2(db_session, store_a):
    """
    店舗Aのメニュー2
    """
    menu = Menu(
        name="店舗Aデラックス弁当",
        price=1200,
        description="店舗A専用の高級弁当",
        image_url="https://example.com/menu_a2.jpg",
        is_available=True,
        store_id=store_a.id,
    )
    db_session.add(menu)
    db_session.commit()
    db_session.refresh(menu)
    return menu


@pytest.fixture
def menu_store_b(db_session, store_b):
    """
    店舗Bのメニュー
    """
    menu = Menu(
        name="店舗B特製弁当",
        price=900,
        description="店舗B専用のテスト弁当",
        image_url="https://example.com/menu_b.jpg",
        is_available=True,
        store_id=store_b.id,
    )
    db_session.add(menu)
    db_session.commit()
    db_session.refresh(menu)
    return menu


@pytest.fixture
def order_store_a(db_session, customer_user_a, menu_store_a, store_a):
    """
    店舗Aの注文
    """
    order = Order(
        user_id=customer_user_a.id,
        menu_id=menu_store_a.id,
        store_id=store_a.id,
        quantity=2,
        total_price=menu_store_a.price * 2,
        status="pending",
        ordered_at=datetime.utcnow(),
        notes="店舗Aへの注文",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def order_store_b(db_session, customer_user_b, menu_store_b, store_b):
    """
    店舗Bの注文
    """
    order = Order(
        user_id=customer_user_b.id,
        menu_id=menu_store_b.id,
        store_id=store_b.id,
        quantity=1,
        total_price=menu_store_b.price * 1,
        status="confirmed",
        ordered_at=datetime.utcnow(),
        notes="店舗Bへの注文",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


# ===== 追加フィクスチャ (test/76用) =====
# これらは既存のstore_aベースのフィクスチャのエイリアス


@pytest.fixture
def sample_store(store_a):
    """
    テスト用の汎用店舗 (store_aのエイリアス)
    """
    return store_a


@pytest.fixture
def sample_menu(test_menu):
    """
    テスト用の汎用メニュー (test_menuのエイリアス)
    """
    return test_menu


@pytest.fixture
def sample_customer(customer_user_a):
    """
    テスト用の汎用顧客 (customer_user_aのエイリアス)
    """
    return customer_user_a


# ===== 監査ログテスト用フィクスチャ =====


@pytest.fixture
def owner_token(client, owner_user_store_a):
    """
    オーナーユーザーの認証トークンを返す
    """
    response = client.post(
        "/auth/token",
        data={"username": owner_user_store_a.username, "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def manager_token(client, manager_user_store_a):
    """
    マネージャーユーザーの認証トークンを返す
    """
    response = client.post(
        "/auth/token",
        data={"username": manager_user_store_a.username, "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def other_store_menu(db_session, store_b):
    """
    他店舗のメニュー（store_bのメニュー）
    """
    menu = Menu(
        name="他店舗の弁当",
        price=700,
        description="店舗Bの弁当",
        is_available=True,
        store_id=store_b.id,
    )
    db_session.add(menu)
    db_session.commit()
    db_session.refresh(menu)
    return menu
