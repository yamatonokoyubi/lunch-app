# デモログイン情報と認証トラブルシューティング

## デモアカウント情報

### 店舗スタッフ

#### オーナー（全権限）
- **ユーザー名**: `admin`
- **パスワード**: `admin@123`
- **権限**: owner (すべての機能を使用可能)

#### マネージャー
- **ユーザー名**: `store1`
- **パスワード**: `password123`
- **権限**: manager (メニュー管理、売上レポート閲覧可能)

#### スタッフ
- **ユーザー名**: `store2`  
- **パスワード**: `password123`
- **権限**: staff (注文管理のみ可能)

### 顧客

#### 顧客1-5
- **ユーザー名**: `customer1` ~ `customer5`
- **パスワード**: `password123`
- **権限**: customer (メニュー閲覧、注文作成、履歴確認)

## ログイン方法

### APIエンドポイント
```bash
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin@123
```

### レスポンス例
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

## トラブルシューティング

### "Incorrect username or password" エラーが表示される

#### 原因1: マイグレーションが実行されていない

**確認方法**:
```bash
# Docker環境
docker compose exec web alembic current

# ローカル環境
alembic current
```

**解決方法**:
```bash
# Docker環境
docker compose exec web alembic upgrade head

# ローカル環境
alembic upgrade head
```

#### 原因2: パスワードハッシュが破損している

**確認方法**:
```bash
# Docker環境
docker compose exec web python scripts/check_database_state.py
docker compose exec web python scripts/verify_demo_users.py

# ローカル環境
python scripts/check_database_state.py
python scripts/verify_demo_users.py
```

**解決方法**:
`verify_demo_users.py`スクリプトが自動的にパスワードを修正します。

#### 原因3: データベースがリセットされた

`docker compose down -v`を実行すると、データベースボリュームが削除され、すべてのデータが失われます。

**解決方法**:
```bash
# コンテナとボリュームを削除して再作成
docker compose down -v
docker compose up -d

# マイグレーションを実行
docker compose exec web alembic upgrade head

# 初期データが自動的に投入されます
```

### 初期データ（カテゴリ・メニュー）が見つからない

#### 確認方法
```bash
# Docker環境
docker compose exec web python scripts/check_database_state.py

# ローカル環境  
python scripts/check_database_state.py
```

期待される出力:
```
✅ 初期データが正常に投入されています
   - 6カテゴリ: 6件 ✓
   - 30メニュー: 30件 ✓
   - 店舗: 1件 ✓
   - デモユーザー: 8名 ✓
```

#### 解決方法
マイグレーション `cc07ab120b94_seed_initial_categories_and_menus` が適用されていることを確認:

```bash
# Docker環境
docker compose exec web alembic current

# ローカル環境
alembic current
```

出力に `cc07ab120b94` が含まれていれば正常です。

含まれていない場合は、マイグレーションを実行:
```bash
# Docker環境
docker compose exec web alembic upgrade head

# ローカル環境
alembic upgrade head
```

## 初期データの内容

### カテゴリ (6種類)
1. **定番** - 幕の内や唐揚げなど、誰もが好きな定番の味
2. **肉の彩り** - ハンバーグやカツなど、お肉をたっぷり楽しむボリューム満点メニュー
3. **海の幸** - 新鮮な魚介を使った、魚好きにはたまらないラインナップ
4. **ヘルシー** - 野菜たっぷり、低カロリーで健康を気遣う方におすすめ
5. **丼もの** - ボリューム満点、がっつり食べたい時の丼ぶりメニュー
6. **サイドメニュー** - お弁当にプラスして、より豊かな食事を

### メニュー (30種類)
各カテゴリに5種類ずつ、合計30種類のメニューが用意されています。

#### 定番 (5品)
- 彩り豊かな特製幕の内弁当 (¥980)
- 若鶏のジューシー唐揚げ弁当 (¥780)
- 豚の生姜焼き御膳 (¥850)
- 鶏の照り焼きと鮭塩焼きのWメイン弁当 (¥920)
- 定番おかずのデラックス弁当 (¥1,100)

*(他のカテゴリも同様に5品ずつ)*

詳細は `alembic/versions/cc07ab120b94_seed_initial_categories_and_menus.py` を参照してください。

## データベースの完全リセット

すべてのデータを削除して、初期状態から始める場合:

```bash
# Docker環境
docker compose down -v
docker compose up --build

# マイグレーションは自動実行されます（entrypoint.sh経由）
```

## よくある質問

### Q: パスワードを変更したい
A: データベースで直接変更する必要があります:
```bash
docker compose exec web python -c "
from database import SessionLocal
from models import User
from auth import get_password_hash

db = SessionLocal()
user = db.query(User).filter(User.username == 'admin').first()
user.hashed_password = get_password_hash('新しいパスワード')
db.commit()
print('パスワードを変更しました')
"
```

### Q: 新しいデモユーザーを追加したい
A: `scripts/init_data.py` または新しいマイグレーションファイルで追加できます。

### Q: `docker compose down -v` を実行してもデータは残る？
A: いいえ、`-v` オプションを使用すると、ボリュームも削除されるため、すべてのデータが失われます。

データを保持したい場合は、`docker compose stop` または `docker compose down`（`-v`なし）を使用してください。

## サポート

問題が解決しない場合は、以下の情報を含めてIssueを作成してください:

1. エラーメッセージ
2. 実行したコマンド
3. `docker compose exec web python scripts/check_database_state.py` の出力
4. `docker compose exec web alembic current` の出力
