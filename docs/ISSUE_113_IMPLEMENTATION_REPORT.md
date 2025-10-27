# Issue #113: 役割ベースの店舗情報アクセス・操作権限制御 - 実装完了レポート

## 📋 概要

**Issue**: #113 - 役割ベースの店舗 API アクセス制御の強化  
**ブランチ**: feature/113-enhance-role-based-store-api  
**実装日**: 2025 年 1 月  
**ステータス**: ✅ **完了（全 18 テストパス）**

Owner が複数店舗を管理し、Manager/Staff が適切な権限範囲内で店舗情報にアクセス・操作できるよう、役割ベースのアクセス制御（RBAC）を店舗 API に実装しました。

---

## 🎯 実装内容

### 1. **新規 API: GET /api/store/stores**

**目的**: Owner が全店舗一覧を取得  
**アクセス権限**: Owner 専用

```python
@router.get("/stores", response_model=StoresListResponse)
def get_all_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner"])),
):
    """
    Owner専用: 全店舗一覧を取得
    店舗切り替えUIのドロップダウンに使用
    """
    stores = db.query(Store).order_by(Store.name.asc()).all()
    return {"stores": stores, "total": len(stores)}
```

**レスポンス例**:

```json
{
  "stores": [
    { "id": 1, "name": "店舗A", "address": "東京都...", "is_active": true },
    { "id": 2, "name": "店舗B", "address": "大阪府...", "is_active": true }
  ],
  "total": 2
}
```

**テスト結果**:

- ✅ Owner: 全店舗取得成功（200）
- ✅ Manager: アクセス拒否（403）
- ✅ Staff: アクセス拒否（403）

---

### 2. **修正 API: GET /api/store/profile**

**変更点**: オプションの`store_id`クエリパラメータを追加

**役割別の動作**:

| 役割        | store_id 指定あり                | store_id 指定なし    |
| ----------- | -------------------------------- | -------------------- |
| **Owner**   | 指定した店舗を取得（任意の店舗） | **400 Error** (必須) |
| **Manager** | 自店舗なら取得、他店舗なら 403   | 自店舗を取得         |
| **Staff**   | 自店舗なら取得、他店舗なら 403   | 自店舗を取得         |

```python
def get_store_profile(
    store_id: Optional[int] = Query(None, description="店舗ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_store_user),
):
    is_owner = user_has_role(current_user, "owner")

    if store_id is not None:
        # store_id指定時: Ownerは任意、Manager/Staffは自店舗のみ
        if not is_owner and current_user.store_id != store_id:
            raise HTTPException(403, "You can only access your own store")
        target_store_id = store_id
    else:
        # store_id未指定: Ownerはエラー、Manager/Staffは自店舗
        if is_owner:
            raise HTTPException(400, "Owner must specify store_id")
        target_store_id = current_user.store_id

    # 店舗情報を取得して返却
    ...
```

**テスト結果** (6 シナリオ):

- ✅ Owner: store_id 指定で任意店舗取得成功
- ✅ Owner: store_id 未指定で 400 エラー
- ✅ Manager: 自店舗取得成功（store_id 指定なし）
- ✅ Manager: 自店舗取得成功（store_id 明示指定）
- ✅ Manager: 他店舗アクセスで 403 エラー
- ✅ Staff: 自店舗取得成功
- ✅ Staff: 他店舗アクセスで 403 エラー

---

### 3. **修正 API: PUT /api/store/profile**

**変更点**:

- `require_role`を`["owner"]`から`["owner", "manager"]`に変更
- リクエストボディに`store_id`フィールドを追加（Owner 用）

**役割別の動作**:

| 役割        | store_id 指定あり                | store_id 指定なし    |
| ----------- | -------------------------------- | -------------------- |
| **Owner**   | 指定した店舗を更新（任意の店舗） | **400 Error** (必須) |
| **Manager** | 自店舗なら更新、他店舗なら 403   | 自店舗を更新         |
| **Staff**   | **403 Error** (更新権限なし)     | **403 Error**        |

```python
@router.put("/profile", response_model=StoreResponse)
def update_store_profile(
    store_update: StoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["owner", "manager"])),
):
    is_owner = user_has_role(current_user, "owner")
    is_manager = user_has_role(current_user, "manager")

    # 対象店舗IDの決定
    if store_update.store_id is not None:
        if not is_owner and current_user.store_id != store_update.store_id:
            raise HTTPException(403, "Can only update your own store")
        target_store_id = store_update.store_id
    else:
        target_store_id = current_user.store_id if is_manager else None
        if is_owner:
            raise HTTPException(400, "Owner must specify store_id")

    # 更新データからstore_idを除外（IDの改ざん防止）
    update_data = store_update.model_dump(
        exclude_unset=True,
        exclude={"store_id"}
    )

    # データベース更新処理
    ...
```

**テスト結果** (7 シナリオ):

- ✅ Owner: store_id 指定で任意店舗更新成功（店舗 A、店舗 B 両方）
- ✅ Owner: store_id 未指定で 400 エラー
- ✅ Manager: 自店舗更新成功（store_id 指定なし）
- ✅ Manager: 自店舗更新成功（store_id 明示指定）
- ✅ Manager: 他店舗更新で 403 エラー
- ✅ Staff: 更新試行で 403 エラー
- ✅ Staff: store_id 指定でも 403 エラー

---

## 📊 テスト結果

### テスト実行サマリー

```bash
$ pytest tests/test_store_profile_rbac.py -v

18 passed, 16 warnings in 11.06s
```

### テストケース一覧

#### **TestStoresListAPI** (3 件)

1. ✅ `test_owner_can_get_all_stores` - Owner は全店舗一覧を取得できる
2. ✅ `test_manager_cannot_access_stores_list` - Manager は全店舗一覧にアクセスできない
3. ✅ `test_staff_cannot_access_stores_list` - Staff は全店舗一覧にアクセスできない

#### **TestStoreProfileGetAPI** (7 件)

4. ✅ `test_owner_can_get_any_store_with_store_id` - Owner は store_id で任意店舗取得
5. ✅ `test_owner_must_specify_store_id` - Owner は store_id 必須（未指定で 400）
6. ✅ `test_manager_can_get_own_store` - Manager は自店舗取得可能
7. ✅ `test_manager_can_get_own_store_with_explicit_store_id` - Manager 明示指定 OK
8. ✅ `test_manager_cannot_access_other_store` - Manager 他店舗アクセス拒否
9. ✅ `test_staff_can_get_own_store` - Staff は自店舗取得可能
10. ✅ `test_staff_cannot_access_other_store` - Staff 他店舗アクセス拒否

#### **TestStoreProfileUpdateAPI** (7 件)

11. ✅ `test_owner_can_update_any_store_with_store_id` - Owner 任意店舗更新可能
12. ✅ `test_owner_must_specify_store_id_for_update` - Owner 更新時 store_id 必須
13. ✅ `test_manager_can_update_own_store` - Manager 自店舗更新可能
14. ✅ `test_manager_can_update_own_store_with_explicit_store_id` - Manager 明示指定 OK
15. ✅ `test_manager_cannot_update_other_store` - Manager 他店舗更新拒否
16. ✅ `test_staff_cannot_update_store` - Staff 更新権限なし（403）
17. ✅ `test_staff_cannot_update_store_even_with_store_id` - Staff 明示指定でも拒否

#### **TestStoreAccessIntegration** (1 件)

18. ✅ `test_all_roles_access_pattern` - 全役割の統合アクセスパターン検証

---

## 🔧 修正ファイル

### 1. **schemas.py**

**追加されたスキーマ**:

```python
class StoreSummary(BaseModel):
    """店舗サマリー（一覧用）"""
    id: int
    name: str
    address: Optional[str]
    is_active: bool

class StoresListResponse(BaseModel):
    """全店舗一覧レスポンス"""
    stores: List[StoreSummary]
    total: int

class StoreUpdate(BaseModel):
    """店舗更新リクエスト"""
    store_id: Optional[int] = Field(None, description="店舗ID（Owner専用）")
    name: Optional[str] = ...
    # ... 他のフィールド
```

**変更行数**: +30 行

---

### 2. **routers/store.py**

**追加された機能**:

- 新規エンドポイント `GET /api/stores` (26 行)
- `GET /api/store/profile` の役割ベースロジック追加 (65 行)
- `PUT /api/store/profile` の役割ベース更新ロジック追加 (78 行)

**変更行数**: +169 行

**主要なヘルパー関数の活用**:

```python
from routers.dashboard import user_has_role  # Issue #111で実装済み

is_owner = user_has_role(current_user, "owner")
is_manager = user_has_role(current_user, "manager")
```

---

### 3. **tests/test_store_profile_rbac.py**

**新規テストファイル**: 500 行

**テストフィクスチャ**:

- `owner_user_no_store` - 店舗未所属の Owner ユーザー
- `staff_user_store_a` - 店舗 A の Staff ユーザー
- `auth_headers_*` - 各ユーザーの認証ヘッダー

---

## 🔒 セキュリティ対策

### 1. **店舗 ID 改ざん防止**

```python
update_data = store_update.model_dump(
    exclude_unset=True,
    exclude={"store_id"}  # IDフィールドは更新対象から除外
)
```

リクエストボディの`store_id`は対象店舗の特定にのみ使用し、実際のデータベース更新からは除外することで、店舗 ID の改ざんを防止しています。

### 2. **役割ベースの権限チェック**

```python
if store_id is not None:
    # 指定された店舗IDが自分の店舗と一致するかチェック
    if not is_owner and current_user.store_id != store_id:
        raise HTTPException(403, "You can only access your own store")
```

Owner 以外のユーザーは常に`current_user.store_id`との照合を行い、他店舗へのアクセスをブロックしています。

### 3. **エラーメッセージの明確化**

| ステータスコード    | 意味             | 使用シーン                       |
| ------------------- | ---------------- | -------------------------------- |
| **400 Bad Request** | パラメータ不正   | Owner が store_id を指定しない   |
| **403 Forbidden**   | 権限不足         | Manager/Staff が他店舗にアクセス |
| **404 Not Found**   | 店舗が存在しない | 指定した store_id が無効         |

---

## 🎨 フロントエンド連携

### 店舗切り替え UI の実装例

**Owner 向けドロップダウン**:

```typescript
// 1. 全店舗一覧を取得
const response = await fetch("/api/store/stores", {
  headers: { Authorization: `Bearer ${token}` },
});
const { stores } = await response.json();

// 2. ドロップダウンに表示
<select onChange={(e) => selectStore(e.target.value)}>
  {stores.map((store) => (
    <option key={store.id} value={store.id}>
      {store.name}
    </option>
  ))}
</select>;

// 3. 選択した店舗の情報を取得
const storeData = await fetch(
  `/api/store/profile?store_id=${selectedStoreId}`,
  { headers: { Authorization: `Bearer ${token}` } }
);
```

**Manager/Staff 向け（自店舗のみ）**:

```typescript
// store_id指定なしで自店舗を取得
const response = await fetch("/api/store/profile", {
  headers: { Authorization: `Bearer ${token}` },
});
const myStore = await response.json();
```

---

## 📈 パフォーマンス

### クエリ最適化

```python
# 全店舗一覧取得（簡易情報のみ）
stores = db.query(Store).order_by(Store.name.asc()).all()
```

- ドロップダウン用に必要最小限のフィールドのみ返却（id, name, address, is_active）
- メニュー、注文などのリレーションは含まず高速化
- 名前順ソートで UI 使いやすさ向上

---

## 🚀 次のステップ

### Milestone 7 の他の Issue

1. **Issue #114**: 店舗別売上分析ダッシュボード
2. **Issue #115**: メニュー人気ランキング可視化
3. **Issue #116**: 顧客行動分析レポート

### 拡張可能な機能

- **店舗グループ管理**: 複数店舗をグループ化して Owner が管理
- **一括更新機能**: Owner が複数店舗の設定を一括変更
- **店舗比較ビュー**: Owner が複数店舗の指標を並列比較

---

## ✅ 完了チェックリスト

- [x] 新規 API `GET /api/stores` 実装完了
- [x] `GET /api/store/profile` 役割ベースロジック追加
- [x] `PUT /api/store/profile` 役割ベース更新ロジック追加
- [x] スキーマ定義（StoreSummary, StoresListResponse）追加
- [x] 18 件の包括的テスト実装
- [x] 全テストパス確認
- [x] セキュリティ対策（ID 改ざん防止）実装
- [x] エラーハンドリング（400, 403, 404）実装
- [x] 実装ドキュメント作成

---

## 📝 まとめ

**Issue #113** の実装により、Owner が複数店舗を効率的に管理し、Manager/Staff が適切な権限範囲内で店舗情報にアクセス・操作できるようになりました。

**主な成果**:

- ✅ **3 つの API 修正/新規実装** (GET /api/stores, GET/PUT /api/store/profile)
- ✅ **18 件の包括的テスト** - 全シナリオで役割ベースアクセス制御を検証
- ✅ **セキュリティ強化** - 店舗 ID 改ざん防止、適切な権限チェック
- ✅ **フロントエンド連携準備** - 店舗切り替え UI 実装に必要な API が揃う

これにより、**Milestone 7: データ可視化・分析機能** の基盤が整い、今後の売上分析や顧客行動分析機能の実装がスムーズに進められます。

---

**実装者**: GitHub Copilot  
**レビュー待ち**: ✅ Ready for Review  
**マージ準備**: ✅ All Tests Passed
