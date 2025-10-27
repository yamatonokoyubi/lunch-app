// カテゴリ管理機能
let currentCategoryId = null;

// ページ読み込み時に実行
document.addEventListener('DOMContentLoaded', () => {
    fetchCategories();
    setupEventListeners();
});

// イベントリスナーの設定
function setupEventListeners() {
    const createBtn = document.getElementById('createCategoryBtn');
    const categoryForm = document.getElementById('categoryForm');
    const closeModalBtn = document.getElementById('closeCategoryModal');
    const cancelCategoryBtn = document.getElementById('cancelCategoryBtn');
    const closeDeleteBtn = document.getElementById('closeDeleteModal');
    const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    
    if (createBtn) {
        createBtn.addEventListener('click', openCreateModal);
    }
    
    if (categoryForm) {
        categoryForm.addEventListener('submit', handleSubmit);
    }
    
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeCategoryModal);
    }
    
    if (cancelCategoryBtn) {
        cancelCategoryBtn.addEventListener('click', closeCategoryModal);
    }
    
    if (closeDeleteBtn) {
        closeDeleteBtn.addEventListener('click', closeDeleteModal);
    }
    
    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', closeDeleteModal);
    }
    
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', confirmDelete);
    }
    
    // モーダル外クリックで閉じる
    const categoryModal = document.getElementById('categoryModal');
    const deleteModal = document.getElementById('deleteModal');
    
    if (categoryModal) {
        categoryModal.addEventListener('click', (e) => {
            if (e.target === categoryModal) {
                closeCategoryModal();
            }
        });
    }
    
    if (deleteModal) {
        deleteModal.addEventListener('click', (e) => {
            if (e.target === deleteModal) {
                closeDeleteModal();
            }
        });
    }
}

// カテゴリ一覧を取得
async function fetchCategories() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorMessage = document.getElementById('errorMessage');
    const emptyMessage = document.getElementById('emptyMessage');
    const categoriesList = document.getElementById('categoriesList');
    
    if (loadingIndicator) loadingIndicator.style.display = 'flex';
    if (errorMessage) errorMessage.style.display = 'none';
    if (emptyMessage) emptyMessage.style.display = 'none';
    if (categoriesList) categoriesList.innerHTML = '';

    try {
        const response = await ApiClient.get('/store/menu-categories');
        
        if (response && response.categories) {
            renderCategories(response.categories);
        } else {
            showError('カテゴリの読み込みに失敗しました');
        }
    } catch (error) {
        showError('カテゴリの読み込み中にエラーが発生しました: ' + error.message);
    } finally {
        if (loadingIndicator) loadingIndicator.style.display = 'none';
    }
}

// カテゴリを表示
function renderCategories(categories) {
    const categoriesList = document.getElementById('categoriesList');
    const emptyMessage = document.getElementById('emptyMessage');
    
    if (!categories || categories.length === 0) {
        if (categoriesList) categoriesList.innerHTML = '';
        if (emptyMessage) emptyMessage.style.display = 'flex';
        return;
    }
    
    if (emptyMessage) emptyMessage.style.display = 'none';

    const categoriesHtml = categories.map(category => `
        <div class="category-card ${category.is_active ? '' : 'inactive'}">
            <div class="category-info">
                <div class="category-header">
                    <h3 class="category-name">${escapeHtml(category.name)}</h3>
                    <span class="category-badge ${category.is_active ? 'active' : 'inactive'}">
                        ${category.is_active ? '✓ 有効' : '✗ 無効'}
                    </span>
                </div>
                ${category.description ? `<p class="category-description">${escapeHtml(category.description)}</p>` : ''}
                <div class="category-meta">
                    <span class="category-meta-item">
                        <span>📋</span>
                        <span>${category.menu_count || 0}件のメニュー</span>
                    </span>
                    <span class="category-meta-item">
                        <span>🔢</span>
                        <span>表示順: ${category.display_order}</span>
                    </span>
                </div>
            </div>
            <div class="category-actions">
                <button type="button" class="btn-icon edit" onclick="openEditModal(${category.id})" title="編集">
                    ✏️
                </button>
                <button type="button" class="btn-icon delete" onclick="openDeleteModal(${category.id})" title="削除">
                    🗑️
                </button>
            </div>
        </div>
    `).join('');

    if (categoriesList) {
        categoriesList.innerHTML = categoriesHtml;
    }
}

// 作成モーダルを開く
function openCreateModal() {
    currentCategoryId = null;
    const modal = document.getElementById('categoryModal');
    const modalTitle = document.getElementById('modalTitle');
    const form = document.getElementById('categoryForm');
    const isActive = document.getElementById('isActive');
    const submitBtn = document.getElementById('submitBtn');
    
    if (modalTitle) modalTitle.textContent = '新しいカテゴリを追加';
    if (form) form.reset();
    if (isActive) isActive.checked = true;
    if (submitBtn) submitBtn.textContent = '作成';
    if (modal) modal.style.display = 'flex';
}

// 編集モーダルを開く
async function openEditModal(categoryId) {
    currentCategoryId = categoryId;
    const modal = document.getElementById('categoryModal');
    const modalTitle = document.getElementById('modalTitle');
    const submitBtn = document.getElementById('submitBtn');
    
    if (modalTitle) modalTitle.textContent = 'カテゴリを編集';
    if (submitBtn) submitBtn.textContent = '更新';
    
    try {
        const response = await ApiClient.get('/store/menu-categories');
        
        if (response && response.categories) {
            const category = response.categories.find(c => c.id === categoryId);
            if (category) {
                const nameInput = document.getElementById('categoryName');
                const descInput = document.getElementById('categoryDescription');
                const orderInput = document.getElementById('displayOrder');
                const activeInput = document.getElementById('isActive');
                
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

// モーダルを閉じる
function closeCategoryModal() {
    const modal = document.getElementById('categoryModal');
    if (modal) modal.style.display = 'none';
    currentCategoryId = null;
}

// フォーム送信
async function handleSubmit(e) {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('categoryName').value,
        description: document.getElementById('categoryDescription').value || null,
        display_order: parseInt(document.getElementById('displayOrder').value),
        is_active: document.getElementById('isActive').checked
    };

    try {
        let response;
        if (currentCategoryId) {
            // 更新
            response = await ApiClient.put(`/store/menu-categories/${currentCategoryId}`, formData);
        } else {
            // 作成
            response = await ApiClient.post('/store/menu-categories', formData);
        }

        showToast(currentCategoryId ? 'カテゴリを更新しました' : 'カテゴリを追加しました', 'success');
        closeCategoryModal();
        fetchCategories();
    } catch (error) {
        showToast('カテゴリの保存に失敗しました: ' + (error.detail || error.message), 'error');
    }
}

// 削除モーダルを開く
async function openDeleteModal(categoryId) {
    currentCategoryId = categoryId;
    const modal = document.getElementById('deleteModal');
    const deleteMessage = document.getElementById('deleteMessage');
    
    // カテゴリ情報を取得してメニュー数を表示
    try {
        const response = await ApiClient.get('/store/menu-categories');
        
        if (response && response.categories) {
            const category = response.categories.find(c => c.id === categoryId);
            if (category) {
                const menuCount = category.menu_count || 0;
                if (deleteMessage) {
                    if (menuCount > 0) {
                        deleteMessage.innerHTML = `
                            カテゴリ「${escapeHtml(category.name)}」を削除しますか?<br>
                            このカテゴリには${menuCount}件のメニューが含まれています。
                        `;
                    } else {
                        deleteMessage.textContent = `カテゴリ「${category.name}」を削除しますか?`;
                    }
                }
            }
        }
    } catch (error) {
        console.error('カテゴリ情報の取得に失敗:', error);
    }
    
    if (modal) modal.style.display = 'flex';
}

// 削除モーダルを閉じる
function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    if (modal) modal.style.display = 'none';
    currentCategoryId = null;
}

// 削除を実行
async function confirmDelete() {
    if (!currentCategoryId) return;

    try {
        const response = await ApiClient.delete(`/store/menu-categories/${currentCategoryId}`);
        
        showToast(response.message || 'カテゴリを削除しました', 'success');
        closeDeleteModal();
        fetchCategories();
    } catch (error) {
        showToast('カテゴリの削除に失敗しました: ' + (error.detail || error.message), 'error');
    }
}

// エラー表示
function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    const categoriesList = document.getElementById('categoriesList');
    
    if (errorMessage) {
        errorMessage.innerHTML = `
            <p>❌ ${escapeHtml(message)}</p>
            <button class="btn btn-primary" onclick="fetchCategories()">再読み込み</button>
        `;
        errorMessage.style.display = 'block';
    }
    
    if (categoriesList) {
        categoriesList.innerHTML = '';
    }
}

// HTML エスケープ
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
