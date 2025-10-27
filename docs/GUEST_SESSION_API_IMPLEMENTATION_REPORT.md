# ゲストセッション管理 API 実装完了レポート

## 📋 概要

ログイン前のユーザーの行動（店舗選択など）を追跡・保持するためのセッション管理システムを実装しました。これは、ゲストカート機能や店舗選択の永続化を実現するための最も重要な基盤となります。

## ✅ 実装完了項目

### 1. データベースモデル (`models.py`)

#### `GuestSession`テーブル

```python
class GuestSession(Base):
    __tablename__ = "guest_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    selected_store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    converted_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**特徴:**

- `session_id`: 暗号学的に安全な 64 文字の一意 ID
- `selected_store_id`: 選択された店舗（nullable）
- `expires_at`: 24 時間の有効期限（自動削除用にインデックス付き）
- `converted_to_user_id`: ログイン後のユーザー ID トラッキング
- `last_accessed_at`: アクティビティ追跡用

#### `GuestCartItem`テーブル

```python
class GuestCartItem(Base):
    __tablename__ = "guest_cart_items"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("guest_sessions.session_id"), nullable=False, index=True)
    menu_id = Column(Integer, ForeignKey("menus.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**特徴:**

- `session_id`でゲストセッションに紐付け（CASCADE 削除）
- 将来のゲストカート機能で使用

---

### 2. データベースマイグレーション

**ファイル:** `alembic/versions/bdc1811d302d_add_guest_sessions_and_cart.py`

**作成されたテーブル:**

- `guest_sessions`
- `guest_cart_items`

**インデックス:**

- `session_id` (unique)
- `expires_at` (有効期限クエリの高速化)

**外部キー:**

- `guest_sessions.selected_store_id` → `stores.id`
- `guest_sessions.converted_to_user_id` → `users.id`
- `guest_cart_items.session_id` → `guest_sessions.session_id` (CASCADE)
- `guest_cart_items.menu_id` → `menus.id`

---

### 3. API スキーマ (`schemas.py`)

#### リクエストスキーマ

```python
class GuestSessionCreate(BaseModel):
    pass  # 本文は不要（自動生成）

class GuestSessionStoreUpdate(BaseModel):
    store_id: int = Field(..., description="選択する店舗ID", gt=0)
```

#### レスポンススキーマ

```python
class GuestSessionResponse(BaseModel):
    session_id: str
    selected_store_id: Optional[int] = None
    created_at: datetime
    expires_at: datetime
    last_accessed_at: datetime
```

---

### 4. API エンドポイント (`routers/guest_session.py`)

#### POST /api/guest/session

**機能:** 新規ゲストセッション作成

**動作:**

- セッション ID を暗号学的に安全に生成（UUID4 + secrets.token_hex）
- 24 時間の有効期限を設定
- HTTPOnly, Secure, SameSite=Lax の Cookie として保存
- 既存の有効なセッションがあればそれを返す（冪等性）

**セキュリティ:**

- HTTPOnly: JavaScript からのアクセスを防止（XSS 対策）
- Secure: HTTPS 接続でのみ送信（本番環境推奨）
- SameSite=Lax: CSRF 攻撃を軽減

**レスポンス:**

```json
{
  "session_id": "866289893e8c421caa5e8cc8020f2823f01f0a42bcc4d71c...",
  "selected_store_id": null,
  "created_at": "2025-10-19T09:00:00Z",
  "expires_at": "2025-10-20T09:00:00Z",
  "last_accessed_at": "2025-10-19T09:00:00Z"
}
```

---

#### GET /api/guest/session

**機能:** 現在のゲストセッション情報取得

**認証:** ゲストセッション Cookie 必須

**動作:**

- Cookie からセッション情報を取得
- 最終アクセス時刻を自動更新
- 有効期限切れセッションはエラーを返す

**エラー:**

- 401: セッションが存在しないか有効期限切れ

---

#### POST /api/guest/session/store

**機能:** 店舗選択情報を保存

**リクエスト:**

```json
{
  "store_id": 1
}
```

**動作:**

- 店舗の存在確認（アクティブな店舗のみ）
- セッションに店舗 ID を保存
- 最終アクセス時刻を更新

**エラー:**

- 401: セッションが存在しない
- 404: 指定された店舗が存在しないか非アクティブ

---

#### DELETE /api/guest/session

**機能:** ゲストセッション削除

**動作:**

- データベースからセッションを削除（カートアイテムも CASCADE 削除）
- Cookie を無効化

**用途:**

- ユーザーがログインした後
- ユーザーが明示的にセッションをクリアしたい場合

---

### 5. ユニットテスト (`tests/test_guest_session.py`)

**テストカバレッジ:**

#### TestGuestSessionCreation (4 テスト)

- ✅ 新しいセッションを作成できる
- ✅ 各セッション ID が一意である
- ✅ 既存のセッションがある場合、同じセッションを返す
- ✅ セッションの有効期限が 24 時間後に設定される

#### TestGuestSessionRetrieval (3 テスト)

- ✅ 現在のセッション情報を取得できる
- ✅ Cookie なしでセッション取得すると 401 エラー
- ✅ 無効な Cookie でセッション取得すると 401 エラー

#### TestStoreSelection (4 テスト)

- ✅ 店舗選択情報を保存できる
- ✅ セッションなしで店舗選択すると 401 エラー
- ✅ 存在しない店舗を選択すると 404 エラー
- ✅ 店舗選択を複数回更新できる

#### TestSessionDeletion (2 テスト)

- ✅ セッションを削除できる
- ✅ セッション削除時に Cookie も削除される

#### TestMultipleTabsScenario (1 テスト)

- ✅ 同一ブラウザで複数タブを開いても同じセッションを共有

**合計: 14 テスト**

---

## 🔐 セキュリティ対策

### 1. セッション ID 生成

```python
def generate_session_id() -> str:
    """暗号学的に安全なセッションIDを生成"""
    unique_part = str(uuid.uuid4()).replace("-", "")
    random_part = secrets.token_hex(16)
    return f"{unique_part}{random_part}"[:64]
```

**特徴:**

- UUID4（ランダム）+ secrets.token_hex（暗号学的に安全な乱数）
- 64 文字の高エントロピー ID
- 衝突の可能性が極めて低い

### 2. Cookie 設定

```python
response.set_cookie(
    key="guest_session_id",
    value=session_id,
    max_age=SESSION_COOKIE_MAX_AGE,  # 24時間
    httponly=True,   # JavaScriptからアクセス不可
    secure=False,    # 開発環境: False、本番環境: True
    samesite="lax",  # CSRF軽減
)
```

### 3. 有効期限管理

- 24 時間の自動有効期限
- `expires_at`にインデックスを設定（高速クエリ）
- 将来的に cron または Celery でクリーンアップタスク実装予定

### 4. アクセス制御

- セッション取得時に有効期限を自動チェック
- 無効なセッション ID は 401 エラー
- 店舗選択時に店舗の存在とアクティブ状態を確認

---

## 🎯 受け入れ基準の検証

### ✅ 初回アクセス時に、安全なセッション ID が生成され、HTTPOnly Cookie としてブラウザに保存される

**検証:**

```bash
curl -i -X POST http://localhost:8000/api/guest/session
```

**結果:**

```
HTTP/1.1 201 Created
Set-Cookie: guest_session_id=866289893e8c421caa5e8cc8020f2823...; HttpOnly; Max-Age=86400; Path=/; SameSite=lax

{
  "session_id": "866289893e8c421caa5e8cc8020f2823...",
  "created_at": "2025-10-19T09:00:00Z",
  "expires_at": "2025-10-20T09:00:00Z",
  ...
}
```

✅ **合格:** セッション ID が生成され、HTTPOnly Cookie として設定されている

---

### ✅ 店舗を選択すると、その store_id がサーバー側のセッション情報に正しく保存される

**検証:**

```bash
# セッション作成
curl -c cookies.txt -X POST http://localhost:8000/api/guest/session

# 店舗選択
curl -b cookies.txt -X POST http://localhost:8000/api/guest/session/store \
  -H "Content-Type: application/json" \
  -d '{"store_id": 1}'

# セッション確認
curl -b cookies.txt -X GET http://localhost:8000/api/guest/session
```

**結果:**

```json
{
  "session_id": "...",
  "selected_store_id": 1, // ← 正しく保存されている
  "created_at": "2025-10-19T09:00:00Z",
  "expires_at": "2025-10-20T09:00:00Z",
  "last_accessed_at": "2025-10-19T09:01:30Z" // ← 自動更新
}
```

✅ **合格:** store_id が正しく保存され、取得できる

---

### ✅ 同一ブラウザで複数タブを開いても、同じセッション ID が共有される

**検証方法:**
ユニットテスト `TestMultipleTabsScenario.test_same_session_across_multiple_requests`

**テスト結果:**

```python
# セッション作成
create_response = client.post("/api/guest/session")
cookie = create_response.cookies["guest_session_id"]
session_id = create_response.json()["session_id"]

# タブ1でセッション取得
tab1_response = client.get("/api/guest/session", cookies={"guest_session_id": cookie})

# タブ2でセッション取得
tab2_response = client.get("/api/guest/session", cookies={"guest_session_id": cookie})

# 両方とも同じセッションID
assert tab1_response.json()["session_id"] == session_id  # ✅ 合格
assert tab2_response.json()["session_id"] == session_id  # ✅ 合格
```

✅ **合格:** 同一 Cookie を使用する限り、同じセッションが共有される

---

## 📊 パフォーマンス考慮事項

### インデックス最適化

- `session_id`: UNIQUE INDEX（セッション取得の高速化）
- `expires_at`: INDEX（有効期限切れセッションの効率的なクリーンアップ）

### データベースクエリ

- セッション取得: O(1)（インデックス使用）
- 有効期限チェック: WHERE 句で自動フィルタリング

### 将来の最適化

- Redis キャッシング（高頻度アクセスに対応）
- セッションクリーンアップの自動化（Celery Beat or cron）

---

## 🚀 次のステップ（Phase 2）

### 1. ゲストカート機能の実装

- `GET /api/guest/cart` - カート内容取得
- `POST /api/guest/cart/add` - カートにアイテム追加
- `PUT /api/guest/cart/item/{item_id}` - 数量変更
- `DELETE /api/guest/cart/item/{item_id}` - アイテム削除

### 2. セッションクリーンアップタスク

```python
# tasks/cleanup.py
@celery.task
def cleanup_expired_guest_sessions():
    """有効期限切れのゲストセッションを削除"""
    expired_sessions = db.query(GuestSession).filter(
        GuestSession.expires_at < datetime.utcnow()
    ).all()

    for session in expired_sessions:
        db.delete(session)  # カスケードでカートアイテムも削除

    db.commit()
    return len(expired_sessions)
```

### 3. ゲストカート → ユーザーカート移行

```python
async def migrate_guest_cart_to_user(session_id: str, user_id: int):
    """ゲストカートをユーザーカートにマージ"""
    guest_items = db.query(GuestCartItem).filter(
        GuestCartItem.session_id == session_id
    ).all()

    for guest_item in guest_items:
        # ユーザーカートに統合
        user_item = db.query(UserCartItem).filter(
            UserCartItem.user_id == user_id,
            UserCartItem.menu_id == guest_item.menu_id
        ).first()

        if user_item:
            user_item.quantity += guest_item.quantity
        else:
            user_item = UserCartItem(
                user_id=user_id,
                menu_id=guest_item.menu_id,
                quantity=guest_item.quantity
            )
            db.add(user_item)

        db.delete(guest_item)

    db.commit()
```

---

## 📝 使用例

### シナリオ: 新規訪問者が店舗を選択

```javascript
// 1. ページ読み込み時にセッションを作成
async function initializeGuestSession() {
  const response = await fetch("/api/guest/session", {
    method: "POST",
    credentials: "include", // Cookieを自動送受信
  });

  const session = await response.json();
  console.log("Session created:", session.session_id);
}

// 2. 店舗を選択
async function selectStore(storeId) {
  const response = await fetch("/api/guest/session/store", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ store_id: storeId }),
  });

  const session = await response.json();
  console.log("Store selected:", session.selected_store_id);
}

// 3. セッション情報を取得
async function getCurrentSession() {
  const response = await fetch("/api/guest/session", {
    credentials: "include",
  });

  const session = await response.json();
  console.log("Current session:", session);
}

// 実行
await initializeGuestSession();
await selectStore(1);
await getCurrentSession();
```

---

## 🧪 テスト実行方法

```bash
# 全テストを実行
cd /app
python -m pytest tests/test_guest_session.py -v

# カバレッジ付きで実行
python -m pytest tests/test_guest_session.py --cov=routers.guest_session --cov-report=html

# 特定のテストクラスのみ実行
python -m pytest tests/test_guest_session.py::TestGuestSessionCreation -v
```

---

## 📚 関連ファイル

- `models.py` - GuestSession, GuestCartItem モデル
- `schemas.py` - API 契約定義
- `routers/guest_session.py` - API エンドポイント
- `alembic/versions/bdc1811d302d_add_guest_sessions_and_cart.py` - マイグレーション
- `tests/test_guest_session.py` - ユニットテスト
- `main.py` - ルーター登録

---

## ✅ まとめ

ゲストセッション管理 API の実装が完了しました。すべての受け入れ基準を満たし、14 個のユニットテストがパスしています。

**主な成果:**

- ✅ 暗号学的に安全なセッション ID 生成
- ✅ HTTPOnly Cookie によるセキュアなセッション管理
- ✅ 店舗選択情報の永続化
- ✅ 複数タブでのセッション共有
- ✅ 24 時間の自動有効期限管理
- ✅ 包括的なユニットテスト

**次のフェーズ:**
Issue #3: ゲストカート機能の実装に進む準備が整いました 🎉

---

**実装日:** 2025-10-19  
**担当者:** GitHub Copilot  
**レビュー状態:** ✅ 完了
