/**
 * 共通ヘッダー初期化スクリプト
 * 全ページで使用可能
 */

(function() {
    'use strict';

    let isLoggedIn = false;

    // ページ読み込み時に実行
    document.addEventListener('DOMContentLoaded', async () => {
        await initializeHeader();
    });

    async function initializeHeader() {
        await checkAuthStatus();
        updateHeaderDisplay();
        setActiveNavLink();
        setupEventListeners();
        
        // カートバッジを更新（window.updateCartBadge が利用可能な場合）
        if (window.updateCartBadge) {
            await window.updateCartBadge();
        }
    }

    async function checkAuthStatus() {
        const token = localStorage.getItem('authToken');
        
        if (!token) {
            isLoggedIn = false;
            return;
        }

        try {
            const response = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const user = await response.json();
                isLoggedIn = true;
                displayUserInfo(user);
                console.log('✅ ログイン状態:', user.username);
            } else {
                isLoggedIn = false;
                localStorage.removeItem('authToken');
            }
        } catch (error) {
            console.error('認証チェックエラー:', error);
            isLoggedIn = false;
        }
    }

    function updateHeaderDisplay() {
        const userSection = document.getElementById('userSection');
        const authSection = document.getElementById('authSection');
        const ordersLink = document.getElementById('ordersLink');

        if (isLoggedIn) {
            if (userSection) userSection.style.display = 'flex';
            if (authSection) authSection.style.display = 'none';
            if (ordersLink) ordersLink.style.display = 'flex';
        } else {
            if (userSection) userSection.style.display = 'none';
            if (authSection) authSection.style.display = 'flex';
            if (ordersLink) ordersLink.style.display = 'none';
        }
    }

    function displayUserInfo(user) {
        const userNameEl = document.getElementById('userName');
        if (userNameEl && user) {
            userNameEl.textContent = user.full_name || user.username || 'ユーザー';
        }
    }

    function setActiveNavLink() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            
            const href = link.getAttribute('href');
            if (href === currentPath) {
                link.classList.add('active');
            } else if (currentPath.startsWith('/stores') && href === '/stores') {
                link.classList.add('active');
            } else if (currentPath.startsWith('/menus') && href === '/menus') {
                link.classList.add('active');
            } else if (currentPath.startsWith('/cart') && href === '/cart') {
                link.classList.add('active');
            } else if (currentPath.startsWith('/customer/orders') && href === '/customer/orders') {
                link.classList.add('active');
            }
        });
    }

    function setupEventListeners() {
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', handleLogout);
        }
    }

    async function handleLogout() {
        try {
            localStorage.removeItem('authToken');
            
            await fetch('/api/logout', {
                method: 'POST',
                credentials: 'include'
            });
            
            console.log('✅ ログアウト成功');
            window.location.href = '/';
        } catch (error) {
            console.error('ログアウトエラー:', error);
            window.location.href = '/';
        }
    }

    // グローバルに公開（他のスクリプトから参照可能）
    window.commonHeaderInitialized = true;
    window.isLoggedIn = () => isLoggedIn;
})();
