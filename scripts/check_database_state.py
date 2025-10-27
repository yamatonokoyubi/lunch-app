"""
データベースの状態を確認するスクリプト

このスクリプトは以下を確認します:
1. 店舗の数
2. メニューカテゴリの数
3. メニューの数
4. ユーザーの数
5. 役割(Role)の数
"""
import sys
from pathlib import Path

# ルートディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Store, MenuCategory, Menu, User, Role, UserRole


def check_database_state():
    """データベースの状態を確認"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("データベース状態確認")
        print("=" * 60)
        
        # 店舗を確認
        stores = db.query(Store).all()
        print(f"\n📍 店舗: {len(stores)}件")
        for store in stores:
            print(f"   - ID:{store.id} {store.name}")
        
        # メニューカテゴリを確認
        categories = db.query(MenuCategory).all()
        print(f"\n📂 メニューカテゴリ: {len(categories)}件")
        for cat in categories:
            menu_count = db.query(Menu).filter(Menu.category_id == cat.id).count()
            print(f"   - ID:{cat.id} {cat.name} (メニュー数: {menu_count})")
        
        # メニューを確認
        menus = db.query(Menu).all()
        print(f"\n🍱 メニュー: {len(menus)}件")
        if len(menus) <= 10:
            for menu in menus:
                print(f"   - ID:{menu.id} {menu.name} (¥{menu.price})")
        else:
            print(f"   最初の5件を表示:")
            for menu in menus[:5]:
                print(f"   - ID:{menu.id} {menu.name} (¥{menu.price})")
            print(f"   ... 他 {len(menus) - 5}件")
        
        # ユーザーを確認
        users = db.query(User).all()
        print(f"\n👤 ユーザー: {len(users)}件")
        
        # ロール別に集計
        store_users = [u for u in users if u.role == 'store']
        customer_users = [u for u in users if u.role == 'customer']
        
        print(f"\n   店舗スタッフ: {len(store_users)}名")
        for user in store_users:
            roles = [ur.role.name for ur in user.user_roles if ur.role]
            role_names = ", ".join(roles) if roles else "役割なし"
            print(f"   - {user.username} ({role_names})")
        
        print(f"\n   顧客: {len(customer_users)}名")
        for user in customer_users[:5]:  # 最初の5名のみ表示
            print(f"   - {user.username}")
        if len(customer_users) > 5:
            print(f"   ... 他 {len(customer_users) - 5}名")
        
        # 役割を確認
        roles = db.query(Role).all()
        print(f"\n🎭 役割: {len(roles)}件")
        for role in roles:
            user_count = db.query(UserRole).filter(UserRole.role_id == role.id).count()
            print(f"   - {role.name} (割り当て: {user_count}名)")
        
        print("\n" + "=" * 60)
        
        # 初期データが投入されているかチェック
        if len(categories) >= 6 and len(menus) >= 30 and len(stores) >= 1:
            print("✅ 初期データが正常に投入されています")
            print(f"   - 6カテゴリ: {len(categories)}件 ✓")
            print(f"   - 30メニュー: {len(menus)}件 ✓")
            print(f"   - 店舗: {len(stores)}件 ✓")
            print(f"   - デモユーザー: {len(users)}名 ✓")
        else:
            print("⚠️  初期データが不完全です")
            print(f"   - カテゴリ: {len(categories)}/6件")
            print(f"   - メニュー: {len(menus)}/30件")
            print(f"   - 店舗: {len(stores)}/1件")
            print("\n   マイグレーションを実行してください:")
            print("   alembic upgrade head")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    check_database_state()
