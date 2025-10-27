"""
ゲストカートUI テスト

UIページのルーティングと基本的な動作を確認
"""

from fastapi.testclient import TestClient


class TestGuestCartUI:
    """ゲストカートUI テストクラス"""

    def test_cart_page_accessible(self, client: TestClient):
        """カートページにアクセスできる"""
        response = client.get("/cart")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # ページタイトルの確認
        content = response.text
        assert "カート" in content
        assert "弁当注文システム" in content

    def test_cart_page_has_header(self, client: TestClient):
        """カートページにヘッダーが含まれる"""
        response = client.get("/cart")

        assert response.status_code == 200
        content = response.text

        # ヘッダーコンポーネントの要素
        assert "guest-header" in content
        assert "cartBadge" in content

    def test_cart_page_has_required_elements(self, client: TestClient):
        """カートページに必要な要素がある"""
        response = client.get("/cart")

        assert response.status_code == 200
        content = response.text

        # 主要要素の確認
        assert "loading" in content  # ローディング表示
        assert "emptyCart" in content  # 空カート表示
        assert "cartContent" in content  # カート内容
        assert "cartItems" in content  # カートアイテム一覧
        assert "checkoutBtn" in content  # 注文ボタン

    def test_cart_page_loads_css(self, client: TestClient):
        """カートページがCSSを読み込む"""
        response = client.get("/cart")

        assert response.status_code == 200
        content = response.text
        assert "/static/css/guest_cart.css" in content

    def test_cart_page_loads_js(self, client: TestClient):
        """カートページがJavaScriptを読み込む"""
        response = client.get("/cart")

        assert response.status_code == 200
        content = response.text
        assert "/static/js/guest_cart.js" in content

    def test_menus_page_has_header(self, client: TestClient):
        """メニューページにヘッダーが含まれる"""
        response = client.get("/menus")

        assert response.status_code == 200
        content = response.text

        # ヘッダーコンポーネント
        assert "guest-header" in content
        assert "cartBadge" in content

    def test_stores_page_has_header(self, client: TestClient):
        """店舗選択ページにヘッダーが含まれる"""
        response = client.get("/stores")

        assert response.status_code == 200
        content = response.text

        # ヘッダーコンポーネント
        assert "guest-header" in content
        assert "cartBadge" in content

    def test_header_has_navigation_links(self, client: TestClient):
        """ヘッダーにナビゲーションリンクがある"""
        response = client.get("/cart")

        assert response.status_code == 200
        content = response.text

        # ナビゲーションリンク
        assert 'href="/stores"' in content
        assert 'href="/menus"' in content
        assert 'href="/cart"' in content

    def test_cart_page_has_back_to_menu_link(self, client: TestClient):
        """カートページにメニューに戻るリンクがある"""
        response = client.get("/cart")

        assert response.status_code == 200
        content = response.text

        # メニューに戻るリンク
        assert 'href="/menus"' in content
        assert "メニュー" in content

    def test_css_file_exists(self, client: TestClient):
        """CSSファイルが存在する"""
        response = client.get("/static/css/guest_cart.css")

        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]

    def test_js_file_exists(self, client: TestClient):
        """JavaScriptファイルが存在する"""
        response = client.get("/static/js/guest_cart.js")

        assert response.status_code == 200
        # JavaScriptのMIMEタイプは複数あるため柔軟にチェック
        content_type = response.headers["content-type"]
        assert "javascript" in content_type or "text/plain" in content_type

    def test_placeholder_image_exists(self, client: TestClient):
        """プレースホルダー画像が存在する"""
        response = client.get("/static/img/menu-placeholder.svg")

        assert response.status_code == 200
        assert "image/svg+xml" in response.headers["content-type"]
