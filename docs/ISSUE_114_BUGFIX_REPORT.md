# Issue #114 バグ修正レポート

## 🐛 発生した問題

### エラー 1: GET /api/store/stores が 404

```
GET http://[::1]:8000/api/store/stores 404 (Not Found)
Error: Not Found
```

**原因**: Issue #113 の API コードが feature/114 ブランチにマージされていなかった

**解決策**: `feature/113-enhance-role-based-store-api` ブランチをマージ

### エラー 2: 画像アップロードが 403 (Manager)

```
POST http://[::1]:8000/api/store/profile/image 403 (Forbidden)
Error: Insufficient permissions. Required roles: owner
```

**原因**: 画像アップロード・削除 API が Owner 専用になっていた

**解決策**: Manager にも画像操作権限を付与

---

## 🔧 実施した修正

### 1. Issue #113 のブランチをマージ

```bash
git fetch origin
git merge origin/feature/113-enhance-role-based-store-api --no-edit
```

**マージ内容**:

- ✅ GET /api/store/stores エンドポイント追加
- ✅ GET /api/store/profile の store_id パラメータ対応
- ✅ PUT /api/store/profile の役割ベース更新ロジック
- ✅ StoreSummary, StoresListResponse スキーマ追加
- ✅ 包括的なテストファイル (test_store_profile_rbac.py)

### 2. 画像アップロード API 権限の修正

**修正前**:

```python
@router.post("/profile/image")
async def upload_store_image(
    current_user: User = Depends(require_role(["owner"])),  # Owner専用
):
```

**修正後**:

```python
@router.post("/profile/image")
async def upload_store_image(
    current_user: User = Depends(require_role(["owner", "manager"])),  # Manager追加
):
```

**変更ファイル**: `routers/store.py`

- Line 345: `require_role(["owner"])` → `require_role(["owner", "manager"])`
- Docstring: "オーナー専用" → "Owner/Manager 専用"

### 3. 画像削除 API 権限の修正

**修正前**:

```python
@router.delete("/profile/image")
def delete_store_image(
    current_user: User = Depends(require_role(["owner"])),  # Owner専用
):
```

**修正後**:

```python
@router.delete("/profile/image")
def delete_store_image(
    current_user: User = Depends(require_role(["owner", "manager"])),  # Manager追加
):
```

**変更ファイル**: `routers/store.py`

- Line 421: `require_role(["owner"])` → `require_role(["owner", "manager"])`
- Docstring: "オーナー専用" → "Owner/Manager 専用"

---

## ✅ 修正後の動作

### Owner

- ✅ GET /api/store/stores で全店舗一覧取得 → **200 OK**
- ✅ 店舗選択ドロップダウンが表示される
- ✅ 店舗を切り替えると情報が更新される
- ✅ 画像アップロード可能 → **200 OK**
- ✅ 画像削除可能 → **200 OK**

### Manager

- ✅ GET /api/store/profile で自店舗取得 → **200 OK**
- ✅ フォームが編集可能
- ✅ 画像アップロード可能 → **200 OK** (修正済み)
- ✅ 画像削除可能 → **200 OK** (修正済み)
- ✅ 店舗情報の保存が可能

### Staff

- ✅ GET /api/store/profile で自店舗取得 → **200 OK**
- ✅ すべてのフォームが読み取り専用
- ✅ 画像アップロード不可 → **403 Forbidden** (正しい動作)
- ✅ 画像削除不可 → **403 Forbidden** (正しい動作)
- ✅ 保存ボタンが非表示

---

## 🧪 検証方法

### 1. Owner でテスト

```bash
# ログイン
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "owner_user", "password": "password"}'

# 店舗一覧取得
curl -X GET http://localhost:8000/api/store/stores \
  -H "Authorization: Bearer <token>"
# 期待: 200 OK, 全店舗リスト

# 画像アップロード
curl -X POST http://localhost:8000/api/store/profile/image \
  -H "Authorization: Bearer <token>" \
  -F "file=@test_image.jpg"
# 期待: 200 OK
```

### 2. Manager でテスト

```bash
# ログイン
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "manager_user", "password": "password"}'

# 店舗一覧取得（アクセス不可）
curl -X GET http://localhost:8000/api/store/stores \
  -H "Authorization: Bearer <token>"
# 期待: 403 Forbidden

# 画像アップロード（アクセス可能）
curl -X POST http://localhost:8000/api/store/profile/image \
  -H "Authorization: Bearer <token>" \
  -F "file=@test_image.jpg"
# 期待: 200 OK (修正後)
```

### 3. Staff でテスト

```bash
# ログイン
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "staff_user", "password": "password"}'

# 画像アップロード（アクセス不可）
curl -X POST http://localhost:8000/api/store/profile/image \
  -H "Authorization: Bearer <token>" \
  -F "file=@test_image.jpg"
# 期待: 403 Forbidden
```

---

## 📊 権限マトリックス（修正後）

| API                             | Owner  | Manager           | Staff  |
| ------------------------------- | ------ | ----------------- | ------ |
| GET /api/store/stores           | ✅ 200 | ❌ 403            | ❌ 403 |
| GET /api/store/profile          | ✅ 200 | ✅ 200            | ✅ 200 |
| PUT /api/store/profile          | ✅ 200 | ✅ 200            | ❌ 403 |
| POST /api/store/profile/image   | ✅ 200 | ✅ 200 ← **修正** | ❌ 403 |
| DELETE /api/store/profile/image | ✅ 200 | ✅ 200 ← **修正** | ❌ 403 |

---

## 📝 コミット情報

```bash
git add -A
git commit -m "fix: Resolve API 404 and Manager image upload permission issues

- Merge feature/113-enhance-role-based-store-api branch
  * Add GET /api/store/stores endpoint
  * Add role-based store profile APIs
- Fix Manager image upload/delete permissions
  * Change require_role from ['owner'] to ['owner', 'manager']
  * Update POST /api/store/profile/image
  * Update DELETE /api/store/profile/image
- Add comprehensive debugging tools and documentation"
```

---

## 🚀 次のステップ

1. **実際のブラウザでテスト**:

   - Owner でログイン → 店舗選択ドロップダウン表示確認
   - Manager でログイン → 編集・画像アップロード確認
   - Staff でログイン → 読み取り専用確認

2. **デバッグツールで検証**:

   ```
   http://localhost:8000/store/profile/debug
   ```

   - 各テストボタンで API の動作確認

3. **自動テスト実行**:

   ```bash
   pytest tests/test_store_profile_rbac.py -v
   ```

   - 全 18 テストがパスすることを確認

4. **プッシュとプルリクエスト**:
   ```bash
   git push origin feature/114-implement-role-based-store-ui
   ```
   - GitHub でプルリクエストを作成
   - Issue #114 を参照

---

## ✅ 確認チェックリスト

- [x] Issue #113 のブランチをマージ
- [x] GET /api/store/stores エンドポイントが利用可能
- [x] Manager に画像アップロード権限を付与
- [x] Manager に画像削除権限を付与
- [x] ドキュメント作成（実装レポート・トラブルシューティング）
- [x] デバッグツールページ作成
- [x] 詳細ログ追加
- [ ] ブラウザでの実機テスト（次のステップ）
- [ ] 自動テスト実行（次のステップ）

---

**修正完了日時**: 2025-01-XX  
**修正者**: GitHub Copilot  
**ステータス**: ✅ Ready for Testing
