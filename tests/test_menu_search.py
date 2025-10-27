"""
メニュー検索機能のテスト
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app
from models import User, Store, Menu, Role, UserRole
from auth import get_password_hash

# テスト用データベース設定
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_menu_search.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """各テスト前にデータベースをセットアップ"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_data():
    """テストデータを作成"""
    db = TestingSessionLocal()
    
    # 店舗作成
    from datetime import time
    store = Store(
        name="テスト店舗",
        email="test@example.com",
        phone_number="03-1234-5678",
        address="東京都渋谷区1-1-1",
        opening_time=time(9, 0),
        closing_time=time(20, 0)
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    
    # 役割作成
    owner_role = Role(name="owner")
    db.add(owner_role)
    db.commit()
    db.refresh(owner_role)
    
    # ユーザー作成
    user = User(
        username="testowner",
        email="owner@example.com",
        hashed_password=get_password_hash("password123"),
        role="store",  # 'customer' or 'store'
        full_name="Test Owner",
        store_id=store.id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # ユーザーに役割を付与
    user_role = UserRole(user_id=user.id, role_id=owner_role.id)
    db.add(user_role)
    db.commit()
    
    # メニュー作成
    menus = [
        Menu(
            name="鮭弁当",
            description="新鮮な鮭を使用した定番のお弁当",
            price=850,
            store_id=store.id,
            is_available=True
        ),
        Menu(
            name="チキン南蛮弁当",
            description="サクサクのチキンに特製タルタルソース",
            price=900,
            store_id=store.id,
            is_available=True
        ),
        Menu(
            name="牛丼",
            description="国産牛を使用したボリューム満点の牛丼",
            price=750,
            store_id=store.id,
            is_available=True
        ),
        Menu(
            name="エビフライ弁当",
            description="大きなエビフライが3本入ったお弁当",
            price=950,
            store_id=store.id,
            is_available=False
        ),
        Menu(
            name="野菜カレー",
            description="たっぷりの野菜が入ったヘルシーカレー",
            price=800,
            store_id=store.id,
            is_available=True
        ),
        Menu(
            name="照り焼きチキン弁当",
            description="甘辛い照り焼きチキンが人気",
            price=880,
            store_id=store.id,
            is_available=True
        ),
    ]
    
    for menu in menus:
        db.add(menu)
    db.commit()
    
    # ログイン
    response = client.post(
        "/auth/login",
        data={"username": "testowner", "password": "password123"}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    token = response.json()["access_token"]
    
    db.close()
    return {"token": token, "store_id": store.id}


def test_search_by_menu_name(test_data):
    """メニュー名での検索"""
    token = test_data["token"]
    
    # "チキン"で検索
    response = client.get(
        "/store/menus",
        params={"keyword": "チキン"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2  # チキン南蛮弁当、照り焼きチキン弁当
    menu_names = [menu["name"] for menu in data["menus"]]
    assert "チキン南蛮弁当" in menu_names
    assert "照り焼きチキン弁当" in menu_names


def test_search_by_description(test_data):
    """説明文での検索"""
    token = test_data["token"]
    
    # "野菜"で検索
    response = client.get(
        "/store/menus",
        params={"keyword": "野菜"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1  # 野菜カレー
    assert data["menus"][0]["name"] == "野菜カレー"


def test_search_case_insensitive(test_data):
    """大文字小文字を区別しない検索"""
    token = test_data["token"]
    
    # "えび"で検索（メニュー名は"エビフライ弁当"）
    response = client.get(
        "/store/menus",
        params={"keyword": "えび"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["menus"][0]["name"] == "エビフライ弁当"


def test_search_partial_match(test_data):
    """部分一致検索"""
    token = test_data["token"]
    
    # "弁当"で検索
    response = client.get(
        "/store/menus",
        params={"keyword": "弁当"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4  # 鮭弁当、チキン南蛮弁当、エビフライ弁当、照り焼きチキン弁当


def test_search_no_results(test_data):
    """検索結果なし"""
    token = test_data["token"]
    
    # 存在しないキーワード
    response = client.get(
        "/store/menus",
        params={"keyword": "ラーメン"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["menus"]) == 0


def test_search_with_filter(test_data):
    """検索 + フィルタの組み合わせ"""
    token = test_data["token"]
    
    # "弁当"で検索 + 公開中のみ
    response = client.get(
        "/store/menus",
        params={"keyword": "弁当", "is_available": True},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3  # エビフライ弁当は非公開なので除外
    menu_names = [menu["name"] for menu in data["menus"]]
    assert "エビフライ弁当" not in menu_names


def test_search_with_sort(test_data):
    """検索 + ソートの組み合わせ"""
    token = test_data["token"]
    
    # "チキン"で検索 + 価格降順
    response = client.get(
        "/store/menus",
        params={"keyword": "チキン", "sort_by": "price", "sort_order": "desc"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    # 価格降順なので、チキン南蛮弁当(900円)が先
    assert data["menus"][0]["name"] == "チキン南蛮弁当"
    assert data["menus"][1]["name"] == "照り焼きチキン弁当"


def test_search_with_pagination(test_data):
    """検索 + ページネーションの組み合わせ"""
    token = test_data["token"]
    
    # "弁当"で検索 + 1ページ2件
    response = client.get(
        "/store/menus",
        params={"keyword": "弁当", "page": 1, "per_page": 2},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    assert len(data["menus"]) == 2
    
    # 2ページ目
    response = client.get(
        "/store/menus",
        params={"keyword": "弁当", "page": 2, "per_page": 2},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    assert len(data["menus"]) == 2


def test_search_empty_keyword(test_data):
    """空のキーワードで検索"""
    token = test_data["token"]
    
    # 空文字列
    response = client.get(
        "/store/menus",
        params={"keyword": ""},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 6  # 全メニュー


def test_search_unauthorized(test_data):
    """認証なしで検索"""
    response = client.get(
        "/store/menus",
        params={"keyword": "チキン"}
    )
    
    assert response.status_code == 401


def test_search_all_features_combined(test_data):
    """検索 + フィルタ + ソート + ページネーションの全組み合わせ"""
    token = test_data["token"]
    
    # "弁当"で検索 + 公開中 + 価格昇順 + 1ページ2件
    response = client.get(
        "/store/menus",
        params={
            "keyword": "弁当",
            "is_available": True,
            "sort_by": "price",
            "sort_order": "asc",
            "page": 1,
            "per_page": 2
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["menus"]) == 2
    # 価格昇順なので、鮭弁当(850円)が先
    assert data["menus"][0]["name"] == "鮭弁当"
    assert data["menus"][0]["price"] == 850
