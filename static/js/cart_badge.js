/**
 * カートバッジ共通ユーティリティ
 * 全ページで使用可能なカートバッジ更新関数
 */

// ========================================
// カートバッジの更新
// ========================================

async function updateCartBadge() {
    try {
        // 認証状態を毎回チェック（他のページから呼ばれる可能性があるため）
        const token = localStorage.getItem('authToken');
        let currentIsLoggedIn = false;
        
        if (token) {
            try {
                const authResponse = await fetch('/api/auth/me', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                currentIsLoggedIn = authResponse.ok;
            } catch (error) {
                console.error('認証チェックエラー:', error);
            }
        }

        const endpoint = currentIsLoggedIn ? '/api/customer/cart' : '/api/guest/cart';
        const headers = {};
        
        if (currentIsLoggedIn) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(endpoint, {
            headers: headers,
            credentials: 'include',
        });

        if (!response.ok) {
            throw new Error('カート情報の取得に失敗しました');
        }

        const cart = await response.json();
        const cartBadge = document.getElementById('cartBadge');

        if (!cartBadge) {
            console.warn('カートバッジ要素が見つかりません');
            return;
        }

        if (cart.items && cart.items.length > 0) {
            const totalItems = cart.items.reduce((sum, item) => sum + item.quantity, 0);
            cartBadge.textContent = totalItems;
            cartBadge.style.display = 'block';
        } else {
            cartBadge.style.display = 'none';
        }
    } catch (error) {
        console.error('カートバッジ更新エラー:', error);
    }
}

// グローバルに公開（他のスクリプトから呼び出せるように）
window.updateCartBadge = updateCartBadge;
