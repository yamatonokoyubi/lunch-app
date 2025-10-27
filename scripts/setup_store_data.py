"""
店舗データとユーザー紐付けスクリプト
初回起動時に3店舗を自動登録します
"""
import sys
from pathlib import Path

# ルートディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Store, User, Role, UserRole
from datetime import time

db = SessionLocal()

# 店舗データの定義
STORES_DATA = [
    {
        "name": "振徳弁当本店",
        "address": "宮崎県日南市飫肥4丁目2-20",
        "phone_number": "0987-34-5678",
        "email": "honten1@bento.com",
        "opening_time": time(9, 0),
        "closing_time": time(21, 0),
        "description": "毎日食べても飽きない手作り、ひとつひとつ丁寧に。まごころ込めた温かい味。ひと口食べればホッとする。こだわりの手作り弁当です。",
        "is_active": True
    },
    {
        "name": "振徳弁当南郷店",
        "address": "日南市南郷町中村乙380-18",
        "phone_number": "0987-46-2111",
        "email": "nangou@example.com",
        "opening_time": time(9, 0),
        "closing_time": time(22, 0),
        "description": "季節の野菜を彩り豊かに使い、食べればホッとするお母さんの手作りの味を再現しました。心も体も満たされるお弁当屋さんです。",
        "is_active": True
    },
    {
        "name": "振徳弁当油津店",
        "address": "宮崎県日南市岩崎2丁目13",
        "phone_number": "0987-75-0805",
        "email": "aburatsu@example.com",
        "opening_time": time(9, 0),
        "closing_time": time(22, 0),
        "description": "手作りの温もりを。朝一番に仕込んだ、愛情たっぷりのお弁当です。季節の野菜を彩り豊かに使い、食べればホッとするお店です。",
        "is_active": True
    }
]

try:
    print("=" * 60)
    print("🏪 店舗データセットアップ開始")
    print("=" * 60)
    
    # 店舗を作成
    created_stores = []
    for store_data in STORES_DATA:
        store = db.query(Store).filter(Store.name == store_data["name"]).first()
        if not store:
            store = Store(**store_data)
            db.add(store)
            db.commit()
            db.refresh(store)
            print(f"✅ 店舗作成: {store.name} (ID: {store.id})")
            created_stores.append(store)
        else:
            print(f"ℹ️  既存店舗: {store.name} (ID: {store.id})")
            created_stores.append(store)
    
    # 最初の店舗を取得（デフォルト店舗として使用）
    default_store = created_stores[0] if created_stores else None
    
    print("\n" + "=" * 60)
    print("👥 ロールとユーザー設定")
    print("=" * 60)
    
    # Rolesを作成
    roles_data = [
        ("owner", "店舗オーナー"),
        ("manager", "店舗マネージャー"),
        ("staff", "店舗スタッフ")
    ]
    
    for role_name, role_desc in roles_data:
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(name=role_name, description=role_desc)
            db.add(role)
            print(f"✅ Role作成: {role_name}")
        else:
            print(f"ℹ️  既存Role: {role_name}")
    
    db.commit()
    
    # 店舗ユーザーに店舗を割り当て
    if default_store:
        store_users = db.query(User).filter(User.role == "store").all()
        
        for user in store_users:
            if not user.store_id:
                user.store_id = default_store.id
                print(f"✅ ユーザー '{user.username}' に店舗を割り当て (店舗ID: {default_store.id})")
            
            # ownerロールを割り当て (admin と store1)
            if user.username in ["admin", "store1"]:
                owner_role = db.query(Role).filter(Role.name == "owner").first()
                existing_user_role = db.query(UserRole).filter(
                    UserRole.user_id == user.id,
                    UserRole.role_id == owner_role.id
                ).first()
                
                if not existing_user_role:
                    user_role = UserRole(user_id=user.id, role_id=owner_role.id)
                    db.add(user_role)
                    print(f"✅ ユーザー '{user.username}' にownerロールを割り当て")
                else:
                    print(f"ℹ️  ユーザー '{user.username}' は既にownerロールを持っています")
            
            # managerロールを割り当て (store2)
            elif user.username == "store2":
                manager_role = db.query(Role).filter(Role.name == "manager").first()
                existing_user_role = db.query(UserRole).filter(
                    UserRole.user_id == user.id,
                    UserRole.role_id == manager_role.id
                ).first()
                
                if not existing_user_role:
                    user_role = UserRole(user_id=user.id, role_id=manager_role.id)
                    db.add(user_role)
                    print(f"✅ ユーザー '{user.username}' にmanagerロールを割り当て")
                else:
                    print(f"ℹ️  ユーザー '{user.username}' は既にmanagerロールを持っています")
    
    db.commit()
    
    print("\n" + "=" * 60)
    print("📊 セットアップ完了サマリー")
    print("=" * 60)
    print(f"✅ 登録店舗数: {len(created_stores)}")
    for store in created_stores:
        print(f"   - {store.name} (ID: {store.id})")
    print(f"✅ デフォルト店舗: {default_store.name if default_store else 'なし'}")
    print("=" * 60)
    print("🎉 すべての設定が完了しました!")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ エラー: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
