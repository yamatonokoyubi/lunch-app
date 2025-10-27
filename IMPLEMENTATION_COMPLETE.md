# 実装完了: 初期データ投入とユーザー認証の修正

## 概要

このPRでは、以下の問題を解決しました:

1. ✅ **初期データ投入**: 6カテゴリと30種類の弁当メニューを自動投入
2. ✅ **デモログイン認証**: 正しい認証情報とトラブルシューティングツールを提供
3. ✅ **マイグレーションの冪等性**: 複数回実行しても安全な設計
4. ✅ **包括的なドキュメント**: トラブルシューティングガイドとFAQ

## 実装内容

### 1. マイグレーションの改善 ✨

**ファイル**: `alembic/versions/cc07ab120b94_seed_initial_categories_and_menus.py`

- 冪等性チェックを追加（既存データがある場合はスキップ）
- 6カテゴリと30メニューを自動作成
- 8名のデモユーザーを作成（店舗スタッフ3名、顧客5名）

### 2. 検証・トラブルシューティングツール 🔧

#### デモユーザー検証スクリプト
```bash
docker compose exec web python scripts/verify_demo_users.py
```
- すべてのデモユーザーのパスワードを検証
- 不正なパスワードハッシュを自動修正
- 検証結果をわかりやすく表示

#### データベース状態確認スクリプト
```bash
docker compose exec web python scripts/check_database_state.py
```
- 店舗、カテゴリ、メニュー、ユーザーの数を確認
- 初期データが正しく投入されているか検証
- 不足している場合は警告を表示

### 3. ドキュメント 📚

#### デモログインガイド
**ファイル**: `docs/DEMO_LOGIN_GUIDE.md`
- デモアカウントの完全なリスト
- ログイン方法とAPI使用例
- トラブルシューティング手順
- よくある質問 (FAQ)

#### 実装サマリー
**ファイル**: `docs/IMPLEMENTATION_SUMMARY_AUTH_AND_SEEDING.md`
- 実装の詳細
- 認証の仕組み
- トラブルシューティング手順
- テスト方法

#### README更新
- デモアカウント表を更新（権限情報を追加）
- DEMO_LOGIN_GUIDE.mdへのリンクを追加

## デモアカウント情報

### 店舗スタッフ 👨‍💼

| ユーザー名 | パスワード  | 権限 | できること |
|-----------|------------|------|----------|
| admin     | admin@123  | owner | すべての機能（メニュー削除含む） |
| store1    | password123| manager | メニュー管理、売上レポート閲覧 |
| store2    | password123| staff | 注文管理のみ |

### 顧客 👥

| ユーザー名 | パスワード |
|-----------|-----------|
| customer1 | password123 |
| customer2 | password123 |
| customer3 | password123 |
| customer4 | password123 |
| customer5 | password123 |

## 使用方法

### 1. システムを起動

```bash
# Docker環境を起動
docker compose up -d

# マイグレーションは自動実行されます（entrypoint.sh経由）
```

### 2. 初期データを確認

```bash
# データベースの状態を確認
docker compose exec web python scripts/check_database_state.py
```

期待される出力:
```
✅ 初期データが正常に投入されています
   - 6カテゴリ: 6件 ✓
   - 30メニュー: 30件 ✓
   - 店舗: 1件 ✓
   - デモユーザー: 8名 ✓
```

### 3. デモユーザーを検証

```bash
# パスワードを検証・修正
docker compose exec web python scripts/verify_demo_users.py
```

### 4. ログインテスト

```bash
# adminユーザーでログイン
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin@123"
```

成功時のレスポンス:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@bento.com",
    "role": "store",
    "full_name": "管理者"
  }
}
```

## トラブルシューティング 🔍

### "Incorrect username or password" エラーが出る

**解決方法**:
```bash
# パスワードを検証・修正
docker compose exec web python scripts/verify_demo_users.py
```

このスクリプトが自動的にパスワードハッシュを修正します。

### 初期データが見つからない

**解決方法**:
```bash
# マイグレーションを実行
docker compose exec web alembic upgrade head
```

### データベースを完全リセットしたい

```bash
# すべてのデータを削除して再作成
docker compose down -v
docker compose up --build
```

## 初期データの内容

### メニューカテゴリ (6種類)

1. **定番** - 幕の内や唐揚げなど、誰もが好きな定番の味（5品）
2. **肉の彩り** - ハンバーグやカツなど、お肉をたっぷり楽しむボリューム満点メニュー（5品）
3. **海の幸** - 新鮮な魚介を使った、魚好きにはたまらないラインナップ（5品）
4. **ヘルシー** - 野菜たっぷり、低カロリーで健康を気遣う方におすすめ（5品）
5. **丼もの** - ボリューム満点、がっつり食べたい時の丼ぶりメニュー（5品）
6. **サイドメニュー** - お弁当にプラスして、より豊かな食事を（5品）

### メニュー例（30種類）

- 彩り豊かな特製幕の内弁当 (¥980)
- 若鶏のジューシー唐揚げ弁当 (¥780)
- とろけるチーズの特製ハンバーグ弁当 (¥950)
- 脂ののった鯖の味噌煮弁当 (¥890)
- 1日に必要な野菜の半分が摂れるバランス弁当 (¥920)
- とろとろ半熟卵のロースカツ丼 (¥980)
- 10種野菜のグリーンサラダ（選べるドレッシング）(¥250)
- なめらか絹プリン (¥320)
- ... 他22品

## その他の機能

### 一括可用性切り替え

**エンドポイント**: `PUT /api/store/menus/bulk-availability`

**リクエスト例**:
```bash
curl -X PUT http://localhost:8000/api/store/menus/bulk-availability \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "menu_ids": [1, 2, 3],
    "is_available": false
  }'
```

**必要な権限**: owner または manager

## セキュリティ

- ✅ CodeQLセキュリティスキャン: 脆弱性なし
- ✅ パスワード: bcryptでハッシュ化
- ✅ JWT認証: アクセストークン30分、リフレッシュトークン7日
- ⚠️  デモ用の簡単なパスワードを使用（本番環境では変更推奨）

## サポート

詳細なトラブルシューティング方法については、以下のドキュメントを参照してください:

- [デモログインガイド](docs/DEMO_LOGIN_GUIDE.md)
- [実装サマリー](docs/IMPLEMENTATION_SUMMARY_AUTH_AND_SEEDING.md)

## まとめ ✨

このPRにより、以下が実現されました:

✅ **自動初期データ投入** - マイグレーション実行で6カテゴリ、30メニュー、8ユーザーを自動作成  
✅ **簡単なログイン** - 正しい認証情報とトラブルシューティングツールを提供  
✅ **冪等性** - マイグレーションを複数回実行しても安全  
✅ **包括的なドキュメント** - ガイド、FAQ、トラブルシューティング手順  
✅ **検証ツール** - データベース状態確認とパスワード検証スクリプト

すぐに使えるデモ環境が整いました！🎉
