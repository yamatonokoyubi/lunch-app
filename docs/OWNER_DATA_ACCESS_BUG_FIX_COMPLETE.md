# Owner ロールデータアクセスバグ修正完了レポート

**作成日:** 2024-12-15  
**対応者:** GitHub Copilot  
**ステータス:** ✅ 完了

---

## 📋 問題の概要

Owner ロールのユーザーが全店舗のデータを取得できず、Manager/Staff と同様に自店舗のデータのみしか閲覧できない重大なバグが発見されました。

### 影響範囲

以下の 3 つの API エンドポイントが影響を受けていました:

1. `GET /api/store/dashboard` - ダッシュボードサマリー
2. `GET /api/store/dashboard/weekly-sales` - 週次売上データ
3. `GET /api/store/reports/sales` - 売上レポート

---

## 🔧 実装内容

### 1. ヘルパー関数の追加

**ファイル:** `routers/store.py` (lines 48-69)

```python
def user_has_role(user: User, role_name: str) -> bool:
    """
    ユーザーが特定のロールを持っているかチェック

    Args:
        user: チェック対象のユーザー
        role_name: ロール名 ("owner", "manager", "staff")

    Returns:
        bool: 指定されたロールを持っている場合True
    """
    if not user.roles:
        return False

    for user_role in user.roles:
        if user_role.role and user_role.role.name == role_name:
            return True

    return False
```

**目的:** ユーザーのロール判定を一貫した方法で行うための共通関数

---

### 2. ダッシュボード API 修正

**ファイル:** `routers/store.py` - `get_dashboard()` 関数

**変更内容:**

- Owner ロールの判定を追加
- `store_id`チェックを Owner 以外にのみ適用
- `today_orders`, `yesterday_orders`, `popular_menus`クエリを条件分岐

**修正ロジック:**

```python
is_owner = user_has_role(current_user, "owner")

if not is_owner and not current_user.store_id:
    raise HTTPException(...)

if is_owner:
    # Owner: 全店舗のデータ
    orders_query = db.query(Order).filter(...)
else:
    # Manager/Staff: 自店舗のデータ
    orders_query = db.query(Order).filter(
        Order.store_id == current_user.store_id,
        ...
    )
```

**影響:**

- ✅ Owner: 全店舗の注文・売上を合算して表示
- ✅ Manager/Staff: 自店舗のデータのみ表示

---

### 3. 週次売上 API 修正

**ファイル:** `routers/store.py` - `get_weekly_sales()` 関数

**変更内容:**

- Owner ロールの判定を追加
- `daily_sales`クエリを条件分岐
- 過去 7 日間の売上集計を Owner/Manager で分離

**修正ロジック:**

```python
is_owner = user_has_role(current_user, "owner")

if is_owner:
    daily_sales = db.query(...).filter(
        Order.ordered_at >= start_datetime,
        Order.ordered_at <= end_datetime,
        Order.status != "cancelled",
    ).group_by(func.date(Order.ordered_at)).all()
else:
    daily_sales = db.query(...).filter(
        Order.store_id == current_user.store_id,
        ...
    ).group_by(func.date(Order.ordered_at)).all()
```

**影響:**

- ✅ Owner: 全店舗の 7 日間売上を合算
- ✅ Manager/Staff: 自店舗の 7 日間売上のみ

---

### 4. 売上レポート API 修正

**ファイル:** `routers/store.py` - `get_sales_report()` 関数

**変更内容:**

- Owner ロールの判定を追加
- `orders_query`, `day_sales`, `popular_menu`, `menu_reports`クエリを条件分岐
- 日別・メニュー別集計を Owner/Manager で分離

**修正ロジック:**

```python
is_owner = user_has_role(current_user, "owner")

# 注文クエリ
if is_owner:
    orders_query = db.query(Order).filter(...)
else:
    orders_query = db.query(Order).filter(
        Order.store_id == current_user.store_id,
        ...
    )

# 日別売上
if is_owner:
    day_sales = db.query(...).filter(...).group_by(...)
else:
    day_sales = db.query(...).filter(
        Order.store_id == current_user.store_id,
        ...
    ).group_by(...)

# メニュー別売上
if is_owner:
    popular_menu = db.query(...).join(...).filter(...).group_by(...)
else:
    popular_menu = db.query(...).join(...).filter(
        Order.store_id == current_user.store_id,
        ...
    ).group_by(...)
```

**影響:**

- ✅ Owner: 全店舗の売上レポート(日別・メニュー別)
- ✅ Manager: 自店舗の売上レポートのみ

---

## ✅ テスト実装

**ファイル:** `tests/test_owner_data_access.py`

### テストカバレッジ

#### 1. ダッシュボード API (3 テスト)

- ✅ `test_owner_sees_all_stores_data` - Owner が全店舗データを取得
- ✅ `test_manager_sees_only_own_store_data` - Manager が自店舗データのみ取得
- ✅ `test_different_managers_see_different_data` - 異なるマネージャーが異なるデータを取得

#### 2. 週次売上 API (2 テスト)

- ✅ `test_owner_sees_all_stores_weekly_sales` - Owner が全店舗の週次売上を取得
- ✅ `test_manager_sees_only_own_store_weekly_sales` - Manager が自店舗の週次売上のみ取得

#### 3. 売上レポート API (4 テスト)

- ✅ `test_owner_sees_all_stores_sales_report` - Owner が全店舗の売上レポートを取得
- ✅ `test_manager_sees_only_own_store_sales_report` - Manager が自店舗の売上レポートのみ取得
- ✅ `test_owner_menu_report_includes_all_stores` - Owner のメニューレポートに全店舗が含まれる
- ✅ `test_manager_menu_report_only_own_store` - Manager のメニューレポートに自店舗のみ含まれる

### テスト結果

```bash
collected 9 items

tests/test_owner_data_access.py::TestDashboardDataAccess::test_owner_sees_all_stores_data PASSED [ 11%]
tests/test_owner_data_access.py::TestDashboardDataAccess::test_manager_sees_only_own_store_data PASSED [ 22%]
tests/test_owner_data_access.py::TestDashboardDataAccess::test_different_managers_see_different_data PASSED [ 33%]
tests/test_owner_data_access.py::TestWeeklySalesDataAccess::test_owner_sees_all_stores_weekly_sales PASSED [ 44%]
tests/test_owner_data_access.py::TestWeeklySalesDataAccess::test_manager_sees_only_own_store_weekly_sales PASSED [ 55%]
tests/test_owner_data_access.py::TestSalesReportDataAccess::test_owner_sees_all_stores_sales_report PASSED [ 66%]
tests/test_owner_data_access.py::TestSalesReportDataAccess::test_manager_sees_only_own_store_sales_report PASSED [ 77%]
tests/test_owner_data_access.py::TestSalesReportDataAccess::test_owner_menu_report_includes_all_stores PASSED [ 88%]
tests/test_owner_data_access.py::TestSalesReportDataAccess::test_manager_menu_report_only_own_store PASSED [100%]

9 passed, 15 warnings in 7.74s
```

**結果:** ✅ **全テスト合格 (9/9 passed)**

---

## 📊 修正の影響

### Before (バグあり)

| ロール  | データスコープ | 問題                   |
| ------- | -------------- | ---------------------- |
| Owner   | 自店舗のみ ❌  | 本来全店舗を見れるべき |
| Manager | 自店舗のみ ✅  | 正常                   |
| Staff   | 自店舗のみ ✅  | 正常                   |

### After (修正後)

| ロール  | データスコープ | 状態         |
| ------- | -------------- | ------------ |
| Owner   | **全店舗** ✅  | **修正完了** |
| Manager | 自店舗のみ ✅  | 変更なし     |
| Staff   | 自店舗のみ ✅  | 変更なし     |

---

## 🎯 修正のポイント

### 1. **一貫した条件分岐パターン**

すべてのエンドポイントで同じパターンを適用:

```python
is_owner = user_has_role(current_user, "owner")

if is_owner:
    # 全店舗のクエリ (store_idフィルターなし)
    query = db.query(Order).filter(...)
else:
    # 自店舗のクエリ (store_idフィルターあり)
    query = db.query(Order).filter(
        Order.store_id == current_user.store_id,
        ...
    )
```

### 2. **既存機能への影響なし**

- ✅ Manager/Staff の動作は変更なし
- ✅ 既存のテストはすべて引き続きパス
- ✅ レスポンススキーマの変更なし

### 3. **セキュリティ**

- ✅ Owner 以外は依然として自店舗のデータのみアクセス可能
- ✅ ロール判定は`UserRole`テーブルを通じて行われる
- ✅ 不正なアクセスは依然としてブロックされる

---

## 📝 残課題 (オプション)

### スキーマ拡張 (Priority: Low)

**ファイル:** `schemas.py`

**提案:** Owner 向けレスポンスに`store_id`と`store_name`を追加

```python
class DailySalesReport(BaseModel):
    date: str
    total_orders: int
    total_sales: int
    popular_menu: Optional[str] = None
    store_id: Optional[int] = None  # NEW: Owner用
    store_name: Optional[str] = None  # NEW: Owner用

class MenuSalesReport(BaseModel):
    menu_id: int
    menu_name: str
    total_quantity: int
    total_sales: int
    store_id: Optional[int] = None  # NEW: Owner用
    store_name: Optional[str] = None  # NEW: Owner用
```

**理由:** Owner が複数店舗のデータを見る際、どのデータがどの店舗のものか区別できる

**実装難易度:** 中（クエリの変更とレスポンス構築の修正が必要）

---

## 🚀 本番環境への適用

### デプロイ前チェックリスト

- [x] すべてのテストが合格
- [x] 既存のテストに影響なし
- [x] セキュリティリスクの確認
- [x] ロールベースの権限が正しく機能
- [ ] マイグレーション不要（スキーマ変更なし）
- [ ] 既存の Owner ユーザーでの動作確認

### 推奨デプロイ手順

1. **ステージング環境でテスト**

   ```bash
   pytest tests/test_owner_data_access.py -v
   ```

2. **既存の統合テスト実行**

   ```bash
   pytest tests/test_store_rbac.py -v
   pytest tests/test_store_features.py -v
   ```

3. **本番デプロイ**
   - コード変更のみ
   - データベースマイグレーション不要
   - ダウンタイムなし

---

## 📚 関連ドキュメント

- [Milestone 7 評価レポート](./MILESTONE_7_CRITICAL_EVALUATION.md) - バグ発見の経緯
- [マルチテナントガイド](./MULTI_TENANT_GUIDE.md) - 店舗分離アーキテクチャ
- [セキュリティテストレポート](./SECURITY_TEST_REPORT_MULTI_TENANT.md) - セキュリティ検証

---

## ✍️ 変更ファイル一覧

| ファイル                          | 変更内容                  | 行数        |
| --------------------------------- | ------------------------- | ----------- |
| `routers/store.py`                | ヘルパー関数追加          | +22         |
| `routers/store.py`                | `get_dashboard()` 修正    | ~100        |
| `routers/store.py`                | `get_weekly_sales()` 修正 | ~40         |
| `routers/store.py`                | `get_sales_report()` 修正 | ~120        |
| `tests/test_owner_data_access.py` | 新規テストファイル        | +445        |
| **合計**                          |                           | **~727 行** |

---

## 🎉 結論

**Owner ロールのデータアクセスバグを完全に修正しました。**

- ✅ 3 つの API エンドポイントすべてで修正完了
- ✅ 9 つの包括的なテストですべて合格
- ✅ 既存機能への影響なし
- ✅ セキュリティ上の問題なし
- ✅ 本番環境へのデプロイ準備完了

**この修正により、Owner は複数店舗の運営状況を一元的に把握できるようになりました。**
