/**
 * 店舗選択画面のJavaScript
 * 
 * 機能:
 * - 店舗一覧の取得と表示
 * - 検索・フィルタリング
 * - 店舗選択とセッション保存
 */

let allStores = []; // すべての店舗データをキャッシュ

/**
 * ページ読み込み時の初期化
 */
document.addEventListener('DOMContentLoaded', () => {
    loadStores();
    
    // Enterキーで検索
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchStores();
        }
    });
});

/**
 * 店舗一覧を取得
 */
async function loadStores() {
    showLoading(true);
    hideError();
    
    try {
        const response = await fetch('/api/public/stores?is_active=true');
        
        if (!response.ok) {
            throw new Error(`HTTPエラー: ${response.status}`);
        }
        
        allStores = await response.json();
        displayStores(allStores);
        
    } catch (error) {
        console.error('店舗読み込みエラー:', error);
        showError('店舗情報の読み込みに失敗しました。インターネット接続を確認してください。');
    } finally {
        showLoading(false);
    }
}

/**
 * 検索を実行
 */
async function searchStores() {
    const searchTerm = document.getElementById('searchInput').value.trim();
    const activeOnly = document.getElementById('activeOnlyFilter').checked;
    
    showLoading(true);
    hideError();
    
    try {
        // APIパラメータ構築
        const params = new URLSearchParams();
        if (searchTerm) {
            params.append('search', searchTerm);
        }
        params.append('is_active', activeOnly);
        
        const response = await fetch(`/api/public/stores?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTPエラー: ${response.status}`);
        }
        
        const stores = await response.json();
        displayStores(stores);
        
    } catch (error) {
        console.error('検索エラー:', error);
        showError('検索中にエラーが発生しました。');
    } finally {
        showLoading(false);
    }
}

/**
 * 店舗一覧を表示
 * @param {Array} stores - 店舗データの配列
 */
function displayStores(stores) {
    const container = document.getElementById('storesContainer');
    const noResults = document.getElementById('noResultsMessage');
    
    container.innerHTML = '';
    
    if (stores.length === 0) {
        container.style.display = 'none';
        noResults.style.display = 'block';
        return;
    }
    
    container.style.display = 'grid';
    noResults.style.display = 'none';
    
    stores.forEach(store => {
        const card = createStoreCard(store);
        container.appendChild(card);
    });
}

/**
 * 店舗カードを作成
 * @param {Object} store - 店舗データ
 * @returns {HTMLElement} 店舗カードのDOM要素
 */
function createStoreCard(store) {
    const card = document.createElement('div');
    card.className = 'store-card';
    
    // 営業時間のフォーマット
    const openingTime = formatTime(store.opening_time);
    const closingTime = formatTime(store.closing_time);
    
    // 現在営業中かチェック
    const isOpen = checkIfOpen(store.opening_time, store.closing_time);
    const statusClass = store.is_active && isOpen ? 'status-active' : 'status-closed';
    const statusText = store.is_active && isOpen ? '営業中' : '営業時間外';
    
    card.innerHTML = `
        ${store.image_url 
            ? `<img src="${store.image_url}" alt="${store.name}" class="store-image">` 
            : '<div class="store-image"></div>'
        }
        <div class="store-content">
            <div class="store-header">
                <div>
                    <h2 class="store-name">${escapeHtml(store.name)}</h2>
                </div>
                <span class="store-status ${statusClass}">${statusText}</span>
            </div>
            
            <div class="store-info">
                <div class="store-info-item">
                    <span class="icon">📍</span>
                    <span>${escapeHtml(store.address)}</span>
                </div>
                <div class="store-info-item">
                    <span class="icon">📞</span>
                    <span>${escapeHtml(store.phone_number)}</span>
                </div>
                <div class="store-info-item">
                    <span class="icon">📧</span>
                    <span>${escapeHtml(store.email)}</span>
                </div>
            </div>
            
            ${store.description ? `
                <p class="store-description">${escapeHtml(store.description)}</p>
            ` : ''}
            
            <p class="store-hours">
                🕒 営業時間: ${openingTime} 〜 ${closingTime}
            </p>
            
            <button 
                class="select-button" 
                onclick="selectStore(${store.id}, '${escapeHtml(store.name)}')"
                ${!store.is_active ? 'disabled' : ''}
            >
                ${store.is_active ? 'この店舗で注文 🍱' : '営業時間外'}
            </button>
        </div>
    `;
    
    return card;
}

/**
 * 店舗を選択してセッションに保存
 * @param {number} storeId - 店舗ID
 * @param {string} storeName - 店舗名
 */
async function selectStore(storeId, storeName) {
    try {
        // まずゲストセッションを作成
        let sessionResponse = await fetch('/api/guest/session', {
            method: 'POST',
            credentials: 'include' // Cookieを送受信
        });
        
        if (!sessionResponse.ok) {
            throw new Error('セッションの作成に失敗しました');
        }
        
        // 店舗選択をセッションに保存
        const response = await fetch('/api/guest/session/store', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include', // Cookieを送受信
            body: JSON.stringify({
                store_id: storeId
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '店舗の選択に失敗しました');
        }
        
        // ローカルストレージにも保存（ログイン状態でも使用可能に）
        localStorage.setItem('selectedStoreId', storeId.toString());
        
        // 成功メッセージを表示（オプション）
        console.log(`店舗「${storeName}」を選択しました`);
        
        // メニュー一覧ページにリダイレクト
        window.location.href = '/menus';
        
    } catch (error) {
        console.error('店舗選択エラー:', error);
        alert(`店舗の選択に失敗しました: ${error.message}`);
    }
}

/**
 * 時刻をフォーマット
 * @param {string} time - "HH:MM:SS" 形式の時刻
 * @returns {string} "HH:MM" 形式の時刻
 */
function formatTime(time) {
    if (!time) return '--:--';
    return time.substring(0, 5); // "HH:MM:SS" -> "HH:MM"
}

/**
 * 現在営業中かチェック
 * @param {string} openingTime - 開店時刻
 * @param {string} closingTime - 閉店時刻
 * @returns {boolean} 営業中ならtrue
 */
function checkIfOpen(openingTime, closingTime) {
    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    
    const [openHour, openMin] = openingTime.split(':').map(Number);
    const openMinutes = openHour * 60 + openMin;
    
    const [closeHour, closeMin] = closingTime.split(':').map(Number);
    const closeMinutes = closeHour * 60 + closeMin;
    
    return currentMinutes >= openMinutes && currentMinutes < closeMinutes;
}

/**
 * HTMLエスケープ
 * @param {string} text - エスケープするテキスト
 * @returns {string} エスケープされたテキスト
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * ローディング表示を切り替え
 * @param {boolean} show - 表示するかどうか
 */
function showLoading(show) {
    document.getElementById('loadingIndicator').style.display = 
        show ? 'block' : 'none';
}

/**
 * エラーメッセージを表示
 * @param {string} message - エラーメッセージ
 */
function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');
    
    errorText.textContent = message;
    errorDiv.style.display = 'block';
}

/**
 * エラーメッセージを非表示
 */
function hideError() {
    document.getElementById('errorMessage').style.display = 'none';
}
