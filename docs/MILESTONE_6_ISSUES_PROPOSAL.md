# Milestone 6: メニュー管理機能 - Issues提案

**作成日**: 2025年10月13日  
**対象**: 弁当注文システム - メニュー管理基盤の完全実装

---

## 📋 Issues 概要

バックエンドAPI（90%カバレッジ達成済み）を最大限活用するため、フロントエンド実装と機能強化を段階的に行います。

**全体構成**:
- 🔴 **Phase 1 (必須)**: フロントエンド基本実装 - 3 Issues
- 🟡 **Phase 2 (推奨)**: UX改善・機能強化 - 4 Issues  
- 🟢 **Phase 3 (拡張)**: 高度な機能追加 - 3 Issues

**合計**: 10 Issues

---

## 🔴 Phase 1: フロントエンド基本実装 (必須)

バックエンドAPIは完全に実装済みのため、フロントエンドを追加するだけで即座に利用可能になります。

---

### Issue #1: メニュー管理画面の基本実装 👑 最優先

**優先度**: 🔴 Critical  
**見積工数**: 8-12時間  
**依存関係**: なし（即座に着手可能）

#### 📝 背景・目的

現在、バックエンドAPIは完全実装済み（テストカバレッジ90%）ですが、店舗スタッフが使用できるフロントエンド画面が存在しません。メニュー管理のコア機能を提供する管理画面を実装します。

#### 🎯 達成目標

店舗スタッフ（owner, manager, staff）が以下の操作を画面上で実行できる:
1. ✅ メニュー一覧の表示（テーブル形式）
2. ✅ 公開/非公開フィルタ
3. ✅ ページネーション
4. ✅ メニュー詳細の即時確認

#### 📐 実装仕様

**ファイル構成**:
```
templates/
  └── store_menus.html         # 新規作成
static/
  ├── css/
  │   └── store_menus.css      # 新規作成
  └── js/
      └── store_menus.js       # 新規作成
```

**画面レイアウト**:
```
┌─────────────────────────────────────────────┐
│ 🍱 メニュー管理                                │
├─────────────────────────────────────────────┤
│ [すべて] [公開中] [非公開]  [+ 新規作成]       │
├─────────────────────────────────────────────┤
│ 名前         │価格   │ステータス│操作         │
├─────────────────────────────────────────────┤
│ 特製弁当     │ ¥1200 │ 🟢 公開中│[編集][削除]│
│ 季節限定     │ ¥1500 │ 🔴 非公開│[編集][削除]│
│ ハンバーグ   │ ¥1000 │ 🟢 公開中│[編集][削除]│
├─────────────────────────────────────────────┤
│              [1] 2 3 ... 10                 │
└─────────────────────────────────────────────┘
```

**使用API**:
```javascript
// メニュー一覧取得
GET /api/store/menus?is_available={bool}&page={int}&per_page={int}

Response:
{
  "menus": [
    {
      "id": 1,
      "name": "特製弁当",
      "price": 1200,
      "description": "...",
      "is_available": true,
      "created_at": "2025-10-01T10:00:00Z",
      "updated_at": "2025-10-10T15:30:00Z"
    }
  ],
  "total": 45
}
```

#### 🔧 技術要件

**HTML** (`store_menus.html`):
- ✅ 既存の`store_dashboard.html`をベースにする
- ✅ ナビゲーション統一
- ✅ レスポンシブデザイン

**CSS** (`store_menus.css`):
- ✅ テーブルスタイル
- ✅ ステータスバッジ（公開=緑、非公開=赤）
- ✅ フィルタボタングループ

**JavaScript** (`store_menus.js`):
```javascript
// 必須機能
1. fetchMenus(isAvailable, page)  // メニュー一覧取得
2. renderMenuTable(menus)          // テーブル描画
3. renderPagination(total, page)   // ページネーション
4. handleFilterChange(filter)      // フィルタ切替
5. confirmDelete(menuId)           // 削除確認
```

#### ✅ 受入基準

- [ ] メニュー一覧が正しく表示される
- [ ] 公開/非公開フィルタが動作する
- [ ] ページネーション（20件/ページ）が機能する
- [ ] ステータスバッジが色分けされている
- [ ] レスポンシブ対応（スマホ・タブレット）
- [ ] ローディング表示がある
- [ ] エラーハンドリングが実装されている

#### 📊 テスト項目

**E2Eテスト**:
```python
def test_menu_list_page_loads():
    """メニュー一覧ページが正常に読み込まれる"""
    
def test_filter_by_availability():
    """公開/非公開フィルタが機能する"""
    
def test_pagination_works():
    """ページネーションが正しく動作する"""
```

#### 🎨 デザイン参考

**既存画面との一貫性**:
- `store_dashboard.html`のヘッダー・ナビゲーション
- `store_orders.html`のテーブルスタイル
- `store_reports.html`のフィルタUI

#### 📚 参考資料

- API仕様: `routers/store.py` (lines 639-673)
- データスキーマ: `schemas.py` (lines 293-335)
- テストコード: `tests/test_store_menus.py`

---

### Issue #2: メニュー作成・編集フォームの実装

**優先度**: 🔴 High  
**見積工数**: 6-8時間  
**依存関係**: Issue #1（メニュー一覧画面）

#### 📝 背景・目的

店舗スタッフがメニューを作成・編集できるフォーム画面を実装します。直感的な操作で季節限定メニューの追加や価格変更が可能になります。

#### 🎯 達成目標

1. ✅ メニュー新規作成フォーム
2. ✅ メニュー編集フォーム
3. ✅ バリデーション（クライアント・サーバー両方）
4. ✅ 公開/非公開トグル

#### 📐 実装仕様

**モーダルフォーム** (推奨):
```
┌─────────────────────────────────────┐
│ ✖ メニューを作成                      │
├─────────────────────────────────────┤
│ 名前 *                               │
│ [_____________________________]     │
│                                     │
│ 価格 (円) *                          │
│ [_____________________________]     │
│                                     │
│ 説明                                 │
│ [_____________________________]     │
│ [_____________________________]     │
│                                     │
│ 画像URL                              │
│ [_____________________________]     │
│                                     │
│ [ ] 公開する                         │
│                                     │
│        [キャンセル]  [作成]          │
└─────────────────────────────────────┘
```

**使用API**:
```javascript
// 作成
POST /api/store/menus
Body: {
  "name": "春の特製弁当",
  "price": 1500,
  "description": "桜エビと筍の春限定弁当",
  "image_url": "https://...",
  "is_available": true
}

// 更新
PUT /api/store/menus/{menu_id}
Body: {
  "name": "春の特製弁当 (期間延長)",
  "price": 1400,
  "is_available": false
}
```

#### 🔧 技術要件

**バリデーション**:
```javascript
function validateMenuForm(formData) {
  const errors = {};
  
  // 名前: 必須、1-255文字
  if (!formData.name || formData.name.length === 0) {
    errors.name = "名前は必須です";
  }
  if (formData.name && formData.name.length > 255) {
    errors.name = "名前は255文字以内で入力してください";
  }
  
  // 価格: 必須、1円以上
  if (!formData.price || formData.price < 1) {
    errors.price = "価格は1円以上で入力してください";
  }
  
  return Object.keys(errors).length === 0 ? null : errors;
}
```

**UX改善**:
- ✅ 入力中のリアルタイムバリデーション
- ✅ エラーメッセージの表示
- ✅ 保存中のローディング表示
- ✅ 成功時のトースト通知

#### ✅ 受入基準

- [ ] メニュー作成フォームが動作する
- [ ] メニュー編集フォームが動作する
- [ ] バリデーションエラーが表示される
- [ ] 公開/非公開トグルが機能する
- [ ] 作成/更新後に一覧が自動更新される
- [ ] モーダルが正しく開閉する
- [ ] ESCキーでモーダルを閉じられる

#### 📊 テスト項目

```python
def test_create_menu_via_form():
    """フォームからメニュー作成できる"""
    
def test_edit_menu_via_form():
    """フォームからメニュー編集できる"""
    
def test_validation_errors_shown():
    """バリデーションエラーが表示される"""
    
def test_toggle_availability():
    """公開/非公開トグルが機能する"""
```

---

### Issue #3: メニュー削除機能と確認ダイアログ

**優先度**: 🔴 High  
**見積工数**: 3-4時間  
**依存関係**: Issue #1（メニュー一覧画面）

#### 📝 背景・目的

メニュー削除機能を実装し、誤削除を防ぐ確認ダイアログを提供します。バックエンドのインテリジェント削除（論理/物理削除の自動判定）を活用します。

#### 🎯 達成目標

1. ✅ 削除ボタンの実装
2. ✅ 確認ダイアログ
3. ✅ 論理削除・物理削除の結果表示
4. ✅ 削除後の一覧自動更新

#### 📐 実装仕様

**確認ダイアログ**:
```
┌──────────────────────────────────────┐
│ ⚠ 確認                                │
├──────────────────────────────────────┤
│                                      │
│ 「特製弁当」を削除しますか?            │
│                                      │
│ ⚠ このメニューには既存の注文があります。│
│ 完全に削除できないため、非公開に       │
│ 設定されます。                        │
│                                      │
│       [キャンセル]  [非公開にする]     │
└──────────────────────────────────────┘
```

**使用API**:
```javascript
DELETE /api/store/menus/{menu_id}

Response (論理削除):
{
  "message": "Menu disabled due to existing orders"
}

Response (物理削除):
{
  "message": "Menu deleted successfully"
}
```

#### 🔧 技術要件

**削除フロー**:
```javascript
async function deleteMenu(menuId, menuName) {
  // 1. 確認ダイアログ表示
  const confirmed = await showConfirmDialog({
    title: "確認",
    message: `「${menuName}」を削除しますか?`,
    confirmText: "削除する",
    cancelText: "キャンセル"
  });
  
  if (!confirmed) return;
  
  // 2. API呼び出し
  try {
    const response = await fetch(`/api/store/menus/${menuId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    
    const result = await response.json();
    
    // 3. 結果に応じた通知
    if (result.message.includes("disabled")) {
      showToast("既存の注文があるため非公開に設定しました", "warning");
    } else {
      showToast("メニューを削除しました", "success");
    }
    
    // 4. 一覧更新
    await fetchMenus();
    
  } catch (error) {
    showToast("削除に失敗しました", "error");
  }
}
```

#### ✅ 受入基準

- [ ] 削除ボタンをクリックすると確認ダイアログが表示される
- [ ] キャンセルで削除が中止される
- [ ] 削除成功時にトースト通知が表示される
- [ ] 論理削除・物理削除で異なるメッセージが表示される
- [ ] 削除後にメニュー一覧が自動更新される
- [ ] エラー時に適切なエラーメッセージが表示される

#### 📊 テスト項目

```python
def test_delete_menu_with_confirmation():
    """確認後にメニュー削除できる"""
    
def test_cancel_delete():
    """削除をキャンセルできる"""
    
def test_logical_delete_message():
    """論理削除時のメッセージが正しい"""
    
def test_physical_delete_message():
    """物理削除時のメッセージが正しい"""
```

---

## 🟡 Phase 2: UX改善・機能強化 (推奨)

基本機能の実装後、ユーザー体験を向上させる機能を追加します。

---

### Issue #4: メニュー画像アップロード機能

**優先度**: 🟡 Medium  
**見積工数**: 8-10時間  
**依存関係**: Issue #2（作成・編集フォーム）

#### 📝 背景・目的

現在は画像URLの手入力のみ対応していますが、画像ファイルを直接アップロードできるようにすることで、スタッフの作業効率を大幅に向上させます。

#### 🎯 達成目標

1. ✅ 画像ファイルのドラッグ&ドロップアップロード
2. ✅ プレビュー表示
3. ✅ 画像の差し替え
4. ✅ 古い画像の自動削除

#### 📐 実装仕様

**画像アップロードエリア**:
```
┌─────────────────────────────────────┐
│ メニュー画像                          │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐   │
│  │                             │   │
│  │    [画像プレビュー]           │   │
│  │    または                     │   │
│  │    📷 ドラッグ&ドロップ        │   │
│  │    クリックしてアップロード     │   │
│  │                             │   │
│  └─────────────────────────────┘   │
│                                     │
│  対応形式: JPEG, PNG, GIF, WebP      │
│  最大サイズ: 5MB                     │
└─────────────────────────────────────┘
```

**新規APIエンドポイント**:
```python
# routers/store.py に追加

@router.post("/menus/{menu_id}/image", response_model=MenuResponse)
async def upload_menu_image(
    menu_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(['owner', 'manager']))
):
    """
    メニュー画像をアップロード
    
    **必要な権限:** owner, manager
    
    **実装**:
    1. ファイル形式検証（JPEG, PNG, GIF, WebP）
    2. ファイルサイズ検証（最大5MB）
    3. 一意のファイル名生成（UUID）
    4. static/uploads/menus/ に保存
    5. 古い画像ファイルを削除
    6. image_url を更新
    """
    # 参考: store.py lines 115-190 (店舗画像アップロード実装済み)
    
    # ファイル形式検証
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # メニュー取得（自店舗のみ）
    menu = db.query(Menu).filter(
        Menu.id == menu_id,
        Menu.store_id == current_user.store_id
    ).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    
    # ファイル保存
    upload_dir = Path("static/uploads/menus")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename
    
    # 古い画像削除
    if menu.image_url and menu.image_url.startswith("/static/uploads/"):
        old_file_path = Path(menu.image_url.lstrip('/'))
        if old_file_path.exists():
            old_file_path.unlink()
    
    # 保存
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # DB更新
    menu.image_url = f"/static/uploads/menus/{unique_filename}"
    db.commit()
    db.refresh(menu)
    
    return menu
```

#### 🔧 技術要件

**フロントエンド**:
```javascript
// 画像アップロード処理
async function uploadMenuImage(menuId, file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`/api/store/menus/${menuId}/image`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData
  });
  
  if (!response.ok) {
    throw new Error('Upload failed');
  }
  
  return await response.json();
}

// ドラッグ&ドロップ
const dropZone = document.getElementById('image-drop-zone');

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('drop', async (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    await uploadMenuImage(currentMenuId, file);
  }
});
```

#### ✅ 受入基準

- [ ] ドラッグ&ドロップで画像アップロードできる
- [ ] クリックでファイル選択ダイアログが開く
- [ ] アップロード前にプレビュー表示される
- [ ] アップロード中のプログレス表示
- [ ] 画像サイズ・形式のバリデーション
- [ ] 古い画像が自動削除される
- [ ] エラー時の適切なメッセージ表示

#### 📊 テスト項目

```python
def test_upload_menu_image():
    """メニュー画像をアップロードできる"""
    
def test_upload_invalid_file_type():
    """不正なファイル形式でエラーになる"""
    
def test_upload_replaces_old_image():
    """古い画像が削除される"""
    
def test_upload_file_too_large():
    """ファイルサイズ超過でエラーになる"""
```

---

### Issue #5: メニューの並び替え・ソート機能

**優先度**: 🟡 Medium  
**見積工数**: 4-6時間  
**依存関係**: Issue #1（メニュー一覧画面）

#### 📝 背景・目的

メニュー一覧の並び替えを可能にし、スタッフが目的のメニューを素早く見つけられるようにします。

#### 🎯 達成目標

1. ✅ カラムヘッダーでソート（クリック）
2. ✅ 昇順・降順の切替
3. ✅ ソート状態の視覚的表示

#### 📐 実装仕様

**ソート対応カラム**:
- 名前（昇順・降順）
- 価格（安い順・高い順）
- 作成日時（新しい順・古い順）
- 更新日時（最近更新順）

**テーブルヘッダー**:
```
┌─────────────────────────────────────────────┐
│ 名前 ↕ │ 価格 ↕ │ ステータス │ 作成日 ↕ │操作│
├─────────────────────────────────────────────┤
```

**APIクエリパラメータ追加**:
```python
# routers/store.py の get_all_menus を拡張

@router.get("/menus", response_model=MenuListResponse)
def get_all_menus(
    is_available: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", regex="^(name|price|created_at|updated_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(['owner', 'manager', 'staff']))
):
    """
    メニュー一覧取得（ソート対応）
    """
    query = db.query(Menu).filter(Menu.store_id == current_user.store_id)
    
    if is_available is not None:
        query = query.filter(Menu.is_available == is_available)
    
    # ソート適用
    order_column = getattr(Menu, sort_by)
    if sort_order == "asc":
        query = query.order_by(order_column.asc())
    else:
        query = query.order_by(order_column.desc())
    
    total = query.count()
    offset = (page - 1) * per_page
    menus = query.offset(offset).limit(per_page).all()
    
    return {"menus": menus, "total": total}
```

#### ✅ 受入基準

- [ ] カラムヘッダークリックでソートされる
- [ ] 昇順・降順の切替ができる
- [ ] ソート状態がアイコンで表示される
- [ ] ページ遷移してもソート状態が維持される
- [ ] フィルタとソートが併用できる

---

### Issue #6: メニュー検索機能

**優先度**: 🟡 Medium  
**見積工数**: 5-7時間  
**依存関係**: Issue #1（メニュー一覧画面）

#### 📝 背景・目的

メニュー数が増加した際に、特定のメニューを素早く見つけられる検索機能を実装します。

#### 🎯 達成目標

1. ✅ メニュー名での部分一致検索
2. ✅ リアルタイム検索（入力中に自動更新）
3. ✅ 検索結果の件数表示

#### 📐 実装仕様

**検索バー**:
```
┌─────────────────────────────────────────────┐
│ 🔍 [メニュー名で検索...____________] [検索]  │
├─────────────────────────────────────────────┤
│ 検索結果: 3件                                 │
├─────────────────────────────────────────────┤
```

**APIクエリパラメータ追加**:
```python
@router.get("/menus", response_model=MenuListResponse)
def get_all_menus(
    is_available: Optional[bool] = Query(None),
    keyword: Optional[str] = Query(None, max_length=255),  # 追加
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(['owner', 'manager', 'staff']))
):
    """
    メニュー一覧取得（検索対応）
    """
    query = db.query(Menu).filter(Menu.store_id == current_user.store_id)
    
    if is_available is not None:
        query = query.filter(Menu.is_available == is_available)
    
    # キーワード検索
    if keyword:
        query = query.filter(
            or_(
                Menu.name.ilike(f"%{keyword}%"),
                Menu.description.ilike(f"%{keyword}%")
            )
        )
    
    total = query.count()
    # ... ページネーション
```

#### ✅ 受入基準

- [ ] キーワード入力で検索できる
- [ ] 部分一致検索が機能する
- [ ] 検索結果件数が表示される
- [ ] 検索クリアボタンで全件表示に戻る
- [ ] 検索中のローディング表示

---

### Issue #7: 一括操作機能（複数メニューの一括公開/非公開）

**優先度**: 🟡 Medium  
**見積工数**: 6-8時間  
**依存関係**: Issue #1（メニュー一覧画面）

#### 📝 背景・目的

複数のメニューを同時に公開/非公開にできる一括操作機能を実装し、季節の変わり目などでの大量メニュー更新を効率化します。

#### 🎯 達成目標

1. ✅ チェックボックスで複数選択
2. ✅ 一括公開・一括非公開
3. ✅ 選択件数の表示
4. ✅ 一括操作の確認ダイアログ

#### 📐 実装仕様

**一括操作UI**:
```
┌─────────────────────────────────────────────┐
│ [✓] 3件選択中  [一括公開] [一括非公開]        │
├─────────────────────────────────────────────┤
│ [✓]│ 春限定弁当   │ ¥1500 │ 🔴 非公開       │
│ [✓]│ 夏限定弁当   │ ¥1600 │ 🔴 非公開       │
│ [✓]│ 秋限定弁当   │ ¥1550 │ 🔴 非公開       │
│ [ ]│ 通年弁当     │ ¥1200 │ 🟢 公開中       │
└─────────────────────────────────────────────┘
```

**新規APIエンドポイント**:
```python
@router.put("/menus/bulk-availability", summary="一括公開/非公開")
def bulk_update_availability(
    menu_ids: List[int] = Body(...),
    is_available: bool = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(['owner', 'manager']))
):
    """
    複数メニューの公開/非公開を一括更新
    
    **必要な権限:** owner, manager
    
    **パラメータ:**
    - menu_ids: 更新対象のメニューIDリスト
    - is_available: 設定する公開状態
    
    **戻り値:**
    - 更新件数
    """
    # 自店舗のメニューのみ対象
    menus = db.query(Menu).filter(
        Menu.id.in_(menu_ids),
        Menu.store_id == current_user.store_id
    ).all()
    
    if not menus:
        raise HTTPException(status_code=404, detail="No menus found")
    
    # 一括更新
    updated_count = 0
    for menu in menus:
        menu.is_available = is_available
        updated_count += 1
    
    db.commit()
    
    return {
        "message": f"{updated_count} menus updated",
        "updated_count": updated_count
    }
```

#### ✅ 受入基準

- [ ] チェックボックスで複数選択できる
- [ ] 選択件数が表示される
- [ ] 一括公開ボタンで選択メニューが公開される
- [ ] 一括非公開ボタンで選択メニューが非公開になる
- [ ] 確認ダイアログが表示される
- [ ] 操作後に選択が解除される

---

## 🟢 Phase 3: 高度な機能追加 (拡張)

将来的な拡張を見据えた高度な機能を追加します。

---

### Issue #8: メニューカテゴリ管理機能

**優先度**: 🟢 Low  
**見積工数**: 12-16時間  
**依存関係**: Issue #1, #2

#### 📝 背景・目的

メニューをカテゴリ別に分類し、顧客の閲覧性を向上させます。

#### 🎯 達成目標

1. ✅ カテゴリマスタ管理（CRUD）
2. ✅ メニューへのカテゴリ紐付け
3. ✅ カテゴリ別フィルタ

#### 📐 データベーススキーマ拡張

```python
# models.py に追加

class MenuCategory(Base):
    """メニューカテゴリテーブル"""
    __tablename__ = "menu_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # "和食", "洋食", "中華"
    display_order = Column(Integer, default=0)  # 表示順
    is_active = Column(Boolean, default=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    store = relationship("Store", back_populates="menu_categories")
    menus = relationship("Menu", back_populates="category")

# Menu モデルに追加
category_id = Column(Integer, ForeignKey("menu_categories.id", ondelete="SET NULL"), nullable=True)
category = relationship("MenuCategory", back_populates="menus")
```

#### ✅ 受入基準

- [ ] カテゴリ一覧が表示される
- [ ] カテゴリの作成・編集・削除ができる
- [ ] メニューにカテゴリを設定できる
- [ ] カテゴリ別フィルタが機能する

---

### Issue #9: 在庫数管理・自動在庫切れ機能

**優先度**: 🟢 Low  
**見積工数**: 10-14時間  
**依存関係**: Issue #1, #2

#### 📝 背景・目的

在庫数を管理し、在庫切れ時に自動的にメニューを非公開にすることで、在庫切れ商品の注文を防止します。

#### 🎯 達成目標

1. ✅ 在庫数の管理
2. ✅ 在庫切れ閾値の設定
3. ✅ 自動非公開機能
4. ✅ 在庫アラート通知

#### 📐 データベーススキーマ拡張

```python
# Menu モデルに追加
stock_quantity = Column(Integer, default=0)           # 在庫数
low_stock_threshold = Column(Integer, default=5)      # 在庫切れ閾値
auto_disable_on_out_of_stock = Column(Boolean, default=True)  # 自動非公開
```

**ビジネスロジック**:
```python
def process_order(menu_id: int, quantity: int, db: Session):
    """
    注文処理時の在庫減算
    """
    menu = db.query(Menu).filter(Menu.id == menu_id).first()
    
    # 在庫確認
    if menu.stock_quantity < quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    # 在庫減算
    menu.stock_quantity -= quantity
    
    # 在庫切れチェック
    if menu.stock_quantity == 0 and menu.auto_disable_on_out_of_stock:
        menu.is_available = False
        # アラート通知
        send_low_stock_alert(menu)
    
    db.commit()
```

#### ✅ 受入基準

- [ ] 在庫数が表示・編集できる
- [ ] 注文時に在庫が減算される
- [ ] 在庫0で自動非公開になる
- [ ] 在庫切れアラートが表示される

---

### Issue #10: メニュー変更履歴・監査ログ

**優先度**: 🟢 Low  
**見積工数**: 8-12時間  
**依存関係**: Issue #1, #2

#### 📝 背景・目的

メニューの変更履歴を記録し、監査・トラブルシューティングに活用します。

#### 🎯 達成目標

1. ✅ 価格変更履歴の記録
2. ✅ 変更者・変更日時の記録
3. ✅ 変更履歴の閲覧画面

#### 📐 データベーススキーマ追加

```python
class MenuChangeLog(Base):
    """メニュー変更履歴テーブル"""
    __tablename__ = "menu_change_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    menu_id = Column(Integer, ForeignKey("menus.id", ondelete="CASCADE"), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    change_type = Column(String(50), nullable=False)  # "created", "updated", "deleted"
    old_values = Column(JSON)  # 変更前の値
    new_values = Column(JSON)  # 変更後の値
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    menu = relationship("Menu")
    user = relationship("User")
```

#### ✅ 受入基準

- [ ] 変更履歴が自動記録される
- [ ] 履歴画面で変更内容を確認できる
- [ ] 変更者・日時が表示される
- [ ] 変更前後の値が比較できる

---

## 📊 Issues優先度マトリックス

| Issue | 優先度 | 工数 | ビジネス価値 | 技術的難易度 | ROI |
|-------|--------|------|------------|------------|-----|
| #1 メニュー一覧画面 | 🔴 Critical | 8-12h | ⭐⭐⭐⭐⭐ | ⭐⭐ | 最高 |
| #2 作成・編集フォーム | 🔴 High | 6-8h | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 高 |
| #3 削除機能 | 🔴 High | 3-4h | ⭐⭐⭐⭐ | ⭐⭐ | 高 |
| #4 画像アップロード | 🟡 Medium | 8-10h | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 中 |
| #5 ソート機能 | 🟡 Medium | 4-6h | ⭐⭐⭐ | ⭐⭐ | 中 |
| #6 検索機能 | 🟡 Medium | 5-7h | ⭐⭐⭐ | ⭐⭐⭐ | 中 |
| #7 一括操作 | 🟡 Medium | 6-8h | ⭐⭐⭐⭐ | ⭐⭐⭐ | 中 |
| #8 カテゴリ管理 | 🟢 Low | 12-16h | ⭐⭐⭐ | ⭐⭐⭐⭐ | 低 |
| #9 在庫管理 | 🟢 Low | 10-14h | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 低 |
| #10 変更履歴 | 🟢 Low | 8-12h | ⭐⭐ | ⭐⭐⭐ | 低 |

---

## 🚀 推奨実装スケジュール

### Sprint 1 (Week 1-2): 基本機能実装
- Day 1-3: Issue #1（メニュー一覧画面）
- Day 4-6: Issue #2（作成・編集フォーム）
- Day 7-8: Issue #3（削除機能）
- **成果物**: 基本的なメニュー管理機能が利用可能

### Sprint 2 (Week 3-4): UX改善
- Day 1-3: Issue #4（画像アップロード）
- Day 4-5: Issue #5（ソート機能）
- Day 6-8: Issue #6（検索機能）
- **成果物**: 使いやすいメニュー管理画面

### Sprint 3 (Week 5-6): 効率化機能
- Day 1-3: Issue #7（一括操作）
- Day 4-8: Issue #8（カテゴリ管理）- オプション
- **成果物**: 大量メニュー管理に対応

### Sprint 4 (Week 7-8): 高度な機能（オプション）
- Day 1-5: Issue #9（在庫管理）
- Day 6-8: Issue #10（変更履歴）
- **成果物**: エンタープライズグレードの機能

---

## 📝 実装時の注意事項

### セキュリティ

1. **権限チェック**:
   ```javascript
   // すべてのAPI呼び出し前に認証確認
   if (!isAuthenticated()) {
     redirectToLogin();
     return;
   }
   ```

2. **XSS対策**:
   ```javascript
   // ユーザー入力のエスケープ
   function escapeHtml(text) {
     const div = document.createElement('div');
     div.textContent = text;
     return div.innerHTML;
   }
   ```

3. **CSRF対策**:
   - すべてのAPI呼び出しに認証トークン付与
   - トークンの定期更新

### パフォーマンス

1. **画像最適化**:
   - アップロード時にリサイズ（最大1200px）
   - WebP形式への変換
   - 遅延読み込み（Lazy Loading）

2. **APIキャッシング**:
   ```javascript
   // メニュー一覧のキャッシング（1分間）
   const CACHE_TTL = 60000;
   let menuCache = null;
   let cacheTimestamp = null;
   
   async function fetchMenus() {
     const now = Date.now();
     if (menuCache && (now - cacheTimestamp < CACHE_TTL)) {
       return menuCache;
     }
     menuCache = await api.get('/api/store/menus');
     cacheTimestamp = now;
     return menuCache;
   }
   ```

### アクセシビリティ

1. **キーボード操作**:
   - Tab順の最適化
   - Enter/Escapeキーでのモーダル操作

2. **スクリーンリーダー対応**:
   - ARIA属性の適切な使用
   - 代替テキストの提供

---

## 🎯 成功指標 (KPI)

### 定量指標

| 指標 | 目標値 | 測定方法 |
|-----|--------|---------|
| メニュー作成時間 | < 2分 | ユーザー操作ログ |
| 画面読み込み時間 | < 1秒 | パフォーマンス測定 |
| エラー率 | < 1% | エラーログ集計 |
| モバイル対応率 | 100% | レスポンシブテスト |

### 定性指標

| 指標 | 評価方法 |
|-----|---------|
| 使いやすさ | ユーザビリティテスト |
| スタッフ満足度 | アンケート調査 |
| エラーメッセージの分かりやすさ | レビュー |

---

## 📚 参考資料

### 既存実装

- **バックエンドAPI**: `routers/store.py` (lines 639-789)
- **データモデル**: `models.py` (lines 85-100)
- **テストコード**: `tests/test_store_menus.py`
- **既存画面**: `templates/store_dashboard.html`, `templates/store_orders.html`

### 技術ドキュメント

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- 画像アップロード参考: `routers/store.py` (lines 115-190)

---

**作成者**: GitHub Copilot  
**最終更新**: 2025年10月13日  
**バージョン**: 1.0
