# Issue #114: 画像アップロード/削除機能の修正

## 問題

Owner ユーザーが店舗画像をアップロード・削除しようとすると、以下のエラーが発生していました：

```
400 Bad Request: User is not associated with any store
```

### 根本原因

Owner は`current_user.store_id`が null であるため、既存の API は自店舗の画像のみを対象としていました。
Owner が店舗セレクターで選択した店舗の画像をアップロード・削除できるようにする必要がありました。

## 修正内容

### 1. フロントエンド修正 (`static/js/store_profile.js`)

#### 画像アップロード処理

```javascript
// 修正前
const response = await apiClient.uploadImage("/store/profile/image", formData);

// 修正後
let apiUrl = "/store/profile/image";
if (isOwner && currentStoreId) {
  apiUrl = `/store/profile/image?store_id=${currentStoreId}`;
}
const response = await apiClient.uploadImage(apiUrl, formData);
```

#### 画像削除処理

```javascript
// 修正前
const response = await apiClient.delete("/store/profile/image");

// 修正後
let apiUrl = "/store/profile/image";
if (isOwner && currentStoreId) {
  apiUrl = `/store/profile/image?store_id=${currentStoreId}`;
}
const response = await apiClient.delete(apiUrl);
```

### 2. バックエンド修正 (`routers/store.py`)

#### POST /api/store/profile/image - 画像アップロード

**パラメータ追加:**

- `store_id` (Optional[int]): 店舗 ID（Owner 専用、省略時は自店舗）

**ロジック:**

```python
# 役割チェック
is_owner = user_has_role(current_user, "owner")

# 店舗IDを決定
if store_id is not None:
    # store_idが指定された場合
    if not is_owner:
        # Manager/Staffは自店舗以外を指定できない
        if current_user.store_id != store_id:
            raise HTTPException(403, "You can only upload images for your own store")
    target_store_id = store_id
else:
    # store_idが指定されていない場合は自店舗
    if not current_user.store_id:
        raise HTTPException(400, "User is not associated with any store")
    target_store_id = current_user.store_id

# target_store_idを使用して店舗情報を取得
store = db.query(Store).filter(Store.id == target_store_id).first()
```

#### DELETE /api/store/profile/image - 画像削除

同様に`store_id`パラメータを追加し、Owner が選択した店舗の画像を削除できるようにしました。

### 3. ヘッダー表示修正 (`static/js/common.js`)

Owner の場合、ヘッダーの店舗名取得時にデフォルトで store_id=1 を使用するように修正：

```javascript
// 店舗情報を取得して表示
// Ownerの場合はデフォルトでstore_id=1を使用
const isOwner = user.user_roles?.some((ur) => ur.role.name === "owner");
const storeIdToUse = user.store_id || (isOwner ? 1 : null);

if (storeIdToUse) {
  const storeProfile = await ApiClient.get(
    `/store/profile?store_id=${storeIdToUse}`
  );
  // ...
}
```

## セキュリティ

### 権限チェック

1. **Owner**: 任意の店舗の画像をアップロード・削除可能（store_id パラメータで指定）
2. **Manager**: 自店舗の画像のみアップロード・削除可能
   - store_id を指定した場合でも、自店舗以外は 403 エラー
3. **Staff**: アクセス不可（require_role 制約）

### API 設計

- `store_id`パラメータはクエリパラメータとして実装
- バックエンドで厳密な権限チェックを実施
- フロントエンドの条件分岐は UI/UX のため（セキュリティはバックエンドが担保）

## テスト方法

### 1. Owner でのテスト

1. Owner アカウントでログイン
2. 店舗セレクターで「真徳弁当飫肥店」(ID=1)を選択
3. 「画像を選択」ボタンで画像をアップロード
4. 画像が表示されることを確認
5. 店舗セレクターで「真徳弁当蔵町店」(ID=2)に切り替え
6. 別の画像をアップロード
7. 各店舗で正しい画像が表示されることを確認
8. 「画像を削除」ボタンで削除動作を確認

### 2. Manager でのテスト

1. Manager アカウントでログイン
2. 自店舗の画像をアップロード・削除できることを確認
3. ブラウザの DevTools で別の店舗 ID を手動指定した場合、403 エラーになることを確認

### 3. Staff でのテスト

1. Staff アカウントでログイン
2. 画像アップロードセクションが表示されないことを確認

## ブラウザコンソールログ

正常動作時のログ例：

```
Uploading image to: /store/profile/image?store_id=1
Image uploaded successfully
Deleting image from: /store/profile/image?store_id=1
Image deleted successfully
```

## 関連ファイル

- `static/js/store_profile.js` - フロントエンド実装
- `static/js/common.js` - ヘッダー表示ロジック
- `routers/store.py` - バックエンド API 実装
- `schemas.py` - レスポンススキーマ（変更なし）

## 修正日

2025-10-19
