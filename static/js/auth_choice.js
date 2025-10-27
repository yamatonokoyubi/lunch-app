// 認証選択ページのJavaScript

document.addEventListener('DOMContentLoaded', function() {
    loadCartSummary();
});

/**
 * カートのサマリーを読み込んで表示
 */
async function loadCartSummary() {
    const summaryContainer = document.getElementById('cartSummary');
    
    try {
        // ゲストカートを取得
        const response = await fetch('/api/guest/cart', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('カート情報の取得に失敗しました');
        }

        const data = await response.json();
        
        // カートが空の場合
        if (!data.items || data.items.length === 0) {
            summaryContainer.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #64748b;">
                    <p>カートに商品がありません</p>
                    <a href="/menus" style="color: #2563eb; text-decoration: none;">メニューを見る</a>
                </div>
            `;
            return;
        }

        // 合計金額を計算
        const totalAmount = data.items.reduce((sum, item) => {
            return sum + (item.menu.price * item.quantity);
        }, 0);

        const totalItems = data.items.reduce((sum, item) => sum + item.quantity, 0);

        // サマリーを表示
        summaryContainer.innerHTML = `
            <div class="cart-summary-details">
                <div class="summary-row items">
                    <span>商品点数</span>
                    <span>${totalItems}点</span>
                </div>
                <div class="summary-row total">
                    <span>合計金額</span>
                    <span>¥${totalAmount.toLocaleString()}</span>
                </div>
            </div>
        `;

    } catch (error) {
        console.error('カートサマリーの読み込みエラー:', error);
        summaryContainer.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #ef4444;">
                <p>カート情報の読み込みに失敗しました</p>
                <button onclick="loadCartSummary()" style="margin-top: 10px; padding: 8px 16px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer;">
                    再読み込み
                </button>
            </div>
        `;
    }
}

/**
 * トースト通知を表示
 */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

/**
 * URLパラメータからメッセージを取得して表示
 */
function checkForMessages() {
    const urlParams = new URLSearchParams(window.location.search);
    const message = urlParams.get('message');
    
    if (message) {
        showToast(decodeURIComponent(message), 'info');
    }
}

// ページ読み込み時にメッセージをチェック
checkForMessages();
