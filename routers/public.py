"""
公開APIルーター

認証不要で誰でもアクセスできるエンドポイント
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import Menu, Store
from schemas import MenuResponse, StorePublicResponse

router = APIRouter(prefix="/public", tags=["公開API"])


@router.get(
    "/stores",
    response_model=List[StorePublicResponse],
    summary="公開店舗一覧取得",
)
async def get_public_stores(
    search: Optional[str] = Query(None, description="店舗名または住所で検索"),
    is_active: bool = Query(True, description="営業中の店舗のみ表示"),
    db: Session = Depends(get_db),
):
    """
    認証不要で店舗一覧を取得

    - **search**: 店舗名または住所で部分一致検索
    - **is_active**: 営業中の店舗のみ表示（デフォルト: True）
    """
    query = db.query(Store)

    # 営業状態でフィルタ
    if is_active:
        query = query.filter(Store.is_active.is_(True))

    # 検索キーワードでフィルタ
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Store.name.ilike(search_pattern)) | (Store.address.ilike(search_pattern))
        )

    # 店舗名でソート
    stores = query.order_by(Store.name).all()

    return stores


@router.get(
    "/stores/{store_id}/menus",
    response_model=List[MenuResponse],
    summary="店舗の公開メニュー一覧取得",
)
async def get_store_menus(
    store_id: int,
    category_id: Optional[int] = Query(None, description="カテゴリIDでフィルタ"),
    is_available: bool = Query(True, description="販売中のメニューのみ"),
    db: Session = Depends(get_db),
):
    """
    認証不要で指定店舗のメニュー一覧を取得

    - **store_id**: 店舗ID
    - **category_id**: カテゴリIDでフィルタ（オプション）
    - **is_available**: 販売中のメニューのみ（デフォルト: True）
    """
    # 店舗の存在確認
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"店舗ID {store_id} が見つかりません",
        )

    # メニュークエリ
    query = db.query(Menu).filter(Menu.store_id == store_id)

    # 販売状態でフィルタ
    if is_available:
        query = query.filter(Menu.is_available.is_(True))

    # カテゴリでフィルタ
    if category_id is not None:
        query = query.filter(Menu.category_id == category_id)

    # メニュー名でソート
    menus = query.order_by(Menu.name).all()

    return menus
