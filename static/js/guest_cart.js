/**
 * ゲストカートページ JavaScript
 * カート内容の表示、数量変更、削除機能
 */

// グローバル変数
let cartData = null;
let isLoggedIn = false;

// ========================================
// 初期化
// ========================================

document.addEventListener('DOMContentLoaded', async () => {
    await checkAuthStatus();
    await loadCart();
    setupEventListeners();
    
    // カートバッジを更新（他のスクリプトの関数を使用）
    if (window.updateCartBadge) {
        await window.updateCartBadge();
    }
});

// ========================================
// 認証状態のチェック
// ========================================

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
            isLoggedIn = true;
            console.log('✅ ログイン状態でカートを表示');
        } else {
            isLoggedIn = false;
            localStorage.removeItem('authToken');
        }
    } catch (error) {
        console.error('認証チェックエラー:', error);
        isLoggedIn = false;
    }
}

// ========================================
// カートデータの読み込み
// ========================================

async function loadCart() {
    const loading = document.getElementById('loading');
    const errorMessage = document.getElementById('errorMessage');
    const emptyCart = document.getElementById('emptyCart');
    const cartContent = document.getElementById('cartContent');

    try {
        loading.style.display = 'block';
        errorMessage.style.display = 'none';
        emptyCart.style.display = 'none';
        cartContent.style.display = 'none';

        // ログイン状態に応じてAPIエンドポイントを変更
        const endpoint = isLoggedIn ? '/api/customer/cart' : '/api/guest/cart';
        const headers = {};
        
        if (isLoggedIn) {
            const token = localStorage.getItem('authToken');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }

        // カートデータを取得
        const response = await fetch(endpoint, {
            headers: headers,
            credentials: 'include',
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('セッションが無効です。店舗選択からやり直してください。');
            }
            throw new Error('カートの取得に失敗しました');
        }

        cartData = await response.json();

        // カートが空の場合
        if (!cartData.items || cartData.items.length === 0) {
            emptyCart.style.display = 'block';
            return;
        }

        // カート内容を表示
        displayCart(cartData);
        cartContent.style.display = 'block';

    } catch (error) {
        console.error('カート読み込みエラー:', error);
        showError(error.message);
    } finally {
        loading.style.display = 'none';
    }
}

// ========================================
// カート表示
// ========================================

function displayCart(data) {
    // 店舗情報を表示
    displayStoreInfo(data);

    // カートアイテムを表示
    renderCartItems(data.items);

    // 合計金額を表示
    updateSummary(data);
}

function displayStoreInfo(data) {
    const storeNameEl = document.getElementById('storeName');
    if (data.store && data.store.name) {
        storeNameEl.textContent = data.store.name;
    } else {
        storeNameEl.textContent = '店舗情報なし';
    }
}

function renderCartItems(items) {
    const cartItemsEl = document.getElementById('cartItems');
    
    // DocumentFragment で一括生成（ちらつき防止）
    const fragment = document.createDocumentFragment();

    items.forEach((item) => {
        const itemCard = createCartItemCard(item);
        fragment.appendChild(itemCard);
    });

    // 一度にDOM更新
    cartItemsEl.innerHTML = '';
    cartItemsEl.appendChild(fragment);
}

function createCartItemCard(item) {
    const card = document.createElement('div');
    card.className = 'cart-item';
    card.dataset.itemId = item.id;

    // データ構造の正規化（ゲストカートとユーザーカートで構造が異なる）
    let menuName, menuPrice, imageUrl, subtotal;
    
    if (item.menu) {
        // ゲストカートの場合: ネスト構造
        menuName = item.menu.name;
        menuPrice = item.menu.price;
        imageUrl = item.menu.image_url || '/static/img/menu-placeholder.svg';
        subtotal = item.menu.price * item.quantity;
    } else {
        // ユーザーカートの場合: フラット構造
        menuName = item.menu_name;
        menuPrice = item.menu_price;
        imageUrl = item.menu_image_url || '/static/img/menu-placeholder.svg';
        subtotal = item.subtotal || (item.menu_price * item.quantity);
    }

    card.innerHTML = `
        <img 
            src="${escapeHtml(imageUrl)}" 
            alt="${escapeHtml(menuName)}" 
            class="item-image"
            onerror="this.src='/static/img/menu-placeholder.svg'"
        >
        <div class="item-details">
            <div class="item-name">${escapeHtml(menuName)}</div>
            <div class="item-price">¥${menuPrice.toLocaleString()}</div>
            <div class="item-controls">
                <div class="quantity-controls">
                    <button 
                        class="btn-quantity btn-decrease" 
                        data-item-id="${item.id}"
                        ${item.quantity <= 1 ? 'disabled' : ''}
                    >
                        −
                    </button>
                    <span class="quantity-value">${item.quantity}</span>
                    <button 
                        class="btn-quantity btn-increase" 
                        data-item-id="${item.id}"
                    >
                        ＋
                    </button>
                </div>
                <button 
                    class="btn-remove" 
                    data-item-id="${item.id}"
                >
                    削除
                </button>
            </div>
        </div>
        <div class="item-subtotal">
            <span class="item-subtotal-label">小計</span>
            <span class="item-subtotal-value">¥${subtotal.toLocaleString()}</span>
        </div>
    `;

    return card;
}

function updateSummary(data) {
    const subtotalEl = document.getElementById('subtotal');
    const totalEl = document.getElementById('total');

    const subtotal = data.items.reduce((sum, item) => {
        // データ構造の正規化（ゲストカートとユーザーカートで構造が異なる）
        if (item.menu) {
            // ゲストカートの場合: ネスト構造
            return sum + item.menu.price * item.quantity;
        } else {
            // ユーザーカートの場合: フラット構造
            return sum + (item.subtotal || (item.menu_price * item.quantity));
        }
    }, 0);

    subtotalEl.textContent = `¥${subtotal.toLocaleString()}`;
    totalEl.textContent = `¥${subtotal.toLocaleString()}`;
}

// ========================================
// カートアイテム操作
// ========================================

async function updateItemQuantity(itemId, newQuantity) {
    try {
        // ログイン状態に応じてAPIエンドポイントを変更
        const endpoint = isLoggedIn 
            ? `/api/customer/cart/${itemId}?quantity=${newQuantity}`
            : `/api/guest/cart/item/${itemId}`;
        
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (isLoggedIn) {
            const token = localStorage.getItem('authToken');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }
        
        const response = await fetch(endpoint, {
            method: 'PUT',
            headers: headers,
            credentials: 'include',
            body: JSON.stringify({ quantity: newQuantity }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '数量の更新に失敗しました');
        }

        // カートを再読み込み
        await loadCart();
        
        // カートバッジを更新
        if (window.updateCartBadge) {
            await window.updateCartBadge();
        }

        showToast('数量を更新しました', false);
    } catch (error) {
        console.error('数量更新エラー:', error);
        showToast(`エラー: ${error.message}`, true);
    }
}

async function removeItem(itemId) {
    if (!confirm('この商品をカートから削除しますか？')) {
        return;
    }

    try {
        // ログイン状態に応じてAPIエンドポイントを変更
        const endpoint = isLoggedIn 
            ? `/api/customer/cart/${itemId}`
            : `/api/guest/cart/item/${itemId}`;
        
        const headers = {};
        
        if (isLoggedIn) {
            const token = localStorage.getItem('authToken');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }
        
        const response = await fetch(endpoint, {
            method: 'DELETE',
            headers: headers,
            credentials: 'include',
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '削除に失敗しました');
        }

        // カートを再読み込み
        await loadCart();
        
        // カートバッジを更新
        if (window.updateCartBadge) {
            await window.updateCartBadge();
        }

        showToast('商品を削除しました', false);
    } catch (error) {
        console.error('削除エラー:', error);
        showToast(`エラー: ${error.message}`, true);
    }
}

// ========================================
// イベントリスナー
// ========================================

function setupEventListeners() {
    // イベント委譲で動的に生成されたボタンにも対応
    const cartItemsEl = document.getElementById('cartItems');

    if (cartItemsEl) {
        cartItemsEl.addEventListener('click', async (e) => {
            const target = e.target;

            // 数量減少ボタン
            if (target.classList.contains('btn-decrease')) {
                const itemId = parseInt(target.dataset.itemId);
                const item = cartData.items.find((i) => i.id === itemId);
                if (item && item.quantity > 1) {
                    await updateItemQuantity(itemId, item.quantity - 1);
                }
            }

            // 数量増加ボタン
            if (target.classList.contains('btn-increase')) {
                const itemId = parseInt(target.dataset.itemId);
                const item = cartData.items.find((i) => i.id === itemId);
                if (item) {
                    await updateItemQuantity(itemId, item.quantity + 1);
                }
            }

            // 削除ボタン
            if (target.classList.contains('btn-remove')) {
                const itemId = parseInt(target.dataset.itemId);
                await removeItem(itemId);
            }
        });
    }

    // 注文手続きボタン
    const checkoutBtn = document.getElementById('checkoutBtn');
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', () => {
            // ログイン状態に応じて遷移先を変更
            if (isLoggedIn) {
                // ログイン済み → 直接注文確認画面へ
                console.log('✅ ログイン済み: 注文確認画面へ遷移');
                window.location.href = '/checkout/confirm';
            } else {
                // 未ログイン → 認証選択ページへ
                console.log('🚪 未ログイン: 認証選択画面へ遷移');
                window.location.href = '/auth/choice';
            }
        });
    }
}

// ========================================
// ユーティリティ関数
// ========================================

function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');

    if (errorMessage && errorText) {
        errorText.textContent = message;
        errorMessage.style.display = 'block';
    }
}

function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className = 'toast show';
    
    if (isError) {
        toast.classList.add('error');
    } else {
        toast.classList.add('success');
    }

    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
