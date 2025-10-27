"""
ゲストカート管理API

ログイン前のユーザーがカートを操作するためのエンドポイント。
セッションIDに基づいて商品の追加・取得・更新・削除を行います。
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import GuestCartItem, GuestSession, Menu
from routers.guest_session import require_guest_session
from schemas import (
    GuestCartItemAdd,
    GuestCartItemResponse,
    GuestCartItemUpdate,
    GuestCartResponse,
)

router = APIRouter(prefix="/guest/cart", tags=["guest-cart"])


def calculate_cart_total(cart_items: List[GuestCartItem]) -> int:
    """
    カート内の合計金額を計算

    Args:
        cart_items: カートアイテムのリスト

    Returns:
        合計金額
    """
    total = 0
    for item in cart_items:
        if item.menu:
            total += item.menu.price * item.quantity
    return total


@router.post(
    "/add",
    response_model=GuestCartResponse,
    summary="カートに商品を追加",
    status_code=status.HTTP_201_CREATED,
)
async def add_to_cart(
    item: GuestCartItemAdd,
    session: GuestSession = Depends(require_guest_session),
    db: Session = Depends(get_db),
):
    """
    ゲストカートに商品を追加

    **必要なもの:**
    - 有効なゲストセッションCookie
    - menu_id: 追加するメニューID
    - quantity: 数量（デフォルト: 1）

    **検証:**
    1. 店舗が選択されているか
    2. メニューが存在するか
    3. メニューが選択店舗のものか
    4. メニューが販売可能か

    **動作:**
    - 同じメニューが既にカートにある場合は数量を加算
    - 新規の場合は新しいアイテムとして追加

    **エラー:**
    - 400: 店舗が選択されていない
    - 404: メニューが存在しない、または選択店舗のものではない
    - 400: メニューが販売不可
    """
    # 店舗が選択されているか確認
    if not session.selected_store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="店舗を選択してください。先に店舗選択を行ってください。",
        )

    # メニューの存在と販売可能性を確認
    menu = db.query(Menu).filter(Menu.id == item.menu_id).first()

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"メニューID {item.menu_id} が見つかりません。",
        )

    # メニューが選択店舗のものか確認
    if menu.store_id != session.selected_store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"このメニューは選択中の店舗では販売されていません。"
                f"メニューの店舗ID: {menu.store_id}, "
                f"選択中の店舗ID: {session.selected_store_id}"
            ),
        )

    # メニューが販売可能か確認
    if not menu.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"メニュー「{menu.name}」は現在販売されていません。",
        )

    # 既存のカートアイテムを確認
    existing_item = (
        db.query(GuestCartItem)
        .filter(
            GuestCartItem.session_id == session.session_id,
            GuestCartItem.menu_id == item.menu_id,
        )
        .first()
    )

    if existing_item:
        # 既存アイテムの数量を加算
        existing_item.quantity += item.quantity
        db.commit()
        db.refresh(existing_item)
    else:
        # 新規アイテムを追加
        new_item = GuestCartItem(
            session_id=session.session_id,
            menu_id=item.menu_id,
            quantity=item.quantity,
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)

    # カート全体を返す
    return get_cart_summary(session.session_id, db)


@router.get(
    "",
    response_model=GuestCartResponse,
    summary="カート内容を取得",
)
async def get_cart(
    session: GuestSession = Depends(require_guest_session),
    db: Session = Depends(get_db),
):
    """
    現在のゲストカート内容を取得

    **必要なもの:**
    - 有効なゲストセッションCookie

    **戻り値:**
    - session_id: セッションID
    - items: カート内のアイテムリスト（メニュー情報含む）
    - total_items: アイテム総数
    - total_amount: 合計金額
    - selected_store_id: 選択中の店舗ID

    **エラー:**
    - 401: セッションが無効
    """
    return get_cart_summary(session.session_id, db)


@router.put(
    "/item/{item_id}",
    response_model=GuestCartResponse,
    summary="カートアイテムの数量を更新",
)
async def update_cart_item(
    item_id: int,
    update: GuestCartItemUpdate,
    session: GuestSession = Depends(require_guest_session),
    db: Session = Depends(get_db),
):
    """
    カート内のアイテムの数量を更新

    **必要なもの:**
    - 有効なゲストセッションCookie
    - item_id: 更新するカートアイテムのID
    - quantity: 新しい数量（1-99）

    **動作:**
    - 指定されたアイテムの数量を更新
    - 数量が0以下の場合はエラー（削除する場合はDELETEを使用）

    **エラー:**
    - 404: カートアイテムが存在しない
    - 403: 他のセッションのカートアイテム
    """
    # カートアイテムを取得
    cart_item = db.query(GuestCartItem).filter(GuestCartItem.id == item_id).first()

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"カートアイテムID {item_id} が見つかりません。",
        )

    # セッションの所有権を確認
    if cart_item.session_id != session.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このカートアイテムにアクセスする権限がありません。",
        )

    # 数量を更新
    cart_item.quantity = update.quantity
    db.commit()
    db.refresh(cart_item)

    # 更新後のカート全体を返す
    return get_cart_summary(session.session_id, db)


@router.delete(
    "/item/{item_id}",
    response_model=GuestCartResponse,
    summary="カートからアイテムを削除",
)
async def delete_cart_item(
    item_id: int,
    session: GuestSession = Depends(require_guest_session),
    db: Session = Depends(get_db),
):
    """
    カートからアイテムを削除

    **必要なもの:**
    - 有効なゲストセッションCookie
    - item_id: 削除するカートアイテムのID

    **動作:**
    - 指定されたアイテムをカートから削除

    **エラー:**
    - 404: カートアイテムが存在しない
    - 403: 他のセッションのカートアイテム
    """
    # カートアイテムを取得
    cart_item = db.query(GuestCartItem).filter(GuestCartItem.id == item_id).first()

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"カートアイテムID {item_id} が見つかりません。",
        )

    # セッションの所有権を確認
    if cart_item.session_id != session.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このカートアイテムにアクセスする権限がありません。",
        )

    # アイテムを削除
    db.delete(cart_item)
    db.commit()

    # 削除後のカート全体を返す
    return get_cart_summary(session.session_id, db)


def get_cart_summary(session_id: str, db: Session) -> GuestCartResponse:
    """
    カートのサマリー情報を取得

    Args:
        session_id: セッションID
        db: データベースセッション

    Returns:
        GuestCartResponse: カートのサマリー
    """
    # セッション情報を取得
    session = (
        db.query(GuestSession).filter(GuestSession.session_id == session_id).first()
    )

    # カートアイテムを取得（メニュー情報も含む）
    cart_items = (
        db.query(GuestCartItem).filter(GuestCartItem.session_id == session_id).all()
    )

    # 各アイテムのメニュー情報を読み込む
    for item in cart_items:
        db.refresh(item)

    # 合計アイテム数と合計金額を計算
    total_items = sum(item.quantity for item in cart_items)
    total_amount = calculate_cart_total(cart_items)

    # レスポンスを構築
    return GuestCartResponse(
        session_id=session_id,
        items=[
            GuestCartItemResponse(
                id=item.id,
                menu_id=item.menu_id,
                quantity=item.quantity,
                added_at=item.added_at,
                menu=item.menu,
            )
            for item in cart_items
        ],
        total_items=total_items,
        total_amount=total_amount,
        selected_store_id=session.selected_store_id if session else None,
    )
