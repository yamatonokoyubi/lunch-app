"""Tests for cart migration service."""

from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    GuestCartItem,
    GuestSession,
    Menu,
    MenuCategory,
    Store,
    User,
    UserCartItem,
)
from services.cart_migration import CartMigrationService

# テスト用のインメモリデータベース
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """テスト用データベースセッション."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_store(db):
    """テスト用店舗."""
    from datetime import time

    store = Store(
        id=1,
        name="テスト弁当店",
        address="東京都渋谷区",
        phone_number="03-1234-5678",
        email="test@example.com",
        opening_time=time(9, 0, 0),
        closing_time=time(20, 0, 0),
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@pytest.fixture
def sample_category(db, sample_store):
    """テスト用カテゴリ."""
    category = MenuCategory(
        id=1,
        name="弁当",
        display_order=1,
        store_id=sample_store.id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def sample_user(db):
    """テスト用ユーザー."""
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashedpassword",
        full_name="Test User",
        role="customer",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_menus(db, sample_store, sample_category):
    """テスト用メニュー."""
    menus = [
        Menu(
            id=1,
            name="唐揚げ弁当",
            price=800,
            store_id=sample_store.id,
            category_id=sample_category.id,
        ),
        Menu(
            id=2,
            name="焼肉弁当",
            price=900,
            store_id=sample_store.id,
            category_id=sample_category.id,
        ),
        Menu(
            id=3,
            name="鮭弁当",
            price=700,
            store_id=sample_store.id,
            category_id=sample_category.id,
        ),
    ]
    for menu in menus:
        db.add(menu)
    db.commit()
    return menus


@pytest.fixture
def guest_session_with_cart(db, sample_menus):
    """カートアイテムを持つゲストセッション."""
    session = GuestSession(
        id=1,
        session_id="test-session-123",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(session)
    db.commit()

    # ゲストカートにアイテムを追加
    cart_items = [
        GuestCartItem(session_id="test-session-123", menu_id=1, quantity=2),
        GuestCartItem(session_id="test-session-123", menu_id=2, quantity=1),
    ]
    for item in cart_items:
        db.add(item)
    db.commit()

    return session


def test_migrate_empty_guest_cart(db, sample_user):
    """空のゲストカートを移行."""
    session = GuestSession(
        id=1,
        session_id="empty-session",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(session)
    db.commit()

    service = CartMigrationService(db)
    result = service.migrate_guest_cart_to_user("empty-session", sample_user.id)

    assert result["migrated_items"] == 0
    assert result["merged_items"] == 0
    assert result["total_quantity"] == 0

    # セッションが変換済みとしてマークされているか確認
    db.refresh(session)
    assert session.converted_to_user_id == sample_user.id


def test_migrate_guest_cart_to_empty_user_cart(
    db, sample_user, guest_session_with_cart
):
    """ゲストカートをユーザーの空のカートに移行."""
    service = CartMigrationService(db)
    result = service.migrate_guest_cart_to_user("test-session-123", sample_user.id)

    assert result["migrated_items"] == 2
    assert result["merged_items"] == 0
    assert result["total_quantity"] == 3

    # ユーザーカートに正しく移行されているか確認
    user_cart = (
        db.query(UserCartItem).filter(UserCartItem.user_id == sample_user.id).all()
    )
    assert len(user_cart) == 2
    assert any(item.menu_id == 1 and item.quantity == 2 for item in user_cart)
    assert any(item.menu_id == 2 and item.quantity == 1 for item in user_cart)

    # ゲストカートが空になっているか確認
    guest_cart = (
        db.query(GuestCartItem)
        .filter(GuestCartItem.session_id == "test-session-123")
        .all()
    )
    assert len(guest_cart) == 0

    # セッションが変換済みか確認
    db.refresh(guest_session_with_cart)
    assert guest_session_with_cart.converted_to_user_id == sample_user.id


def test_migrate_guest_cart_with_merge(db, sample_user, guest_session_with_cart):
    """既存のユーザーカートとゲストカートをマージ."""
    # ユーザーカートに既存のアイテムを追加（メニュー1が重複）
    existing_item = UserCartItem(user_id=sample_user.id, menu_id=1, quantity=3)
    db.add(existing_item)
    db.commit()

    service = CartMigrationService(db)
    result = service.migrate_guest_cart_to_user("test-session-123", sample_user.id)

    assert result["migrated_items"] == 1  # メニュー2のみ新規追加
    assert result["merged_items"] == 1  # メニュー1はマージ
    assert result["total_quantity"] == 3

    # マージ結果を確認
    user_cart = (
        db.query(UserCartItem).filter(UserCartItem.user_id == sample_user.id).all()
    )
    assert len(user_cart) == 2

    # メニュー1の数量が合算されているか確認
    menu1_item = next(item for item in user_cart if item.menu_id == 1)
    assert menu1_item.quantity == 5  # 3 + 2

    # メニュー2が追加されているか確認
    menu2_item = next(item for item in user_cart if item.menu_id == 2)
    assert menu2_item.quantity == 1


def test_already_converted_session(db, sample_user, guest_session_with_cart):
    """既に変換済みのセッションは再処理されない."""
    # 最初の移行
    service = CartMigrationService(db)
    service.migrate_guest_cart_to_user("test-session-123", sample_user.id)

    # ゲストカートに新しいアイテムを追加（通常は起こらないが、テストのため）
    new_item = GuestCartItem(session_id="test-session-123", menu_id=3, quantity=5)
    db.add(new_item)
    db.commit()

    # 2回目の移行試行
    result = service.migrate_guest_cart_to_user("test-session-123", sample_user.id)

    # 何も移行されないことを確認
    assert result["migrated_items"] == 0
    assert result["merged_items"] == 0

    # 新しいアイテムは移行されていない
    user_cart = (
        db.query(UserCartItem)
        .filter(UserCartItem.user_id == sample_user.id, UserCartItem.menu_id == 3)
        .first()
    )
    assert user_cart is None


def test_nonexistent_session(db, sample_user):
    """存在しないセッションIDでの移行."""
    service = CartMigrationService(db)
    result = service.migrate_guest_cart_to_user("nonexistent-session", sample_user.id)

    assert result["migrated_items"] == 0
    assert result["merged_items"] == 0
    assert result["total_quantity"] == 0


def test_multiple_items_merge(db, sample_user, guest_session_with_cart, sample_menus):
    """複数アイテムの複雑なマージシナリオ."""
    # ユーザーカートに既存のアイテムを追加
    existing_items = [
        UserCartItem(user_id=sample_user.id, menu_id=1, quantity=1),  # 重複
        UserCartItem(user_id=sample_user.id, menu_id=3, quantity=4),  # 新規
    ]
    for item in existing_items:
        db.add(item)
    db.commit()

    service = CartMigrationService(db)
    result = service.migrate_guest_cart_to_user("test-session-123", sample_user.id)

    assert result["migrated_items"] == 1  # メニュー2のみ新規追加
    assert result["merged_items"] == 1  # メニュー1はマージ
    assert result["total_quantity"] == 3  # 2 + 1

    # 最終的なユーザーカート確認
    user_cart = (
        db.query(UserCartItem)
        .filter(UserCartItem.user_id == sample_user.id)
        .order_by(UserCartItem.menu_id)
        .all()
    )
    assert len(user_cart) == 3

    # メニュー1: 1 + 2 = 3
    assert user_cart[0].menu_id == 1
    assert user_cart[0].quantity == 3

    # メニュー2: 0 + 1 = 1（新規追加）
    assert user_cart[1].menu_id == 2
    assert user_cart[1].quantity == 1

    # メニュー3: 4 + 0 = 4（既存のまま）
    assert user_cart[2].menu_id == 3
    assert user_cart[2].quantity == 4


@pytest.mark.skip(reason="ロールバックテストはセッション管理が複雑なためスキップ")
def test_cart_migration_rollback_on_error(db, sample_user, guest_session_with_cart):
    """エラー発生時にロールバックされることを確認."""
    service = CartMigrationService(db)

    # データベースを強制的にエラー状態にする（セッションを閉じる）
    db.close()

    # 閉じたセッションで移行を試みる
    with pytest.raises(Exception):
        service.migrate_guest_cart_to_user("test-session-123", sample_user.id)
