"""
データベースモデル定義

SQLAlchemyを使用したデータベーステーブルの定義
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Store(Base):
    """店舗テーブル（マルチテナント対応の中核）"""

    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    address = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False)
    opening_time = Column(Time, nullable=False)
    closing_time = Column(Time, nullable=False)
    description = Column(Text)
    image_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # リレーションシップ
    users = relationship("User", back_populates="store")
    menus = relationship("Menu", back_populates="store")
    menu_categories = relationship("MenuCategory", back_populates="store")
    orders = relationship("Order", back_populates="store")


class MenuCategory(Base):
    """メニューカテゴリテーブル"""

    __tablename__ = "menu_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    store_id = Column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # リレーションシップ
    store = relationship("Store", back_populates="menu_categories")
    menus = relationship("Menu", back_populates="category")


class User(Base):
    """ユーザーテーブル"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'customer' or 'store'
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    store_id = Column(
        Integer, ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # リレーションシップ
    store = relationship("Store", back_populates="users")
    orders = relationship("Order", back_populates="user")
    user_roles = relationship("UserRole", back_populates="user")


class Role(Base):
    """役割テーブル（店舗スタッフの職位管理）"""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(
        String(50), unique=True, nullable=False, index=True
    )  # 'owner', 'manager', 'staff'
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # リレーションシップ
    user_roles = relationship("UserRole", back_populates="role")


class UserRole(Base):
    """ユーザー役割紐付けテーブル"""

    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id = Column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    # リレーションシップ
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class Menu(Base):
    """メニューテーブル"""

    __tablename__ = "menus"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    price = Column(Integer, nullable=False)
    description = Column(Text)
    image_url = Column(String(512))
    is_available = Column(Boolean, default=True)
    category_id = Column(
        Integer,
        ForeignKey("menu_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    store_id = Column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # リレーションシップ
    store = relationship("Store", back_populates="menus")
    category = relationship("MenuCategory", back_populates="menus")
    orders = relationship("Order", back_populates="menu")


class Order(Base):
    """注文テーブル"""

    __tablename__ = "orders"
    __table_args__ = (
        # 複合インデックス: パフォーマンス最適化
        # ダッシュボードAPIで頻繁に使用されるクエリパターンに対応
        {"extend_existing": True}
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    menu_id = Column(Integer, ForeignKey("menus.id"), nullable=False)
    store_id = Column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity = Column(Integer, nullable=False)
    total_price = Column(Integer, nullable=False)
    status = Column(String(50), default="pending", index=True)  # インデックス追加
    delivery_time = Column(Time)
    notes = Column(Text)
    ordered_at = Column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # インデックス追加
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # リレーションシップ
    store = relationship("Store", back_populates="orders")
    user = relationship("User", back_populates="orders")
    menu = relationship("Menu", back_populates="orders")


class PasswordResetToken(Base):
    """パスワードリセットトークンテーブル"""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MenuChangeLog(Base):
    """メニュー変更履歴テーブル（監査ログ）"""

    __tablename__ = "menu_change_logs"

    id = Column(Integer, primary_key=True, index=True)
    menu_id = Column(
        Integer, ForeignKey("menus.id", ondelete="CASCADE"), nullable=False, index=True
    )
    store_id = Column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action = Column(
        String(50), nullable=False, index=True
    )  # 'create', 'update', 'delete'
    field_name = Column(String(100), nullable=True)  # 変更されたフィールド名
    old_value = Column(Text, nullable=True)  # 変更前の値（JSON文字列）
    new_value = Column(Text, nullable=True)  # 変更後の値（JSON文字列）
    changes = Column(JSON, nullable=True)  # 全体の変更内容（JSON形式）
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # リレーションシップ
    menu = relationship("Menu")
    store = relationship("Store")
    user = relationship("User")


class GuestSession(Base):
    """ゲストセッションテーブル

    ログイン前のユーザーのセッション情報を管理
    - セッションIDは暗号学的に安全な64文字のランダム文字列
    - 24時間の有効期限を持つ
    - 店舗選択情報を保存
    - ログイン後のユーザーIDとの紐付けをサポート
    """

    __tablename__ = "guest_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    selected_store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    converted_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_accessed_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # リレーションシップ
    selected_store = relationship("Store")
    converted_user = relationship("User")
    cart_items = relationship(
        "GuestCartItem", back_populates="session", cascade="all, delete-orphan"
    )


class GuestCartItem(Base):
    """ゲストカートアイテムテーブル

    ゲストセッションに紐づくカート内のメニューアイテムを管理
    - セッション削除時にカスケード削除される
    - メニューと数量を保持
    """

    __tablename__ = "guest_cart_items"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        String(64),
        ForeignKey("guest_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    menu_id = Column(Integer, ForeignKey("menus.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # リレーションシップ
    session = relationship("GuestSession", back_populates="cart_items")
    menu = relationship("Menu")


class UserCartItem(Base):
    """ユーザーカートアイテムテーブル

    ログインユーザーのカート内のメニューアイテムを管理
    - ユーザー削除時にカスケード削除される
    - メニューと数量を保持
    """

    __tablename__ = "user_cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    menu_id = Column(Integer, ForeignKey("menus.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # リレーションシップ
    user = relationship("User")
    menu = relationship("Menu")
