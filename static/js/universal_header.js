// 共通ヘッダーJavaScript - universal_header.js

class UniversalHeader {
    constructor() {
        this.hamburgerBtn = document.getElementById('hamburgerBtn');
        this.headerNav = document.getElementById('headerNav');
        this.mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
        this.userMenuTrigger = document.getElementById('userMenuTrigger');
        this.userDropdown = document.getElementById('userDropdown');
        this.logoutBtn = document.getElementById('logoutBtn');
        this.authButtons = document.getElementById('authButtons');
        this.userMenuWrapper = document.getElementById('userMenuWrapper');
        this.cartBadge = document.getElementById('cartBadge');

        this.isLoggedIn = false;
        this.currentUser = null;
        this.currentPage = this.detectCurrentPage();

        this.initialize();
    }

    initialize() {
        this.setupEventListeners();
        this.checkAuthStatus();
        this.setActivePage();
        this.updateCartBadge();
    }

    /**
     * イベントリスナーの設定
     */
    setupEventListeners() {
        // ハンバーガーメニュー
        if (this.hamburgerBtn) {
            this.hamburgerBtn.addEventListener('click', () => this.toggleMobileMenu());
        }

        // モバイルメニューオーバーレイ
        if (this.mobileMenuOverlay) {
            this.mobileMenuOverlay.addEventListener('click', () => this.closeMobileMenu());
        }

        // ユーザーメニュートリガー
        if (this.userMenuTrigger) {
            this.userMenuTrigger.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleUserMenu();
            });
        }

        // ログアウトボタン
        if (this.logoutBtn) {
            this.logoutBtn.addEventListener('click', () => this.handleLogout());
        }

        // ドキュメントクリックでメニューを閉じる
        document.addEventListener('click', (e) => {
            if (!this.userMenuWrapper?.contains(e.target)) {
                this.closeUserMenu();
            }
        });

        // ESCキーでメニューを閉じる
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeMobileMenu();
                this.closeUserMenu();
            }
        });

        // ウィンドウリサイズ時にモバイルメニューを閉じる
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                this.closeMobileMenu();
            }
        });
    }

    /**
     * 現在のページを検出
     */
    detectCurrentPage() {
        const path = window.location.pathname;
        
        if (path === '/' || path === '/stores') return 'stores';
        if (path.startsWith('/menus')) return 'menus';
        if (path.startsWith('/cart')) return 'cart';
        if (path.startsWith('/login')) return 'login';
        if (path.startsWith('/register')) return 'register';
        if (path.startsWith('/customer/orders')) return 'orders';
        if (path.startsWith('/customer/account')) return 'account';
        if (path.startsWith('/checkout')) return 'checkout';
        
        return 'other';
    }

    /**
     * アクティブページの設定
     */
    setActivePage() {
        // bodyにページクラスを追加
        document.body.classList.add(`page-${this.currentPage}`);

        // ナビゲーションリンクのアクティブ状態
        const navLinks = document.querySelectorAll('.nav-link[data-page]');
        navLinks.forEach(link => {
            const linkPage = link.getAttribute('data-page');
            if (linkPage === this.currentPage) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });

        // ドロップダウンアイテムのアクティブ状態
        const dropdownItems = document.querySelectorAll('.dropdown-item[data-page]');
        dropdownItems.forEach(item => {
            const itemPage = item.getAttribute('data-page');
            if (itemPage === this.currentPage) {
                item.style.fontWeight = '600';
                item.style.color = '#667eea';
            }
        });

        // ページ別のナビゲーション表示制御
        this.controlNavigationVisibility();
    }

    /**
     * ページ別のナビゲーション表示制御
     */
    controlNavigationVisibility() {
        const storesLink = document.querySelector('[data-page="stores"]');
        const menusLink = document.querySelector('[data-page="menus"]');
        const cartLink = document.querySelector('[data-page="cart"]');
        const loginBtn = document.querySelector('.btn-login[data-page="login"]');
        const registerBtn = document.querySelector('.btn-register[data-page="register"]');

        // デフォルトは全て表示
        [storesLink, menusLink, cartLink, loginBtn, registerBtn].forEach(el => {
            if (el) el.style.display = '';
        });

        switch (this.currentPage) {
            case 'stores':
                // 店舗選択ページ: メニュー・カート非表示
                if (menusLink) menusLink.style.display = 'none';
                if (cartLink) cartLink.style.display = 'none';
                break;
            
            case 'login':
                // ログインページ: ログインボタン非表示
                if (loginBtn) loginBtn.style.display = 'none';
                break;
            
            case 'register':
                // 新規登録ページ: 新規登録ボタン非表示
                if (registerBtn) registerBtn.style.display = 'none';
                break;
            
            case 'checkout':
                // 注文確認ページ: ヘッダー全体を非表示（CSSで制御）
                break;
        }
    }

    /**
     * 認証状態の確認
     */
    async checkAuthStatus() {
        const token = localStorage.getItem('authToken');
        
        if (!token) {
            this.updateHeaderForGuest();
            return;
        }

        try {
            // Auth クラスが存在する場合
            if (typeof Auth !== 'undefined' && Auth.getUser) {
                this.currentUser = Auth.getUser();
                if (this.currentUser) {
                    this.isLoggedIn = true;
                    this.updateHeaderForUser(this.currentUser);
                    return;
                }
            }

            // API経由で認証確認
            const response = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                this.currentUser = await response.json();
                this.isLoggedIn = true;
                this.updateHeaderForUser(this.currentUser);
            } else {
                localStorage.removeItem('authToken');
                this.updateHeaderForGuest();
            }
        } catch (error) {
            console.error('認証チェックエラー:', error);
            this.updateHeaderForGuest();
        }
    }

    /**
     * ログインユーザー用のヘッダー表示
     */
    updateHeaderForUser(user) {
        if (this.authButtons) {
            this.authButtons.style.display = 'none';
        }
        if (this.userMenuWrapper) {
            this.userMenuWrapper.style.display = 'flex';
        }

        // ユーザー名表示
        const userNameEl = document.getElementById('userName');
        if (userNameEl && user) {
            const displayName = user.full_name || user.name || user.username || 'ゲスト';
            userNameEl.textContent = `${displayName}さん`;
        }
    }

    /**
     * ゲスト用のヘッダー表示
     */
    updateHeaderForGuest() {
        if (this.authButtons) {
            this.authButtons.style.display = 'flex';
        }
        if (this.userMenuWrapper) {
            this.userMenuWrapper.style.display = 'none';
        }
    }

    /**
     * カートバッジの更新
     */
    async updateCartBadge() {
        try {
            // cart_badge.js が存在する場合はそれを使用
            if (typeof window.updateCartBadge === 'function') {
                window.updateCartBadge();
                return;
            }

            // ローカルストレージからカート情報を取得
            const guestCart = JSON.parse(localStorage.getItem('guestCart') || '[]');
            const totalQuantity = guestCart.reduce((sum, item) => sum + item.quantity, 0);

            if (this.cartBadge) {
                if (totalQuantity > 0) {
                    this.cartBadge.textContent = totalQuantity;
                    this.cartBadge.style.display = 'block';
                } else {
                    this.cartBadge.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('カートバッジ更新エラー:', error);
        }
    }

    /**
     * モバイルメニューの開閉
     */
    toggleMobileMenu() {
        if (this.headerNav) {
            this.headerNav.classList.toggle('active');
        }
        if (this.hamburgerBtn) {
            this.hamburgerBtn.classList.toggle('active');
        }
        if (this.mobileMenuOverlay) {
            this.mobileMenuOverlay.classList.toggle('active');
        }
        
        // ボディのスクロールを制御
        document.body.style.overflow = this.headerNav?.classList.contains('active') ? 'hidden' : '';
    }

    /**
     * モバイルメニューを閉じる
     */
    closeMobileMenu() {
        if (this.headerNav) {
            this.headerNav.classList.remove('active');
        }
        if (this.hamburgerBtn) {
            this.hamburgerBtn.classList.remove('active');
        }
        if (this.mobileMenuOverlay) {
            this.mobileMenuOverlay.classList.remove('active');
        }
        document.body.style.overflow = '';
    }

    /**
     * ユーザーメニューの開閉
     */
    toggleUserMenu() {
        if (this.userDropdown) {
            this.userDropdown.classList.toggle('active');
        }
        if (this.userMenuTrigger) {
            this.userMenuTrigger.classList.toggle('active');
        }
    }

    /**
     * ユーザーメニューを閉じる
     */
    closeUserMenu() {
        if (this.userDropdown) {
            this.userDropdown.classList.remove('active');
        }
        if (this.userMenuTrigger) {
            this.userMenuTrigger.classList.remove('active');
        }
    }

    /**
     * ログアウト処理
     */
    async handleLogout() {
        try {
            // Auth クラスが存在する場合
            if (typeof Auth !== 'undefined' && Auth.logout) {
                Auth.logout();
                return;
            }

            // API経由でログアウト
            await fetch('/api/logout', {
                method: 'POST',
                credentials: 'include'
            });

            // ローカルストレージをクリア
            localStorage.removeItem('authToken');
            localStorage.removeItem('currentUser');

            // ユーザーの役割に応じてリダイレクト
            const user = this.currentUser;
            const isStaff = user && user.role === 'store';
            window.location.href = isStaff ? '/staff/login' : '/';
        } catch (error) {
            console.error('ログアウトエラー:', error);
            window.location.href = '/';
        }
    }
}

// ページロード時に初期化
document.addEventListener('DOMContentLoaded', () => {
    window.universalHeader = new UniversalHeader();
});

// カートバッジ更新用のグローバル関数
window.refreshHeaderCartBadge = () => {
    if (window.universalHeader) {
        window.universalHeader.updateCartBadge();
    }
};
