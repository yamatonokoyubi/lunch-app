"""
ゲストセッション管理API

ログイン前のユーザーの行動を追跡・保持するためのセッション管理エンドポイント。
店舗選択やカート機能の基盤となる重要なモジュール。
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from database import get_db
from models import GuestSession, Store
from schemas import GuestSessionResponse, GuestSessionStoreUpdate

router = APIRouter(prefix="/guest", tags=["guest-session"])

# セッション設定
SESSION_COOKIE_NAME = "guest_session_id"
SESSION_EXPIRY_HOURS = 24
SESSION_COOKIE_MAX_AGE = SESSION_EXPIRY_HOURS * 3600  # 秒単位


def generate_session_id() -> str:
    """
    暗号学的に安全なセッションIDを生成

    Returns:
        64文字の一意なセッションID
    """
    # UUID4 + secrets.token_hex の組み合わせで高いエントロピーを確保
    unique_part = str(uuid.uuid4()).replace("-", "")
    random_part = secrets.token_hex(16)
    return f"{unique_part}{random_part}"[:64]


def get_guest_session_from_cookie(
    guest_session_id: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> Optional[GuestSession]:
    """
    Cookieからゲストセッションを取得

    Args:
        guest_session_id: CookieからのセッションID
        db: データベースセッション

    Returns:
        GuestSession or None
    """
    if not guest_session_id:
        return None

    session = (
        db.query(GuestSession)
        .filter(
            GuestSession.session_id == guest_session_id,
            GuestSession.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if session:
        # 最終アクセス時刻を更新
        session.last_accessed_at = datetime.utcnow()
        db.commit()

    return session


def require_guest_session(
    guest_session_id: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> GuestSession:
    """
    ゲストセッションを必須とする依存関数

    Args:
        guest_session_id: CookieからのセッションID
        db: データベースセッション

    Returns:
        GuestSession

    Raises:
        HTTPException: セッションが存在しないか有効期限切れの場合
    """
    session = get_guest_session_from_cookie(guest_session_id, db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=("Valid guest session required. " "Please create a new session."),
        )
    return session


@router.post(
    "/session",
    response_model=GuestSessionResponse,
    summary="新規ゲストセッション作成",
    status_code=status.HTTP_201_CREATED,
)
async def create_guest_session(
    response: Response,
    db: Session = Depends(get_db),
    existing_session: Optional[GuestSession] = Depends(get_guest_session_from_cookie),
):
    """
    新しいゲストセッションを作成し、HTTPOnly Cookieとして設定

    **動作:**
    - 既存の有効なセッションがあればそれを返す
    - なければ新しいセッションIDを生成し、24時間の有効期限を設定
    - HTTPOnly, Secure, SameSite=Lax のCookieとして保存

    **戻り値:**
    - session_id: セッションID
    - created_at: 作成日時
    - expires_at: 有効期限
    - last_accessed_at: 最終アクセス日時

    **セキュリティ:**
    - HTTPOnly: JavaScriptからのアクセスを防止（XSS対策）
    - Secure: HTTPS接続でのみ送信（本番環境推奨）
    - SameSite=Lax: CSRF攻撃を軽減
    """
    # 既存のセッションがあればそれを返す
    if existing_session:
        # Cookieを再設定（期限延長）
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=existing_session.session_id,
            max_age=SESSION_COOKIE_MAX_AGE,
            httponly=True,
            secure=False,  # 開発環境ではFalse、本番環境ではTrue
            samesite="lax",
        )
        return existing_session

    # 新しいセッションを作成
    session_id = generate_session_id()
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_EXPIRY_HOURS)

    new_session = GuestSession(
        session_id=session_id,
        expires_at=expires_at,
        last_accessed_at=datetime.utcnow(),
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # HTTPOnly Cookieとして設定
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=False,  # 開発環境ではFalse、本番環境ではTrue
        samesite="lax",
    )

    return new_session


@router.get(
    "/session",
    response_model=GuestSessionResponse,
    summary="現在のゲストセッション情報取得",
)
async def get_current_session(
    session: GuestSession = Depends(require_guest_session),
):
    """
    現在のゲストセッション情報を取得

    **必要なもの:**
    - 有効なゲストセッションCookie

    **戻り値:**
    - session_id: セッションID
    - selected_store_id: 選択中の店舗ID（未選択の場合はnull）
    - created_at: 作成日時
    - expires_at: 有効期限
    - last_accessed_at: 最終アクセス日時

    **エラー:**
    - 401: セッションが存在しないか有効期限切れ
    """
    return session


@router.post(
    "/session/store",
    response_model=GuestSessionResponse,
    summary="店舗選択情報を保存",
)
async def update_selected_store(
    store_update: GuestSessionStoreUpdate,
    session: GuestSession = Depends(require_guest_session),
    db: Session = Depends(get_db),
):
    """
    ゲストセッションに店舗選択情報を保存

    **必要なもの:**
    - 有効なゲストセッションCookie
    - store_id: 選択する店舗のID

    **戻り値:**
    - 更新されたセッション情報

    **エラー:**
    - 401: セッションが存在しないか有効期限切れ
    - 404: 指定された店舗が存在しない
    """
    # 店舗の存在確認
    store = (
        db.query(Store)
        .filter(Store.id == store_update.store_id, Store.is_active.is_(True))
        .first()
    )

    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Store with id {store_update.store_id} " "not found or inactive"),
        )

    # セッションに店舗IDを保存
    session.selected_store_id = store_update.store_id
    session.last_accessed_at = datetime.utcnow()

    db.commit()
    db.refresh(session)

    return session


@router.delete(
    "/session",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="ゲストセッション削除",
)
async def delete_guest_session(
    response: Response,
    session: GuestSession = Depends(require_guest_session),
    db: Session = Depends(get_db),
):
    """
    現在のゲストセッションを削除

    **動作:**
    - データベースからセッションを削除
    - Cookieを無効化

    **用途:**
    - ユーザーがログインした後
    - ユーザーが明示的にセッションをクリアしたい場合

    **必要なもの:**
    - 有効なゲストセッションCookie
    """
    # データベースから削除（カスケードでカートアイテムも削除される）
    db.delete(session)
    db.commit()

    # Cookieを削除
    response.delete_cookie(key=SESSION_COOKIE_NAME)

    return None
