"""
API契約定義 - Single Source of Truth

このファイルは、バックエンドAPI（FastAPI）とフロントエンドの間の
すべてのデータ構造を定義する唯一の信頼できる情報源です。

編集時のルール:
1. 頻繁にgit pullを実行してコンフリクトを避ける
2. 小さな変更単位でPull Requestを作成する
3. 変更前にチームメンバーに事前連絡する
4. 変更後は必ずTypeScript型定義を再生成する
"""

import re
from datetime import datetime, time
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

# ===== 注文ステータス定義 =====


class OrderStatus(str, Enum):
    """
    注文ステータス（簡素化版）

    シンプルで直感的な4つのステータスで注文フローを管理:
    - PENDING: 注文受付（確認・在庫確認・決済処理中）
    - READY: 準備完了（弁当完成、顧客通知送信）
    - COMPLETED: 受取完了（顧客が受取済み）
    - CANCELLED: キャンセル（注文取消）
    """

    PENDING = "pending"  # 注文受付
    READY = "ready"  # 準備完了
    COMPLETED = "completed"  # 受取完了
    CANCELLED = "cancelled"  # キャンセル

    @classmethod
    def get_allowed_transitions(cls, current_status: str) -> List[str]:
        """
        許可されているステータス遷移を返す

        Args:
            current_status: 現在のステータス

        Returns:
            遷移可能なステータスのリスト
        """
        transitions = {
            cls.PENDING.value: [cls.READY.value, cls.CANCELLED.value],
            cls.READY.value: [cls.COMPLETED.value],
            cls.COMPLETED.value: [],
            cls.CANCELLED.value: [],
        }
        return transitions.get(current_status, [])


# ===== 共通型定義 =====


class SuccessResponse(BaseModel):
    """成功時の共通レスポンス"""

    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """エラー時の共通レスポンス"""

    success: bool = False
    message: str
    detail: Optional[str] = None


# ===== 認証関連 =====


class UserCreate(BaseModel):
    """ユーザー作成時のリクエスト"""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern="^(customer|store)$")


class UserLogin(BaseModel):
    """ログイン時のリクエスト"""

    username: str
    password: str


class RoleResponse(BaseModel):
    """ロール情報のレスポンス"""

    id: int
    name: str

    class Config:
        from_attributes = True


class UserRoleResponse(BaseModel):
    """ユーザーロール情報のレスポンス"""

    id: int
    role: RoleResponse

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """ユーザー情報のレスポンス"""

    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    store_id: Optional[int] = None
    created_at: datetime
    user_roles: List[UserRoleResponse] = []

    # 店舗情報も含める(オプショナル)
    store: Optional["StoreResponse"] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """認証トークンのレスポンス"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# ===== パスワードリセット関連 =====


class PasswordResetRequest(BaseModel):
    """パスワードリセット要求"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """パスワードリセット確認"""

    token: str
    new_password: str = Field(..., min_length=6)


class PasswordResetResponse(BaseModel):
    """パスワードリセットレスポンス"""

    message: str


# ===== 役割（Role）関連 =====


class RoleResponse(BaseModel):
    """役割情報のレスポンス"""

    id: int
    name: Literal["owner", "manager", "staff"]
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RoleAssignRequest(BaseModel):
    """ユーザーへ役割を割り当てるリクエスト"""

    user_id: int = Field(..., ge=1, description="割り当て対象のユーザーID")
    role_id: int = Field(..., ge=1, description="割り当てる役割ID")


class UserRoleResponse(BaseModel):
    """ユーザー役割割り当て情報のレスポンス"""

    id: int
    user_id: int
    role_id: int
    assigned_at: datetime
    # 役割の詳細情報も含める
    role: RoleResponse

    class Config:
        from_attributes = True


class UserWithRolesResponse(BaseModel):
    """ユーザー情報＋割り当てられた役割一覧"""

    id: int
    username: str
    email: str
    full_name: str
    role: str  # 'customer' or 'store'
    is_active: bool
    created_at: datetime
    # 店舗ユーザーの場合、割り当てられた役割一覧
    user_roles: List[UserRoleResponse] = []

    class Config:
        from_attributes = True


# ===== 店舗（Store）関連 =====


class StoreBase(BaseModel):
    """店舗の基本情報"""

    name: str = Field(..., min_length=1, max_length=100, description="店舗名")
    address: str = Field(..., min_length=1, max_length=255, description="住所")
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="電話番号（ハイフンあり/なし両対応）",
    )
    email: EmailStr = Field(..., description="店舗のメールアドレス")
    opening_time: time = Field(..., description="開店時刻")
    closing_time: time = Field(..., description="閉店時刻")
    description: Optional[str] = Field(None, max_length=1000, description="店舗説明")
    image_url: Optional[str] = Field(None, max_length=500, description="店舗画像URL")
    is_active: bool = Field(True, description="店舗の有効/無効状態")

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """電話番号の形式を検証（日本の電話番号形式）"""
        # ハイフンを除去して数字のみにする
        digits_only = re.sub(r"[^0-9]", "", v)

        # 10桁または11桁の数字であることを確認
        if not re.match(r"^0\d{9,10}$", digits_only):
            raise ValueError(
                "電話番号は0から始まる10桁または11桁の数字である必要があります（例: 03-1234-5678, 090-1234-5678）"
            )

        return v

    @field_validator("closing_time")
    @classmethod
    def validate_closing_time(cls, v: time, info) -> time:
        """閉店時刻が開店時刻より後であることを検証"""
        # info.data から opening_time を取得
        if "opening_time" in info.data:
            opening_time = info.data["opening_time"]
            if v == opening_time:
                raise ValueError("閉店時刻は開店時刻と同じにはできません")
            # 開店時刻 < 閉店時刻（同日営業）または 開店時刻 > 閉店時刻（翌日営業）を許容
        return v


class StoreCreate(StoreBase):
    """店舗作成時のリクエスト"""

    pass


class StoreUpdate(BaseModel):
    """店舗更新時のリクエスト（すべてオプショナル）"""

    store_id: Optional[int] = Field(None, description="店舗ID（Owner専用）")
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="店舗名"
    )
    address: Optional[str] = Field(
        None, min_length=1, max_length=255, description="住所"
    )
    phone_number: Optional[str] = Field(
        None, min_length=10, max_length=20, description="電話番号"
    )
    email: Optional[EmailStr] = Field(None, description="店舗のメールアドレス")
    opening_time: Optional[time] = Field(None, description="開店時刻")
    closing_time: Optional[time] = Field(None, description="閉店時刻")
    description: Optional[str] = Field(None, max_length=1000, description="店舗説明")
    image_url: Optional[str] = Field(None, max_length=500, description="店舗画像URL")
    is_active: Optional[bool] = Field(None, description="店舗の有効/無効状態")

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """電話番号の形式を検証（日本の電話番号形式）"""
        if v is None:
            return v

        # ハイフンを除去して数字のみにする
        digits_only = re.sub(r"[^0-9]", "", v)

        # 10桁または11桁の数字であることを確認
        if not re.match(r"^0\d{9,10}$", digits_only):
            raise ValueError(
                "電話番号は0から始まる10桁または11桁の数字である必要があります（例: 03-1234-5678, 090-1234-5678）"
            )

        return v


class StoreResponse(StoreBase):
    """店舗情報のレスポンス"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StoreListResponse(BaseModel):
    """店舗一覧のレスポンス"""

    stores: List[StoreResponse]
    total: int


class StoreSummary(BaseModel):
    """店舗の簡易情報（Owner用店舗切替UI向け）"""

    id: int
    name: str
    address: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class StoresListResponse(BaseModel):
    """Owner用全店舗一覧レスポンス"""

    stores: List[StoreSummary]
    total: int


# ===== メニュー関連 =====


class MenuBase(BaseModel):
    """メニューの基本情報"""

    name: str = Field(..., min_length=1, max_length=255)
    price: int = Field(..., ge=1)
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_available: bool = True
    category_id: Optional[int] = None


class MenuCreate(MenuBase):
    """メニュー作成時のリクエスト（store_idは自動設定）"""

    pass


class MenuUpdate(BaseModel):
    """メニュー更新時のリクエスト"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    category_id: Optional[int] = None


class MenuBulkAvailabilityUpdate(BaseModel):
    """メニュー一括公開/非公開更新のリクエスト"""

    menu_ids: List[int] = Field(
        ..., min_length=1, description="更新対象のメニューIDリスト"
    )
    is_available: bool = Field(..., description="公開状態 (true=公開, false=非公開)")

    @field_validator("menu_ids")
    @classmethod
    def validate_menu_ids(cls, v):
        """メニューIDの重複をチェック"""
        if len(v) != len(set(v)):
            raise ValueError("重複したメニューIDが含まれています")
        return v


# ===== メニューカテゴリスキーマ =====


class MenuCategoryBase(BaseModel):
    """メニューカテゴリの基本スキーマ"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = Field(default=0, ge=0)
    is_active: Optional[bool] = True


class MenuCategoryCreate(MenuCategoryBase):
    """メニューカテゴリ作成のリクエスト"""

    pass


class MenuCategoryUpdate(BaseModel):
    """メニューカテゴリ更新のリクエスト"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class MenuCategoryResponse(MenuCategoryBase):
    """メニューカテゴリのレスポンス"""

    id: int
    store_id: int
    menu_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MenuCategoryListResponse(BaseModel):
    """メニューカテゴリ一覧のレスポンス"""

    categories: List[MenuCategoryResponse]
    total: int


class MenuResponse(MenuBase):
    """メニュー情報のレスポンス"""

    id: int
    store_id: int
    created_at: datetime
    updated_at: datetime

    # 関連情報（オプショナル）
    store: Optional["StoreResponse"] = None
    category: Optional[MenuCategoryResponse] = None

    class Config:
        from_attributes = True


class MenuListResponse(BaseModel):
    """メニュー一覧のレスポンス"""

    menus: List[MenuResponse]
    total: int


# ===== メニュー変更履歴（監査ログ）関連 =====


class MenuChangeLogResponse(BaseModel):
    """メニュー変更履歴のレスポンス"""

    id: int
    menu_id: int
    store_id: int
    user_id: Optional[int] = None
    action: Literal["create", "update", "delete"]
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changes: Optional[dict] = None
    changed_at: datetime

    # 関連情報（オプショナル）
    user: Optional["UserResponse"] = None

    class Config:
        from_attributes = True


class MenuChangeLogListResponse(BaseModel):
    """メニュー変更履歴一覧のレスポンス"""

    logs: List[MenuChangeLogResponse]
    total: int


# ===== 注文関連 =====


class OrderBase(BaseModel):
    """注文の基本情報"""

    menu_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1, le=10)
    delivery_time: Optional[time] = None
    notes: Optional[str] = Field(None, max_length=500)


class OrderCreate(OrderBase):
    """注文作成時のリクエスト（お客様用）"""

    # store_idはメニューから自動取得されるため不要
    pass


class OrderStatusUpdate(BaseModel):
    """注文ステータス更新時のリクエスト"""

    status: OrderStatus = Field(
        ..., description="新しいステータス（pending, ready, completed, cancelled のみ）"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """ステータスの妥当性を検証"""
        if isinstance(v, str):
            try:
                return OrderStatus(v)
            except ValueError:
                raise ValueError(
                    f"Invalid status. Must be one of: {[s.value for s in OrderStatus]}"
                )
        return v


class OrderResponse(BaseModel):
    """注文情報のレスポンス"""

    id: int
    user_id: int
    menu_id: int
    store_id: int
    quantity: int
    total_price: int
    status: str
    delivery_time: Optional[time]
    notes: Optional[str]
    ordered_at: datetime
    updated_at: datetime

    # メニュー情報も含める
    menu: MenuResponse

    # 店舗情報も含める（オプショナル）
    store: Optional["StoreResponse"] = None

    # お客様情報（店舗向けのみ）
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """注文一覧のレスポンス"""

    orders: List[OrderResponse]
    total: int


class OrderHistoryItem(BaseModel):
    """注文履歴の項目（メニュー情報を含む）"""

    id: int
    quantity: int
    total_price: int
    status: str
    delivery_time: Optional[time]
    notes: Optional[str]
    ordered_at: datetime
    updated_at: datetime

    # メニュー情報（商品名、画像URL）
    menu_id: int
    menu_name: str
    menu_image_url: Optional[str]
    menu_price: int

    class Config:
        from_attributes = True


class OrderHistoryResponse(BaseModel):
    """注文履歴のレスポンス"""

    orders: List[OrderHistoryItem]
    total: int


class YesterdayComparison(BaseModel):
    """前日比較データ"""

    orders_change: int  # 注文数の増減
    orders_change_percent: float  # 注文数の増減率（%）
    revenue_change: int  # 売上の増減
    revenue_change_percent: float  # 売上の増減率（%）


class PopularMenu(BaseModel):
    """人気メニュー情報"""

    menu_id: int
    menu_name: str
    order_count: int
    total_revenue: int


class HourlyOrderData(BaseModel):
    """時間帯別注文データ"""

    hour: int  # 0-23
    order_count: int


class OrderSummary(BaseModel):
    """注文サマリー（ダッシュボード用・簡素化版）"""

    # 基本統計
    total_orders: int
    pending_orders: int  # 注文受付中
    ready_orders: int  # 準備完了
    completed_orders: int  # 受取完了
    cancelled_orders: int  # キャンセル
    total_sales: int

    # 拡張統計
    today_revenue: int  # 本日の総売上（キャンセル除く）
    average_order_value: float  # 平均注文単価
    yesterday_comparison: YesterdayComparison  # 前日比較
    popular_menus: List[PopularMenu]  # 人気メニュートップ3
    hourly_orders: List[HourlyOrderData]  # 時間帯別注文数


# ===== レポート関連 =====


class DailySalesReport(BaseModel):
    """日別売上レポート"""

    date: str  # YYYY-MM-DD format
    total_orders: int
    total_sales: int
    popular_menu: Optional[str] = None


class MenuSalesReport(BaseModel):
    """メニュー別売上レポート"""

    menu_id: int
    menu_name: str
    total_quantity: int
    total_sales: int


class SalesReportResponse(BaseModel):
    """売上レポートのレスポンス"""

    period: str  # "daily", "weekly", "monthly"
    start_date: str
    end_date: str
    daily_reports: List[DailySalesReport]
    menu_reports: List[MenuSalesReport]
    total_sales: int
    total_orders: int


# ===== 検索・フィルタ関連 =====


class OrderFilter(BaseModel):
    """注文一覧フィルタ"""

    status: Optional[str] = None
    user_id: Optional[int] = None
    menu_id: Optional[int] = None
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class MenuFilter(BaseModel):
    """メニュー一覧フィルタ"""

    is_available: Optional[bool] = None
    price_min: Optional[int] = Field(None, ge=0)
    price_max: Optional[int] = Field(None, ge=0)
    search: Optional[str] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


# ===== ページネーション =====


class PaginationInfo(BaseModel):
    """ページネーション情報"""

    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel):
    """ページネーション付きレスポンスの基底クラス"""

    pagination: PaginationInfo


# ===== 店舗プロフィール =====


class StoreBase(BaseModel):
    """店舗基本情報"""

    name: str = Field(..., min_length=1, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = True


class StoreCreate(StoreBase):
    """店舗作成リクエスト"""

    opening_time: time = Field(..., description="開店時間")
    closing_time: time = Field(..., description="閉店時間")


class StoreUpdate(BaseModel):
    """店舗更新リクエスト（部分更新対応）"""

    store_id: Optional[int] = Field(None, description="店舗ID（Owner専用）")
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class StoreResponse(StoreBase):
    """店舗レスポンス"""

    id: int
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== 公開API用スキーマ =====


class StorePublicResponse(BaseModel):
    """公開店舗情報レスポンス（認証不要）"""

    id: int
    name: str
    address: str
    phone_number: str
    email: str
    opening_time: time
    closing_time: time
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# ===== ゲストセッション =====


class GuestSessionCreate(BaseModel):
    """ゲストセッション作成リクエスト"""

    pass  # 本文は不要（自動生成）


class GuestSessionResponse(BaseModel):
    """ゲストセッション情報レスポンス"""

    session_id: str
    selected_store_id: Optional[int] = None
    created_at: datetime
    expires_at: datetime
    last_accessed_at: datetime

    class Config:
        from_attributes = True


class GuestSessionStoreUpdate(BaseModel):
    """ゲストセッションの店舗選択更新リクエスト"""

    store_id: int = Field(..., description="選択する店舗ID", gt=0)


class GuestCartItemAdd(BaseModel):
    """ゲストカートへのアイテム追加リクエスト"""

    menu_id: int = Field(..., description="メニューID", gt=0)
    quantity: int = Field(1, description="数量", ge=1, le=99)


class GuestCartItemUpdate(BaseModel):
    """ゲストカートアイテムの数量更新リクエスト"""

    quantity: int = Field(..., description="数量", ge=1, le=99)


class GuestCartItemResponse(BaseModel):
    """ゲストカートアイテムレスポンス"""

    id: int
    menu_id: int
    quantity: int
    added_at: datetime
    menu: Optional["MenuResponse"] = None

    class Config:
        from_attributes = True


class GuestCartResponse(BaseModel):
    """ゲストカート全体のレスポンス"""

    session_id: str
    items: List[GuestCartItemResponse]
    total_items: int
    total_amount: int
    selected_store_id: Optional[int] = None


# ===== ユーザーカート関連 =====


class CartItemCreate(BaseModel):
    """カートアイテム作成リクエスト"""

    menu_id: int = Field(..., description="メニューID", gt=0)
    quantity: int = Field(1, description="数量", ge=1, le=99)


class CartItemResponse(BaseModel):
    """カートアイテムレスポンス"""

    id: int
    menu_id: int
    menu_name: str
    menu_price: int
    menu_image_url: Optional[str] = None
    quantity: int
    subtotal: int

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    """カート全体のレスポンス"""

    items: List[CartItemResponse]
    total_price: int
    total_items: int


# ===== 前方参照の解決 =====
# StoreResponse の前方参照を解決
UserResponse.model_rebuild()
MenuResponse.model_rebuild()
OrderResponse.model_rebuild()
GuestCartItemResponse.model_rebuild()
