// 認証画面専用JavaScript - auth.js

console.log('🔧 auth.js loaded');

class AuthForm {
    constructor() {
        console.log('🔧 AuthForm constructor called');
        this.initializeLoginForm();
        this.initializeRegisterForm();
        this.setupDemoLogin();
        this.checkExistingAuth();
    }

    initializeLoginForm() {
        const loginForm = document.getElementById('loginForm');
        console.log('🔧 initializeLoginForm:', loginForm ? 'Form found' : 'Form NOT found');
        if (!loginForm) return;

        console.log('✅ Login form event listener attached');
        loginForm.addEventListener('submit', async (e) => {
            console.log('📝 Login form submitted!');
            e.preventDefault();
            
            const formData = new FormData(loginForm);
            const credentials = {
                username: formData.get('username'),
                password: formData.get('password')
            };

            // バリデーション
            if (!this.validateLoginForm(credentials)) {
                return;
            }

            const submitBtn = loginForm.querySelector('.auth-submit');
            const hideLoading = UI.showLoading(submitBtn);

            try {
                console.log('🔐 Sending login request...');
                const response = await ApiClient.post('/auth/login', credentials);
                console.log('✅ Login API response:', response);
                
                // 認証情報を保存
                console.log('💾 Saving auth token and user info...');
                Auth.login(response.access_token, response.user);
                console.log('✅ Auth info saved');
                
                // ゲストカートをユーザーカートに移行
                if (response.user.role === 'customer') {
                    console.log('🔄 Starting cart migration for customer...');
                    try {
                        const migrateResponse = await ApiClient.post('/customer/cart/migrate', {});
                        console.log('✅ Cart migration result:', migrateResponse);
                        
                        // カートバッジを更新
                        if (window.updateCartBadge) {
                            console.log('🔄 Updating cart badge...');
                            await window.updateCartBadge();
                            console.log('✅ Cart badge updated');
                        }
                    } catch (migrateError) {
                        console.error('❌ Cart migration error:', migrateError);
                        // マイグレーションエラーは無視してログインを続行
                    }
                } else {
                    console.log('ℹ️ User is not a customer, skipping cart migration');
                }
                
                // 成功メッセージ
                UI.showAlert('ログインしました', 'success');
                
                // カート移行が完了するまで少し待機してからリダイレクト
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // ロールに応じてリダイレクト
                this.redirectAfterLogin(response.user.role);
                
            } catch (error) {
                console.error('Login error:', error);
                UI.showAlert('ログインに失敗しました: ' + error.message, 'danger');
            } finally {
                hideLoading();
            }
        });
    }

    initializeRegisterForm() {
        const registerForm = document.getElementById('registerForm');
        if (!registerForm) return;

        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(registerForm);
            const userData = {
                username: formData.get('username'),
                email: formData.get('email'),
                password: formData.get('password'),
                full_name: formData.get('full_name'),
                role: formData.get('role')
            };

            // バリデーション
            if (!this.validateRegisterForm(userData, formData.get('confirmPassword'))) {
                return;
            }

            const submitBtn = registerForm.querySelector('.auth-submit');
            const hideLoading = UI.showLoading(submitBtn);

            try {
                const response = await ApiClient.post('/auth/register', userData);
                
                UI.showAlert('アカウントが作成されました。ログインしてください。', 'success');
                
                // redirectパラメータを引き継いでログインページにリダイレクト
                const urlParams = new URLSearchParams(window.location.search);
                const redirect = urlParams.get('redirect');
                const loginUrl = redirect ? `/login?redirect=${encodeURIComponent(redirect)}` : '/login';
                
                setTimeout(() => {
                    window.location.href = loginUrl;
                }, 2000);
                
            } catch (error) {
                console.error('Registration error:', error);
                UI.showAlert('登録に失敗しました: ' + error.message, 'danger');
            } finally {
                hideLoading();
            }
        });
    }

    setupDemoLogin() {
        const demoButtons = document.querySelectorAll('.demo-login-btn');
        demoButtons.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                
                const username = btn.dataset.username;
                const password = btn.dataset.password;
                
                try {
                    const hideLoading = UI.showLoading(btn);
                    
                    const response = await ApiClient.post('/auth/login', {
                        username,
                        password
                    });
                    
                    Auth.login(response.access_token, response.user);
                    
                    // ゲストカートをユーザーカートに移行
                    if (response.user.role === 'customer') {
                        console.log('🔄 Starting cart migration for customer (demo login)...');
                        try {
                            const migrateResponse = await ApiClient.post('/customer/cart/migrate', {});
                            console.log('✅ Cart migration result:', migrateResponse);
                            
                            // カートバッジを更新
                            if (window.updateCartBadge) {
                                console.log('🔄 Updating cart badge...');
                                await window.updateCartBadge();
                                console.log('✅ Cart badge updated');
                            }
                        } catch (migrateError) {
                            console.error('❌ Cart migration error:', migrateError);
                            // マイグレーションエラーは無視してログインを続行
                        }
                    } else {
                        console.log('ℹ️ User is not a customer, skipping cart migration');
                    }
                    
                    UI.showAlert(`${username} でログインしました`, 'success');
                    
                    // カート移行が完了するまで少し待機してからリダイレクト
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    this.redirectAfterLogin(response.user.role);
                    
                } catch (error) {
                    console.error('Demo login error:', error);
                    UI.showAlert('デモログインに失敗しました', 'danger');
                    btn.innerHTML = 'ログイン';
                    btn.disabled = false;
                }
            });
        });
    }

    validateLoginForm(credentials) {
        let isValid = true;
        
        // クリア既存のエラー
        this.clearErrors();
        
        // ユーザー名チェック
        if (!Validator.validateRequired(credentials.username)) {
            this.showFieldError('username', 'ユーザー名を入力してください');
            isValid = false;
        }
        
        // パスワードチェック
        if (!Validator.validateRequired(credentials.password)) {
            this.showFieldError('password', 'パスワードを入力してください');
            isValid = false;
        }
        
        return isValid;
    }

    validateRegisterForm(userData, confirmPassword) {
        let isValid = true;
        
        // クリア既存のエラー
        this.clearErrors();
        
        // ユーザー名チェック
        if (!Validator.validateRequired(userData.username)) {
            this.showFieldError('username', 'ユーザー名を入力してください');
            isValid = false;
        } else if (!Validator.validateMinLength(userData.username, 3)) {
            this.showFieldError('username', 'ユーザー名は3文字以上で入力してください');
            isValid = false;
        }
        
        // メールアドレスチェック
        if (!Validator.validateRequired(userData.email)) {
            this.showFieldError('email', 'メールアドレスを入力してください');
            isValid = false;
        } else if (!Validator.validateEmail(userData.email)) {
            this.showFieldError('email', '有効なメールアドレスを入力してください');
            isValid = false;
        }
        
        // パスワードチェック
        if (!Validator.validateRequired(userData.password)) {
            this.showFieldError('password', 'パスワードを入力してください');
            isValid = false;
        } else if (!Validator.validateMinLength(userData.password, 6)) {
            this.showFieldError('password', 'パスワードは6文字以上で入力してください');
            isValid = false;
        }
        
        // パスワード確認チェック
        if (userData.password !== confirmPassword) {
            this.showFieldError('confirmPassword', 'パスワードが一致しません');
            isValid = false;
        }
        
        // 氏名チェック
        if (!Validator.validateRequired(userData.full_name)) {
            this.showFieldError('full_name', '氏名を入力してください');
            isValid = false;
        }
        
        // ロールチェック
        if (!userData.role || !['customer', 'store'].includes(userData.role)) {
            this.showFieldError('role', '利用者タイプを選択してください');
            isValid = false;
        }
        
        return isValid;
    }

    showFieldError(fieldName, message) {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.classList.add('error');
            
            // エラーメッセージを表示
            let errorElement = field.parentNode.querySelector('.field-error');
            if (!errorElement) {
                errorElement = document.createElement('span');
                errorElement.className = 'field-error';
                field.parentNode.appendChild(errorElement);
            }
            errorElement.textContent = message;
        }
    }

    clearErrors() {
        // エラークラスを削除
        document.querySelectorAll('.form-control.error').forEach(el => {
            el.classList.remove('error');
        });
        
        // エラーメッセージを削除
        document.querySelectorAll('.field-error').forEach(el => {
            el.remove();
        });
    }

    checkExistingAuth() {
        // 既にログイン済みの場合はリダイレクト
        if (Auth.isLoggedIn()) {
            this.redirectAfterLogin(currentUser.role);
        }
    }

    redirectAfterLogin(role) {
        // URLパラメータからリダイレクト先を取得
        const urlParams = new URLSearchParams(window.location.search);
        const redirect = urlParams.get('redirect');
        
        // リダイレクトパラメータがある場合はそこに遷移
        if (redirect) {
            window.location.href = redirect;
            return;
        }
        
        // デフォルトのリダイレクト先
        if (role === 'customer') {
            window.location.href = '/menus';
        } else if (role === 'store') {
            window.location.href = '/store/dashboard';
        } else {
            window.location.href = '/';
        }
    }
}

// パスワード表示切り替え機能
function setupPasswordToggle() {
    const passwordFields = document.querySelectorAll('input[type="password"]');
    
    passwordFields.forEach(field => {
        // 目のアイコンを追加
        const wrapper = document.createElement('div');
        wrapper.style.position = 'relative';
        
        field.parentNode.insertBefore(wrapper, field);
        wrapper.appendChild(field);
        
        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.innerHTML = '👁️';
        toggleBtn.style.cssText = `
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            border: none;
            background: none;
            cursor: pointer;
            font-size: 16px;
            opacity: 0.6;
        `;
        
        toggleBtn.addEventListener('click', () => {
            if (field.type === 'password') {
                field.type = 'text';
                toggleBtn.innerHTML = '🙈';
            } else {
                field.type = 'password';
                toggleBtn.innerHTML = '👁️';
            }
        });
        
        wrapper.appendChild(toggleBtn);
    });
}

// リアルタイムバリデーション
function setupRealtimeValidation() {
    const form = document.querySelector('.auth-form');
    if (!form) return;
    
    const fields = form.querySelectorAll('input[required]');
    
    fields.forEach(field => {
        field.addEventListener('blur', () => {
            validateField(field);
        });
        
        field.addEventListener('input', () => {
            // エラー状態をクリア
            field.classList.remove('error');
            const errorElement = field.parentNode.querySelector('.field-error');
            if (errorElement) {
                errorElement.remove();
            }
        });
    });
}

function validateField(field) {
    const value = field.value.trim();
    const name = field.name;
    let isValid = true;
    let message = '';
    
    if (field.hasAttribute('required') && !value) {
        isValid = false;
        message = 'この項目は必須です';
    } else if (name === 'email' && value && !Validator.validateEmail(value)) {
        isValid = false;
        message = '有効なメールアドレスを入力してください';
    } else if (name === 'password' && value && value.length < 6) {
        isValid = false;
        message = 'パスワードは6文字以上で入力してください';
    } else if (name === 'username' && value && value.length < 3) {
        isValid = false;
        message = 'ユーザー名は3文字以上で入力してください';
    }
    
    if (!isValid) {
        field.classList.add('error');
        let errorElement = field.parentNode.querySelector('.field-error');
        if (!errorElement) {
            errorElement = document.createElement('span');
            errorElement.className = 'field-error';
            field.parentNode.appendChild(errorElement);
        }
        errorElement.textContent = message;
    }
}

// DOM読み込み完了時の初期化
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOMContentLoaded - Initializing auth page...');
    new AuthForm();
    setupPasswordToggle();
    setupRealtimeValidation();
    
    // ロール選択のアニメーション
    const roleOptions = document.querySelectorAll('.role-option input[type="radio"]');
    roleOptions.forEach(option => {
        option.addEventListener('change', function() {
            // 他の選択肢をリセット
            roleOptions.forEach(other => {
                other.parentNode.classList.remove('selected');
            });
            
            // 選択された項目をハイライト
            if (this.checked) {
                this.parentNode.classList.add('selected');
            }
        });
    });
    
    // フォームのアニメーション
    const authCard = document.querySelector('.auth-card');
    if (authCard) {
        authCard.style.opacity = '0';
        authCard.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            authCard.style.transition = 'all 0.5s ease';
            authCard.style.opacity = '1';
            authCard.style.transform = 'translateY(0)';
        }, 100);
    }
});