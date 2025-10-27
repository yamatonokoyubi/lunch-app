"""
店舗向けルーター

店舗スタッフ専用のAPIエンドポイント
"""

import json
import os
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_active_user, get_current_store_user, require_role
from models import Menu, MenuCategory, MenuChangeLog, Order, Store, User
from schemas import (
    DailySalesReport,
    HourlyOrderData,
    MenuBulkAvailabilityUpdate,
    MenuCategoryCreate,
    MenuCategoryListResponse,
    MenuCategoryResponse,
    MenuCategoryUpdate,
    MenuChangeLogListResponse,
    MenuChangeLogResponse,
    MenuCreate,
    MenuListResponse,
    MenuResponse,
    MenuSalesReport,
    MenuUpdate,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdate,
    OrderSummary,
    PopularMenu,
    SalesReportResponse,
    StoreResponse,
    StoresListResponse,
    StoreUpdate,
    YesterdayComparison,
)

router = APIRouter(prefix="/store", tags=["店舗"])


# ===== ユーティリティ関数 =====


def user_has_role(user: User, role_name: str) -> bool:
    """
    ユーザーが指定されたロールを持っているかチェック

    Args:
        user: ユーザーオブジェクト
        role_name: ロール名 ('owner', 'manager', 'staff')

    Returns:
        bool: ロールを持っていればTrue
    """
    if not user or not user.user_roles:
        return False

    return any(ur.role and ur.role.name == role_name for ur in user.user_roles)


# ===== 監査ログヘルパー関数 =====


def log_menu_change(
    db: Session,
    menu_id: int,
    store_id: int,
    user_id: int,
    action: str,
    old_menu: Optional[Menu] = None,
    new_data: Optional[dict] = None,
):
    """
    メニュー変更履歴を記録する

    Args:
        db: データベースセッション
        menu_id: メニューID
        store_id: 店舗ID
        user_id: 変更者のユーザーID
        action: 操作種別 ('create', 'update', 'delete')
        old_menu: 変更前のMenuオブジェクト（update/deleteの場合）
        new_data: 変更後のデータ（create/updateの場合）
    """
    try:
        changes = {}

        if action == "create":
            # 作成時は新しいデータをそのまま記録
            changes = new_data or {}
            change_log = MenuChangeLog(
                menu_id=menu_id,
                store_id=store_id,
                user_id=user_id,
                action=action,
                changes=changes,
            )
            db.add(change_log)

        elif action == "update" and old_menu and new_data:
            # 更新時は変更されたフィールドのみ記録
            for field, new_value in new_data.items():
                old_value = getattr(old_menu, field, None)

                # 値が変更された場合のみ記録
                if old_value != new_value:
                    # 複雑なオブジェクトは文字列に変換
                    old_str = str(old_value) if old_value is not None else None
                    new_str = str(new_value) if new_value is not None else None

                    changes[field] = {"old": old_str, "new": new_str}

            # 全体の変更内容を1つのログとして記録
            if changes:
                summary_log = MenuChangeLog(
                    menu_id=menu_id,
                    store_id=store_id,
                    user_id=user_id,
                    action=action,
                    changes=changes,
                )
                db.add(summary_log)

        elif action == "delete" and old_menu:
            # 削除時は削除されたメニューの情報を記録
            menu_data = {
                "name": old_menu.name,
                "price": old_menu.price,
                "description": old_menu.description,
                "is_available": old_menu.is_available,
            }
            change_log = MenuChangeLog(
                menu_id=menu_id,
                store_id=store_id,
                user_id=user_id,
                action=action,
                changes=menu_data,
            )
            db.add(change_log)

        # ログ記録をコミット（メイン処理のコミット前）
        db.flush()

    except Exception as e:
        # ログ記録に失敗してもメイン処理は継続
        print(f"Warning: Failed to log menu change: {e}")


# ===== 店舗プロフィール管理 =====


@router.get(
    "/stores", response_model=StoresListResponse, summary="全店舗一覧取得（Owner専用）"
)
def get_all_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner"])),
):
    """
    Owner専用: 管理下の全店舗一覧を取得

    フロントエンドの店舗切替UIで使用される簡易店舗情報を返します。

    **必要な権限:** owner

    **戻り値:**
    - stores: 店舗一覧（id, name, address, is_activeのみ）
    - total: 総店舗数

    **エラー:**
    - 403: Owner権限がない場合
    """
    # 全店舗を取得（アクティブ/非アクティブ両方）
    stores = db.query(Store).order_by(Store.name.asc()).all()

    return {
        "stores": stores,
        "total": len(stores),
    }


@router.get("/profile", response_model=StoreResponse, summary="店舗プロフィール取得")
def get_store_profile(
    store_id: Optional[int] = Query(None, description="店舗ID（Owner専用）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_store_user),
):
    """
    店舗情報を取得

    - **Owner:** store_idパラメータで任意の店舗情報を取得可能
    - **Manager/Staff:** 自身の所属店舗情報のみ取得可能

    **必要な権限:** store (owner, manager, staff)

    **パラメータ:**
    - **store_id** (Optional): 取得する店舗のID（Owner専用）

    **戻り値:**
    - 店舗の詳細情報

    **エラー:**
    - 400: ユーザーが店舗に所属していない（Manager/Staffの場合）
    - 403: 他店舗へのアクセス試行（Manager/Staffの場合）
    - 404: 店舗が見つからない
    """
    is_owner = user_has_role(current_user, "owner")

    # 取得対象の店舗IDを決定
    if store_id is not None:
        # store_idが指定されている場合
        if not is_owner:
            # Owner以外は他店舗へのアクセス不可
            if current_user.store_id != store_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access your own store information",
                )
        target_store_id = store_id
    else:
        # store_idが指定されていない場合は自店舗
        if not is_owner and not current_user.store_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with any store",
            )
        target_store_id = current_user.store_id if not is_owner else None

        # Ownerでstore_id未指定の場合はエラー
        if is_owner and target_store_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Owner must specify store_id parameter",
            )

    # 店舗情報を取得
    store = db.query(Store).filter(Store.id == target_store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    return store


@router.put("/profile", response_model=StoreResponse, summary="店舗プロフィール更新")
def update_store_profile(
    store_update: StoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
):
    """
    店舗情報を更新

    - **Owner:** リクエストボディのstore_idで任意の店舗を更新可能
    - **Manager:** 自身の所属店舗のみ更新可能
    - **Staff:** 更新不可（403 Forbidden）

    **必要な権限:** owner, manager

    **パラメータ:**
    - **store_update**: 更新する店舗情報（部分更新可能）
      - store_id (Optional): 更新対象の店舗ID（Owner専用）

    **戻り値:**
    - 更新後の店舗情報

    **エラー:**
    - 400: ユーザーが店舗に所属していない（Manager）
    - 403: 他店舗への更新試行（Manager）/ Staff権限での更新試行
    - 404: 店舗が見つからない
    """
    is_owner = user_has_role(current_user, "owner")
    is_manager = user_has_role(current_user, "manager")

    # 更新対象の店舗IDを決定
    if store_update.store_id is not None:
        # store_idが指定されている場合
        if not is_owner:
            # Owner以外は他店舗への更新不可
            if current_user.store_id != store_update.store_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update your own store information",
                )
        target_store_id = store_update.store_id
    else:
        # store_idが未指定の場合
        if is_manager:
            # Managerは自店舗を更新
            if not current_user.store_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is not associated with any store",
                )
            target_store_id = current_user.store_id
        elif is_owner:
            # Ownerはstore_id必須
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Owner must specify store_id in request body",
            )
        else:
            # Staffは更新不可（ここには到達しないはず）
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff cannot update store information",
            )

    # 店舗情報を取得
    store = db.query(Store).filter(Store.id == target_store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    # 更新データを適用（提供されたフィールドのみ）
    # store_idは更新対象から除外
    update_data = store_update.model_dump(exclude_unset=True, exclude={"store_id"})
    for field, value in update_data.items():
        setattr(store, field, value)

    db.commit()
    db.refresh(store)

    return store


@router.post(
    "/profile/image", response_model=StoreResponse, summary="店舗画像アップロード"
)
async def upload_store_image(
    file: UploadFile = File(..., description="アップロードする画像ファイル"),
    store_id: Optional[int] = Query(None, description="店舗ID（Owner専用）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
):
    """
    店舗画像をアップロード（Owner/Manager専用）

    **必要な権限:** owner, manager

    **パラメータ:**
    - **file**: 画像ファイル（JPEG, PNG, GIF対応）
    - **store_id**: 店舗ID（Owner専用、省略時は自店舗）

    **戻り値:**
    - 更新後の店舗情報（image_urlが更新される）

    **エラー:**
    - 400: ユーザーが店舗に所属していない、または不正なファイル形式
    - 403: 指定した店舗へのアクセス権限がない
    - 404: 店舗が見つからない
    """
    # 役割チェック
    is_owner = user_has_role(current_user, "owner")

    # 店舗IDを決定
    if store_id is not None:
        # store_idが指定された場合
        if not is_owner:
            # Manager/Staffは自店舗以外を指定できない
            if current_user.store_id != store_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only upload images for your own store",
                )
        target_store_id = store_id
    else:
        # store_idが指定されていない場合は自店舗
        if not current_user.store_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with any store",
            )
        target_store_id = current_user.store_id

    # ファイル形式の検証
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Invalid file type. " f"Allowed: {', '.join(allowed_extensions)}"),
        )

    # 店舗情報を取得
    store = db.query(Store).filter(Store.id == target_store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    # アップロードディレクトリの作成
    upload_dir = Path("static/uploads/stores")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 一意のファイル名を生成
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename

    # 古い画像ファイルを削除（存在する場合）
    if store.image_url and store.image_url.startswith("/static/uploads/"):
        old_file_path = Path(store.image_url.lstrip("/"))
        if old_file_path.exists():
            old_file_path.unlink()

    # ファイルを保存
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    # データベースのimage_urlを更新
    store.image_url = f"/static/uploads/stores/{unique_filename}"
    db.commit()
    db.refresh(store)

    return store


@router.delete(
    "/profile/image",
    response_model=StoreResponse,
    summary="店舗画像削除",
)
def delete_store_image(
    store_id: Optional[int] = Query(None, description="店舗ID（Owner専用）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
):
    """
    店舗画像を削除（Owner/Manager専用）

    **必要な権限:** owner, manager

    **パラメータ:**
    - **store_id**: 店舗ID（Owner専用、省略時は自店舗）

    **戻り値:**
    - 更新後の店舗情報（image_urlがNullになる）

    **エラー:**
    - 400: ユーザーが店舗に所属していない
    - 403: 指定した店舗へのアクセス権限がない
    - 404: 店舗が見つからない
    """
    # 役割チェック
    is_owner = user_has_role(current_user, "owner")

    # 店舗IDを決定
    if store_id is not None:
        # store_idが指定された場合
        if not is_owner:
            # Manager/Staffは自店舗以外を指定できない
            if current_user.store_id != store_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only delete images for your own store",
                )
        target_store_id = store_id
    else:
        # store_idが指定されていない場合は自店舗
        if not current_user.store_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with any store",
            )
        target_store_id = current_user.store_id

    # 店舗情報を取得
    store = db.query(Store).filter(Store.id == target_store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    # 画像ファイルを削除（存在する場合）
    if store.image_url and store.image_url.startswith("/static/uploads/"):
        file_path = Path(store.image_url.lstrip("/"))
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                # ファイル削除に失敗してもDBは更新する
                pass

    # データベースのimage_urlをクリア
    store.image_url = None
    db.commit()
    db.refresh(store)

    return store


# ===== ダッシュボード =====


@router.get("/dashboard", response_model=OrderSummary, summary="ダッシュボード情報取得")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager", "staff"])),
):
    """
    本日の注文状況サマリーを取得（最適化版・簡素化ステータス対応）

    **必要な権限:** owner, manager, staff

    **注意:**
    - Owner: 全店舗のデータを合算
    - Manager/Staff: 自店舗のデータのみ

    **レスポンス:**
    - total_orders: 本日の総注文数
    - 各ステータスの注文数（pending, ready, completed, cancelled）
    - total_sales: 本日の総売上（キャンセル除く）
    - today_revenue: 本日の総売上（total_salesと同値）
    - average_order_value: 平均注文単価
    - yesterday_comparison: 前日との比較データ（注文数・売上の増減）
    - popular_menus: 本日の人気メニュートップ3
    - hourly_orders: 時間帯別の注文数（0-23時）

    **ステータス定義:**
    - pending: 注文受付（確認・在庫確認・決済処理）
    - ready: 準備完了（弁当完成、顧客通知）
    - completed: 受取完了（顧客が受取済み）
    - cancelled: キャンセル（注文取消）

    **最適化:**
    - 複数クエリを1つのCTEクエリに統合してDB往復を削減
    - インデックスを活用した高速検索
    - 不要なデータフェッチを排除
    """
    # Owner以外はユーザーが店舗に所属しているか確認
    is_owner = user_has_role(current_user, "owner")

    if not is_owner and not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    today = date.today()
    yesterday = today - timedelta(days=1)

    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    yesterday_start = datetime.combine(yesterday, datetime.min.time())
    yesterday_end = datetime.combine(yesterday, datetime.max.time())

    # === 最適化: 本日の注文を1回のクエリで全件取得 ===
    # DBへの往復を1回に削減し、Pythonメモリ上で集計
    if is_owner:
        # Owner: 全店舗のデータ
        today_orders = (
            db.query(Order)
            .filter(
                Order.ordered_at >= today_start,
                Order.ordered_at <= today_end,
            )
            .all()
        )
    else:
        # Manager/Staff: 自店舗のデータ
        today_orders = (
            db.query(Order)
            .filter(
                Order.store_id == current_user.store_id,
                Order.ordered_at >= today_start,
                Order.ordered_at <= today_end,
            )
            .all()
        )

    # Pythonメモリ上でステータス別集計（簡素化版: 4ステータス）
    total_orders = len(today_orders)
    pending_orders = sum(1 for o in today_orders if o.status == "pending")
    ready_orders = sum(1 for o in today_orders if o.status == "ready")
    completed_orders = sum(1 for o in today_orders if o.status == "completed")
    cancelled_orders = sum(1 for o in today_orders if o.status == "cancelled")

    # 売上計算（キャンセル除く）
    total_sales = sum(o.total_price for o in today_orders if o.status != "cancelled")

    # 平均注文単価の計算
    completed_order_count = total_orders - cancelled_orders
    average_order_value = (
        float(total_sales) / completed_order_count if completed_order_count > 0 else 0.0
    )

    # === 最適化: 前日データを集約クエリで一括取得 ===
    # キャンセル以外の注文数と売上を一度のクエリで取得
    if is_owner:
        # Owner: 全店舗のデータ
        yesterday_orders = (
            db.query(Order)
            .filter(
                Order.ordered_at >= yesterday_start,
                Order.ordered_at <= yesterday_end,
            )
            .all()
        )
    else:
        # Manager/Staff: 自店舗のデータ
        yesterday_orders = (
            db.query(Order)
            .filter(
                Order.store_id == current_user.store_id,
                Order.ordered_at >= yesterday_start,
                Order.ordered_at <= yesterday_end,
            )
            .all()
        )

    yesterday_orders_count = len(yesterday_orders)
    yesterday_revenue = sum(
        o.total_price for o in yesterday_orders if o.status != "cancelled"
    )

    # 前日比較の計算
    orders_change = total_orders - yesterday_orders_count
    orders_change_percent = (
        (orders_change / yesterday_orders_count * 100)
        if yesterday_orders_count > 0
        else 0.0
    )
    revenue_change = total_sales - yesterday_revenue
    revenue_change_percent = (
        (revenue_change / yesterday_revenue * 100) if yesterday_revenue > 0 else 0.0
    )

    yesterday_comparison = YesterdayComparison(
        orders_change=orders_change,
        orders_change_percent=round(orders_change_percent, 2),
        revenue_change=revenue_change,
        revenue_change_percent=round(revenue_change_percent, 2),
    )

    # === 最適化: 人気メニュートップ3（JOINを維持、インデックス活用） ===
    if is_owner:
        # Owner: 全店舗のデータ
        popular_menus_query = (
            db.query(
                Order.menu_id,
                Menu.name,
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_price).label("total_revenue"),
            )
            .join(Menu, Order.menu_id == Menu.id)
            .filter(
                Order.ordered_at >= today_start,
                Order.ordered_at <= today_end,
                Order.status != "cancelled",
            )
            .group_by(Order.menu_id, Menu.name)
            .order_by(desc("order_count"))
            .limit(3)
        )
    else:
        # Manager/Staff: 自店舗のデータ
        popular_menus_query = (
            db.query(
                Order.menu_id,
                Menu.name,
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_price).label("total_revenue"),
            )
            .join(Menu, Order.menu_id == Menu.id)
            .filter(
                Order.store_id == current_user.store_id,
                Order.ordered_at >= today_start,
                Order.ordered_at <= today_end,
                Order.status != "cancelled",
            )
            .group_by(Order.menu_id, Menu.name)
            .order_by(desc("order_count"))
            .limit(3)
        )

    popular_menus_data = popular_menus_query.all()

    popular_menus = [
        PopularMenu(
            menu_id=menu_id,
            menu_name=menu_name,
            order_count=order_count,
            total_revenue=total_revenue or 0,
        )
        for menu_id, menu_name, order_count, total_revenue in popular_menus_data
    ]

    # === 最適化: 時間帯別注文数（既に取得した今日の注文データを再利用） ===
    hourly_orders_dict = {}
    for order in today_orders:
        hour = order.ordered_at.hour
        hourly_orders_dict[hour] = hourly_orders_dict.get(hour, 0) + 1

    hourly_orders = [
        HourlyOrderData(hour=hour, order_count=hourly_orders_dict.get(hour, 0))
        for hour in range(24)
    ]

    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "ready_orders": ready_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "total_sales": total_sales,
        "today_revenue": total_sales,
        "average_order_value": round(average_order_value, 2),
        "yesterday_comparison": yesterday_comparison,
        "popular_menus": popular_menus,
        "hourly_orders": hourly_orders,
    }


@router.get("/dashboard/weekly-sales", summary="週間売上データ取得")
def get_weekly_sales(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager", "staff"])),
):
    """
    過去7日間の日別売上データを取得

    **必要な権限:** owner, manager, staff

    **注意:**
    - Owner: 全店舗のデータを合算
    - Manager/Staff: 自店舗のデータのみ

    **レスポンス:**
    - labels: 日付のリスト（YYYY-MM-DD形式）
    - data: 各日の売上金額のリスト

    **最適化:**
    - 7回のクエリを1回の集約クエリに統合
    - DATE関数とGROUP BYを活用
    - インデックスによる高速検索
    """
    # Owner以外はユーザーが店舗に所属しているか確認
    is_owner = user_has_role(current_user, "owner")

    if not is_owner and not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # 過去7日間のデータを取得
    today = date.today()
    start_date = today - timedelta(days=6)  # 6日前
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(today, datetime.max.time())

    # === 最適化: 1回のクエリで全7日分のデータを取得 ===
    if is_owner:
        # Owner: 全店舗のデータ
        daily_sales = (
            db.query(
                func.date(Order.ordered_at).label("order_date"),
                func.sum(Order.total_price).label("revenue"),
            )
            .filter(
                Order.ordered_at >= start_datetime,
                Order.ordered_at <= end_datetime,
                Order.status != "cancelled",
            )
            .group_by(func.date(Order.ordered_at))
            .all()
        )
    else:
        # Manager/Staff: 自店舗のデータ
        daily_sales = (
            db.query(
                func.date(Order.ordered_at).label("order_date"),
                func.sum(Order.total_price).label("revenue"),
            )
            .filter(
                Order.store_id == current_user.store_id,
                Order.ordered_at >= start_datetime,
                Order.ordered_at <= end_datetime,
                Order.status != "cancelled",
            )
            .group_by(func.date(Order.ordered_at))
            .all()
        )

    # 日付をキーとした辞書に変換
    sales_dict = {str(day): revenue for day, revenue in daily_sales}

    # 7日分のデータを構築（データがない日は0円）
    weekly_data = []
    for days_ago in range(6, -1, -1):
        target_date = today - timedelta(days=days_ago)
        date_str = target_date.strftime("%Y-%m-%d")
        revenue = sales_dict.get(date_str, 0) or 0

        weekly_data.append({"date": date_str, "revenue": revenue})

    return {
        "labels": [item["date"] for item in weekly_data],
        "data": [item["revenue"] for item in weekly_data],
    }


# ===== 注文管理 =====


@router.get("/orders", response_model=OrderListResponse, summary="全注文一覧取得")
def get_all_orders(
    order_status: Optional[str] = Query(
        None,
        alias="status",
        description="ステータスでフィルタ（カンマ区切りで複数指定可）",
    ),
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    q: Optional[str] = Query(None, description="検索キーワード（顧客名、メニュー名）"),
    sort: Optional[str] = Query(
        "newest", description="ソート順: newest, oldest, price_high, price_low"
    ),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(100, ge=1, le=1000, description="1ページあたりの件数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager", "staff"])),
):
    """
    全ての注文一覧を取得（自店舗のみ）

    - 最新の注文から順に表示
    - ステータス、日付、キーワードでフィルタリング可能
    - 注文日時、金額でソート可能
    - ユーザー情報とメニュー情報を含む

    **必要な権限:** owner, manager, staff
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # 自店舗の注文のみを取得
    query = db.query(Order).filter(Order.store_id == current_user.store_id)

    # キーワード検索がある場合はJOINを追加
    needs_user_join = False
    needs_menu_join = False

    # ステータスフィルタ（複数選択対応）
    if order_status:
        status_list = [s.strip() for s in order_status.split(",")]
        query = query.filter(Order.status.in_(status_list))

    # 日付フィルタ
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Order.ordered_at >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD",
            )

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # 終了日の23:59:59まで含める
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Order.ordered_at <= end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD",
            )

    # キーワード検索（顧客名、メニュー名）
    if q:
        search_term = f"%{q}%"
        # JOINを1回だけ行う
        if not needs_user_join:
            query = query.join(User, Order.user_id == User.id)
            needs_user_join = True
        if not needs_menu_join:
            query = query.join(Menu, Order.menu_id == Menu.id)
            needs_menu_join = True

        query = query.filter(
            (User.full_name.ilike(search_term))
            | (User.username.ilike(search_term))
            | (Menu.name.ilike(search_term))
        )

    # ソート
    if sort == "oldest":
        query = query.order_by(Order.ordered_at.asc())
    elif sort == "price_high":
        query = query.order_by(Order.total_price.desc())
    elif sort == "price_low":
        query = query.order_by(Order.total_price.asc())
    else:  # newest (デフォルト)
        query = query.order_by(Order.ordered_at.desc())

    # 総件数を取得
    total = query.count()

    # ページネーション
    offset = (page - 1) * per_page
    orders = query.offset(offset).limit(per_page).all()

    # ユーザー情報とメニュー情報を含める（JOINしていない場合）
    if not needs_user_join or not needs_menu_join:
        for order in orders:
            if not needs_user_join:
                order.user = db.query(User).filter(User.id == order.user_id).first()
            if not needs_menu_join:
                order.menu = db.query(Menu).filter(Menu.id == order.menu_id).first()

    return {"orders": orders, "total": total}


@router.put(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    summary="注文ステータス更新",
)
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager", "staff"])),
):
    """
    注文のステータスを更新（自店舗の注文のみ・簡素化ステータス対応）

    可能なステータス:
    - pending: 注文受付（確認・在庫確認・決済処理）
    - ready: 準備完了（弁当完成、顧客通知）
    - completed: 受取完了（顧客が受取済み）
    - cancelled: キャンセル（注文取消）

    **ステータス遷移ルール:**
    - pending → ready または cancelled
    - ready → completed
    - completed → 変更不可
    - cancelled → 変更不可

    **必要な権限:** owner, manager, staff
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # 自店舗の注文のみを取得
    order = (
        db.query(Order)
        .filter(
            Order.id == order_id,
            Order.store_id == current_user.store_id,  # 店舗フィルタ追加
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # ステータス遷移のバリデーション（簡素化ステータス対応）
    from schemas import OrderStatus

    allowed_transitions = OrderStatus.get_allowed_transitions(order.status)
    new_status = (
        status_update.status.value
        if hasattr(status_update.status, "value")
        else status_update.status
    )

    if new_status not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{order.status}' to '{new_status}'. Allowed: {allowed_transitions}",
        )

    order.status = new_status
    db.commit()
    db.refresh(order)

    # ユーザー情報とメニュー情報を含める
    order.user = db.query(User).filter(User.id == order.user_id).first()
    order.menu = db.query(Menu).filter(Menu.id == order.menu_id).first()

    return order


# ===== メニューカテゴリ管理 =====


@router.get(
    "/menu-categories",
    response_model=MenuCategoryListResponse,
    summary="カテゴリ一覧取得",
)
def get_menu_categories(
    is_active: Optional[bool] = Query(None, description="有効なカテゴリのみ取得"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager", "staff"])),
):
    """
    店舗のメニューカテゴリ一覧を取得

    **必要な権限:** owner, manager, staff
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # クエリ構築
    query = db.query(MenuCategory).filter(
        MenuCategory.store_id == current_user.store_id
    )

    # フィルタ適用
    if is_active is not None:
        query = query.filter(MenuCategory.is_active == is_active)

    # 表示順でソート
    query = query.order_by(MenuCategory.display_order.asc(), MenuCategory.name.asc())

    categories = query.all()

    # 各カテゴリのメニュー数を取得
    category_responses = []
    for category in categories:
        menu_count = (
            db.query(Menu)
            .filter(
                Menu.category_id == category.id, Menu.store_id == current_user.store_id
            )
            .count()
        )

        category_dict = {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "display_order": category.display_order,
            "is_active": category.is_active,
            "store_id": category.store_id,
            "menu_count": menu_count,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
        }
        category_responses.append(MenuCategoryResponse(**category_dict))

    return MenuCategoryListResponse(
        categories=category_responses, total=len(category_responses)
    )


@router.post(
    "/menu-categories", response_model=MenuCategoryResponse, summary="カテゴリ作成"
)
def create_menu_category(
    category_data: MenuCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
):
    """
    新しいメニューカテゴリを作成

    **必要な権限:** owner, manager
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # 同じ店舗で同じ名前のカテゴリが存在しないか確認
    existing_category = (
        db.query(MenuCategory)
        .filter(
            MenuCategory.store_id == current_user.store_id,
            MenuCategory.name == category_data.name,
        )
        .first()
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with name '{category_data.name}' already exists",
        )

    # 新しいカテゴリを作成
    new_category = MenuCategory(
        name=category_data.name,
        description=category_data.description,
        display_order=category_data.display_order,
        is_active=category_data.is_active,
        store_id=current_user.store_id,
    )

    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    # メニュー数を取得
    menu_count = db.query(Menu).filter(Menu.category_id == new_category.id).count()

    category_dict = {
        "id": new_category.id,
        "name": new_category.name,
        "description": new_category.description,
        "display_order": new_category.display_order,
        "is_active": new_category.is_active,
        "store_id": new_category.store_id,
        "menu_count": menu_count,
        "created_at": new_category.created_at,
        "updated_at": new_category.updated_at,
    }

    return MenuCategoryResponse(**category_dict)


@router.put(
    "/menu-categories/{category_id}",
    response_model=MenuCategoryResponse,
    summary="カテゴリ更新",
)
def update_menu_category(
    category_id: int,
    category_update: MenuCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
):
    """
    メニューカテゴリを更新

    **必要な権限:** owner, manager
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # カテゴリを取得
    category = (
        db.query(MenuCategory)
        .filter(
            MenuCategory.id == category_id,
            MenuCategory.store_id == current_user.store_id,
        )
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    # 名前を変更する場合、重複チェック
    if category_update.name and category_update.name != category.name:
        existing_category = (
            db.query(MenuCategory)
            .filter(
                MenuCategory.store_id == current_user.store_id,
                MenuCategory.name == category_update.name,
                MenuCategory.id != category_id,
            )
            .first()
        )

        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with name '{category_update.name}' already exists",
            )

    # 更新
    update_data = category_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)

    # メニュー数を取得
    menu_count = db.query(Menu).filter(Menu.category_id == category.id).count()

    category_dict = {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "display_order": category.display_order,
        "is_active": category.is_active,
        "store_id": category.store_id,
        "menu_count": menu_count,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }

    return MenuCategoryResponse(**category_dict)


@router.delete("/menu-categories/{category_id}", summary="カテゴリ削除")
def delete_menu_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
):
    """
    メニューカテゴリを削除
    カテゴリに紐づくメニューは「カテゴリなし」になります

    **必要な権限:** owner, manager
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # カテゴリを取得
    category = (
        db.query(MenuCategory)
        .filter(
            MenuCategory.id == category_id,
            MenuCategory.store_id == current_user.store_id,
        )
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    # 関連するメニュー数を取得
    menu_count = db.query(Menu).filter(Menu.category_id == category_id).count()

    # カテゴリを削除（ON DELETE SET NULLにより、メニューのcategory_idは自動的にNULLになる）
    db.delete(category)
    db.commit()

    return {
        "message": f"Category '{category.name}' deleted successfully",
        "affected_menus": menu_count,
    }


# ===== メニュー管理 =====


@router.get("/menus", response_model=MenuListResponse, summary="メニュー管理一覧")
def get_all_menus(
    is_available: Optional[bool] = Query(None, description="利用可能フラグでフィルタ"),
    category_id: Optional[int] = Query(None, description="カテゴリIDでフィルタ"),
    keyword: Optional[str] = Query(
        None, description="検索キーワード（メニュー名・説明文で部分一致）"
    ),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    sort_by: Optional[str] = Query(
        None, description="ソート対象のカラム (name, price, created_at, updated_at)"
    ),
    sort_order: Optional[str] = Query("asc", description="ソート順序 (asc, desc)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager", "staff"])),
):
    """
    全てのメニュー一覧を取得（自店舗のみ、管理用）

    **必要な権限:** owner, manager, staff

    **パラメータ:**
    - **is_available**: 利用可能フラグでフィルタ
    - **keyword**: 検索キーワード（メニュー名・説明文で部分一致）
    - **page**: ページ番号
    - **per_page**: 1ページあたりの件数
    - **sort_by**: ソート対象 (name, price, created_at, updated_at)
    - **sort_order**: ソート順序 (asc, desc)
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # 自店舗のメニューのみを取得
    query = db.query(Menu).filter(Menu.store_id == current_user.store_id)

    # 利用可能フラグでフィルタ
    if is_available is not None:
        query = query.filter(Menu.is_available == is_available)

    # カテゴリでフィルタ
    if category_id is not None:
        if category_id == 0:
            # category_id=0 の場合、カテゴリなしのメニューを取得
            query = query.filter(Menu.category_id.is_(None))
        else:
            query = query.filter(Menu.category_id == category_id)

    # キーワード検索（メニュー名または説明文に部分一致）
    if keyword:
        search_pattern = f"%{keyword}%"
        query = query.filter(
            or_(Menu.name.ilike(search_pattern), Menu.description.ilike(search_pattern))
        )

    # ソート処理
    if sort_by:
        # 許可されたソートカラムのマッピング
        sort_columns = {
            "id": Menu.id,
            "name": Menu.name,
            "price": Menu.price,
            "created_at": Menu.created_at,
            "updated_at": Menu.updated_at,
        }

        # 無効なソートカラムをチェック
        if sort_by not in sort_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by parameter. Allowed values: {', '.join(sort_columns.keys())}",
            )

        # ソート順序の検証
        if sort_order not in ["asc", "desc"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid sort_order parameter. Allowed values: asc, desc",
            )

        # ソートを適用
        sort_column = sort_columns[sort_by]
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
    else:
        # デフォルトソート: IDの昇順（登録順）
        query = query.order_by(Menu.id)

    # 総件数を取得
    total = query.count()

    # ページネーション
    offset = (page - 1) * per_page
    menus = query.offset(offset).limit(per_page).all()

    return {"menus": menus, "total": total}


@router.post("/menus", response_model=MenuResponse, summary="メニュー作成")
def create_menu(
    menu: MenuCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
):
    """
    新しいメニューを作成（自店舗に紐づけ）

    **必要な権限:** owner, manager
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # メニュー作成時に自動的にstore_idを設定
    db_menu = Menu(**menu.dict(), store_id=current_user.store_id)

    db.add(db_menu)
    db.commit()
    db.refresh(db_menu)

    # 監査ログを記録
    log_menu_change(
        db=db,
        menu_id=db_menu.id,
        store_id=current_user.store_id,
        user_id=current_user.id,
        action="create",
        new_data=menu.dict(),
    )
    db.commit()

    return db_menu


# ===== メニュー一括操作 =====


@router.put("/menus/bulk-availability", summary="メニュー一括公開/非公開更新")
def bulk_update_menu_availability(
    bulk_update: MenuBulkAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
):
    """
    複数のメニューの公開状態を一括更新（自店舗のメニューのみ）

    **必要な権限:** owner, manager

    **パラメータ:**
    - **menu_ids**: 更新対象のメニューIDリスト
    - **is_available**: 公開状態 (true=公開, false=非公開)

    **戻り値:**
    - **updated_count**: 更新されたメニュー数
    - **failed_ids**: 更新に失敗したメニューID（存在しない、または他店舗のメニュー）
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # 自店舗のメニューのみを取得
    menus = (
        db.query(Menu)
        .filter(
            Menu.id.in_(bulk_update.menu_ids), Menu.store_id == current_user.store_id
        )
        .all()
    )

    # 見つかったメニューのIDリスト
    found_menu_ids = {menu.id for menu in menus}

    # 更新に失敗したID（存在しない、または他店舗のメニュー）
    failed_ids = [
        menu_id for menu_id in bulk_update.menu_ids if menu_id not in found_menu_ids
    ]

    # 一括更新
    updated_count = 0
    for menu in menus:
        menu.is_available = bulk_update.is_available
        updated_count += 1

    db.commit()

    return {
        "updated_count": updated_count,
        "failed_ids": failed_ids,
        "message": f"{updated_count}件のメニューを{'公開' if bulk_update.is_available else '非公開'}に更新しました",
    }


@router.put("/menus/{menu_id}", response_model=MenuResponse, summary="メニュー更新")
def update_menu(
    menu_id: int,
    menu_update: MenuUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
):
    """
    既存メニューを更新（自店舗のみ）

    **必要な権限:** owner, manager
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # 自店舗のメニューのみを取得
    menu = (
        db.query(Menu)
        .filter(
            Menu.id == menu_id,
            Menu.store_id == current_user.store_id,  # 店舗フィルタ追加
        )
        .first()
    )

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found"
        )

    # 変更前の状態を保存（監査ログ用）
    old_menu_copy = Menu(
        id=menu.id,
        name=menu.name,
        price=menu.price,
        description=menu.description,
        image_url=menu.image_url,
        is_available=menu.is_available,
        category_id=menu.category_id,
    )

    # 更新データを適用
    update_data = menu_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(menu, field, value)

    db.commit()
    db.refresh(menu)

    # 監査ログを記録
    log_menu_change(
        db=db,
        menu_id=menu.id,
        store_id=current_user.store_id,
        user_id=current_user.id,
        action="update",
        old_menu=old_menu_copy,
        new_data=update_data,
    )
    db.commit()

    return menu


@router.delete("/menus/{menu_id}", summary="メニュー削除")
def delete_menu(
    menu_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner"])),
):
    """
    メニューを削除（自店舗のみ）

    注意: 既存の注文がある場合は論理削除（is_available = False）を推奨

    **必要な権限:** owner
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # 自店舗のメニューのみを取得
    menu = (
        db.query(Menu)
        .filter(
            Menu.id == menu_id,
            Menu.store_id == current_user.store_id,  # 店舗フィルタ追加
        )
        .first()
    )

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found"
        )

    # 削除前の状態を保存（監査ログ用）
    old_menu_copy = Menu(
        id=menu.id,
        name=menu.name,
        price=menu.price,
        description=menu.description,
        image_url=menu.image_url,
        is_available=menu.is_available,
        category_id=menu.category_id,
    )

    # 既存の注文があるかチェック
    existing_orders = db.query(Order).filter(Order.menu_id == menu_id).first()
    if existing_orders:
        # 論理削除
        menu.is_available = False
        db.commit()

        # 監査ログを記録（論理削除）
        log_menu_change(
            db=db,
            menu_id=menu.id,
            store_id=current_user.store_id,
            user_id=current_user.id,
            action="update",
            old_menu=old_menu_copy,
            new_data={"is_available": False},
        )
        db.commit()

        return {"message": "Menu disabled due to existing orders"}
    else:
        # 物理削除
        db.delete(menu)

        # 監査ログを記録（物理削除）
        log_menu_change(
            db=db,
            menu_id=menu.id,
            store_id=current_user.store_id,
            user_id=current_user.id,
            action="delete",
            old_menu=old_menu_copy,
        )

        db.commit()
        return {"message": "Menu deleted successfully"}


# ===== メニュー変更履歴（監査ログ）=====


@router.get(
    "/menus/{menu_id}/change-logs",
    response_model=MenuChangeLogListResponse,
    summary="メニュー変更履歴取得",
)
def get_menu_change_logs(
    menu_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
    action: Optional[str] = Query(
        None, description="アクション (create/update/delete)"
    ),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
):
    """
    特定メニューの変更履歴を取得（自店舗のみ）

    **必要な権限:** owner, manager

    **パラメータ:**
    - **menu_id**: メニューID
    - **action**: フィルター: create, update, delete
    - **page**: ページ番号
    - **per_page**: 1ページあたりの件数
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # メニューが自店舗のものか確認
    menu = (
        db.query(Menu)
        .filter(Menu.id == menu_id, Menu.store_id == current_user.store_id)
        .first()
    )

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found"
        )

    # 変更履歴を取得
    query = db.query(MenuChangeLog).filter(
        MenuChangeLog.menu_id == menu_id,
        MenuChangeLog.store_id == current_user.store_id,
    )

    # アクションでフィルター
    if action:
        query = query.filter(MenuChangeLog.action == action)

    # 総件数を取得
    total = query.count()

    # 日時の降順でソート（新しい順）
    query = query.order_by(desc(MenuChangeLog.changed_at))

    # ページネーション
    offset = (page - 1) * per_page
    logs = query.offset(offset).limit(per_page).all()

    return {"logs": logs, "total": total}


@router.get(
    "/change-logs",
    response_model=MenuChangeLogListResponse,
    summary="店舗全体のメニュー変更履歴取得",
)
def get_store_change_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
    menu_id: Optional[int] = Query(None, description="メニューIDでフィルター"),
    action: Optional[str] = Query(
        None, description="アクション (create/update/delete)"
    ),
    user_id: Optional[int] = Query(None, description="変更者IDでフィルター"),
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(50, ge=1, le=100, description="1ページあたりの件数"),
):
    """
    店舗全体のメニュー変更履歴を取得（自店舗のみ）

    **必要な権限:** owner, manager

    **パラメータ:**
    - **menu_id**: 特定メニューの履歴のみ取得
    - **action**: フィルター: create, update, delete
    - **user_id**: 特定ユーザーによる変更のみ取得
    - **start_date**: 期間フィルター（開始日）
    - **end_date**: 期間フィルター（終了日）
    - **page**: ページ番号
    - **per_page**: 1ページあたりの件数

    **注意:**
    - Ownerは全店舗の履歴を閲覧可能
    - Managerは自身の店舗の履歴のみ閲覧可能
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # 自店舗の変更履歴を取得
    query = db.query(MenuChangeLog).filter(
        MenuChangeLog.store_id == current_user.store_id
    )

    # フィルター適用
    if menu_id:
        query = query.filter(MenuChangeLog.menu_id == menu_id)

    if action:
        query = query.filter(MenuChangeLog.action == action)

    if user_id:
        query = query.filter(MenuChangeLog.user_id == user_id)

    if start_date:
        query = query.filter(MenuChangeLog.changed_at >= start_date)

    if end_date:
        query = query.filter(MenuChangeLog.changed_at <= end_date)

    # 総件数を取得
    total = query.count()

    # 日時の降順でソート（新しい順）
    query = query.order_by(desc(MenuChangeLog.changed_at))

    # ページネーション
    offset = (page - 1) * per_page
    logs = query.offset(offset).limit(per_page).all()

    return {"logs": logs, "total": total}


# ===== メニュー画像アップロード =====

# 画像保存用のディレクトリ
UPLOAD_DIR = Path("static/images/menus")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 許可する画像形式とサイズ
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB


@router.post(
    "/menus/{menu_id}/image",
    response_model=MenuResponse,
    summary="メニュー画像アップロード",
)
async def upload_menu_image(
    menu_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager", "staff"])),
):
    """
    メニュー画像をアップロード（自店舗のメニューのみ）

    **必要な権限:** owner, manager, staff

    **パラメータ:**
    - **menu_id**: メニューID
    - **file**: 画像ファイル（JPEG, PNG, GIF, WebP）

    **制限:**
    - ファイルサイズ: 最大2MB
    - 形式: JPEG, PNG, GIF, WebP

    **戻り値:**
    - 更新後のメニュー情報

    **エラー:**
    - 400: 無効なファイル形式またはサイズ超過
    - 404: メニューが見つからない
    - 403: 他店舗のメニューへのアクセス
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # 自店舗のメニューのみを取得
    menu = (
        db.query(Menu)
        .filter(Menu.id == menu_id, Menu.store_id == current_user.store_id)
        .first()
    )

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found"
        )

    # ファイル拡張子のチェック
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # ファイルサイズのチェック
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB",
        )

    # 古い画像ファイルを削除
    if menu.image_url:
        old_image_path = Path(menu.image_url.lstrip("/"))
        if old_image_path.exists():
            try:
                old_image_path.unlink()
            except Exception as e:
                print(f"Failed to delete old image: {e}")

    # 新しいファイル名を生成（UUID + 拡張子）
    new_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / new_filename

    # ファイルを保存
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    # DBのimage_urlを更新
    menu.image_url = f"/static/images/menus/{new_filename}"
    db.commit()
    db.refresh(menu)

    return menu


@router.delete(
    "/menus/{menu_id}/image", response_model=MenuResponse, summary="メニュー画像削除"
)
def delete_menu_image(
    menu_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager", "staff"])),
):
    """
    メニュー画像を削除（自店舗のメニューのみ）

    **必要な権限:** owner, manager, staff

    **パラメータ:**
    - **menu_id**: メニューID

    **戻り値:**
    - 更新後のメニュー情報

    **エラー:**
    - 404: メニューが見つからない
    - 403: 他店舗のメニューへのアクセス
    """
    # ユーザーが店舗に所属しているか確認
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # 自店舗のメニューのみを取得
    menu = (
        db.query(Menu)
        .filter(Menu.id == menu_id, Menu.store_id == current_user.store_id)
        .first()
    )

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found"
        )

    # 画像ファイルを削除
    if menu.image_url:
        image_path = Path(menu.image_url.lstrip("/"))
        if image_path.exists():
            try:
                image_path.unlink()
            except Exception as e:
                print(f"Failed to delete image: {e}")

    # DBのimage_urlをクリア
    menu.image_url = None
    db.commit()
    db.refresh(menu)

    return menu


# ===== 売上レポート =====


@router.get(
    "/reports/sales", response_model=SalesReportResponse, summary="売上レポート取得"
)
def get_sales_report(
    period: str = Query("daily", description="レポート期間 (daily, weekly, monthly)"),
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
):
    """
    売上レポートを取得

    - 日別、週別、月別の売上集計
    - メニュー別売上ランキング
    - 指定期間での集計

    **必要な権限:** owner, manager
    **注意:**
    - Owner: 全店舗のデータを閲覧可能
    - Manager: 自身が所属する店舗のデータのみ閲覧可能
    """
    # Owner以外はユーザーが店舗に所属しているか確認
    is_owner = user_has_role(current_user, "owner")

    if not is_owner and not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any store",
        )

    # デフォルトの期間設定
    if not start_date:
        if period == "daily":
            start_date = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
        elif period == "weekly":
            start_date = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        else:  # monthly
            start_date = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")

    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD",
        )

    # 指定期間の注文を取得（キャンセル除く）
    # Owner: 全店舗、Manager: 自店舗のみ
    if is_owner:
        # Owner: 全店舗のデータ
        orders_query = db.query(Order).filter(
            and_(
                Order.ordered_at >= start_dt,
                Order.ordered_at <= end_dt,
                Order.status != "cancelled",
            )
        )
    else:
        # Manager: 自店舗のみ
        orders_query = db.query(Order).filter(
            and_(
                Order.store_id == current_user.store_id,
                Order.ordered_at >= start_dt,
                Order.ordered_at <= end_dt,
                Order.status != "cancelled",
            )
        )

    # 日別売上集計
    daily_reports = []
    current_date = start_dt.date()
    end_date_obj = end_dt.date()

    while current_date <= end_date_obj:
        day_start = datetime.combine(current_date, datetime.min.time())
        day_end = datetime.combine(current_date, datetime.max.time())

        day_orders = orders_query.filter(
            and_(Order.ordered_at >= day_start, Order.ordered_at <= day_end)
        )

        day_count = day_orders.count()

        # 日別売上を集計（Owner: 全店舗、Manager: 自店舗のみ）
        if is_owner:
            day_sales = (
                db.query(func.sum(Order.total_price))
                .filter(
                    and_(
                        Order.ordered_at >= day_start,
                        Order.ordered_at <= day_end,
                        Order.status != "cancelled",
                    )
                )
                .scalar()
                or 0
            )
        else:
            day_sales = (
                db.query(func.sum(Order.total_price))
                .filter(
                    and_(
                        Order.store_id == current_user.store_id,
                        Order.ordered_at >= day_start,
                        Order.ordered_at <= day_end,
                        Order.status != "cancelled",
                    )
                )
                .scalar()
                or 0
            )

        # 人気メニューを取得（Owner: 全店舗、Manager: 自店舗のみ）
        if is_owner:
            popular_menu = (
                db.query(Menu.name, func.sum(Order.quantity).label("total_quantity"))
                .join(Order)
                .filter(
                    and_(
                        Order.ordered_at >= day_start,
                        Order.ordered_at <= day_end,
                        Order.status != "cancelled",
                    )
                )
                .group_by(Menu.name)
                .order_by(desc("total_quantity"))
                .first()
            )
        else:
            popular_menu = (
                db.query(Menu.name, func.sum(Order.quantity).label("total_quantity"))
                .join(Order)
                .filter(
                    and_(
                        Order.store_id == current_user.store_id,
                        Order.ordered_at >= day_start,
                        Order.ordered_at <= day_end,
                        Order.status != "cancelled",
                    )
                )
                .group_by(Menu.name)
                .order_by(desc("total_quantity"))
                .first()
            )

        daily_reports.append(
            {
                "date": current_date.strftime("%Y-%m-%d"),
                "total_orders": day_count,
                "total_sales": day_sales,
                "popular_menu": popular_menu[0] if popular_menu else None,
            }
        )

        current_date += timedelta(days=1)

    # メニュー別売上集計（Owner: 全店舗、Manager: 自店舗のみ）
    if is_owner:
        menu_reports = (
            db.query(
                Menu.id,
                Menu.name,
                func.sum(Order.quantity).label("total_quantity"),
                func.sum(Order.total_price).label("total_sales"),
            )
            .join(Order)
            .filter(
                and_(
                    Order.ordered_at >= start_dt,
                    Order.ordered_at <= end_dt,
                    Order.status != "cancelled",
                )
            )
            .group_by(Menu.id, Menu.name)
            .order_by(desc("total_sales"))
            .all()
        )
    else:
        menu_reports = (
            db.query(
                Menu.id,
                Menu.name,
                func.sum(Order.quantity).label("total_quantity"),
                func.sum(Order.total_price).label("total_sales"),
            )
            .join(Order)
            .filter(
                and_(
                    Order.store_id == current_user.store_id,
                    Order.ordered_at >= start_dt,
                    Order.ordered_at <= end_dt,
                    Order.status != "cancelled",
                )
            )
            .group_by(Menu.id, Menu.name)
            .order_by(desc("total_sales"))
            .all()
        )

    menu_report_list = [
        {
            "menu_id": report.id,
            "menu_name": report.name,
            "total_quantity": report.total_quantity,
            "total_sales": report.total_sales,
        }
        for report in menu_reports
    ]

    # 合計集計（Owner: 全店舗、Manager: 自店舗のみ）
    total_orders = orders_query.count()

    if is_owner:
        total_sales = (
            db.query(func.sum(Order.total_price))
            .filter(
                and_(
                    Order.ordered_at >= start_dt,
                    Order.ordered_at <= end_dt,
                    Order.status != "cancelled",
                )
            )
            .scalar()
            or 0
        )
    else:
        total_sales = (
            db.query(func.sum(Order.total_price))
            .filter(
                and_(
                    Order.store_id == current_user.store_id,
                    Order.ordered_at >= start_dt,
                    Order.ordered_at <= end_dt,
                    Order.status != "cancelled",
                )
            )
            .scalar()
            or 0
        )

    return {
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "daily_reports": daily_reports,
        "menu_reports": menu_report_list,
        "total_sales": total_sales,
        "total_orders": total_orders,
    }
