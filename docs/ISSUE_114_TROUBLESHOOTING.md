# Issue #114 トラブルシューティングガイド

## 🐛 報告された問題

### 問題 1: Owner - 店舗選択ドロップダウンが表示されない

**症状**:

- Owner でログインしても店舗選択ドロップダウンが表示されない
- ページ上部に何も表示されない

**考えられる原因**:

1. **JavaScript エラー**

   - ブラウザのコンソールにエラーが表示されていないか確認
   - `initializeStoreSelector()` が呼ばれているか確認

2. **API 呼び出しの失敗**

   - `GET /api/store/stores` が 403 エラーを返している
   - Owner ロールが正しく設定されていない

3. **DOM 要素の不足**
   - `#store-selector-section` または `#store-selector` が存在しない
   - HTML テンプレートが正しくデプロイされていない

### 問題 2: Manager - 編集が不可能

**症状**:

- Manager でログインしても全フォームが `disabled` 状態
- 保存ボタンが表示されない

**考えられる原因**:

1. **役割判定の失敗**

   - `isManager` フラグが `false` のまま
   - ユーザーロールの取得に失敗している

2. **フォーム要素の設定ミス**
   - `setupFormBehavior()` が呼ばれていない
   - DOM 要素の cloneNode 処理でイベントが失われている

---

## 🔍 デバッグ手順

### ステップ 1: デバッグツールを使用

1. ブラウザで以下にアクセス:

   ```
   http://localhost:8000/store/profile/debug
   ```

2. 自動的に以下の情報が表示されます:

   - 現在のユーザー名
   - 役割（Owner/Manager/Staff）
   - 各役割のフラグ状態

3. テストボタンで順番に確認:
   - **1. ユーザー役割を取得** → 役割が正しく取得できているか
   - **2. 店舗一覧を取得** → Owner 権限で店舗リストが取得できるか
   - **3. 店舗情報を取得** → 店舗プロフィールが取得できるか
   - **4. DOM 要素を確認** → 必要な要素がすべて存在するか

### ステップ 2: ブラウザコンソールを確認

1. ブラウザの開発者ツールを開く（F12）
2. Console タブを選択
3. 以下のログメッセージを確認:

**正常な場合のログ**:

```
User roles: { isOwner: true, isManager: false, isStaff: false }
Initializing store selector for Owner...
Fetching stores list...
Stores response: { stores: [...], total: 3 }
Default store selected: 1
Store selector displayed successfully
Loading store profile... { isOwner: true, isManager: false, isStaff: false, currentStoreId: 1 }
Owner mode: fetching store with ID 1
Fetching store profile from: /store/profile?store_id=1
Store data loaded: { id: 1, name: "店舗A", ... }
Setting up form behavior... { isOwner: true, isManager: false, isStaff: false }
Configuring form for Manager/Owner (editable)
Found inputs: 8
Enabled input: store-name
Enabled input: store-email
...
Save button section displayed
Form submit handler attached
```

**エラーがある場合**:

```
❌ Error loading user roles: ...
❌ Error initializing store selector: ...
❌ Store selector elements not found: ...
```

### ステップ 3: ネットワークタブを確認

1. 開発者ツールの Network タブを開く
2. ページをリロード
3. 以下の API リクエストを確認:

**Owner の場合**:

```
GET /api/auth/me → 200 OK
GET /api/store/stores → 200 OK (店舗一覧取得)
GET /api/store/profile?store_id=1 → 200 OK (店舗情報取得)
```

**Manager の場合**:

```
GET /api/auth/me → 200 OK
GET /api/store/profile → 200 OK (自店舗取得)
```

**エラーがある場合**:

```
GET /api/store/stores → 403 Forbidden (Owner権限がない)
GET /api/store/profile → 400 Bad Request (store_id必須だがない)
```

### ステップ 4: DOM 要素を手動確認

ブラウザコンソールで以下を実行:

```javascript
// 店舗選択セクションの確認
const selectorSection = document.getElementById("store-selector-section");
console.log("Selector section:", selectorSection);
console.log("Display:", selectorSection?.style.display);

// 店舗選択ドロップダウンの確認
const selector = document.getElementById("store-selector");
console.log("Selector:", selector);
console.log("Options:", selector?.options.length);

// フォームの確認
const form = document.getElementById("store-form");
const inputs = form?.querySelectorAll("input, textarea");
console.log("Form inputs:", inputs?.length);
inputs?.forEach((input) => {
  console.log(`${input.id}: disabled=${input.disabled}`);
});

// 保存ボタンの確認
const saveBtn = document.getElementById("save-button-section");
console.log("Save button section:", saveBtn);
console.log("Display:", saveBtn?.style.display);
```

---

## 🔧 修正方法

### 修正 1: Owner - 店舗選択が表示されない

**原因: API 呼び出しの失敗**

1. ユーザーに Owner ロールが設定されているか確認:

```sql
SELECT u.username, r.name as role_name
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE u.username = 'your_owner_username';
```

2. Owner ロールが存在しない場合、追加:

```sql
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u, roles r
WHERE u.username = 'your_owner_username'
AND r.name = 'owner';
```

**原因: HTML テンプレートの問題**

1. `templates/store_profile.html` に以下のセクションがあるか確認:

```html
<!-- Owner専用: 店舗選択ドロップダウン -->
<div
  id="store-selector-section"
  class="store-selector-section"
  style="display: none;"
>
  <div class="store-selector-container">
    <label for="store-selector" class="store-selector-label">
      🏪 表示する店舗を選択:
    </label>
    <select id="store-selector" class="store-selector">
      <option value="">読込中...</option>
    </select>
  </div>
</div>
```

2. ない場合は、`<main class="main">` の直後、`<!-- ローディング表示 -->` の前に追加

**原因: JavaScript の初期化失敗**

ブラウザコンソールで手動実行してテスト:

```javascript
// 役割を確認
const currentUser = await apiClient.getCurrentUser();
console.log(
  "User roles:",
  currentUser.user_roles.map((ur) => ur.role.name)
);

// 店舗一覧を取得
const stores = await apiClient.get("/store/stores");
console.log("Stores:", stores);

// ドロップダウンを手動で表示
const section = document.getElementById("store-selector-section");
section.style.display = "block";
```

### 修正 2: Manager - 編集ができない

**原因: 役割判定の失敗**

ブラウザコンソールで確認:

```javascript
// グローバル変数を確認
console.log({ isOwner, isManager, isStaff });
```

`isManager` が `false` の場合:

```javascript
// ユーザー情報を再取得
const user = await apiClient.getCurrentUser();
const roles = user.user_roles.map((ur) => ur.role.name);
console.log("Roles:", roles);
console.log("Is Manager?", roles.includes("manager"));
```

**原因: フォーム要素が無効化されたまま**

手動で有効化してテスト:

```javascript
const form = document.getElementById("store-form");
const inputs = form.querySelectorAll("input, textarea");
inputs.forEach((input) => {
  input.disabled = false;
  console.log(`Enabled: ${input.id}`);
});

// 保存ボタンを表示
const saveBtn = document.getElementById("save-button-section");
saveBtn.style.display = "flex";
```

**原因: setupFormBehavior の実行タイミング**

JavaScript ファイルの `setupFormBehavior()` 関数内にログが表示されるか確認:

```javascript
console.log("Setting up form behavior...", { isOwner, isManager, isStaff });
```

このログが表示されない場合:

- `loadStoreProfile()` が完了していない
- エラーが発生して関数が呼ばれていない

---

## ✅ 検証チェックリスト

### Owner

- [ ] ブラウザコンソールに `isOwner: true` が表示される
- [ ] `GET /api/store/stores` が 200 OK を返す
- [ ] 店舗選択ドロップダウンが画面上部に表示される
- [ ] ドロップダウンに複数の店舗が表示される
- [ ] ドロップダウンで店舗を変更すると画面が更新される
- [ ] フォームが編集可能（disabled = false）
- [ ] 保存ボタンが表示される
- [ ] 画像アップロードセクションが表示される

### Manager

- [ ] ブラウザコンソールに `isManager: true` が表示される
- [ ] `GET /api/store/profile` が 200 OK を返す
- [ ] 店舗選択ドロップダウンが表示されない
- [ ] 自分の所属店舗の情報が表示される
- [ ] フォームが編集可能（disabled = false）
- [ ] 保存ボタンが表示される
- [ ] 画像アップロードセクションが表示される
- [ ] 保存が正常に動作する

### Staff

- [ ] ブラウザコンソールに `isStaff: true` が表示される
- [ ] `GET /api/store/profile` が 200 OK を返す
- [ ] 店舗選択ドロップダウンが表示されない
- [ ] 自分の所属店舗の情報が表示される
- [ ] すべてのフォームが無効（disabled = true）
- [ ] 保存ボタンが表示されない
- [ ] 画像アップロードセクションが表示されない
- [ ] 読み取り専用メッセージが表示される

---

## 🚀 クイックフィックス

### 問題が解決しない場合の緊急対応

1. **ブラウザキャッシュをクリア**:

   - Ctrl + Shift + Delete (Windows/Linux)
   - Cmd + Shift + Delete (Mac)
   - JavaScript と CSS ファイルをクリア

2. **ハードリロード**:

   - Ctrl + F5 (Windows/Linux)
   - Cmd + Shift + R (Mac)

3. **JavaScript ファイルを直接確認**:

   ```
   http://localhost:8000/static/js/store_profile.js
   ```

   最新のコードが反映されているか確認

4. **CSS ファイルを直接確認**:

   ```
   http://localhost:8000/static/css/store_profile.css
   ```

   店舗選択のスタイルが含まれているか確認

5. **サーバーを再起動**:

   ```bash
   # コンテナを再起動
   docker-compose restart web

   # または完全に再ビルド
   docker-compose down
   docker-compose up --build
   ```

---

## 📞 サポート情報

### ログの収集方法

問題を報告する際は以下の情報を含めてください:

1. **ブラウザコンソールのログ**:

   - F12 → Console タブの全内容をコピー

2. **ネットワークログ**:

   - F12 → Network タブで以下のリクエストのレスポンスをコピー:
     - `GET /api/auth/me`
     - `GET /api/store/stores` (Owner)
     - `GET /api/store/profile`

3. **デバッグツールの結果**:

   - `/store/profile/debug` のスクリーンショット

4. **環境情報**:
   - ブラウザ名とバージョン
   - ユーザー名と役割
   - エラーメッセージ（あれば）

### 既知の問題

1. **古いブラウザ**: IE11 では動作しません（ES6 以降の機能を使用）
2. **キャッシュ**: ブラウザキャッシュが原因で旧バージョンの JS が実行される可能性
3. **権限**: データベース内の役割設定が正しくない可能性

---

## 📝 変更履歴

- 2025-01-XX: 初版作成
- 2025-01-XX: デバッグツール追加
- 2025-01-XX: ログ強化
