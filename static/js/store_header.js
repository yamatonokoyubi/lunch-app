/**
 * 店舗共通ヘッダー用JavaScript
 * 店舗名、ユーザー情報、通知バッジの動的表示を制御
 */

class StoreHeaderManager {
    constructor() {
        this.storeNameElement = document.getElementById('storeName');
        this.userNameElement = document.getElementById('userName');
        this.userRoleElement = document.getElementById('userRole');
        this.notificationBadge = document.getElementById('notificationBadge');
        
        this.init();
    }

    async init() {
        await this.loadUserInfo();
        await this.loadStoreInfo();
        this.setupNotifications();
        this.updateActiveNavigation();
    }

    /**
     * ユーザー情報を取得して表示
     */
    async loadUserInfo() {
        try {
            const response = await fetch('/api/user/profile');
            if (response.ok) {
                const userData = await response.json();
                this.updateUserInfo(userData);
            }
        } catch (error) {
            console.warn('ユーザー情報の取得に失敗しました:', error);
            this.setDefaultUserInfo();
        }
    }

    /**
     * 店舗情報を取得して表示
     */
    async loadStoreInfo() {
        try {
            const response = await fetch('/api/store/current');
            if (response.ok) {
                const storeData = await response.json();
                this.updateStoreInfo(storeData);
            }
        } catch (error) {
            console.warn('店舗情報の取得に失敗しました:', error);
            this.setDefaultStoreInfo();
        }
    }

    /**
     * ユーザー情報を画面に反映
     */
    updateUserInfo(userData) {
        if (this.userNameElement) {
            this.userNameElement.textContent = userData.username || 'ユーザー';
        }
        
        if (this.userRoleElement) {
            const roleLabels = {
                'owner': 'オーナー',
                'manager': '店長',
                'staff': 'スタッフ'
            };
            this.userRoleElement.textContent = roleLabels[userData.role] || userData.role || '-';
        }
    }

    /**
     * 店舗情報を画面に反映
     */
    updateStoreInfo(storeData) {
        if (this.storeNameElement) {
            this.storeNameElement.textContent = storeData.name || '店舗未設定';
        }
    }

    /**
     * デフォルトのユーザー情報を設定
     */
    setDefaultUserInfo() {
        if (this.userNameElement) {
            this.userNameElement.textContent = 'ユーザー';
        }
        if (this.userRoleElement) {
            this.userRoleElement.textContent = '-';
        }
    }

    /**
     * デフォルトの店舗情報を設定
     */
    setDefaultStoreInfo() {
        if (this.storeNameElement) {
            this.storeNameElement.textContent = '店舗未設定';
        }
    }

    /**
     * 通知システムの設定
     */
    setupNotifications() {
        this.updateNotificationCount();
        
        // 定期的に通知数を更新 (30秒間隔)
        setInterval(() => {
            this.updateNotificationCount();
        }, 30000);
    }

    /**
     * 通知数を取得して表示
     */
    async updateNotificationCount() {
        try {
            const response = await fetch('/api/notifications/count');
            if (response.ok) {
                const data = await response.json();
                this.displayNotificationBadge(data.count || 0);
            }
        } catch (error) {
            console.warn('通知数の取得に失敗しました:', error);
        }
    }

    /**
     * 通知バッジの表示制御
     */
    displayNotificationBadge(count) {
        if (this.notificationBadge) {
            if (count > 0) {
                this.notificationBadge.textContent = count > 99 ? '99+' : count.toString();
                this.notificationBadge.style.display = 'block';
            } else {
                this.notificationBadge.style.display = 'none';
            }
        }
    }

    /**
     * 現在のページに基づいてナビゲーションの active クラスを更新
     */
    updateActiveNavigation() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            
            // URLパスとナビゲーションリンクをマッチング
            const href = link.getAttribute('href');
            if (href && currentPath.includes(href)) {
                link.classList.add('active');
            }
        });
    }
}

// UIオブジェクト（後方互換性のため）
// common.jsで既に定義されている場合は拡張、なければ新規作成
window.UI = window.UI || {};
window.UI.initializeStoreHeader = async function() {
    // 店舗管理ページでのみ初期化
    if (document.querySelector('.header')) {
        return new StoreHeaderManager();
    }
    return null;
};

// DOM読み込み完了後に初期化
document.addEventListener('DOMContentLoaded', () => {
    // 店舗管理ページでのみ初期化
    if (document.querySelector('.header')) {
        new StoreHeaderManager();
    }
});

// エラーハンドリング
window.addEventListener('error', (event) => {
    console.warn('Store header error:', event.error);
});

// グローバルに公開（他のスクリプトから使用可能）
// window.UI は既に上で定義済み
window.StoreHeaderManager = StoreHeaderManager;