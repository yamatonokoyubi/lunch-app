/**
 * 店舗プロフィール画面のJavaScriptロジック
 */

// グローバル変数
let storeData = null;
let userRoles = [];
let isOwner = false;
let isManager = false;
let isStaff = false;
let originalImageUrl = null;
let currentStoreId = null; // Owner用: 現在表示中の店舗ID
let allStores = []; // Owner用: 全店舗リスト

// 初期化
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // 認証チェック
        if (!Auth.requireRole('store')) return;

        // ヘッダー情報を表示
        await UI.initializeStoreHeader();

        // 共通UI初期化（ログアウトボタンなど）
        initializeCommonUI();

        // ユーザー情報を取得して役割を判定
        await loadUserRoles();

        // Owner用の店舗選択UIを初期化
        if (isOwner) {
            await initializeStoreSelector();
        }

        // 店舗プロフィールを読み込む
        await loadStoreProfile();
        
    } catch (error) {
        console.error('Initialization error:', error);
        const errorMessage = document.getElementById('error-message');
        const errorText = document.getElementById('error-text');
        if (errorMessage && errorText) {
            errorText.textContent = `初期化エラー: ${error.message}`;
            errorMessage.style.display = 'block';
        }
    }
});

/**
 * ユーザーの役割を取得
 */
async function loadUserRoles() {
    try {
        const currentUser = await apiClient.getCurrentUser();
        userRoles = currentUser.user_roles.map(ur => ur.role.name);
        isOwner = userRoles.includes('owner');
        isManager = userRoles.includes('manager');
        isStaff = userRoles.includes('staff');
        
        console.log('User roles:', { isOwner, isManager, isStaff });
    } catch (error) {
        console.error('Error loading user roles:', error);
        throw error;
    }
}

/**
 * Owner用: 店舗選択ドロップダウンを初期化
 */
async function initializeStoreSelector() {
    console.log('Initializing store selector for Owner...');
    const selectorSection = document.getElementById('store-selector-section');
    const selector = document.getElementById('store-selector');

    if (!selectorSection || !selector) {
        console.error('Store selector elements not found:', { selectorSection, selector });
        return;
    }

    try {
        console.log('Fetching stores list...');
        // 全店舗一覧を取得
        const response = await apiClient.get('/store/stores');
        console.log('Stores response:', response);
        allStores = response.stores;

        if (!allStores || allStores.length === 0) {
            console.warn('No stores found');
            showErrorMessage('管理可能な店舗が見つかりませんでした');
            return;
        }

        // ドロップダウンのオプションを生成
        selector.innerHTML = '';
        allStores.forEach(store => {
            const option = document.createElement('option');
            option.value = store.id;
            option.textContent = `${store.name}${store.is_active ? '' : ' (休業中)'}`;
            selector.appendChild(option);
        });

        // デフォルトでstore_id=1（真徳弁当飫肥店）を選択
        const defaultStoreId = 1;
        const defaultStore = allStores.find(store => store.id === defaultStoreId);
        
        if (defaultStore) {
            currentStoreId = defaultStoreId;
            selector.value = currentStoreId;
            console.log('Default store selected (ID=1):', defaultStore.name);
        } else if (allStores.length > 0) {
            // store_id=1が存在しない場合は最初の店舗を選択
            currentStoreId = allStores[0].id;
            selector.value = currentStoreId;
            console.log('Default store selected (first):', currentStoreId);
        }

        // 店舗選択イベント
        selector.addEventListener('change', async (e) => {
            currentStoreId = parseInt(e.target.value);
            console.log('Store changed to:', currentStoreId);
            await loadStoreProfile();
        });

        // 表示
        selectorSection.style.display = 'block';
        console.log('Store selector displayed successfully');

    } catch (error) {
        console.error('Error initializing store selector:', error);
        showErrorMessage(`店舗一覧の取得に失敗しました: ${error.message}`);
    }
}

/**
 * 店舗プロフィールを読み込む
 */
async function loadStoreProfile() {
    console.log('Loading store profile...', { isOwner, isManager, isStaff, currentStoreId });
    const loading = document.getElementById('loading');
    const errorMessage = document.getElementById('error-message');
    const storeContent = document.getElementById('store-content');

    try {
        loading.style.display = 'block';
        errorMessage.style.display = 'none';
        storeContent.style.display = 'none';

        // 認証チェック
        const authToken = localStorage.getItem('authToken');
        if (!authToken) {
            window.location.href = '/login?redirect=/store/profile';
            return;
        }

        // 店舗情報を取得
        let apiUrl = '/store/profile';
        
        // Owner: store_idをクエリパラメータで指定
        if (isOwner) {
            // currentStoreIdが未設定の場合はデフォルトで1を使用
            const storeIdToFetch = currentStoreId || 1;
            apiUrl = `/store/profile?store_id=${storeIdToFetch}`;
            console.log('Owner mode: fetching store with ID', storeIdToFetch);
            
            // currentStoreIdが未設定の場合は設定
            if (!currentStoreId) {
                currentStoreId = storeIdToFetch;
                console.log('Set default currentStoreId to:', currentStoreId);
            }
        }
        // Manager/Staff: パラメータなし（自店舗を自動取得）
        
        console.log('Fetching store profile from:', apiUrl);
        const response = await apiClient.get(apiUrl);
        storeData = response;
        console.log('Store data loaded:', storeData);

        // 画面を表示
        displayStoreInfo(storeData);
        setupFormBehavior();

        loading.style.display = 'none';
        storeContent.style.display = 'block';

    } catch (error) {
        loading.style.display = 'none';
        
        // 401エラーの場合はログインページにリダイレクト
        if (error.message && error.message.includes('401')) {
            localStorage.removeItem('authToken');
            localStorage.removeItem('currentUser');
            window.location.href = '/login?redirect=/store/profile';
            return;
        }
        
        errorMessage.style.display = 'block';
        document.getElementById('error-text').textContent = 
            `エラーが発生しました: ${error.message || '店舗情報を読み込めませんでした'}`;
        console.error('Error loading store profile:', error);
    }
}

/**
 * 店舗情報を画面に表示
 */
function displayStoreInfo(store) {
    // 画像
    const storeImage = document.getElementById('store-image');
    const deleteImageButton = document.getElementById('delete-image-button');
    
    if (store.image_url) {
        storeImage.src = store.image_url;
        originalImageUrl = store.image_url;
        // Owner/Managerのみ削除ボタンを表示
        if ((isOwner || isManager) && deleteImageButton) {
            deleteImageButton.style.display = 'inline-block';
        }
    } else {
        storeImage.src = '/static/images/no-image.svg';
        originalImageUrl = null;
        if (deleteImageButton) {
            deleteImageButton.style.display = 'none';
        }
    }

    // 基本情報
    document.getElementById('store-name').value = store.name || '';
    document.getElementById('store-email').value = store.email || '';
    document.getElementById('store-phone').value = store.phone_number || '';
    document.getElementById('store-address').value = store.address || '';

    // 営業時間
    document.getElementById('opening-time').value = store.opening_time || '';
    document.getElementById('closing-time').value = store.closing_time || '';

    // 説明
    document.getElementById('store-description').value = store.description || '';

    // ステータス
    document.getElementById('store-active').checked = store.is_active;

    // メタ情報
    document.getElementById('created-at').textContent = formatDateTime(store.created_at);
    document.getElementById('updated-at').textContent = formatDateTime(store.updated_at);
}

/**
 * フォームの動作を設定
 */
function setupFormBehavior() {
    console.log('Setting up form behavior...', { isOwner, isManager, isStaff });
    
    const form = document.getElementById('store-form');
    const inputs = form.querySelectorAll('input, textarea');
    const saveButtonSection = document.getElementById('save-button-section');
    const readonlyMessage = document.getElementById('readonly-message');
    const imageUploadSection = document.getElementById('image-upload-section');
    const cancelButton = document.getElementById('cancel-button');
    const imageFile = document.getElementById('image-file');
    const deleteImageButton = document.getElementById('delete-image-button');

    if (!form) {
        console.error('Store form not found!');
        return;
    }

    if (isStaff) {
        console.log('Configuring form for Staff (read-only)');
        // Staff: 完全に読み取り専用
        inputs.forEach(input => {
            input.disabled = true;
            input.classList.add('readonly');
        });
        
        // 保存ボタンを非表示
        if (saveButtonSection) {
            saveButtonSection.style.display = 'none';
            console.log('Save button section hidden for Staff');
        }
        
        // 画像アップロードセクションを非表示
        if (imageUploadSection) {
            imageUploadSection.style.display = 'none';
        }
        
        // 読み取り専用メッセージを表示
        if (readonlyMessage) {
            readonlyMessage.style.display = 'block';
        }
        
        // ページ説明を更新
        const pageDescription = document.getElementById('page-description');
        if (pageDescription) {
            pageDescription.textContent = '店舗の基本情報を確認（閲覧専用）';
        }

    } else if (isManager || isOwner) {
        console.log('Configuring form for Manager/Owner (editable)');
        
        // Manager/Owner: 編集可能
        console.log('Found inputs:', inputs.length);
        inputs.forEach(input => {
            input.disabled = false;
            input.classList.remove('readonly');
            console.log('Enabled input:', input.id || input.name);
        });
        
        // 保存ボタンを表示
        if (saveButtonSection) {
            saveButtonSection.style.display = 'flex';
            console.log('✅ Save button section displayed:', saveButtonSection.style.display);
        } else {
            console.error('❌ Save button section not found!');
        }
        
        // 画像アップロードセクションを表示
        if (imageUploadSection) {
            imageUploadSection.style.display = 'block';
            console.log('Image upload section displayed');
        }
        
        // 読み取り専用メッセージを非表示
        if (readonlyMessage) {
            readonlyMessage.style.display = 'none';
        }
        
        // ページ説明を更新
        const pageDescription = document.getElementById('page-description');
        if (pageDescription) {
            pageDescription.textContent = '店舗の基本情報を確認・編集';
        }

        // 既存のイベントリスナーを削除（重複防止）
        const newForm = form.cloneNode(true);
        form.parentNode.replaceChild(newForm, form);
        const refreshedForm = document.getElementById('store-form');

        // フォーム送信イベント
        refreshedForm.addEventListener('submit', handleFormSubmit);
        console.log('Form submit handler attached');

        // キャンセルボタン
        const refreshedCancelButton = document.getElementById('cancel-button');
        if (refreshedCancelButton) {
            refreshedCancelButton.addEventListener('click', () => {
                if (confirm('変更を破棄してもよろしいですか?')) {
                    displayStoreInfo(storeData);
                }
            });
            console.log('Cancel button handler attached');
        }

        // 画像アップロード
        const refreshedImageFile = document.getElementById('image-file');
        if (refreshedImageFile) {
            refreshedImageFile.addEventListener('change', handleImageUpload);
            console.log('Image upload handler attached');
        }

        // 画像削除
        const refreshedDeleteButton = document.getElementById('delete-image-button');
        if (refreshedDeleteButton) {
            refreshedDeleteButton.addEventListener('click', handleImageDelete);
            console.log('Image delete handler attached');
        }
        
        // 保存ボタンの表示を再確認（クローン後）
        const refreshedSaveButtonSection = document.getElementById('save-button-section');
        if (refreshedSaveButtonSection) {
            refreshedSaveButtonSection.style.display = 'flex';
            console.log('✅ Save button re-displayed after cloning');
        }
        
    } else {
        console.warn('Unknown user role configuration');
    }
}

/**
 * フォーム送信処理
 */
async function handleFormSubmit(event) {
    event.preventDefault();

    const saveButton = document.getElementById('save-button');
    const originalText = saveButton.textContent;

    try {
        saveButton.disabled = true;
        saveButton.textContent = '保存中...';

        // フォームデータを収集
        const formData = {
            name: document.getElementById('store-name').value.trim(),
            email: document.getElementById('store-email').value.trim() || null,
            phone_number: document.getElementById('store-phone').value.trim() || null,
            address: document.getElementById('store-address').value.trim() || null,
            opening_time: document.getElementById('opening-time').value || null,
            closing_time: document.getElementById('closing-time').value || null,
            description: document.getElementById('store-description').value.trim() || null,
            is_active: document.getElementById('store-active').checked
        };

        // Ownerの場合: store_idを追加
        if (isOwner && currentStoreId) {
            formData.store_id = currentStoreId;
        }

        // バリデーション
        if (!formData.name) {
            throw new Error('店舗名は必須です');
        }

        if (formData.description && formData.description.length > 1000) {
            throw new Error('説明文は1000文字以内で入力してください');
        }

        // API呼び出し
        const response = await apiClient.put('/store/profile', formData);
        storeData = response;

        // 成功メッセージを表示
        showSuccessMessage('店舗情報を更新しました');

        // 画面を更新
        displayStoreInfo(storeData);

    } catch (error) {
        showErrorMessage(error.message || '更新に失敗しました');
        console.error('Error updating store profile:', error);
    } finally {
        saveButton.disabled = false;
        saveButton.textContent = originalText;
    }
}

/**
 * 画像アップロード処理
 */
async function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // ファイル形式チェック
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        showErrorMessage('JPEG, PNG, GIF, WebP 形式の画像のみアップロードできます');
        event.target.value = '';
        return;
    }

    // ファイルサイズチェック（5MB）
    if (file.size > 5 * 1024 * 1024) {
        showErrorMessage('画像サイズは5MB以下にしてください');
        event.target.value = '';
        return;
    }

    try {
        // FormDataを作成
        const formData = new FormData();
        formData.append('file', file);

        // OwnerはURLにstore_idパラメータを追加
        let apiUrl = '/store/profile/image';
        if (isOwner && currentStoreId) {
            apiUrl = `/store/profile/image?store_id=${currentStoreId}`;
        }

        // API呼び出し
        console.log('Uploading image to:', apiUrl);
        const response = await apiClient.uploadImage(apiUrl, formData);
        storeData = response;

        // 画像を更新
        document.getElementById('store-image').src = response.image_url;
        originalImageUrl = response.image_url;
        document.getElementById('delete-image-button').style.display = 'inline-block';

        showSuccessMessage('画像をアップロードしました');

    } catch (error) {
        showErrorMessage(error.message || '画像のアップロードに失敗しました');
        console.error('Error uploading image:', error);
    } finally {
        event.target.value = '';
    }
}

/**
 * 画像削除処理
 */
async function handleImageDelete() {
    if (!confirm('店舗画像を削除してもよろしいですか?')) {
        return;
    }

    try {
        // OwnerはURLにstore_idパラメータを追加
        let apiUrl = '/store/profile/image';
        if (isOwner && currentStoreId) {
            apiUrl = `/store/profile/image?store_id=${currentStoreId}`;
        }

        console.log('Deleting image from:', apiUrl);
        const response = await apiClient.delete(apiUrl);
        storeData = response;

        // 画像を更新
        document.getElementById('store-image').src = '/static/images/no-image.svg';
        originalImageUrl = null;
        document.getElementById('delete-image-button').style.display = 'none';

        showSuccessMessage('画像を削除しました');

    } catch (error) {
        showErrorMessage(error.message || '画像の削除に失敗しました');
        console.error('Error deleting image:', error);
    }
}

/**
 * 成功メッセージを表示
 */
function showSuccessMessage(message) {
    const successMessage = document.getElementById('success-message');
    const successText = document.getElementById('success-text');
    
    successText.textContent = message;
    successMessage.style.display = 'block';

    // スクロール
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // 3秒後に非表示
    setTimeout(() => {
        successMessage.style.display = 'none';
    }, 3000);
}

/**
 * エラーメッセージを表示
 */
function showErrorMessage(message) {
    const errorMessage = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    
    errorText.textContent = message;
    errorMessage.style.display = 'block';

    // スクロール
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // 5秒後に非表示
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

/**
 * 日時フォーマット
 */
function formatDateTime(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${year}年${month}月${day}日 ${hours}:${minutes}`;
}
