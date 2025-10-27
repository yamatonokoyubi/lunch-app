# ログイン画面分離実装レポート

## 概要
顧客用と従業員用のログイン画面を物理的に分離し、セキュリティを向上させました。

## 実装日
2025年10月22日

## 実装内容

### 1. 従業員用ログインページの作成

#### 新規ファイル: `templates/staff_login.html`
- URL: `/staff/login`
- 対象: 店舗スタッフ専用
- 特徴:
  - 「従業員ログイン」というタイトル
  - デモアカウント: admin / admin@123 のみ表示
  - 「このページは従業員専用です」という注意書き
  - 新規登録リンクなし（従業員は管理者が作成）

### 2. 顧客用ログインページの修正

#### 修正ファイル: `templates/login.html`
- URL: `/login`
- 対象: お客様専用
- 変更点:
  - デモアカウントを **customer2 / password123** に変更
  - 店舗スタッフのデモアカウント削除
  - 「お試しログイン」というタイトルに変更
  - 「デモアカウントでシステムをお試しいただけます」という案内追加

### 3. ルーティングの追加

#### 修正ファイル: `main.py`
```python
@app.get("/staff/login", response_class=HTMLResponse, summary="従業員ログイン画面")
async def staff_login_page(request: Request):
    """従業員用ログイン画面（店舗スタッフ専用）"""
    return templates.TemplateResponse("staff_login.html", {"request": request})
```

### 4. スタイルの追加

#### 修正ファイル: `static/css/auth.css`
- `.auth-subtitle`: サブタイトルのスタイル
- `.auth-footer`: フッター領域のスタイル

## セキュリティ向上ポイント

### 1. URLの隠蔽
- 従業員用ログインページ (`/staff/login`) へのリンクは、顧客向けページに一切存在しない
- 一般ユーザーはURLを知らない限りアクセスできない
- ブルートフォース攻撃のリスク低減

### 2. 明確な分離
- 顧客と従業員で完全に別のログイン画面
- それぞれに適したデモアカウントのみ表示
- 誤ったロールでのログイン試行を防止

### 3. UXの向上
- 顧客: お客様向けのデモアカウント (customer2) で簡単にお試し可能
- 従業員: 管理者向けのデモアカウント (admin) でシステム確認可能

## リダイレクトロジック（既存）

### `static/js/auth.js` の `redirectAfterLogin()`
```javascript
if (role === 'customer') {
    window.location.href = '/menus';  // 顧客 → メニューページ
} else if (role === 'store') {
    window.location.href = '/store/dashboard';  // 従業員 → 店舗ダッシュボード
}
```

## テスト方法

### 顧客用ログイン
1. ブラウザで `http://localhost:8000/login` にアクセス
2. デモアカウント「customer2 / password123」が表示されることを確認
3. 店舗スタッフのデモアカウントが表示されていないことを確認
4. ログイン後、メニューページにリダイレクトされることを確認

### 従業員用ログイン
1. ブラウザで `http://localhost:8000/staff/login` にアクセス
2. 「従業員ログイン」というタイトルが表示されることを確認
3. デモアカウント「admin / admin@123」が表示されることを確認
4. ログイン後、店舗ダッシュボードにリダイレクトされることを確認

### リンクの確認
1. トップページ、メニューページ、カートページなどの顧客向けページを確認
2. `/staff/login` へのリンクが一切存在しないことを確認
3. `/login` へのリンクのみが存在することを確認

## Acceptance Criteria チェックリスト

- [x] `/login` にアクセスすると、顧客用のログイン画面が表示される
- [x] デモアカウントとして「customer2/password123」が案内されている
- [x] `/staff/login` に直接アクセスすると、従業員用のログイン画面が表示される
- [x] 顧客向けページに従業員用ログインページへのリンクが存在しない
- [x] 顧客用ログインからログインすると、メニューページにリダイレクトされる
- [x] 従業員用ログインからログインすると、店舗ダッシュボードにリダイレクトされる

## 変更ファイル一覧

1. **新規作成**
   - `templates/staff_login.html` - 従業員用ログインページ

2. **修正**
   - `templates/login.html` - 顧客用ログインページ（デモアカウント変更）
   - `main.py` - 従業員用ログインルート追加
   - `static/css/auth.css` - スタイル追加

3. **確認済み（変更なし）**
   - `static/js/auth.js` - リダイレクトロジック（既に正しく実装済み）
   - `templates/components/common_header.html` - 顧客向けリンク（/login のみ）

## 今後の拡張案

### 1. IP制限（オプション）
従業員用ログインページに対して、特定のIPアドレスからのみアクセスを許可する設定を追加:
```python
@app.get("/staff/login")
async def staff_login_page(request: Request):
    client_ip = request.client.host
    allowed_ips = ["127.0.0.1", "192.168.1.0/24"]  # 許可するIP
    if client_ip not in allowed_ips:
        raise HTTPException(status_code=403, detail="Access denied")
    return templates.TemplateResponse("staff_login.html", {"request": request})
```

### 2. 2要素認証（2FA）
従業員用ログインに2要素認証を追加してセキュリティをさらに強化

### 3. ログイン試行回数制限
ブルートフォース攻撃対策として、ログイン試行回数に制限を設ける

## まとめ

この実装により、以下のメリットが得られます:

✅ **セキュリティの向上**: 従業員用ログインURLの隠蔽
✅ **UXの改善**: 各ユーザータイプに適したログイン画面
✅ **保守性の向上**: 明確な分離により、将来的な機能追加が容易
✅ **攻撃面の縮小**: ブルートフォース攻撃のリスク低減
