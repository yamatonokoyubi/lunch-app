/**
 * 注文確認ページ JavaScript
 */

let cartData = null;

document.addEventListener('DOMContentLoaded', async function() {
    await loadUserAndCart();
    setupEventListeners();
});

async function loadUserAndCart() {
    try {
        const token = localStorage.getItem('authToken');
        if (!token) {
            console.error('トークンが見つかりません');
            alert('ログインが必要です');
            window.location.href = '/login';
            return;
        }

        console.log('✅ トークン確認完了');

        // ユーザー情報を取得
        try {
            const userResponse = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (userResponse.ok) {
                const currentUser = await userResponse.json();
                const userDetails = document.getElementById('userDetails');
                
                if (currentUser) {
                    userDetails.innerHTML = `
                        <p><strong>ユーザー名:</strong> ${currentUser.username}</p>
                        <p><strong>メールアドレス:</strong> ${currentUser.email || 'N/A'}</p>
                    `;
                    console.log('✅ ユーザー情報取得完了:', currentUser);
                }
            } else {
                console.warn('ユーザー情報の取得に失敗しました');
            }
        } catch (userError) {
            console.error('ユーザー情報取得エラー:', userError);
        }

        // カート内容を取得
        console.log('📦 カート情報を取得中...');
        const cartResponse = await fetch('/api/customer/cart', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        console.log('カートレスポンスステータス:', cartResponse.status);
        
        if (!cartResponse.ok) {
            const errorText = await cartResponse.text();
            console.error('カートAPIエラー:', errorText);
            throw new Error(`カート情報の取得に失敗しました (${cartResponse.status})`);
        }
        
        cartData = await cartResponse.json();
        console.log('✅ カートデータ取得完了:', cartData);
        
        document.getElementById('loading').style.display = 'none';
        
        if (!cartData.items || cartData.items.length === 0) {
            console.log('⚠️ カートが空です');
            document.getElementById('emptyCart').style.display = 'block';
            return;
        }
        
        displayOrderItems(cartData);
        document.getElementById('orderContent').style.display = 'block';
        console.log('✅ 注文確認画面表示完了');
        
    } catch (error) {
        console.error('❌ 読み込みエラー:', error);
        console.error('エラー詳細:', error.message);
        console.error('エラースタック:', error.stack);
        document.getElementById('loading').style.display = 'none';
        alert(`注文情報の読み込みに失敗しました: ${error.message}`);
        window.location.href = '/cart';
    }
}

function displayOrderItems(data) {
    const orderItemsEl = document.getElementById('orderItems');
    const totalAmountEl = document.getElementById('totalAmount');
    
    orderItemsEl.innerHTML = data.items.map(item => `
        <div class="order-item">
            <img src="${item.menu_image_url || '/static/img/menu-placeholder.svg'}" 
                 alt="${item.menu_name}"
                 onerror="this.src='/static/img/menu-placeholder.svg'">
            <div class="order-item-details">
                <div class="order-item-name">${item.menu_name}</div>
                <div class="order-item-price">単価: ¥${item.menu_price.toLocaleString()}</div>
                <div class="order-item-quantity">数量: ${item.quantity}個</div>
            </div>
            <div class="order-item-subtotal">
                ¥${item.subtotal.toLocaleString()}
            </div>
        </div>
    `).join('');
    
    totalAmountEl.textContent = `¥${data.total_price.toLocaleString()}`;
}

function setupEventListeners() {
    // 注文確定ボタン
    const confirmBtn = document.getElementById('confirmOrderBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', async function() {
            await confirmOrder(this);
        });
    }
}

async function confirmOrder(btn) {
    if (!cartData || !cartData.items || cartData.items.length === 0) {
        alert('カートが空です');
        return;
    }
    
    const confirmed = confirm(`合計 ¥${cartData.total_price.toLocaleString()} の注文を確定しますか？`);
    if (!confirmed) return;
    
    btn.disabled = true;
    btn.textContent = '処理中...';
    
    try {
        const token = localStorage.getItem('authToken');
        
        // 各アイテムを注文として登録
        for (const item of cartData.items) {
            const response = await fetch('/api/customer/orders', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    menu_id: item.menu_id,
                    quantity: item.quantity
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                console.error('注文エラー:', errorData);
                throw new Error('注文の作成に失敗しました');
            }
        }
        
        console.log('✅ 注文作成完了');
        
        // 注文完了後、カートバッジを更新
        if (window.updateCartBadge) {
            await window.updateCartBadge();
        }
        
        // 注文完了ページへ遷移
        window.location.href = '/checkout/complete';
        
    } catch (error) {
        console.error('注文作成エラー:', error);
        alert('注文の作成に失敗しました。もう一度お試しください。');
        btn.disabled = false;
        btn.textContent = '注文を確定する';
    }
}
