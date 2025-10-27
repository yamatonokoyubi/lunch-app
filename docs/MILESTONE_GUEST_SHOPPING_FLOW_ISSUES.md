# Milestone: 顧客体験を最大化する新しい購入フロー

## 概要

「ログインの壁」を取り除き、カート先行型の購入フローを実装することで、新規顧客の離脱率を改善し、ストレスのない購買体験を提供します。

## 目標

- 新規顧客の離脱率を 50%削減
- コンバージョン率を 30%向上
- カート到達率を 80%向上
- 初回購入までの時間を 50%短縮

---

## 🎯 Phase 1: 基盤整備（Week 1-2）

### Issue #1: ゲストユーザーセッション管理システムの実装

**優先度:** 🔴 最高  
**見積もり:** 13 ポイント  
**依存関係:** なし

**目的:**
ログイン前のユーザーの行動（店舗選択、カート操作）を追跡・保持するためのセッション管理システムを構築します。

**技術仕様:**

```python
# models.py に追加
class GuestSession(Base):
    __tablename__ = "guest_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    selected_store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # 24時間後
    converted_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

class GuestCartItem(Base):
    __tablename__ = "guest_cart_items"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), ForeignKey("guest_sessions.session_id"))
    menu_id = Column(Integer, ForeignKey("menus.id"))
    quantity = Column(Integer, default=1)
    added_at = Column(DateTime, default=datetime.utcnow)
```

**実装タスク:**

1. **データベースマイグレーション:**

   - `guest_sessions` テーブル作成
   - `guest_cart_items` テーブル作成
   - インデックス最適化（session_id, expires_at）

2. **セッション管理 API:**

   - `POST /api/guest/session` - 新規セッション生成
   - `GET /api/guest/session/{session_id}` - セッション情報取得
   - Cookie/LocalStorage で session_id を保持

3. **セッションクリーンアップ:**
   - 有効期限切れセッションの自動削除（Celery タスク or cron）
   - 注文完了後のゲストカート削除

**受け入れ基準:**

- [ ] セッション ID が暗号学的に安全に生成される（uuid4 + secrets）
- [ ] 24 時間後に自動的にセッションが無効化される
- [ ] セッション ID が HTTPOnly Cookie で安全に保存される
- [ ] 同一ブラウザで複数タブを開いても同じセッションを共有
- [ ] セキュリティ: CSRF 対策、XSS 対策が実装されている

---

### Issue #2: 店舗検索・選択 UI の実装（ゲスト対応）

**優先度:** 🔴 最高  
**見積もり:** 8 ポイント  
**依存関係:** Issue #1

**目的:**
添付画像のような、ログイン不要で利用できる店舗検索・選択画面を実装します。

**UI/UX 要件:**

1. **トップページ改修:**

   - Hero Section: 「お近くの店舗を探す」CTA
   - 店舗検索ボックス（地域名、駅名、住所で検索）
   - 人気店舗の表示

2. **店舗一覧ページ (`/stores`):**

   ```
   - 検索バー（テキスト検索）
   - フィルタードロップダウン（地域、営業状態）
   - 店舗カード表示:
     * 店舗名
     * 住所
     * 営業時間
     * 受取可能時間
     * 「この店舗で注文」ボタン（目立つデザイン）
     * 「地図」リンク
   ```

3. **店舗詳細ページ (`/stores/{store_id}`):**
   - 店舗情報
   - 営業時間カレンダー
   - アクセス情報
   - 「メニューを見る」CTA ボタン

**技術実装:**

```javascript
// store_selector.js
class StoreSelector {
  async selectStore(storeId) {
    // ゲストセッションに店舗を保存
    const sessionId = getGuestSessionId();
    await ApiClient.post("/api/guest/session/store", {
      session_id: sessionId,
      store_id: storeId,
    });

    // LocalStorageにも保存（フォールバック）
    localStorage.setItem("selectedStoreId", storeId);

    // メニュー一覧へリダイレクト
    window.location.href = `/menu?store=${storeId}`;
  }
}
```

**受け入れ基準:**

- [ ] ログインなしで全店舗を閲覧・検索できる
- [ ] 検索が高速（< 200ms）でレスポンシブ
- [ ] 店舗選択がセッションに保存される
- [ ] モバイル対応（タッチ操作最適化）
- [ ] アクセシビリティ対応（ARIA、キーボード操作）

---

## 🛒 Phase 2: ゲストカート機能（Week 3-4）

### Issue #3: ゲストカート API・UI の実装

**優先度:** 🔴 最高  
**見積もり:** 13 ポイント  
**依存関係:** Issue #1, #2

**目的:**
ログイン前のユーザーがメニューをカートに追加・編集できる機能を実装します。

**API 設計:**

```python
# routers/guest_cart.py
@router.post("/cart/add")
async def add_to_guest_cart(
    request: GuestCartAddRequest,
    session_id: str = Depends(get_guest_session),
    db: Session = Depends(get_db)
):
    """
    ゲストカートに商品を追加

    パラメータ:
    - session_id: ゲストセッションID（Cookie or Header）
    - menu_id: メニューID
    - quantity: 数量
    - store_id: 店舗ID（検証用）
    """
    # セッション検証
    session = validate_guest_session(session_id, db)

    # メニューが選択店舗のものか確認
    menu = db.query(Menu).filter(
        Menu.id == request.menu_id,
        Menu.store_id == session.selected_store_id,
        Menu.is_available == True
    ).first()

    if not menu:
        raise HTTPException(404, "Menu not found or not available")

    # カートアイテム追加 or 更新
    cart_item = db.query(GuestCartItem).filter(
        GuestCartItem.session_id == session_id,
        GuestCartItem.menu_id == request.menu_id
    ).first()

    if cart_item:
        cart_item.quantity += request.quantity
    else:
        cart_item = GuestCartItem(
            session_id=session_id,
            menu_id=request.menu_id,
            quantity=request.quantity
        )
        db.add(cart_item)

    db.commit()
    return get_cart_summary(session_id, db)

@router.get("/cart")
async def get_guest_cart(
    session_id: str = Depends(get_guest_session),
    db: Session = Depends(get_db)
):
    """ゲストカート内容を取得"""
    pass

@router.put("/cart/item/{item_id}")
async def update_cart_item_quantity():
    """カートアイテムの数量変更"""
    pass

@router.delete("/cart/item/{item_id}")
async def remove_from_cart():
    """カートからアイテム削除"""
    pass
```

**フロントエンド実装:**

```html
<!-- templates/menu_list.html -->
<div class="menu-card">
  <img src="{{ menu.image_url }}" alt="{{ menu.name }}" />
  <h3>{{ menu.name }}</h3>
  <p class="price">¥{{ menu.price }}</p>
  <button class="add-to-cart-btn" data-menu-id="{{ menu.id }}">
    🛒 カートに追加
  </button>
</div>

<!-- カートアイコン（ヘッダー固定） -->
<div class="cart-icon-container">
  <a href="/cart" class="cart-icon"> 🛒 <span class="cart-count">0</span> </a>
</div>
```

```javascript
// cart.js
class GuestCart {
  async addItem(menuId, quantity = 1) {
    try {
      const response = await ApiClient.post("/api/guest/cart/add", {
        menu_id: menuId,
        quantity: quantity,
      });

      // カート数更新
      this.updateCartBadge(response.total_items);

      // 成功通知
      showToast("カートに追加しました", "success");

      // アニメーション
      animateAddToCart(menuId);
    } catch (error) {
      showToast("追加に失敗しました", "error");
    }
  }

  updateCartBadge(count) {
    document.querySelector(".cart-count").textContent = count;
    if (count > 0) {
      document.querySelector(".cart-icon").classList.add("has-items");
    }
  }
}
```

**カートページ (`/cart`):**

```
- カート内容一覧（商品名、単価、数量、小計）
- 数量変更（+/-ボタン）
- 削除ボタン
- 合計金額表示
- 「注文手続きへ進む」CTAボタン（大きく目立つ）
- 「買い物を続ける」リンク
```

**受け入れ基準:**

- [ ] ログインなしでカートに商品を追加できる
- [ ] カート内容がページ遷移しても保持される
- [ ] カートアイコンにアイテム数バッジが表示される
- [ ] 在庫切れメニューは追加できない
- [ ] カート内容の永続化（セッション有効期間中）
- [ ] レスポンシブデザイン（モバイル最適化）

---

### Issue #4: メニュー一覧ページの改善（ゲスト体験向け）

**優先度:** 🟡 高  
**見積もり:** 5 ポイント  
**依存関係:** Issue #2, #3

**目的:**
ゲストユーザーがストレスなくメニューを閲覧・選択できる UI/UX を実装します。

**改善ポイント:**

1. **店舗コンテキストの明示:**

   ```html
   <div class="selected-store-banner">
     📍 受け取り店舗: 真徳弁当飫肥店
     <a href="/stores">変更</a>
   </div>
   ```

2. **カテゴリフィルター:**

   - カテゴリタブ（人気、定番、季節限定、etc.）
   - 価格帯フィルター
   - アレルギー情報フィルター

3. **商品カード最適化:**

   - 高品質な画像（遅延読み込み）
   - 価格を大きく表示
   - 「カートに追加」ボタンを目立たせる
   - ホバーで詳細情報を表示

4. **クイックビュー:**
   - モーダルで商品詳細を表示
   - ページ遷移なしで数量選択＆カート追加

**受け入れ基準:**

- [ ] ページ読み込みが 2 秒以内
- [ ] 画像の遅延読み込みが実装されている
- [ ] カテゴリ切り替えがスムーズ（アニメーション）
- [ ] モバイルで片手操作しやすいレイアウト

---

## 🔐 Phase 3: チェックアウトフロー（Week 5-6）

### Issue #5: ゲストチェックアウト → 認証フローの実装

**優先度:** 🔴 最高  
**見積もり:** 21 ポイント  
**依存関係:** Issue #3

**目的:**
カート確認後、最適なタイミングで認証を求め、スムーズに注文完了まで導きます。

**フロー設計:**

```
[カートページ]
    ↓ 「注文手続きへ」ボタンクリック
[認証チェック]
    ↓ 未ログイン
[認証選択画面] ← 新規実装
    - 「会員の方（ログイン）」
    - 「初めての方（新規登録）」
    ↓
[ログイン or 登録]
    ↓ 認証成功
[ゲストカート→ユーザーカートへ移行] ← 重要
    ↓
[注文確認画面]
    - お客様情報（自動入力）
    - 受け取り日時選択
    - 支払い方法選択
    - 合計金額
    ↓ 「注文を確定」
[注文完了]
```

**技術実装:**

```python
# routers/checkout.py
@router.post("/checkout/initiate")
async def initiate_checkout(
    session_id: str = Depends(get_guest_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    チェックアウト開始

    1. ゲストセッションのカート内容を検証
    2. 在庫確認
    3. ユーザーが未ログインなら認証URLを返す
    4. ログイン済みならゲストカートをマージ
    """
    # カート検証
    cart_items = get_guest_cart_items(session_id, db)
    if not cart_items:
        raise HTTPException(400, "Cart is empty")

    # 在庫・営業時間チェック
    validate_cart_availability(cart_items, db)

    # 未ログインの場合
    if not current_user:
        return {
            "requires_auth": True,
            "auth_url": "/auth/login?redirect=/checkout/confirm",
            "cart_summary": get_cart_summary(session_id, db)
        }

    # ログイン済み: ゲストカート→ユーザーカートへ移行
    await migrate_guest_cart_to_user(session_id, current_user.id, db)

    return {
        "requires_auth": False,
        "redirect_url": "/checkout/confirm"
    }

async def migrate_guest_cart_to_user(
    session_id: str,
    user_id: int,
    db: Session
):
    """ゲストカートをユーザーカートにマージ"""
    guest_items = db.query(GuestCartItem).filter(
        GuestCartItem.session_id == session_id
    ).all()

    for guest_item in guest_items:
        # 既存のユーザーカートに同じアイテムがあれば統合
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

    # セッションを変換済みとしてマーク
    session = db.query(GuestSession).filter(
        GuestSession.session_id == session_id
    ).first()
    if session:
        session.converted_to_user_id = user_id

    db.commit()
```

**認証選択画面 (`/auth/choice`):**

```html
<div class="auth-choice-container">
  <h1>注文を確定するにはログインが必要です</h1>

  <div class="cart-preview">
    <!-- カート内容のサマリー表示 -->
    <p>カート: {{ cart_item_count }}点 / 合計 ¥{{ total_amount }}</p>
  </div>

  <div class="auth-options">
    <div class="auth-option">
      <h2>会員の方</h2>
      <p>ログインして注文を完了</p>
      <a href="/login?redirect=/checkout/confirm" class="btn btn-primary">
        ログイン
      </a>
    </div>

    <div class="auth-option">
      <h2>初めての方</h2>
      <p>新規会員登録（1分で完了）</p>
      <a href="/register?redirect=/checkout/confirm" class="btn btn-success">
        新規登録
      </a>
    </div>
  </div>

  <div class="guest-checkout-note">
    ※ 会員登録いただくと、次回からの注文がさらに簡単になります
  </div>
</div>
```

**受け入れ基準:**

- [ ] カート → 認証 → 確認の流れがシームレス
- [ ] ゲストカートがログイン後に正しくマージされる
- [ ] 認証後、選択していた店舗・商品が保持される
- [ ] エラー時（在庫切れ等）に適切なメッセージを表示
- [ ] セキュリティ: 他人のカートを覗けない

---

### Issue #6: 新規登録フォームの簡素化

**優先度:** 🟡 高  
**見積もり:** 5 ポイント  
**依存関係:** Issue #5

**目的:**
チェックアウトフロー内での新規登録を最小限の入力項目で完了できるようにします。

**改善ポイント:**

1. **必須項目の最小化:**

   ```
   必須:
   - メールアドレス
   - パスワード
   - 氏名
   - 電話番号

   任意（後で入力可能）:
   - 住所
   - 生年月日
   ```

2. **バリデーション改善:**

   - リアルタイムバリデーション
   - わかりやすいエラーメッセージ
   - パスワード強度メーター

3. **ソーシャルログイン（オプション）:**
   - Google 認証
   - LINE 認証
   - 1 クリック登録

**受け入れ基準:**

- [ ] 登録完了まで 1 分以内
- [ ] モバイルで入力しやすいフォーム
- [ ] 登録後すぐにチェックアウトに戻れる

---

### Issue #7: 注文確認ページの実装

**優先度:** 🟡 高  
**見積もり:** 8 ポイント  
**依存関係:** Issue #5

**目的:**
ログイン後、スムーズに注文を確定できる確認画面を実装します。

**画面構成:**

```html
<div class="checkout-confirm">
  <!-- 1. お客様情報（自動入力済み） -->
  <section class="customer-info">
    <h2>お客様情報</h2>
    <p>{{ user.full_name }}</p>
    <p>{{ user.email }}</p>
    <p>{{ user.phone }}</p>
    <a href="/profile/edit">変更</a>
  </section>

  <!-- 2. 受け取り情報 -->
  <section class="pickup-info">
    <h2>受け取り情報</h2>
    <p>店舗: {{ store.name }}</p>
    <div class="datetime-selector">
      <label>受け取り日:</label>
      <input type="date" id="pickup-date" />

      <label>受け取り時間:</label>
      <select id="pickup-time">
        <!-- 営業時間内の30分刻み -->
      </select>
    </div>
  </section>

  <!-- 3. 注文内容 -->
  <section class="order-items">
    <h2>ご注文内容</h2>
    <!-- カート内容を表示 -->
  </section>

  <!-- 4. 支払い方法 -->
  <section class="payment-method">
    <h2>お支払い方法</h2>
    <label>
      <input type="radio" name="payment" value="cash" checked />
      店頭支払い（現金）
    </label>
    <label>
      <input type="radio" name="payment" value="card" />
      クレジットカード（オンライン決済）
    </label>
  </section>

  <!-- 5. 合計金額 -->
  <section class="order-total">
    <div class="total-row">
      <span>小計:</span>
      <span>¥{{ subtotal }}</span>
    </div>
    <div class="total-row">
      <span>消費税:</span>
      <span>¥{{ tax }}</span>
    </div>
    <div class="total-row grand-total">
      <span>合計:</span>
      <span>¥{{ total }}</span>
    </div>
  </section>

  <!-- 6. 確定ボタン -->
  <button class="btn-confirm-order" id="confirm-order-btn">
    注文を確定する
  </button>
</div>
```

**受け入れ基準:**

- [ ] ユーザー情報が自動入力される
- [ ] 受け取り日時を選択できる（営業時間内のみ）
- [ ] 注文内容を最終確認できる
- [ ] 確定ボタンがわかりやすく配置されている

---

## 📊 Phase 4: 分析・改善（Week 7-8）

### Issue #8: ゲストユーザー行動分析ダッシュボード

**優先度:** 🟢 中  
**見積もり:** 8 ポイント  
**依存関係:** Issue #1-7

**目的:**
ゲストユーザーの行動を可視化し、離脱ポイントを特定して継続的に改善します。

**分析指標:**

```python
class GuestAnalytics:
    """ゲストユーザー分析"""

    def get_funnel_metrics(self, start_date, end_date):
        """
        ファネル分析
        1. 店舗選択率
        2. メニュー閲覧率
        3. カート追加率
        4. チェックアウト開始率
        5. 登録完了率
        6. 注文完了率
        """
        pass

    def get_cart_abandonment_rate(self):
        """カート放棄率"""
        pass

    def get_average_items_per_cart(self):
        """カートあたりの平均アイテム数"""
        pass

    def get_conversion_time(self):
        """訪問から注文完了までの平均時間"""
        pass
```

**ダッシュボード画面:**

- ファネルチャート（各ステップの通過率）
- 時系列グラフ（日別のコンバージョン率）
- 離脱ポイントヒートマップ
- 人気メニューランキング（カート追加回数順）

**受け入れ基準:**

- [ ] リアルタイムで指標が更新される
- [ ] 期間指定でフィルタリングできる
- [ ] CSV エクスポート機能

---

### Issue #9: パフォーマンス最適化

**優先度:** 🟢 中  
**見積もり:** 5 ポイント  
**依存関係:** Issue #1-7

**目的:**
ゲストユーザー体験を高速化し、離脱率をさらに削減します。

**最適化項目:**

1. **フロントエンド:**

   - 画像最適化（WebP、遅延読み込み）
   - JavaScript バンドルサイズ削減
   - Critical CSS inline 化
   - Service Worker 導入（PWA 化）

2. **バックエンド:**

   - データベースクエリ最適化
   - Redis キャッシング（メニュー一覧、店舗情報）
   - API レスポンスタイム < 200ms

3. **インフラ:**
   - CDN 導入（静的ファイル配信）
   - データベース接続プール最適化

**目標:**

- ページ読み込み時間: < 2 秒（3G 回線）
- Time to Interactive: < 3 秒
- Lighthouse Score: 90+

---

### Issue #10: A/B テストフレームワークの導入

**優先度:** 🟢 中  
**見積もり:** 8 ポイント  
**依存関係:** なし

**目的:**
UI の改善案をデータドリブンで検証できる仕組みを構築します。

**テスト候補:**

- CTA ボタンの文言（「注文手続きへ」vs「レジへ進む」）
- カートアイコンの配置（ヘッダー右 vs 画面下部固定）
- 認証タイミング（カート追加時 vs チェックアウト時）
- 新規登録フォームのステップ数（1 ページ vs 複数ステップ）

**技術実装:**

```python
# utils/ab_test.py
from enum import Enum

class ABTestVariant(Enum):
    CONTROL = "A"
    VARIANT = "B"

def assign_variant(user_id: Optional[int], session_id: str) -> ABTestVariant:
    """ユーザーをA/Bグループに振り分け"""
    identifier = user_id or session_id
    hash_value = int(hashlib.md5(identifier.encode()).hexdigest(), 16)
    return ABTestVariant.VARIANT if hash_value % 2 == 0 else ABTestVariant.CONTROL
```

---

## 🔧 Phase 5: 追加機能（Week 9-10）

### Issue #11: お気に入り機能（ゲスト対応）

**優先度:** 🟢 中  
**見積もり:** 5 ポイント

**概要:**
ログイン前でもメニューをお気に入り登録でき、登録後にマージされる機能。

---

### Issue #12: 最近見た商品の履歴

**優先度:** 🟢 低  
**見積もり:** 3 ポイント

**概要:**
閲覧履歴をセッションに保存し、「また見る」を簡単にする。

---

### Issue #13: レコメンデーション機能

**優先度:** 🟢 低  
**見積もり:** 13 ポイント

**概要:**

- 「この商品を見た人はこちらも購入」
- カテゴリベースのレコメンド
- 協調フィルタリング（将来的）

---

## 📋 実装優先度まとめ

### Sprint 1（Week 1-2）: 基盤構築

- ✅ Issue #1: ゲストセッション管理
- ✅ Issue #2: 店舗選択 UI

### Sprint 2（Week 3-4）: カート機能

- ✅ Issue #3: ゲストカート
- ✅ Issue #4: メニュー一覧改善

### Sprint 3（Week 5-6）: チェックアウト

- ✅ Issue #5: 認証フロー
- ✅ Issue #6: 新規登録簡素化
- ✅ Issue #7: 注文確認ページ

### Sprint 4（Week 7-8）: 分析・最適化

- ⭐ Issue #8: 分析ダッシュボード
- ⭐ Issue #9: パフォーマンス最適化

### Sprint 5（Week 9-10）: 追加機能

- 🎁 Issue #10: A/B テスト
- 🎁 Issue #11-13: 付加価値機能

---

## 🎯 成功指標（KPI）

| 指標                       | 現状 | 目標   | 測定方法               |
| -------------------------- | ---- | ------ | ---------------------- |
| 新規ユーザーの初回購入率   | -    | 30%    | Google Analytics       |
| カート到達率               | -    | 80%    | Funnel 分析            |
| カート放棄率               | -    | < 50%  | カート作成 vs 注文完了 |
| 訪問から注文完了までの時間 | -    | < 5 分 | Session 分析           |
| モバイルコンバージョン率   | -    | 25%    | デバイス別分析         |

---

## 📚 技術スタック

- **フロントエンド:** HTML5, CSS3, Vanilla JS（既存コードベースに合わせて）
- **バックエンド:** FastAPI, SQLAlchemy（既存と同じ）
- **データベース:** PostgreSQL + 新規テーブル（guest_sessions, guest_cart_items）
- **セッション管理:** HTTPOnly Cookies + LocalStorage（フォールバック）
- **キャッシング:** Redis（オプション）
- **分析:** Google Analytics + カスタムイベント

---

## ⚠️ リスクと対策

| リスク                             | 影響 | 対策                                         |
| ---------------------------------- | ---- | -------------------------------------------- |
| セッション管理のセキュリティ脆弱性 | 高   | セキュリティレビュー、ペネトレーションテスト |
| ゲストカートのデータ肥大化         | 中   | 定期的なクリーンアップ、有効期限管理         |
| 既存ユーザーフローとの競合         | 中   | 段階的ロールアウト、A/B テスト               |
| パフォーマンス低下                 | 中   | 負荷テスト、キャッシング戦略                 |

---

## 🚀 ロールアウト戦略

1. **Phase 1:** 内部テスト（開発環境）
2. **Phase 2:** ベータテスト（限定ユーザー 10%）
3. **Phase 3:** 段階的ロールアウト（10% → 50% → 100%）
4. **Phase 4:** 継続的改善（A/B テスト、フィードバック収集）

---

## 📞 サポート体制

- **開発チーム:** フルスタック 2 名、フロントエンド 1 名
- **QA チーム:** テストエンジニア 1 名
- **データ分析:** アナリスト 1 名（パートタイム）

---

このマイルストーンを完遂することで、顧客体験が劇的に向上し、ビジネス成長の新たなステージに到達できます！🎉
