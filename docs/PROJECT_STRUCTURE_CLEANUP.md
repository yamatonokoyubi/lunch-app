# プロジェクト構造整理レポート

**実施日**: 2025年10月14日  
**ブランチ**: `feature/87-implement-menu-management-ui`

## 📋 整理の目的

ルートディレクトリが多数のファイルで散らかっていたため、以下の目的で整理を実施：

1. **可読性の向上**: ルートディレクトリをすっきりさせ、プロジェクト構造を明確化
2. **保守性の向上**: ファイルを用途別に適切なディレクトリに配置
3. **チーム開発の効率化**: 新規メンバーがプロジェクト構造を理解しやすくする

## 📂 ファイル移動の概要

### 1. ドキュメント類 → `docs/`

**移動したファイル（14件のmdファイル + 2件のtxtファイル）:**

```
✅ COVERAGE_IMPROVEMENT_PLAN.md → docs/
✅ CUSTOMER_ORDER_BUG_FIX.md → docs/
✅ DASHBOARD_API_ENHANCEMENT.md → docs/
✅ DASHBOARD_DYNAMIC_DATA_IMPLEMENTATION.md → docs/
✅ FEATURE_76_90_COVERAGE_ACHIEVEMENT_REPORT.md → docs/
✅ FINAL_90_PERCENT_ANALYSIS.md → docs/
✅ FINAL_TEST_REPORT.md → docs/
✅ IMPLEMENTATION_SUMMARY_ISSUE_87.md → docs/
✅ MENU_IMAGE_FIX.md → docs/
✅ MENU_MANAGEMENT_UI_IMPLEMENTATION_REPORT.md → docs/
✅ MILESTONE_6_GITHUB_ISSUES_TEMPLATE.md → docs/
✅ MILESTONE_6_ISSUES_PROPOSAL.md → docs/
✅ MILESTONE_6_MENU_MANAGEMENT_ANALYSIS.md → docs/
✅ TEST_PROGRESS_REPORT.md → docs/
✅ FIX_SUMMARY.txt → docs/FIX_SUMMARY.md (拡張子変更)
✅ IMAGE_FIX_SUMMARY.txt → docs/IMAGE_FIX_SUMMARY.md (拡張子変更)
```

**ルートに残したファイル:**
- `README.md` - プロジェクトのメインドキュメント

### 2. スクリプト類 → `scripts/`

**移動したファイル（8件のPythonスクリプト）:**

```
✅ init_data.py → scripts/
✅ setup_test_data.py → scripts/
✅ setup_store_data.py → scripts/
✅ recreate_tables.py → scripts/
✅ update_menu_images.py → scripts/
✅ verify_image_urls.py → scripts/
✅ generate_ts_types.py → scripts/
✅ check_openapi_schema.py → scripts/
```

**ルートに残したファイル（アプリケーションのコア）:**
- `main.py` - FastAPIエントリーポイント
- `models.py` - データベースモデル
- `schemas.py` - Pydanticスキーマ
- `database.py` - DB接続設定
- `dependencies.py` - 依存性注入
- `auth.py` - 認証機能
- `mail.py` - メール機能

### 3. テストファイル → `tests/`

**移動したファイル（4件のテストファイル）:**

```
✅ test_auth_me.py → tests/
✅ test_customer_comprehensive.py → tests/
✅ test_customer_features.py → tests/
✅ test_dashboard_api.py → tests/ (既存ファイルを上書き)
```

## 🔧 ドキュメント更新

ファイル移動に伴い、以下のドキュメントを更新：

### メインREADME.md

**更新箇所:**
1. プロジェクト構成図（ファイルツリー）
2. セットアップ手順のコマンド
3. デプロイ手順
4. マルチテナント機能の使い方

**変更前:**
```bash
docker-compose exec web python init_data.py
docker-compose exec web python setup_store_data.py
```

**変更後:**
```bash
docker-compose exec web python scripts/init_data.py
docker-compose exec web python scripts/setup_store_data.py
```

### その他のドキュメント

**更新したファイル:**
- ✅ `docs/ERROR_FIX_404_STORE_PROFILE.md`
- ✅ `docs/MULTI_TENANT_DOCS_UPDATE_REPORT.md`
- ✅ `docs/MULTI_TENANT_GUIDE.md`
- ✅ `tests/e2e/README.md`

## 📊 整理前後の比較

### ルートディレクトリのファイル数

| カテゴリ | 整理前 | 整理後 | 削減数 |
|---------|--------|--------|--------|
| **Pythonファイル** | 19 | 7 | -12 |
| **ドキュメント（md）** | 15 | 1 | -14 |
| **その他テキスト** | 4 | 0 | -4 |
| **合計** | 38+ | 8 | **-30** |

### 整理後のルートディレクトリ構成

```
bento-order-system/
├── 📄 auth.py                # 認証機能
├── 📄 database.py            # DB接続設定
├── 📄 dependencies.py        # 依存性注入
├── 📄 mail.py                # メール機能
├── 📄 main.py                # FastAPIエントリーポイント
├── 📄 models.py              # データベースモデル
├── 📄 schemas.py             # Pydanticスキーマ
├── 📄 README.md              # プロジェクトドキュメント
├── 📁 docs/                  # ドキュメント類（40+ファイル）
├── 📁 scripts/               # ユーティリティスクリプト（18ファイル）
├── 📁 tests/                 # テストコード（30+ファイル）
├── 📁 routers/               # FastAPIルーター
├── 📁 static/                # 静的ファイル
├── 📁 templates/             # HTMLテンプレート
└── 📁 alembic/               # DBマイグレーション
```

## 🚀 Docker Composeへの影響

### 変更が必要なコマンド

**初期データ投入:**
```bash
# 変更前
docker-compose exec web python init_data.py
docker-compose exec web python setup_store_data.py

# 変更後
docker-compose exec web python scripts/init_data.py
docker-compose exec web python scripts/setup_store_data.py
```

**スクリプト実行:**
```bash
# 変更前
docker-compose exec web python update_menu_images.py
docker-compose exec web python verify_image_urls.py

# 変更後
docker-compose exec web python scripts/update_menu_images.py
docker-compose exec web python scripts/verify_image_urls.py
```

### 変更が不要なコマンド

以下のコマンドは影響を受けません：

```bash
✅ docker-compose up -d
✅ docker-compose exec web alembic upgrade head
✅ docker-compose exec web pytest
✅ docker-compose logs web
```

## 📝 開発者への影響

### 既存の開発者

**対応が必要な作業:**

1. **ブランチの更新**
   ```bash
   git pull origin feature/87-implement-menu-management-ui
   ```

2. **スクリプト実行時のパス変更**
   - `python init_data.py` → `python scripts/init_data.py`
   - `python setup_store_data.py` → `python scripts/setup_store_data.py`

3. **ドキュメント参照先の更新**
   - ルートの`.md`ファイル → `docs/`ディレクトリ内

### 新規の開発者

**メリット:**
- ✅ プロジェクト構造が明確で理解しやすい
- ✅ 必要なファイルが見つけやすい
- ✅ ドキュメントが`docs/`に集約されている

## ✅ チェックリスト

整理完了後の確認事項：

- [x] すべてのファイルが適切なディレクトリに移動
- [x] README.mdが最新の構成を反映
- [x] セットアップ手順のコマンドが正しく更新
- [x] 関連ドキュメントのパスが更新
- [x] gitでファイル移動が正しく記録（`git mv`相当）
- [x] テストファイルが`tests/`に配置
- [x] スクリプトが`scripts/`に配置
- [x] ドキュメントが`docs/`に配置

## 🎯 次のステップ

1. **コミット**
   ```bash
   git commit -m "chore: プロジェクト構造を整理 - ファイルを適切なディレクトリに移動"
   ```

2. **プッシュ**
   ```bash
   git push origin feature/87-implement-menu-management-ui
   ```

3. **チームへの通知**
   - Slack等でファイル移動を周知
   - コマンドのパス変更を共有

## 📚 参考資料

- [README.md](../README.md) - 更新済みのプロジェクトドキュメント
- [docs/](.) - すべてのドキュメントが集約
- [scripts/](../scripts/) - ユーティリティスクリプト
- [tests/](../tests/) - テストコード

---

**整理担当**: GitHub Copilot  
**レビュー**: プロジェクトメンバー全員で確認推奨
