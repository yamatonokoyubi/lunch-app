// 店舗メニュー管理 - store_menus.js

// ===== グローバル変数 =====
let currentPage = 1;
let perPage = 20;
let totalMenus = 0;
let currentFilter = null; // null=すべて, true=公開中, false=非公開
let currentSortBy = 'id'; // ソート対象カラム (デフォルト: ID)
let currentSortOrder = 'asc'; // ソート順序 (デフォルト: 昇順)
let currentKeyword = ''; // 検索キーワード
let searchDebounceTimer = null; // 検索デバウンスタイマー
let menus = [];
let selectedMenuIds = new Set(); // 選択されたメニューID
let currentCategoryId = null; // カテゴリフィルタ (null=すべて, 0=カテゴリなし, 数値=特定のカテゴリ)
let categories = []; // カテゴリ一覧

// ===== ページ初期化 =====
document.addEventListener('DOMContentLoaded', async () => {
    console.log('メニュー管理画面を初期化中...');
    
    // 認証チェック
    if (!Auth.requireRole('store')) return;
    
    // ヘッダー情報を表示
    await UI.initializeStoreHeader();
    
    // 共通UI初期化
    initializeCommonUI();
    
    // モーダル初期化
    MenuModal.init();
    DeleteModal.init();
    
    // カテゴリを読み込み
    await fetchCategories();
    
    // URLパラメータから状態を復元
    restoreStateFromURL();
    
    // イベントリスナー設定
    setupEventListeners();
    
    // メニュー一覧を取得
    await fetchMenus();
});

// ===== カテゴリ取得 =====
async function fetchCategories() {
    try {
        const response = await ApiClient.get('/store/menu-categories');
        if (response && response.categories) {
            categories = response.categories;
            updateCategorySelects();
        }
    } catch (error) {
        console.error('カテゴリの取得に失敗:', error);
        // カテゴリが取得できなくてもメニュー表示は継続
    }
}

// カテゴリセレクトボックスを更新
function updateCategorySelects() {
    // フィルタ用セレクトボックス
    const filterSelect = document.getElementById('categoryFilter');
    if (filterSelect) {
        // 既存のオプションを保持しつつカテゴリを追加
        const existingOptions = filterSelect.innerHTML;
        const categoryOptions = categories
            .filter(cat => cat.is_active) // 有効なカテゴリのみ表示
            .map(cat => `<option value="${cat.id}">${escapeHtml(cat.name)}</option>`)
            .join('');
        filterSelect.innerHTML = existingOptions.split('<!-- JavaScriptで動的に生成 -->')[0] + categoryOptions;
    }
    
    // メニューフォーム用セレクトボックス (MenuModal.openCreateModal/openEditModal で呼び出される)
    const menuCategorySelect = document.getElementById('menuCategory');
    if (menuCategorySelect) {
        const categoryOptions = categories
            .filter(cat => cat.is_active)
            .map(cat => `<option value="${cat.id}">${escapeHtml(cat.name)}</option>`)
            .join('');
        menuCategorySelect.innerHTML = '<option value="">📁 カテゴリなし</option>' + categoryOptions;
    }
}

// ===== URLパラメータから状態を復元 =====
function restoreStateFromURL() {
    const params = new URLSearchParams(window.location.search);
    
    // 検索キーワードを復元
    const keyword = params.get('keyword');
    if (keyword) {
        currentKeyword = keyword;
        const searchInput = document.getElementById('searchInput');
        const clearBtn = document.getElementById('clearSearchBtn');
        
        if (searchInput) {
            searchInput.value = keyword;
        }
        
        if (clearBtn) {
            clearBtn.style.display = 'flex';
        }
    }
    
    // カテゴリフィルタを復元
    const categoryId = params.get('category_id');
    if (categoryId !== null) {
        currentCategoryId = categoryId === '0' ? 0 : (categoryId === '' ? null : parseInt(categoryId));
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            categoryFilter.value = categoryId;
        }
    }
    
    // ソート状態を復元
    const sortBy = params.get('sort_by');
    const sortOrder = params.get('sort_order');
    
    if (sortBy) {
        currentSortBy = sortBy;
        currentSortOrder = sortOrder || 'asc';
        updateSortUI();
    }
}

// ===== イベントリスナー設定 =====
function setupEventListeners() {
    // 検索入力
    const searchInput = document.getElementById('searchInput');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    
    if (searchInput) {
        searchInput.addEventListener('input', handleSearchInput);
        
        // エンターキーで即座に検索
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                if (searchDebounceTimer) {
                    clearTimeout(searchDebounceTimer);
                }
                handleSearch();
            }
        });
    }
    
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', clearSearch);
    }
    
    // フィルタボタン
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            handleFilterChange(e.target.closest('.filter-btn'));
        });
    });
    
    // カテゴリフィルタ
    const categoryFilter = document.getElementById('categoryFilter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', handleCategoryFilterChange);
    }
    
    // ソート可能なヘッダー
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', () => {
            handleSort(th.dataset.sort);
        });
    });
    
    // 表示件数変更
    const perPageSelect = document.getElementById('perPageSelect');
    if (perPageSelect) {
        perPageSelect.addEventListener('change', (e) => {
            perPage = parseInt(e.target.value);
            currentPage = 1;
            fetchMenus();
        });
    }
    
    // 全選択チェックボックス
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', handleSelectAll);
    }
    
    // 一括公開ボタン
    const bulkAvailableBtn = document.getElementById('bulkAvailableBtn');
    if (bulkAvailableBtn) {
        bulkAvailableBtn.addEventListener('click', () => handleBulkAvailability(true));
    }
    
    // 一括非公開ボタン
    const bulkUnavailableBtn = document.getElementById('bulkUnavailableBtn');
    if (bulkUnavailableBtn) {
        bulkUnavailableBtn.addEventListener('click', () => handleBulkAvailability(false));
    }
    
    // 選択クリアボタン
    const clearSelectionBtn = document.getElementById('clearSelectionBtn');
    if (clearSelectionBtn) {
        clearSelectionBtn.addEventListener('click', clearSelection);
    }
}

// ===== 検索処理 =====
function handleSearchInput(e) {
    const keyword = e.target.value.trim();
    
    // クリアボタンの表示/非表示
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) {
        clearBtn.style.display = keyword ? 'flex' : 'none';
    }
    
    // デバウンス処理（300ms待機）
    if (searchDebounceTimer) {
        clearTimeout(searchDebounceTimer);
    }
    
    searchDebounceTimer = setTimeout(() => {
        handleSearch();
    }, 300);
}

function handleSearch() {
    const searchInput = document.getElementById('searchInput');
    currentKeyword = searchInput ? searchInput.value.trim() : '';
    
    // URLパラメータを更新
    updateURLParams();
    
    // ページを1に戻して再取得
    currentPage = 1;
    fetchMenus();
}

function clearSearch() {
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearSearchBtn');
    
    if (searchInput) {
        searchInput.value = '';
    }
    
    if (clearBtn) {
        clearBtn.style.display = 'none';
    }
    
    currentKeyword = '';
    
    // URLパラメータを更新
    updateURLParams();
    
    // ページを1に戻して再取得
    currentPage = 1;
    fetchMenus();
}

function updateSearchResultInfo() {
    const searchResultInfo = document.getElementById('searchResultInfo');
    const searchResultText = document.getElementById('searchResultText');
    
    if (!searchResultInfo || !searchResultText) return;
    
    if (currentKeyword) {
        searchResultInfo.style.display = 'block';
        searchResultText.textContent = `"${currentKeyword}" の検索結果: ${totalMenus}件`;
    } else {
        searchResultInfo.style.display = 'none';
    }
}

// ===== フィルタ変更 =====
function handleFilterChange(btn) {
    // すべてのフィルタボタンからactiveクラスを削除
    document.querySelectorAll('.filter-btn').forEach(b => {
        b.classList.remove('active');
    });
    
    // クリックされたボタンにactiveクラスを追加
    btn.classList.add('active');
    
    // フィルタ値を取得
    const filterValue = btn.dataset.filter;
    
    if (filterValue === 'all') {
        currentFilter = null;
    } else {
        currentFilter = filterValue === 'true';
    }
    
    // ページを1に戻して再取得
    currentPage = 1;
    fetchMenus();
}

// カテゴリフィルタ変更
function handleCategoryFilterChange(e) {
    const value = e.target.value;
    
    if (value === '') {
        currentCategoryId = null; // すべてのカテゴリ
    } else if (value === '0') {
        currentCategoryId = 0; // カテゴリなし
    } else {
        currentCategoryId = parseInt(value);
    }
    
    // URLパラメータを更新
    updateURLParams();
    
    // ページを1に戻して再取得
    currentPage = 1;
    fetchMenus();
}

// ===== ソート処理 =====
function handleSort(sortBy) {
    // 同じカラムをクリックした場合は順序を反転
    if (currentSortBy === sortBy) {
        currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        // 新しいカラムの場合は昇順から開始
        currentSortBy = sortBy;
        currentSortOrder = 'asc';
    }
    
    // ソート状態をUIに反映
    updateSortUI();
    
    // URLパラメータを更新
    updateURLParams();
    
    // ページを1に戻して再取得
    currentPage = 1;
    fetchMenus();
}

function updateSortUI() {
    // すべてのソートヘッダーからactiveクラスを削除
    document.querySelectorAll('.sortable').forEach(th => {
        th.classList.remove('active', 'asc', 'desc');
    });
    
    // 現在のソート対象にactiveクラスとソート方向を追加
    if (currentSortBy) {
        const activeTh = document.querySelector(`.sortable[data-sort="${currentSortBy}"]`);
        if (activeTh) {
            activeTh.classList.add('active', currentSortOrder);
        }
    }
}

function updateURLParams() {
    const params = new URLSearchParams(window.location.search);
    
    // 検索キーワード
    if (currentKeyword) {
        params.set('keyword', currentKeyword);
    } else {
        params.delete('keyword');
    }
    
    // カテゴリフィルタ
    if (currentCategoryId !== null) {
        params.set('category_id', currentCategoryId.toString());
    } else {
        params.delete('category_id');
    }
    
    // ソート
    if (currentSortBy) {
        params.set('sort_by', currentSortBy);
        params.set('sort_order', currentSortOrder);
    } else {
        params.delete('sort_by');
        params.delete('sort_order');
    }
    
    // URLを更新（ページリロードなし）
    const newURL = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, '', newURL);
}

// ===== メニュー一覧取得 =====
async function fetchMenus() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorMessage = document.getElementById('errorMessage');
    const tableBody = document.getElementById('menuTableBody');
    const emptyMessage = document.getElementById('emptyMessage');
    const paginationSection = document.getElementById('paginationSection');
    
    // ページ遷移時に選択をクリア
    clearSelection();
    
    try {
        // ローディング表示
        if (loadingIndicator) loadingIndicator.style.display = 'flex';
        if (errorMessage) errorMessage.style.display = 'none';
        if (tableBody) tableBody.innerHTML = '';
        
        // APIリクエストURLを構築
        const params = new URLSearchParams();
        
        // ページネーション
        params.append('page', currentPage);
        params.append('limit', perPage);
        
        // 検索
        if (currentKeyword) {
            params.append('keyword', currentKeyword);
        }
        
        // フィルタ（is_available パラメータ）
        if (currentFilter !== null) {
            params.append('is_available', currentFilter);
        }
        
        // カテゴリフィルタ
        if (currentCategoryId !== null) {
            params.append('category_id', currentCategoryId);
        }
        
        // ソート
        if (currentSortBy) {
            params.append('sort_by', currentSortBy);
            params.append('sort_order', currentSortOrder);
        }
        
        const apiUrl = `/store/menus?${params.toString()}`;
        
        // APIからメニュー一覧を取得
        const response = await ApiClient.get(apiUrl);
        console.log('APIレスポンス:', response);
        
        // レスポンスからメニューと総件数を取得
        if (response && Array.isArray(response.menus) && typeof response.total === 'number') {
            // ページネーション付きレスポンス（バックエンド対応）
            menus = response.menus;
            totalMenus = response.total;
        } else if (Array.isArray(response)) {
            // 配列のみのレスポンス（後方互換性）
            menus = response;
            totalMenus = response.length;
        } else {
            console.error('予期しないレスポンス形式:', response);
            menus = [];
            totalMenus = 0;
        }
        
        console.log('取得したメニュー数:', menus.length, '/ 総件数:', totalMenus);
        
        // メニュー表示（既にサーバー側でフィルタ・ページネーション済み）
        renderMenus(menus);
        
        // カウント更新
        updateCounts();
        
        // ページネーション更新
        updatePagination(totalMenus);
        
        // 検索結果情報を更新
        updateSearchResultInfo();
        
        // 空メッセージの表示/非表示
        if (totalMenus === 0) {
            if (emptyMessage) {
                emptyMessage.style.display = 'flex';
                const emptyText = currentKeyword 
                    ? `"${currentKeyword}" に一致するメニューが見つかりません`
                    : (currentFilter !== null ? 'フィルタ条件に一致するメニューがありません' : 'メニューがありません');
                document.getElementById('emptyMessageText').textContent = emptyText;
            }
            if (paginationSection) paginationSection.style.display = 'none';
        } else {
            if (emptyMessage) emptyMessage.style.display = 'none';
            if (paginationSection) paginationSection.style.display = 'flex';
        }
        
    } catch (error) {
        console.error('メニューの取得に失敗:', error);
        if (errorMessage) {
            errorMessage.textContent = 'メニューの取得に失敗しました';
            errorMessage.style.display = 'block';
        }
        showToast('メニューの取得に失敗しました', 'error');
    } finally {
        if (loadingIndicator) loadingIndicator.style.display = 'none';
    }
}

// ===== メニュー表示 =====
function renderMenus(menusToRender) {
    const tableBody = document.getElementById('menuTableBody');
    if (!tableBody) return;
    
    if (menusToRender.length === 0) {
        tableBody.innerHTML = '';
        return;
    }
    
    // 現在のユーザー情報を取得
    const user = Auth.getUser();
    
    // オーナーロールを持っているかチェック
    // user.user_roles は { role: { name: "owner" } } の形式の配列
    const isOwner = user && user.user_roles && 
                   user.user_roles.some(ur => ur.role && ur.role.name === 'owner');
    
    tableBody.innerHTML = menusToRender.map(menu => {
        // 検索キーワードハイライト
        const highlightedName = highlightKeyword(menu.name);
        const highlightedDescription = highlightKeyword(menu.description || '');
        
        // チェックボックスの状態
        const isChecked = selectedMenuIds.has(menu.id);
        
        return `
        <tr>
            <td>
                <input type="checkbox" 
                       class="row-checkbox" 
                       data-menu-id="${menu.id}"
                       ${isChecked ? 'checked' : ''}
                       onchange="handleCheckboxChange(event)">
            </td>
            <td>${escapeHtml(String(menu.id))}</td>
            <td>
                ${menu.image_url 
                    ? `<img src="${escapeHtml(menu.image_url)}" alt="${escapeHtml(menu.name)}" class="menu-image">`
                    : '<div class="menu-no-image">📷</div>'
                }
            </td>
            <td class="menu-name">${highlightedName}</td>
            <td class="menu-description">${highlightedDescription}</td>
            <td class="menu-price">¥${menu.price.toLocaleString()}</td>
            <td>
                <span class="status-badge ${menu.is_available ? 'available' : 'unavailable'}">
                    ${menu.is_available ? '🟢 公開中' : '🔴 非公開'}
                </span>
            </td>
            <td class="menu-date">${formatDateTime(menu.created_at)}</td>
            <td class="menu-date">${formatDateTime(menu.updated_at)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn-action btn-edit" onclick="openEditModal(${menu.id})" title="編集">
                        ✏️ 編集
                    </button>
                    ${isOwner ? `
                    <button class="btn-action btn-delete" onclick="deleteMenu(${menu.id})" title="削除">
                        🗑️ 削除
                    </button>
                    ` : ''}
                </div>
            </td>
        </tr>
        `;
    }).join('');
}

// ===== キーワードハイライト =====
function highlightKeyword(text) {
    if (!currentKeyword || !text) {
        return escapeHtml(text);
    }
    
    const escapedText = escapeHtml(text);
    const escapedKeyword = escapeHtml(currentKeyword);
    
    // 大文字小文字を区別しない検索
    const regex = new RegExp(`(${escapedKeyword})`, 'gi');
    return escapedText.replace(regex, '<span class="search-highlight">$1</span>');
}

// ===== カウント更新 =====
async function updateCounts() {
    const countAll = document.getElementById('countAll');
    const countAvailable = document.getElementById('countAvailable');
    const countUnavailable = document.getElementById('countUnavailable');
    
    try {
        // 各フィルタのカウントを取得
        const [allResponse, availableResponse, unavailableResponse] = await Promise.all([
            ApiClient.get('/store/menus?page=1&limit=1'),  // すべて
            ApiClient.get('/store/menus?is_available=true&page=1&limit=1'),  // 公開中
            ApiClient.get('/store/menus?is_available=false&page=1&limit=1')  // 非公開
        ]);
        
        if (countAll && allResponse?.total !== undefined) {
            countAll.textContent = allResponse.total;
        }
        if (countAvailable && availableResponse?.total !== undefined) {
            countAvailable.textContent = availableResponse.total;
        }
        if (countUnavailable && unavailableResponse?.total !== undefined) {
            countUnavailable.textContent = unavailableResponse.total;
        }
    } catch (error) {
        console.error('カウントの取得に失敗:', error);
        // エラー時は現在のページのデータから推定
        if (countAll) countAll.textContent = totalMenus;
        if (countAvailable) countAvailable.textContent = menus.filter(m => m.is_available).length;
        if (countUnavailable) countUnavailable.textContent = menus.filter(m => !m.is_available).length;
    }
    
    // フィルタ情報更新
    const filterInfo = document.getElementById('filterInfo');
    if (filterInfo) {
        if (currentFilter === null) {
            filterInfo.textContent = `全メニューを表示中 (${totalMenus}件)`;
        } else if (currentFilter === true) {
            filterInfo.textContent = `公開中のメニューを表示中 (${totalMenus}件)`;
        } else {
            filterInfo.textContent = `非公開のメニューを表示中 (${totalMenus}件)`;
        }
    }
}

// ===== ページネーション更新 =====
function updatePagination(total) {
    const pagination = document.getElementById('pagination');
    const paginationInfo = document.getElementById('paginationInfo');
    
    if (!pagination || total === 0) return;
    
    const totalPages = Math.ceil(total / perPage);
    const startIndex = (currentPage - 1) * perPage + 1;
    const endIndex = Math.min(currentPage * perPage, total);
    
    // ページネーション情報
    if (paginationInfo) {
        paginationInfo.textContent = `${startIndex}-${endIndex} / ${total}件`;
    }
    
    // ページネーションボタン
    let paginationHTML = '';
    
    // 前へボタン
    paginationHTML += `
        <button class="pagination-btn ${currentPage === 1 ? 'disabled' : ''}" 
                onclick="changePage(${currentPage - 1})"
                ${currentPage === 1 ? 'disabled' : ''}>
            ← 前へ
        </button>
    `;
    
    // ページ番号ボタン
    const maxButtons = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    
    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }
    
    if (startPage > 1) {
        paginationHTML += `<button class="pagination-btn" onclick="changePage(1)">1</button>`;
        if (startPage > 2) {
            paginationHTML += `<span class="pagination-ellipsis">...</span>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <button class="pagination-btn ${i === currentPage ? 'active' : ''}" 
                    onclick="changePage(${i})">
                ${i}
            </button>
        `;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHTML += `<span class="pagination-ellipsis">...</span>`;
        }
        paginationHTML += `<button class="pagination-btn" onclick="changePage(${totalPages})">${totalPages}</button>`;
    }
    
    // 次へボタン
    paginationHTML += `
        <button class="pagination-btn ${currentPage === totalPages ? 'disabled' : ''}" 
                onclick="changePage(${currentPage + 1})"
                ${currentPage === totalPages ? 'disabled' : ''}>
            次へ →
        </button>
    `;
    
    pagination.innerHTML = paginationHTML;
}

// ===== ページ変更 =====
function changePage(page) {
    const totalPages = Math.ceil(totalMenus / perPage);
    if (page < 1 || page > totalPages) return;
    
    currentPage = page;
    fetchMenus();
}

// ===== メニュー削除 =====
async function deleteMenu(menuId) {
    if (!confirm('このメニューを削除してもよろしいですか?')) {
        return;
    }
    
    try {
        await ApiClient.delete(`/store/menus/${menuId}`);
        showToast('メニューを削除しました', 'success');
        await fetchMenus();
    } catch (error) {
        console.error('メニューの削除に失敗:', error);
        showToast('メニューの削除に失敗しました', 'error');
    }
}

// ===== ユーティリティ関数 =====
function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}/${month}/${day} ${hours}:${minutes}`;
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
}

function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };

    const titles = {
        success: '成功',
        error: 'エラー',
        warning: '警告',
        info: '情報'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${icons[type] || icons.info}</div>
        <div class="toast-content">
            <div class="toast-title">${titles[type] || titles.info}</div>
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 5000);
}

// ===== モーダル管理 =====
const MenuModal = {
    modal: null,
    form: null,
    isEditMode: false,
    currentMenuId: null,
    selectedImageFile: null,

    init() {
        this.modal = document.getElementById('menuModal');
        this.form = document.getElementById('menuForm');
        
        // モーダルを開くボタン
        const addMenuBtn = document.getElementById('addMenuBtn');
        if (addMenuBtn) {
            addMenuBtn.addEventListener('click', () => this.openCreateModal());
        }

        // モーダルを閉じるボタン
        const closeBtn = document.getElementById('modalCloseBtn');
        const cancelBtn = document.getElementById('modalCancelBtn');
        
        if (closeBtn) closeBtn.addEventListener('click', () => this.close());
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.close());

        // モーダル外をクリックで閉じる
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.close();
            }
        });

        // フォーム送信
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));

        // リアルタイムバリデーション
        this.setupValidation();
        
        // 画像アップロード機能
        this.setupImageUpload();
    },

    setupValidation() {
        const nameInput = document.getElementById('menuName');
        const priceInput = document.getElementById('menuPrice');
        const descInput = document.getElementById('menuDescription');

        // 名前のバリデーション
        nameInput.addEventListener('input', () => {
            this.validateName();
        });

        // 価格のバリデーション
        priceInput.addEventListener('input', () => {
            this.validatePrice();
        });

        // 説明文の文字数カウント
        descInput.addEventListener('input', () => {
            const charCount = document.getElementById('descriptionCharCount');
            if (charCount) {
                charCount.textContent = descInput.value.length;
            }
        });
    },

    setupImageUpload() {
        const dropZone = document.getElementById('imageDropZone');
        const fileInput = document.getElementById('menuImageFile');
        const selectBtn = document.getElementById('selectImageBtn');
        const removeBtn = document.getElementById('removeImageBtn');

        // ファイル選択ボタン
        if (selectBtn) {
            selectBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                fileInput.click();
            });
        }

        // ドラッグ&ドロップエリアのクリック
        if (dropZone) {
            dropZone.addEventListener('click', () => {
                fileInput.click();
            });
        }

        // ドラッグオーバー
        if (dropZone) {
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('drag-over');
            });

            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('drag-over');
            });

            // ドロップ
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('drag-over');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleImageFile(files[0]);
                }
            });
        }

        // ファイル選択
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const files = e.target.files;
                if (files.length > 0) {
                    this.handleImageFile(files[0]);
                }
            });
        }

        // 画像削除ボタン
        if (removeBtn) {
            removeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.clearImage();
            });
        }
    },

    handleImageFile(file) {
        const errorEl = document.getElementById('imageError');
        
        // ファイル形式チェック
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            this.showImageError(errorEl, '対応していないファイル形式です。JPEG, PNG, GIF, WebPのみ対応しています。');
            return;
        }

        // ファイルサイズチェック (2MB)
        const maxSize = 2 * 1024 * 1024;
        if (file.size > maxSize) {
            this.showImageError(errorEl, 'ファイルサイズが大きすぎます。2MB以下のファイルを選択してください。');
            return;
        }

        // エラーをクリア
        this.hideImageError(errorEl);

        // ファイルを保存
        this.selectedImageFile = file;

        // プレビュー表示
        const reader = new FileReader();
        reader.onload = (e) => {
            this.showImagePreview(e.target.result, file.name);
        };
        reader.readAsDataURL(file);
    },

    showImagePreview(dataUrl, fileName) {
        const dropZone = document.getElementById('imageDropZone');
        const previewContainer = document.getElementById('imagePreviewContainer');
        const previewImg = document.getElementById('imagePreview');
        const fileNameEl = document.getElementById('imageFileName');

        // ドロップゾーンを非表示
        dropZone.style.display = 'none';

        // プレビューを表示
        previewImg.src = dataUrl;
        fileNameEl.textContent = fileName;
        previewContainer.style.display = 'block';
    },

    clearImage() {
        const dropZone = document.getElementById('imageDropZone');
        const previewContainer = document.getElementById('imagePreviewContainer');
        const fileInput = document.getElementById('menuImageFile');
        const errorEl = document.getElementById('imageError');

        // ファイルをクリア
        this.selectedImageFile = null;
        fileInput.value = '';

        // プレビューを非表示
        previewContainer.style.display = 'none';

        // ドロップゾーンを表示
        dropZone.style.display = 'block';

        // エラーをクリア
        this.hideImageError(errorEl);
    },

    showImageError(errorEl, message) {
        errorEl.textContent = message;
        errorEl.classList.add('show');
    },

    hideImageError(errorEl) {
        errorEl.classList.remove('show');
    },

    validateName() {
        const nameInput = document.getElementById('menuName');
        const errorEl = document.getElementById('nameError');
        const value = nameInput.value.trim();

        if (!value) {
            this.showError(nameInput, errorEl, 'メニュー名は必須です');
            return false;
        }

        if (value.length > 100) {
            this.showError(nameInput, errorEl, 'メニュー名は100文字以内で入力してください');
            return false;
        }

        this.hideError(nameInput, errorEl);
        return true;
    },

    validatePrice() {
        const priceInput = document.getElementById('menuPrice');
        const errorEl = document.getElementById('priceError');
        const value = priceInput.value;

        if (!value) {
            this.showError(priceInput, errorEl, '価格は必須です');
            return false;
        }

        const price = parseInt(value);
        if (isNaN(price) || price < 1) {
            this.showError(priceInput, errorEl, '価格は1円以上を入力してください');
            return false;
        }

        if (price > 100000) {
            this.showError(priceInput, errorEl, '価格は100,000円以下で入力してください');
            return false;
        }

        this.hideError(priceInput, errorEl);
        return true;
    },

    validateForm() {
        const isNameValid = this.validateName();
        const isPriceValid = this.validatePrice();
        return isNameValid && isPriceValid;
    },

    showError(input, errorEl, message) {
        input.classList.add('error');
        errorEl.textContent = message;
        errorEl.classList.add('show');
    },

    hideError(input, errorEl) {
        input.classList.remove('error');
        errorEl.classList.remove('show');
    },

    openCreateModal() {
        this.isEditMode = false;
        this.currentMenuId = null;
        
        document.getElementById('modalTitle').textContent = 'メニュー追加';
        this.form.reset();
        
        // デフォルト値を設定
        document.getElementById('menuAvailable').value = 'true';
        document.getElementById('descriptionCharCount').textContent = '0';
        
        // カテゴリセレクトボックスを更新
        updateCategorySelects();
        
        // エラー表示をクリア
        this.clearErrors();
        
        // 画像をクリア
        this.clearImage();
        
        this.show();
    },

    async openEditModal(menuId) {
        this.isEditMode = true;
        this.currentMenuId = menuId;
        
        document.getElementById('modalTitle').textContent = 'メニュー編集';
        
        try {
            // メニューデータを取得（一覧から取得）
            const menu = menus.find(m => m.id === menuId);
            
            if (!menu) {
                throw new Error('メニューが見つかりません');
            }
            
            // カテゴリセレクトボックスを更新
            updateCategorySelects();
            
            // フォームにデータをセット
            document.getElementById('menuId').value = menu.id;
            document.getElementById('menuName').value = menu.name || '';
            document.getElementById('menuDescription').value = menu.description || '';
            document.getElementById('menuPrice').value = menu.price || '';
            document.getElementById('menuAvailable').value = menu.is_available ? 'true' : 'false';
            document.getElementById('menuImageUrl').value = menu.image_url || '';
            document.getElementById('menuCategory').value = menu.category_id || '';
            
            // 文字数カウントを更新
            const descLength = (menu.description || '').length;
            document.getElementById('descriptionCharCount').textContent = descLength;
            
            // 既存の画像がある場合はプレビュー表示
            if (menu.image_url) {
                this.showImagePreview(menu.image_url, '現在の画像');
            } else {
                this.clearImage();
            }
            
            // エラー表示をクリア
            this.clearErrors();
            
            this.show();
        } catch (error) {
            console.error('メニューデータの取得に失敗:', error);
            showToast('メニューデータの取得に失敗しました', 'error');
        }
    },

    show() {
        this.modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    },

    close() {
        this.modal.classList.remove('show');
        document.body.style.overflow = '';
        this.form.reset();
        this.clearErrors();
        this.clearImage();
    },

    clearErrors() {
        // すべてのエラー表示をクリア
        document.querySelectorAll('.error-message').forEach(el => {
            el.classList.remove('show');
        });
        document.querySelectorAll('.form-input, .form-textarea, .form-select').forEach(el => {
            el.classList.remove('error');
        });
    },

    async handleSubmit(e) {
        e.preventDefault();

        // バリデーション
        if (!this.validateForm()) {
            showToast('入力内容を確認してください', 'warning');
            return;
        }

        // 送信ボタンを無効化
        const submitBtn = document.getElementById('modalSubmitBtn');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="btn-icon">⏳</span> 保存中...';

        try {
            // フォームデータを取得
            const categoryValue = document.getElementById('menuCategory').value;
            const formData = {
                name: document.getElementById('menuName').value.trim(),
                description: document.getElementById('menuDescription').value.trim() || null,
                price: parseInt(document.getElementById('menuPrice').value),
                is_available: document.getElementById('menuAvailable').value === 'true',
                image_url: document.getElementById('menuImageUrl').value.trim() || null,
                category_id: categoryValue ? parseInt(categoryValue) : null
            };

            let response;
            if (this.isEditMode) {
                // 編集: PUT /api/store/menus/{id}
                response = await ApiClient.put(`/store/menus/${this.currentMenuId}`, formData);
            } else {
                // 作成: POST /api/store/menus
                response = await ApiClient.post('/store/menus', formData);
            }

            // 画像がアップロードされている場合
            if (this.selectedImageFile) {
                submitBtn.innerHTML = '<span class="btn-icon">📤</span> 画像アップロード中...';
                await this.uploadImage(response.id);
            }

            showToast(this.isEditMode ? 'メニューを更新しました' : 'メニューを追加しました', 'success');

            // モーダルを閉じる
            this.close();

            // メニュー一覧を再読み込み
            await fetchMenus();

        } catch (error) {
            console.error('メニューの保存に失敗:', error);
            
            // APIエラーレスポンスを処理
            if (error.detail) {
                if (typeof error.detail === 'string') {
                    showToast(error.detail, 'error');
                } else if (Array.isArray(error.detail)) {
                    // バリデーションエラーの場合
                    error.detail.forEach(err => {
                        const field = err.loc[err.loc.length - 1];
                        const message = err.msg;
                        
                        // フィールドごとにエラーを表示
                        if (field === 'name') {
                            const input = document.getElementById('menuName');
                            const errorEl = document.getElementById('nameError');
                            this.showError(input, errorEl, message);
                        } else if (field === 'price') {
                            const input = document.getElementById('menuPrice');
                            const errorEl = document.getElementById('priceError');
                            this.showError(input, errorEl, message);
                        }
                    });
                    showToast('入力内容を確認してください', 'error');
                }
            } else {
                showToast('メニューの保存に失敗しました', 'error');
            }
        } finally {
            // 送信ボタンを有効化
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    },

    async uploadImage(menuId) {
        if (!this.selectedImageFile) return;

        try {
            // FormDataを作成
            const formData = new FormData();
            formData.append('file', this.selectedImageFile);

            // 画像アップロード APIを呼び出し
            const response = await fetch(`/api/store/menus/${menuId}/image`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('authToken')}`
                },
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '画像のアップロードに失敗しました');
            }

            console.log('画像アップロード成功');
        } catch (error) {
            console.error('画像アップロードエラー:', error);
            showToast(`画像のアップロードに失敗しました: ${error.message}`, 'error');
        }
    }
};

// 編集ボタンのグローバル関数(テーブルから呼び出される)
function openEditModal(menuId) {
    MenuModal.openEditModal(menuId);
}

// ===== 削除確認ダイアログ =====
const DeleteModal = {
    modal: null,
    menuId: null,
    menuName: null,

    init() {
        this.modal = document.getElementById('deleteModal');
        
        // 閉じるボタン
        const closeBtn = this.modal.querySelector('.modal-close');
        closeBtn.addEventListener('click', () => this.close());

        // キャンセルボタン
        const cancelBtn = document.getElementById('deleteCancelBtn');
        cancelBtn.addEventListener('click', () => this.close());

        // 削除実行ボタン
        const deleteBtn = document.getElementById('deleteConfirmBtn');
        deleteBtn.addEventListener('click', () => this.confirmDelete());

        // モーダル外クリックで閉じる
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.close();
            }
        });

        // ESCキーで閉じる
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.classList.contains('show')) {
                this.close();
            }
        });
    },

    show() {
        this.modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    },

    close() {
        this.modal.classList.remove('show');
        document.body.style.overflow = '';
        
        // リセット
        this.menuId = null;
        this.menuName = null;
    },

    openDeleteModal(menuId, menuName) {
        this.menuId = menuId;
        this.menuName = menuName;
        
        // メニュー名を表示
        const menuNameEl = document.getElementById('deleteMenuName');
        if (menuNameEl) {
            menuNameEl.textContent = menuName;
        }
        
        this.show();
    },

    async confirmDelete() {
        if (!this.menuId) return;

        const deleteBtn = document.getElementById('deleteConfirmBtn');
        const originalText = deleteBtn.innerHTML;
        
        try {
            // ボタンを無効化
            deleteBtn.disabled = true;
            deleteBtn.innerHTML = '<span class="loading-spinner"></span> 削除中...';

            // API呼び出し
            const response = await ApiClient.delete(`/store/menus/${this.menuId}`);
            
            // 削除成功
            this.close();
            
            // レスポンスの種類に応じてメッセージを変更
            if (response.is_deleted === true) {
                // 物理削除された場合
                showToast(`メニュー「${this.menuName}」を削除しました`, 'success');
            } else if (response.is_deleted === false) {
                // 論理削除された場合(注文履歴があるため)
                showToast(`メニュー「${this.menuName}」を非公開にしました（注文履歴があるため削除されませんでした）`, 'info');
            } else {
                // デフォルトメッセージ
                showToast(`メニュー「${this.menuName}」の削除処理が完了しました`, 'success');
            }

            // メニュー一覧を再読み込み
            await fetchMenus();

        } catch (error) {
            console.error('メニューの削除に失敗:', error);
            
            // APIエラーレスポンスを処理
            if (error.detail) {
                if (typeof error.detail === 'string') {
                    showToast(error.detail, 'error');
                } else {
                    showToast('メニューの削除に失敗しました', 'error');
                }
            } else {
                showToast('メニューの削除に失敗しました', 'error');
            }
        } finally {
            // ボタンを有効化
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = originalText;
        }
    }
};

// 削除ボタンのグローバル関数(テーブルから呼び出される)
function deleteMenu(menuId) {
    const menu = menus.find(m => m.id === menuId);
    if (menu) {
        DeleteModal.openDeleteModal(menuId, menu.name);
    }
}

// ===== 一括操作機能 =====

// 全選択チェックボックスの処理
function handleSelectAll(e) {
    const isChecked = e.target.checked;
    const checkboxes = document.querySelectorAll('.row-checkbox');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = isChecked;
        const menuId = parseInt(checkbox.dataset.menuId);
        
        if (isChecked) {
            selectedMenuIds.add(menuId);
        } else {
            selectedMenuIds.delete(menuId);
        }
    });
    
    updateBulkActionBar();
}

// 個別チェックボックスの処理
function handleCheckboxChange(e) {
    const menuId = parseInt(e.target.dataset.menuId);
    
    if (e.target.checked) {
        selectedMenuIds.add(menuId);
    } else {
        selectedMenuIds.delete(menuId);
    }
    
    // 全選択チェックボックスの状態を更新
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const checkboxes = document.querySelectorAll('.row-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = allChecked && checkboxes.length > 0;
    }
    
    updateBulkActionBar();
}

// 一括操作バーの表示/非表示と選択数の更新
function updateBulkActionBar() {
    const bulkActionBar = document.querySelector('.bulk-action-bar');
    const selectedCount = document.getElementById('selectedCount');
    
    if (bulkActionBar && selectedCount) {
        if (selectedMenuIds.size > 0) {
            bulkActionBar.style.display = 'flex';
            selectedCount.textContent = selectedMenuIds.size;
        } else {
            bulkActionBar.style.display = 'none';
        }
    }
}

// 選択クリア
function clearSelection() {
    selectedMenuIds.clear();
    
    // すべてのチェックボックスをクリア
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = false;
    }
    
    document.querySelectorAll('.row-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
    
    updateBulkActionBar();
}

// 一括公開/非公開の処理
async function handleBulkAvailability(isAvailable) {
    if (selectedMenuIds.size === 0) {
        showToast('メニューが選択されていません', 'warning');
        return;
    }
    
    const action = isAvailable ? '公開' : '非公開';
    const message = `選択した${selectedMenuIds.size}件のメニューを一括${action}しますか?`;
    
    if (!confirm(message)) {
        return;
    }
    
    try {
        const response = await ApiClient.put('/store/menus/bulk-availability', {
            menu_ids: Array.from(selectedMenuIds),
            is_available: isAvailable
        });
        
        if (response.updated_count > 0) {
            let successMsg = `${response.updated_count}件のメニューを${action}しました`;
            
            if (response.failed_ids && response.failed_ids.length > 0) {
                successMsg += `\n（${response.failed_ids.length}件のメニューは更新できませんでした）`;
            }
            
            showToast(successMsg, 'success');
        } else {
            showToast('更新できるメニューがありませんでした', 'warning');
        }
        
        // 選択をクリア
        clearSelection();
        
        // メニュー一覧を再読み込み
        await fetchMenus();
        
    } catch (error) {
        console.error('一括更新に失敗:', error);
        
        // エラーメッセージを表示
        let errorMessage = '一括更新に失敗しました';
        if (error.message && error.message !== '[object Object]') {
            errorMessage = error.message;
        }
        
        showToast(errorMessage, 'error');
    }
}


// ===== カテゴリ管理機能 =====

let currentEditingCategoryId = null;

// カテゴリ管理モーダルを開く
function openCategoryManagementModal() {
    const modal = document.getElementById('categoryManagementModal');
    if (modal) {
        modal.style.display = 'flex';
        loadCategoriesForManagement();
    }
}

// カテゴリ管理モーダルを閉じる
function closeCategoryManagementModal() {
    const modal = document.getElementById('categoryManagementModal');
    if (modal) modal.style.display = 'none';
}

// カテゴリ一覧をカテゴリ管理モーダルに読み込む
async function loadCategoriesForManagement() {
    const loadingIndicator = document.getElementById('categoryLoadingIndicator');
    const errorMessage = document.getElementById('categoryErrorMessage');
    const emptyMessage = document.getElementById('categoryEmptyMessage');
    const categoriesList = document.getElementById('categoriesList');
    
    if (loadingIndicator) loadingIndicator.style.display = 'flex';
    if (errorMessage) errorMessage.style.display = 'none';
    if (emptyMessage) emptyMessage.style.display = 'none';
    if (categoriesList) categoriesList.innerHTML = '';
    
    try {
        const response = await ApiClient.get('/store/menu-categories');
        
        if (response && response.categories) {
            renderCategoriesForManagement(response.categories);
        } else {
            showCategoryError('カテゴリの読み込みに失敗しました');
        }
    } catch (error) {
        showCategoryError('カテゴリの読み込み中にエラーが発生しました: ' + error.message);
    } finally {
        if (loadingIndicator) loadingIndicator.style.display = 'none';
    }
}

// カテゴリ一覧を表示
function renderCategoriesForManagement(cats) {
    const categoriesList = document.getElementById('categoriesList');
    const emptyMessage = document.getElementById('categoryEmptyMessage');
    
    if (!cats || cats.length === 0) {
        if (categoriesList) categoriesList.innerHTML = '';
        if (emptyMessage) emptyMessage.style.display = 'flex';
        return;
    }
    
    if (emptyMessage) emptyMessage.style.display = 'none';
    
    const categoriesHtml = cats.map(category => `
        <div class="category-card ${category.is_active ? '' : 'inactive'}" style="background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: flex-start;">
            <div style="flex: 1;">
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                    <h4 style="margin: 0; font-size: 1.125rem;">${escapeHtml(category.name)}</h4>
                    <span class="status-badge ${category.is_active ? 'available' : 'unavailable'}" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;">
                        ${category.is_active ? '✓ 有効' : '✗ 無効'}
                    </span>
                </div>
                ${category.description ? `<p style="color: var(--text-secondary); margin: 0.5rem 0; font-size: 0.875rem;">${escapeHtml(category.description)}</p>` : ''}
                <div style="display: flex; gap: 1rem; margin-top: 0.75rem; font-size: 0.875rem; color: var(--text-secondary);">
                    <span>📋 ${category.menu_count || 0}件のメニュー</span>
                    <span>🔢 表示順: ${category.display_order}</span>
                </div>
            </div>
            <div style="display: flex; gap: 0.5rem;">
                <button type="button" class="btn btn-sm btn-secondary" onclick="openEditCategoryModal(${category.id})" title="編集">
                    ✏️ 編集
                </button>
                <button type="button" class="btn btn-sm btn-danger" onclick="openDeleteCategoryModal(${category.id})" title="削除">
                    🗑️
                </button>
            </div>
        </div>
    `).join('');
    
    if (categoriesList) {
        categoriesList.innerHTML = categoriesHtml;
    }
}

// カテゴリエラー表示
function showCategoryError(message) {
    const errorMessage = document.getElementById('categoryErrorMessage');
    const categoriesList = document.getElementById('categoriesList');
    
    if (errorMessage) {
        errorMessage.innerHTML = `
            <p>❌ ${escapeHtml(message)}</p>
            <button class="btn btn-primary" onclick="loadCategoriesForManagement()">再読み込み</button>
        `;
        errorMessage.style.display = 'block';
    }
    
    if (categoriesList) {
        categoriesList.innerHTML = '';
    }
}

// カテゴリ追加モーダルを開く
function openAddCategoryModal() {
    currentEditingCategoryId = null;
    const modal = document.getElementById('categoryModal');
    const modalTitle = document.getElementById('categoryModalTitle');
    const form = document.getElementById('categoryForm');
    const isActive = document.getElementById('categoryIsActive');
    const submitBtn = document.getElementById('submitCategoryBtn');
    
    if (modalTitle) modalTitle.textContent = 'カテゴリ追加';
    if (form) form.reset();
    if (isActive) isActive.checked = true;
    if (submitBtn) submitBtn.textContent = '作成';
    if (modal) modal.style.display = 'flex';
}

// カテゴリ編集モーダルを開く
async function openEditCategoryModal(categoryId) {
    currentEditingCategoryId = categoryId;
    const modal = document.getElementById('categoryModal');
    const modalTitle = document.getElementById('categoryModalTitle');
    const submitBtn = document.getElementById('submitCategoryBtn');
    
    if (modalTitle) modalTitle.textContent = 'カテゴリ編集';
    if (submitBtn) submitBtn.textContent = '更新';
    
    try {
        const response = await ApiClient.get('/store/menu-categories');
        
        if (response && response.categories) {
            const category = response.categories.find(c => c.id === categoryId);
            if (category) {
                const nameInput = document.getElementById('categoryName');
                const descInput = document.getElementById('categoryDescription');
                const orderInput = document.getElementById('displayOrder');
                const activeInput = document.getElementById('categoryIsActive');
                
                if (nameInput) nameInput.value = category.name;
                if (descInput) descInput.value = category.description || '';
                if (orderInput) orderInput.value = category.display_order;
                if (activeInput) activeInput.checked = category.is_active;
                if (modal) modal.style.display = 'flex';
            }
        }
    } catch (error) {
        showToast('カテゴリ情報の取得に失敗しました', 'error');
    }
}

// カテゴリモーダルを閉じる
function closeCategoryModalForm() {
    const modal = document.getElementById('categoryModal');
    if (modal) modal.style.display = 'none';
    currentEditingCategoryId = null;
}

// カテゴリフォーム送信
async function handleCategoryFormSubmit(e) {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('categoryName').value.trim(),
        description: document.getElementById('categoryDescription').value.trim() || null,
        display_order: parseInt(document.getElementById('displayOrder').value),
        is_active: document.getElementById('categoryIsActive').checked
    };

    try {
        if (currentEditingCategoryId) {
            await ApiClient.put(`/store/menu-categories/${currentEditingCategoryId}`, formData);
            showToast('カテゴリを更新しました', 'success');
        } else {
            await ApiClient.post('/store/menu-categories', formData);
            showToast('カテゴリを追加しました', 'success');
        }
        
        closeCategoryModalForm();
        await fetchCategories(); // カテゴリ一覧を更新
        loadCategoriesForManagement(); // カテゴリ管理モーダルを更新
        updateCategorySelects(); // フィルタとメニューフォームのセレクトを更新
    } catch (error) {
        showToast('カテゴリの保存に失敗しました: ' + (error.detail || error.message), 'error');
    }
}

// カテゴリ削除モーダルを開く
async function openDeleteCategoryModal(categoryId) {
    currentEditingCategoryId = categoryId;
    const modal = document.getElementById('deleteCategoryModal');
    const deleteMessage = document.getElementById('deleteCategoryMessage');
    
    try {
        const response = await ApiClient.get('/store/menu-categories');
        
        if (response && response.categories) {
            const category = response.categories.find(c => c.id === categoryId);
            if (category) {
                const menuCount = category.menu_count || 0;
                if (deleteMessage) {
                    if (menuCount > 0) {
                        deleteMessage.innerHTML = `
                            カテゴリ「<strong>${escapeHtml(category.name)}</strong>」を削除しますか?<br>
                            このカテゴリには${menuCount}件のメニューが含まれています。
                        `;
                    } else {
                        deleteMessage.innerHTML = `カテゴリ「<strong>${escapeHtml(category.name)}</strong>」を削除しますか?`;
                    }
                }
            }
        }
    } catch (error) {
        console.error('カテゴリ情報の取得に失敗:', error);
    }
    
    if (modal) modal.style.display = 'flex';
}

// カテゴリ削除モーダルを閉じる
function closeDeleteCategoryModal() {
    const modal = document.getElementById('deleteCategoryModal');
    if (modal) modal.style.display = 'none';
    currentEditingCategoryId = null;
}

// カテゴリ削除を実行
async function confirmDeleteCategory() {
    if (!currentEditingCategoryId) return;

    try {
        const response = await ApiClient.delete(`/store/menu-categories/${currentEditingCategoryId}`);
        
        showToast(response.message || 'カテゴリを削除しました', 'success');
        closeDeleteCategoryModal();
        await fetchCategories(); // カテゴリ一覧を更新
        loadCategoriesForManagement(); // カテゴリ管理モーダルを更新
        updateCategorySelects(); // フィルタとメニューフォームのセレクトを更新
        await fetchMenus(); // メニュー一覧を更新（カテゴリが削除されたメニューを反映）
    } catch (error) {
        showToast('カテゴリの削除に失敗しました: ' + (error.detail || error.message), 'error');
    }
}

// カテゴリ管理のイベントリスナーを設定
document.addEventListener('DOMContentLoaded', () => {
    // カテゴリ管理ボタン
    const manageCategoriesBtn = document.getElementById('manageCategoriesBtn');
    if (manageCategoriesBtn) {
        manageCategoriesBtn.addEventListener('click', openCategoryManagementModal);
    }
    
    // カテゴリ管理モーダルを閉じる
    const closeCategoryManagementBtn = document.getElementById('closeCategoryManagementModal');
    if (closeCategoryManagementBtn) {
        closeCategoryManagementBtn.addEventListener('click', closeCategoryManagementModal);
    }
    
    // カテゴリ追加ボタン
    const addCategoryBtn = document.getElementById('addCategoryBtn');
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', openAddCategoryModal);
    }
    
    // カテゴリフォーム
    const categoryForm = document.getElementById('categoryForm');
    if (categoryForm) {
        categoryForm.addEventListener('submit', handleCategoryFormSubmit);
    }
    
    // カテゴリモーダルを閉じる
    const closeCategoryModalBtn = document.getElementById('closeCategoryModal');
    const cancelCategoryBtn = document.getElementById('cancelCategoryBtn');
    if (closeCategoryModalBtn) {
        closeCategoryModalBtn.addEventListener('click', closeCategoryModalForm);
    }
    if (cancelCategoryBtn) {
        cancelCategoryBtn.addEventListener('click', closeCategoryModalForm);
    }
    
    // カテゴリ削除モーダルを閉じる
    const closeDeleteCategoryModalBtn = document.getElementById('closeDeleteCategoryModal');
    const cancelDeleteCategoryBtn = document.getElementById('cancelDeleteCategoryBtn');
    if (closeDeleteCategoryModalBtn) {
        closeDeleteCategoryModalBtn.addEventListener('click', closeDeleteCategoryModal);
    }
    if (cancelDeleteCategoryBtn) {
        cancelDeleteCategoryBtn.addEventListener('click', closeDeleteCategoryModal);
    }
    
    // カテゴリ削除確認
    const confirmDeleteCategoryBtn = document.getElementById('confirmDeleteCategoryBtn');
    if (confirmDeleteCategoryBtn) {
        confirmDeleteCategoryBtn.addEventListener('click', confirmDeleteCategory);
    }
    
    // モーダル外クリックで閉じる
    const categoryManagementModal = document.getElementById('categoryManagementModal');
    const categoryModal = document.getElementById('categoryModal');
    const deleteCategoryModal = document.getElementById('deleteCategoryModal');
    
    if (categoryManagementModal) {
        categoryManagementModal.addEventListener('click', (e) => {
            if (e.target === categoryManagementModal) {
                closeCategoryManagementModal();
            }
        });
    }
    
    if (categoryModal) {
        categoryModal.addEventListener('click', (e) => {
            if (e.target === categoryModal) {
                closeCategoryModalForm();
            }
        });
    }
    
    if (deleteCategoryModal) {
        deleteCategoryModal.addEventListener('click', (e) => {
            if (e.target === deleteCategoryModal) {
                closeDeleteCategoryModal();
            }
        });
    }
});

// ===== 監査ログ機能 =====

// 監査ログモーダルを開く
async function openAuditLogModal() {
    const modal = document.getElementById('auditLogModal');
    if (!modal) return;
    
    modal.style.display = 'block';
    
    // フィルターをクリア
    document.getElementById('auditActionFilter').value = '';
    document.getElementById('auditStartDate').value = '';
    document.getElementById('auditEndDate').value = '';
    
    // ログを読み込み
    await loadAuditLogs();
}

// 監査ログモーダルを閉じる
function closeAuditLogModal() {
    const modal = document.getElementById('auditLogModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 監査ログを読み込み
async function loadAuditLogs(page = 1) {
    const loading = document.getElementById('auditLogLoading');
    const list = document.getElementById('auditLogList');
    const empty = document.getElementById('auditLogEmpty');
    const pagination = document.getElementById('auditLogPagination');
    
    try {
        // ローディング表示
        if (loading) loading.style.display = 'block';
        if (list) list.innerHTML = '';
        if (empty) empty.style.display = 'none';
        if (pagination) pagination.style.display = 'none';
        
        // フィルター値を取得
        const action = document.getElementById('auditActionFilter')?.value || '';
        const startDate = document.getElementById('auditStartDate')?.value || '';
        const endDate = document.getElementById('auditEndDate')?.value || '';
        
        // クエリパラメータを構築
        const params = new URLSearchParams({
            page: page,
            per_page: 20
        });
        
        if (action) params.append('action', action);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        
        // APIリクエスト
        const response = await ApiClient.get(`/store/change-logs?${params.toString()}`);
        
        // ローディング非表示
        if (loading) loading.style.display = 'none';
        
        if (response.logs && response.logs.length > 0) {
            // ログを表示
            renderAuditLogs(response.logs);
            
            // ページネーション表示
            renderAuditLogPagination(response.total, page);
        } else {
            // 空メッセージ表示
            if (empty) empty.style.display = 'block';
        }
        
    } catch (error) {
        console.error('監査ログの読み込みに失敗:', error);
        if (loading) loading.style.display = 'none';
        UI.showToast('監査ログの読み込みに失敗しました', 'error');
    }
}

// 監査ログを表示
function renderAuditLogs(logs) {
    const list = document.getElementById('auditLogList');
    if (!list) return;
    
    list.innerHTML = logs.map(log => {
        const actionClass = log.action;
        const actionIcon = log.action === 'create' ? '➕' : 
                          log.action === 'update' ? '✏️' : '🗑️';
        const actionText = log.action === 'create' ? '作成' : 
                          log.action === 'update' ? '更新' : '削除';
        
        const date = new Date(log.changed_at);
        const formattedDate = date.toLocaleString('ja-JP', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        const userName = log.user ? 
            `${log.user.full_name || log.user.username}` : 
            '不明';
        
        // 変更内容を表示
        let changesHtml = '';
        if (log.changes && typeof log.changes === 'object') {
            changesHtml = '<div class="audit-log-changes">';
            
            // フィールド名の日本語マッピング
            const fieldNames = {
                'name': 'メニュー名',
                'price': '価格',
                'description': '説明',
                'is_available': '公開状態',
                'category_id': 'カテゴリID',
                'image_url': '画像URL'
            };
            
            for (const [field, value] of Object.entries(log.changes)) {
                const fieldName = fieldNames[field] || field;
                
                if (typeof value === 'object' && value.old !== undefined && value.new !== undefined) {
                    // 更新の場合
                    let oldValue = value.old || '(なし)';
                    let newValue = value.new || '(なし)';
                    
                    // 価格の場合は円マークをつける
                    if (field === 'price') {
                        oldValue = oldValue !== '(なし)' ? `¥${oldValue}` : oldValue;
                        newValue = newValue !== '(なし)' ? `¥${newValue}` : newValue;
                    }
                    
                    // 公開状態の場合は日本語に
                    if (field === 'is_available') {
                        oldValue = oldValue === 'True' || oldValue === 'true' ? '公開' : '非公開';
                        newValue = newValue === 'True' || newValue === 'true' ? '公開' : '非公開';
                    }
                    
                    changesHtml += `
                        <div class="audit-change-item">
                            <div class="audit-change-field">${fieldName}:</div>
                            <div class="audit-change-values">
                                <span class="audit-change-old">${oldValue}</span>
                                <span class="audit-change-arrow">→</span>
                                <span class="audit-change-new">${newValue}</span>
                            </div>
                        </div>
                    `;
                } else {
                    // 作成または削除の場合
                    const displayValue = value !== null && value !== undefined ? value : '(なし)';
                    changesHtml += `
                        <div class="audit-change-item">
                            <div class="audit-change-field">${fieldName}:</div>
                            <div class="audit-change-values">
                                <span>${displayValue}</span>
                            </div>
                        </div>
                    `;
                }
            }
            
            changesHtml += '</div>';
        }
        
        return `
            <div class="audit-log-item">
                <div class="audit-log-header">
                    <div class="audit-log-info">
                        <div class="audit-log-action ${actionClass}">
                            ${actionIcon} ${actionText}
                        </div>
                        <div class="audit-log-time">🕐 ${formattedDate}</div>
                        <div class="audit-log-user">👤 ${userName}</div>
                    </div>
                </div>
                ${changesHtml}
            </div>
        `;
    }).join('');
}

// 監査ログのページネーション
function renderAuditLogPagination(total, currentPage) {
    const paginationSection = document.getElementById('auditLogPagination');
    const paginationInfo = document.getElementById('auditPaginationInfo');
    const pagination = document.getElementById('auditPagination');
    
    if (!paginationSection || !pagination) return;
    
    const perPage = 20;
    const totalPages = Math.ceil(total / perPage);
    
    if (totalPages <= 1) {
        paginationSection.style.display = 'none';
        return;
    }
    
    paginationSection.style.display = 'flex';
    
    // ページ情報
    const start = (currentPage - 1) * perPage + 1;
    const end = Math.min(currentPage * perPage, total);
    if (paginationInfo) {
        paginationInfo.textContent = `${start}-${end} / ${total}件`;
    }
    
    // ページネーションボタン
    let paginationHtml = '';
    
    // 前へボタン
    if (currentPage > 1) {
        paginationHtml += `<button class="pagination-btn" onclick="loadAuditLogs(${currentPage - 1})">‹ 前へ</button>`;
    }
    
    // ページ番号
    const maxButtons = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    
    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }
    
    if (startPage > 1) {
        paginationHtml += `<button class="pagination-btn" onclick="loadAuditLogs(1)">1</button>`;
        if (startPage > 2) {
            paginationHtml += `<span class="pagination-ellipsis">...</span>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === currentPage ? 'active' : '';
        paginationHtml += `<button class="pagination-btn ${activeClass}" onclick="loadAuditLogs(${i})">${i}</button>`;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHtml += `<span class="pagination-ellipsis">...</span>`;
        }
        paginationHtml += `<button class="pagination-btn" onclick="loadAuditLogs(${totalPages})">${totalPages}</button>`;
    }
    
    // 次へボタン
    if (currentPage < totalPages) {
        paginationHtml += `<button class="pagination-btn" onclick="loadAuditLogs(${currentPage + 1})">次へ ›</button>`;
    }
    
    pagination.innerHTML = paginationHtml;
}

// イベントリスナーを追加
document.addEventListener('DOMContentLoaded', () => {
    // 監査ログボタン - Owner と Manager のみ表示
    const viewAuditLogsBtn = document.getElementById('viewAuditLogsBtn');
    if (viewAuditLogsBtn) {
        const user = Auth.getUser();
        const hasAuditPermission = user && user.user_roles && 
            user.user_roles.some(ur => ur.role && 
                (ur.role.name === 'owner' || ur.role.name === 'manager'));
        
        if (hasAuditPermission) {
            viewAuditLogsBtn.style.display = 'inline-flex';
            viewAuditLogsBtn.addEventListener('click', openAuditLogModal);
        } else {
            viewAuditLogsBtn.style.display = 'none';
        }
    }
    
    // 監査ログモーダルを閉じる
    const closeAuditLogModal = document.getElementById('closeAuditLogModal');
    if (closeAuditLogModal) {
        closeAuditLogModal.addEventListener('click', () => {
            document.getElementById('auditLogModal').style.display = 'none';
        });
    }
    
    // フィルター適用ボタン
    const applyAuditFiltersBtn = document.getElementById('applyAuditFiltersBtn');
    if (applyAuditFiltersBtn) {
        applyAuditFiltersBtn.addEventListener('click', () => loadAuditLogs(1));
    }
    
    // フィルタークリアボタン
    const clearAuditFiltersBtn = document.getElementById('clearAuditFiltersBtn');
    if (clearAuditFiltersBtn) {
        clearAuditFiltersBtn.addEventListener('click', () => {
            document.getElementById('auditActionFilter').value = '';
            document.getElementById('auditStartDate').value = '';
            document.getElementById('auditEndDate').value = '';
            loadAuditLogs(1);
        });
    }
    
    // モーダル外クリックで閉じる
    const auditLogModal = document.getElementById('auditLogModal');
    if (auditLogModal) {
        auditLogModal.addEventListener('click', (e) => {
            if (e.target === auditLogModal) {
                auditLogModal.style.display = 'none';
            }
        });
    }
});
