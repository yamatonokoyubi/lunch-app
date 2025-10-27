/**
 * 統一メニューページ
 * ログイン/ログアウト状態で動的に表示を切り替え
 * 
 * グローバル変数 currentUser, authToken は common.js で定義済み
 */

// グローバル変数（メニューページ専用）
let selectedStoreId = null;
let allMenus = [];
let allCategories = [];
let currentCategory = 'all';
let isLoggedIn = false;
// currentUser は common.js で定義済み（重複宣言を避ける）

// ========================================
// 初期化
// ========================================

document.addEventListener('DOMContentLoaded', async () => {
    await checkAuthStatus();
    await loadStoreInfo();
    await loadMenus();
    setupEventListeners();
    await updateCartBadge();
});

// ========================================
// 認証状態のチェック
// ========================================

async function checkAuthStatus() {
    const token = localStorage.getItem('authToken');
    console.log('🔐 認証チェック開始:', token ? 'トークンあり' : 'トークンなし');
    
    if (!token) {
        // ログアウト状態
        console.log('👤 ログアウト状態として表示');
        isLoggedIn = false;
        // ヘッダー処理は universal_header.js に委譲
        return;
    }

    try {
        // トークンの有効性を確認
        console.log('🔍 トークンの有効性を確認中...');
        const response = await fetch('/api/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            currentUser = await response.json();
            console.log('✅ ログイン成功:', currentUser);
            isLoggedIn = true;
            // ヘッダー処理は universal_header.js に委譲
        } else {
            // トークンが無効
            console.log('❌ トークンが無効:', response.status);
            localStorage.removeItem('authToken');
            isLoggedIn = false;
            // ヘッダー処理は universal_header.js に委譲
        }
    } catch (error) {
        console.error('❌ 認証チェックエラー:', error);
        isLoggedIn = false;
        // ヘッダー処理は universal_header.js に委譲
    }
}

// ========================================
// ヘッダー表示の更新（universal_header.js に移行）
// ========================================

// 以下の関数は universal_header.js で処理されるため不要
/*
function updateHeaderForUser(user) {
    // universal_header.js に移行
}

function updateHeaderForGuest() {
    // universal_header.js に移行
}
*/

// ========================================
// 店舗情報の読み込み
// ========================================

async function loadStoreInfo() {
    try {
        console.log('🏪 店舗情報を読み込み中...', { isLoggedIn });
        
        // ログイン状態の場合は、ローカルストレージまたはゲストセッションから店舗IDを取得
        const response = await fetch('/api/guest/session', {
            credentials: 'include',
        });

        if (response.ok) {
            const data = await response.json();
            selectedStoreId = data.selected_store_id;
            console.log('✅ ゲストセッションから店舗ID取得:', selectedStoreId);
        } else {
            // ゲストセッションが無い場合（ログイン済みでセッションが削除された場合など）
            // ローカルストレージから取得を試みる
            const storedStoreId = localStorage.getItem('selectedStoreId');
            if (storedStoreId) {
                selectedStoreId = parseInt(storedStoreId);
                console.log('📦 ローカルストレージから店舗ID取得:', selectedStoreId);
            }
        }

        if (!selectedStoreId) {
            // 店舗が選択されていない場合は店舗選択ページへ
            console.log('⚠️ 店舗が未選択のため店舗選択ページへリダイレクト');
            window.location.href = '/stores';
            return;
        }

        // ローカルストレージに保存（次回用）
        localStorage.setItem('selectedStoreId', selectedStoreId.toString());

        // 店舗名を取得して表示
        await displayStoreName(selectedStoreId);
    } catch (error) {
        console.error('❌ 店舗情報の読み込みエラー:', error);
        
        // エラーでも継続（デフォルト店舗を使用）
        const storedStoreId = localStorage.getItem('selectedStoreId');
        if (storedStoreId) {
            selectedStoreId = parseInt(storedStoreId);
            console.log('🔄 エラー発生、ローカルストレージから店舗ID使用:', selectedStoreId);
            await displayStoreName(selectedStoreId);
        } else {
            // 完全に取得できない場合は店舗選択ページへ
            window.location.href = '/stores';
        }
    }
}

async function displayStoreName(storeId) {
    try {
        const response = await fetch(
            `/api/public/stores?is_active=true`,
            {
                credentials: 'include',
            }
        );

        if (!response.ok) {
            throw new Error('店舗一覧の取得に失敗しました');
        }

        const stores = await response.json();
        const store = stores.find((s) => s.id === storeId);

        if (store) {
            document.getElementById('storeName').textContent = store.name;
        } else {
            document.getElementById('storeName').textContent =
                '店舗情報が見つかりません';
        }
    } catch (error) {
        console.error('店舗名の表示エラー:', error);
        document.getElementById('storeName').textContent = '不明な店舗';
    }
}

// ========================================
// メニュー情報の読み込み
// ========================================

async function loadMenus() {
    const loading = document.getElementById('loading');
    const menuGrid = document.getElementById('menuGrid');
    const errorMessage = document.getElementById('errorMessage');

    try {
        console.log('📋 メニュー読み込み開始', { selectedStoreId });
        
        if (!selectedStoreId) {
            console.error('❌ selectedStoreId が設定されていません');
            throw new Error('店舗が選択されていません');
        }

        loading.style.display = 'block';
        errorMessage.style.display = 'none';

        // メニュー一覧を取得
        const apiUrl = `/api/public/stores/${selectedStoreId}/menus?is_available=true`;
        console.log('🔗 API URL:', apiUrl);
        
        const response = await fetch(apiUrl, {
            credentials: 'include',
        });

        console.log('📡 API レスポンス:', response.status, response.statusText);

        if (!response.ok) {
            throw new Error(`メニューの取得に失敗しました (${response.status})`);
        }

        allMenus = await response.json();
        console.log('✅ メニュー取得成功:', allMenus.length, '件');

        // カテゴリ情報を抽出
        extractCategories(allMenus);

        // UIを更新
        renderCategoryFilter();
        renderMenus(allMenus);
    } catch (error) {
        console.error('メニュー読み込みエラー:', error);
        showError(
            'メニューの読み込みに失敗しました。しばらく経ってから再度お試しください。'
        );
    } finally {
        loading.style.display = 'none';
    }
}

function extractCategories(menus) {
    // メニューからユニークなカテゴリを抽出
    const categorySet = new Set();

    menus.forEach((menu) => {
        if (menu.category && menu.category.name) {
            categorySet.add(JSON.stringify({
                id: menu.category.id,
                name: menu.category.name,
            }));
        }
    });

    allCategories = Array.from(categorySet).map((cat) => JSON.parse(cat));

    // カテゴリを名前順でソート
    allCategories.sort((a, b) => a.name.localeCompare(b.name));
}

// ========================================
// カテゴリフィルタのレンダリング
// ========================================

function renderCategoryFilter() {
    const categoryFilter = document.getElementById('categoryFilter');

    // フラグメントで一括生成（ちらつき防止）
    const fragment = document.createDocumentFragment();

    // 「すべて」ボタン
    const allBtn = document.createElement('button');
    allBtn.className = 'category-btn active';
    allBtn.dataset.category = 'all';
    allBtn.textContent = 'すべて';
    allBtn.addEventListener('click', () => filterByCategory('all'));
    fragment.appendChild(allBtn);

    // カテゴリボタンを追加
    allCategories.forEach((category) => {
        const btn = document.createElement('button');
        btn.className = 'category-btn';
        btn.dataset.category = category.id;
        btn.textContent = category.name;
        btn.addEventListener('click', () => filterByCategory(category.id));
        fragment.appendChild(btn);
    });

    // 一度にDOM更新（ちらつき防止）
    categoryFilter.innerHTML = '';
    categoryFilter.appendChild(fragment);
}

// ========================================
// メニューのレンダリング
// ========================================

function renderMenus(menus) {
    console.log('🎨 メニュー表示開始:', menus.length, '件');
    const menuGrid = document.getElementById('menuGrid');
    const emptyState = document.getElementById('emptyState');

    // 販売可能なメニューのみフィルタ
    const availableMenus = menus.filter((menu) => menu.is_available);
    console.log('✅ 販売可能なメニュー:', availableMenus.length, '件');

    if (availableMenus.length === 0) {
        console.log('⚠️ 販売可能なメニューがありません');
        emptyState.style.display = 'block';
        menuGrid.innerHTML = '';
        return;
    }

    emptyState.style.display = 'none';

    // メニューカードを一括で生成（ちらつき防止）
    const fragment = document.createDocumentFragment();
    availableMenus.forEach((menu) => {
        const card = createMenuCard(menu);
        fragment.appendChild(card);
    });

    // 一度にDOM更新（ちらつき防止）
    menuGrid.innerHTML = '';
    menuGrid.appendChild(fragment);
    console.log('✅ メニュー表示完了');
}

function createMenuCard(menu) {
    const card = document.createElement('div');
    card.className = 'menu-card';
    card.dataset.menuId = menu.id;

    // 画像URL
    const imageUrl = menu.image_url || '/static/images/menu-placeholder.jpg';

    // カテゴリバッジ
    const categoryBadge = menu.category
        ? `<span class="menu-badge">${escapeHtml(menu.category.name)}</span>`
        : '';

    card.innerHTML = `
        <img 
            src="${escapeHtml(imageUrl)}" 
            alt="${escapeHtml(menu.name)}" 
            class="menu-image"
            onerror="this.src='/static/img/menu-placeholder.svg'"
        >
        <div class="menu-content">
            <div class="menu-header">
                <h3 class="menu-name">${escapeHtml(menu.name)}</h3>
                ${categoryBadge}
            </div>
            <p class="menu-description">${escapeHtml(
                menu.description || 'おいしいお弁当です'
            )}</p>
            <div class="menu-footer">
                <div class="menu-price">
                    ¥${menu.price.toLocaleString()}
                    <span class="menu-price-unit">税込</span>
                </div>
                <button 
                    class="btn-add-cart" 
                    onclick="addToCart(${menu.id}, '${escapeHtml(menu.name)}')"
                    ${!menu.is_available ? 'disabled' : ''}
                >
                    <span class="cart-icon">🛒</span>
                    カートに追加
                </button>
            </div>
        </div>
    `;

    return card;
}

// ========================================
// カテゴリフィルタ
// ========================================

function filterByCategory(categoryId) {
    currentCategory = categoryId;

    // アクティブボタンを更新（ちらつき防止のため一括更新）
    const buttons = document.querySelectorAll('.category-btn');
    const categoryIdStr = String(categoryId);
    
    // requestAnimationFrameで一度に更新
    requestAnimationFrame(() => {
        buttons.forEach((btn) => {
            if (btn.dataset.category === categoryIdStr) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    });

    // メニューをフィルタ
    let filteredMenus;
    if (categoryId === 'all') {
        filteredMenus = allMenus;
    } else {
        filteredMenus = allMenus.filter(
            (menu) => menu.category && menu.category.id === categoryId
        );
    }

    renderMenus(filteredMenus);
}

// ========================================
// カートに追加
// ========================================

async function addToCart(menuId, menuName) {
    try {
        // ログイン状態に応じてAPIエンドポイントを変更
        const endpoint = isLoggedIn ? '/api/customer/cart/add' : '/api/guest/cart/add';
        const headers = {
            'Content-Type': 'application/json',
        };
        
        // ログイン時は認証トークンを追加
        if (isLoggedIn) {
            const token = localStorage.getItem('authToken');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: headers,
            credentials: 'include',
            body: JSON.stringify({
                menu_id: menuId,
                quantity: 1,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'カートへの追加に失敗しました');
        }

        // 成功メッセージを表示
        showToast(`「${menuName}」をカートに追加しました`);
        
        // カートバッジを更新
        await updateCartBadge();
    } catch (error) {
        console.error('カート追加エラー:', error);
        showToast(`エラー: ${error.message}`, true);
    }
}

// ========================================
// ログアウト処理
// ========================================

// ========================================
// ログアウト処理（universal_header.js に移行）
// ========================================

// ログアウト処理は universal_header.js で実行

// ========================================
// イベントリスナー
// ========================================

function setupEventListeners() {
    // 店舗変更ボタン
    const changeStoreBtn = document.getElementById('changeStoreBtn');
    if (changeStoreBtn) {
        changeStoreBtn.addEventListener('click', () => {
            window.location.href = '/stores';
        });
    }

    // ログアウトボタンは universal_header.js で処理
}

// ========================================
// ユーティリティ関数
// ========================================

function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');

    errorText.textContent = message;
    errorMessage.style.display = 'block';
}

function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');

    toastMessage.textContent = message;

    if (isError) {
        toast.style.background = '#e53e3e';
    } else {
        toast.style.background = '#48bb78';
    }

    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
}
