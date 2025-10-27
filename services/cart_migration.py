"""Cart migration service for transferring guest cart to user cart."""

from datetime import datetime
from typing import Dict

from sqlalchemy import and_
from sqlalchemy.orm import Session

from models import GuestCartItem, GuestSession, User, UserCartItem


class CartMigrationService:
    """ゲストカートからユーザーカートへの移行を担当するサービス."""

    def __init__(self, db: Session):
        """Initialize the cart migration service.

        Args:
            db: Database session
        """
        self.db = db

    def migrate_guest_cart_to_user(
        self, session_id: str, user_id: int
    ) -> Dict[str, int]:
        """ゲストカートの内容をユーザーカートに移行する.

        Args:
            session_id: ゲストセッションID
            user_id: ログインしたユーザーのID

        Returns:
            移行結果を含む辞書 {
                'migrated_items': int,  # 移行されたアイテム数
                'merged_items': int,    # マージされたアイテム数
                'total_quantity': int   # 移行後の総数量
            }

        Raises:
            Exception: カート移行中にエラーが発生した場合
        """
        result = {"migrated_items": 0, "merged_items": 0, "total_quantity": 0}

        try:
            # ゲストセッションを取得
            guest_session = (
                self.db.query(GuestSession)
                .filter(GuestSession.session_id == session_id)
                .first()
            )

            if not guest_session:
                return result

            # 既に変換済みの場合はスキップ
            if guest_session.converted_to_user_id is not None:
                return result

            # ゲストカートアイテムを取得
            guest_cart_items = (
                self.db.query(GuestCartItem)
                .filter(GuestCartItem.session_id == guest_session.session_id)
                .all()
            )

            if not guest_cart_items:
                # カートが空でも変換済みとしてマーク
                guest_session.converted_to_user_id = user_id
                self.db.commit()
                return result

            # 各ゲストカートアイテムを処理
            for guest_item in guest_cart_items:
                # ユーザーカートに同じ商品が既に存在するかチェック
                existing_user_item = (
                    self.db.query(UserCartItem)
                    .filter(
                        and_(
                            UserCartItem.user_id == user_id,
                            UserCartItem.menu_id == guest_item.menu_id,
                        )
                    )
                    .first()
                )

                if existing_user_item:
                    # 既存のアイテムに数量を加算
                    existing_user_item.quantity += guest_item.quantity
                    existing_user_item.updated_at = datetime.utcnow()
                    result["merged_items"] += 1
                else:
                    # 新しいユーザーカートアイテムを作成
                    new_user_item = UserCartItem(
                        user_id=user_id,
                        menu_id=guest_item.menu_id,
                        quantity=guest_item.quantity,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    self.db.add(new_user_item)
                    result["migrated_items"] += 1

                result["total_quantity"] += guest_item.quantity

            # ゲストカートアイテムを削除
            for guest_item in guest_cart_items:
                self.db.delete(guest_item)

            # セッションを変換済みとしてマーク
            guest_session.converted_to_user_id = user_id
            guest_session.last_accessed_at = datetime.utcnow()

            # コミット
            self.db.commit()

            return result

        except Exception as e:
            self.db.rollback()
            raise Exception(f"カート移行中にエラーが発生しました: {str(e)}")
