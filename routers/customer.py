"""
お客様向けルーター

お客様専用のAPIエンドポイント
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Cookie
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from database import get_db
from dependencies import get_current_customer
from models import User, Menu, Order, UserCartItem, GuestCartItem, GuestSession
from schemas import (
    MenuResponse, MenuListResponse, MenuFilter,
    OrderCreate, OrderResponse, OrderListResponse,
    OrderHistoryResponse, OrderHistoryItem,
    CartItemCreate, CartResponse, CartItemResponse
)

router = APIRouter(prefix="/customer", tags=["お客様"])


@router.get("/menus", response_model=MenuListResponse, summary="メニュー一覧取得")
def get_menus(
    is_available: Optional[bool] = Query(None, description="利用可能フラグでフィルタ"),
    price_min: Optional[int] = Query(None, description="最低価格"),
    price_max: Optional[int] = Query(None, description="最高価格"),
    search: Optional[str] = Query(None, description="メニュー名で検索"),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    メニュー一覧を取得
    
    - 利用可能なメニューのみ表示可能
    - 価格範囲やキーワードでフィルタリング
    - ページネーション対応
    """
    query = db.query(Menu)
    
    # フィルタリング
    if is_available is not None:
        query = query.filter(Menu.is_available == is_available)
    else:
        # お客様には利用可能なメニューのみ表示
        query = query.filter(Menu.is_available == True)
    
    if price_min is not None:
        query = query.filter(Menu.price >= price_min)
    
    if price_max is not None:
        query = query.filter(Menu.price <= price_max)
    
    if search:
        query = query.filter(Menu.name.contains(search))
    
    # 総件数を取得
    total = query.count()
    
    # ページネーション
    offset = (page - 1) * per_page
    menus = query.offset(offset).limit(per_page).all()
    
    return {"menus": menus, "total": total}


@router.get("/menus/{menu_id}", response_model=MenuResponse, summary="メニュー詳細取得")
def get_menu(
    menu_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    指定されたIDのメニュー詳細を取得
    """
    menu = db.query(Menu).filter(
        Menu.id == menu_id,
        Menu.is_available == True
    ).first()
    
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )
    
    return menu


@router.post("/orders", response_model=OrderResponse, summary="注文作成")
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    新しい注文を作成
    
    - **menu_id**: メニューID
    - **quantity**: 数量（1-10個）
    - **delivery_time**: 希望受取時間（任意）
    - **notes**: 備考（任意、500文字以内）
    """
    # メニューの存在確認
    menu = db.query(Menu).filter(
        Menu.id == order.menu_id,
        Menu.is_available == True
    ).first()
    
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found or not available"
        )
    
    # 合計金額を計算
    total_price = menu.price * order.quantity
    
    # 注文を作成（store_idをメニューから取得）
    db_order = Order(
        user_id=current_user.id,
        store_id=menu.store_id,  # メニューの店舗IDを設定
        menu_id=order.menu_id,
        quantity=order.quantity,
        total_price=total_price,
        delivery_time=order.delivery_time,
        notes=order.notes
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # 注文完了後、カートをクリア
    db.query(UserCartItem).filter(
        UserCartItem.user_id == current_user.id
    ).delete()
    db.commit()
    
    # メニュー情報も含めて返す
    db_order.menu = menu
    
    return db_order


@router.get("/orders", response_model=OrderHistoryResponse, summary="注文履歴取得")
def get_my_orders(
    status_filter: Optional[str] = Query(None, description="ステータスでフィルタ"),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    認証されたお客様の注文履歴を取得
    
    - JWT認証必須
    - 現在のユーザーの注文のみ取得
    - メニュー情報をJOINで効率的に取得
    - 最新の注文から順に表示（ordered_at降順）
    - ステータスでフィルタリング可能
    - ページネーション対応
    """
    # JOINを使用してパフォーマンスを向上
    query = db.query(
        Order.id,
        Order.quantity,
        Order.total_price,
        Order.status,
        Order.delivery_time,
        Order.notes,
        Order.ordered_at,
        Order.updated_at,
        Order.menu_id,
        Menu.name.label('menu_name'),
        Menu.image_url.label('menu_image_url'),
        Menu.price.label('menu_price')
    ).join(Menu, Order.menu_id == Menu.id).filter(
        Order.user_id == current_user.id
    )
    
    # ステータスフィルタ
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    # 最新順でソート（ordered_at降順）
    query = query.order_by(desc(Order.ordered_at))
    
    # 総件数を取得
    total = query.count()
    
    # ページネーション
    offset = (page - 1) * per_page
    results = query.offset(offset).limit(per_page).all()
    
    # OrderHistoryItem形式に変換
    order_items = []
    for result in results:
        order_item = OrderHistoryItem(
            id=result.id,
            quantity=result.quantity,
            total_price=result.total_price,
            status=result.status,
            delivery_time=result.delivery_time,
            notes=result.notes,
            ordered_at=result.ordered_at,
            updated_at=result.updated_at,
            menu_id=result.menu_id,
            menu_name=result.menu_name,
            menu_image_url=result.menu_image_url,
            menu_price=result.menu_price
        )
        order_items.append(order_item)
    
    return OrderHistoryResponse(orders=order_items, total=total)


@router.get("/orders/{order_id}", response_model=OrderResponse, summary="注文詳細取得")
def get_my_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    指定された注文の詳細を取得
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # メニュー情報を含める
    order.menu = db.query(Menu).filter(Menu.id == order.menu_id).first()
    
    return order


@router.put("/orders/{order_id}/cancel", response_model=OrderResponse, summary="注文キャンセル")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    注文をキャンセル
    
    注意: pendingステータスの注文のみキャンセル可能
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be cancelled"
        )
    
    order.status = "cancelled"
    db.commit()
    db.refresh(order)
    
    # メニュー情報を含める
    order.menu = db.query(Menu).filter(Menu.id == order.menu_id).first()
    
    return order


# ===== カート管理 =====


@router.get("/cart", response_model=CartResponse, summary="カート取得")
def get_user_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    ログインユーザーのカート内容を取得
    
    - カート内のすべてのアイテムとメニュー情報を返す
    - 合計金額も計算して返す
    """
    cart_items = (
        db.query(UserCartItem)
        .options(joinedload(UserCartItem.menu))
        .filter(UserCartItem.user_id == current_user.id)
        .all()
    )
    
    # レスポンスデータを構築
    items = []
    total_price = 0
    
    for cart_item in cart_items:
        if cart_item.menu:
            item_total = cart_item.menu.price * cart_item.quantity
            total_price += item_total
            
            items.append(CartItemResponse(
                id=cart_item.id,
                menu_id=cart_item.menu_id,
                menu_name=cart_item.menu.name,
                menu_price=cart_item.menu.price,
                menu_image_url=cart_item.menu.image_url,
                quantity=cart_item.quantity,
                subtotal=item_total
            ))
    
    return CartResponse(
        items=items,
        total_price=total_price,
        total_items=sum(item.quantity for item in items)
    )


@router.post("/cart/add", response_model=CartItemResponse, summary="カートにアイテム追加")
def add_to_user_cart(
    item: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    ログインユーザーのカートにメニューを追加
    
    - 既に同じメニューがある場合は数量を増やす
    - メニューの在庫状況を確認
    """
    # メニューの存在と利用可能性を確認
    menu = db.query(Menu).filter(Menu.id == item.menu_id).first()
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )
    
    if not menu.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Menu is not available"
        )
    
    # 既存のカートアイテムを確認
    existing_item = (
        db.query(UserCartItem)
        .filter(
            UserCartItem.user_id == current_user.id,
            UserCartItem.menu_id == item.menu_id
        )
        .first()
    )
    
    if existing_item:
        # 既存アイテムの数量を更新
        existing_item.quantity += item.quantity
        db.commit()
        db.refresh(existing_item)
        
        return CartItemResponse(
            id=existing_item.id,
            menu_id=menu.id,
            menu_name=menu.name,
            menu_price=menu.price,
            menu_image_url=menu.image_url,
            quantity=existing_item.quantity,
            subtotal=menu.price * existing_item.quantity
        )
    else:
        # 新しいカートアイテムを作成
        new_item = UserCartItem(
            user_id=current_user.id,
            menu_id=item.menu_id,
            quantity=item.quantity
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        return CartItemResponse(
            id=new_item.id,
            menu_id=menu.id,
            menu_name=menu.name,
            menu_price=menu.price,
            menu_image_url=menu.image_url,
            quantity=new_item.quantity,
            subtotal=menu.price * new_item.quantity
        )


@router.put("/cart/{item_id}", response_model=CartItemResponse, summary="カートアイテム更新")
def update_cart_item(
    item_id: int,
    quantity: int = Query(..., ge=1, description="新しい数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    カートアイテムの数量を更新
    """
    cart_item = (
        db.query(UserCartItem)
        .filter(
            UserCartItem.id == item_id,
            UserCartItem.user_id == current_user.id
        )
        .first()
    )
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    # メニュー情報を取得
    menu = db.query(Menu).filter(Menu.id == cart_item.menu_id).first()
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )
    
    cart_item.quantity = quantity
    db.commit()
    db.refresh(cart_item)
    
    return CartItemResponse(
        id=cart_item.id,
        menu_id=menu.id,
        menu_name=menu.name,
        menu_price=menu.price,
        menu_image_url=menu.image_url,
        quantity=cart_item.quantity,
        subtotal=menu.price * cart_item.quantity
    )


@router.delete("/cart/{item_id}", summary="カートアイテム削除")
def delete_cart_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    カートからアイテムを削除
    """
    cart_item = (
        db.query(UserCartItem)
        .filter(
            UserCartItem.id == item_id,
            UserCartItem.user_id == current_user.id
        )
        .first()
    )
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    db.delete(cart_item)
    db.commit()
    
    return {"success": True, "message": "Item removed from cart"}


@router.delete("/cart", summary="カートをクリア")
def clear_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    カート内のすべてのアイテムを削除
    """
    db.query(UserCartItem).filter(
        UserCartItem.user_id == current_user.id
    ).delete()
    db.commit()
    
    return {"success": True, "message": "Cart cleared"}


@router.post("/cart/migrate", summary="ゲストカートをユーザーカートに移行")
def migrate_guest_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer),
    guest_session_id: Optional[str] = Cookie(None, alias="guest_session_id")
):
    """
    ゲストセッションのカートアイテムをログインユーザーのカートに移行
    
    - ログイン後に呼び出す
    - ゲストカートのアイテムをユーザーカートにコピー
    - 既存のユーザーカートにアイテムがある場合は数量を加算
    - 移行後、ゲストカートはクリア
    - ゲストセッションIDはCookieから自動取得
    """
    # ゲストセッションIDがない場合は移行不要
    if not guest_session_id:
        return {"success": True, "message": "No guest session found", "migrated_count": 0}
    
    # ゲストセッションを確認
    guest_session = db.query(GuestSession).filter(
        GuestSession.session_id == guest_session_id
    ).first()
    
    if not guest_session:
        return {"success": True, "message": "Guest session not found", "migrated_count": 0}
    
    # ゲストカートのアイテムを取得（session_idで検索）
    guest_cart_items = db.query(GuestCartItem).filter(
        GuestCartItem.session_id == guest_session_id
    ).all()
    
    if not guest_cart_items:
        return {"success": True, "message": "No items to migrate", "migrated_count": 0}
    
    migrated_count = 0
    
    for guest_item in guest_cart_items:
        # 既にユーザーカートに同じメニューがあるかチェック
        existing_item = db.query(UserCartItem).filter(
            UserCartItem.user_id == current_user.id,
            UserCartItem.menu_id == guest_item.menu_id
        ).first()
        
        if existing_item:
            # 既存アイテムの数量を加算
            existing_item.quantity += guest_item.quantity
        else:
            # 新規アイテムを追加
            new_item = UserCartItem(
                user_id=current_user.id,
                menu_id=guest_item.menu_id,
                quantity=guest_item.quantity
            )
            db.add(new_item)
        
        migrated_count += 1
    
    # ゲストカートをクリア（session_idで削除）
    db.query(GuestCartItem).filter(
        GuestCartItem.session_id == guest_session_id
    ).delete()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully migrated {migrated_count} items",
        "migrated_count": migrated_count
    }