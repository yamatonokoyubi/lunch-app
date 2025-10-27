"""
デモユーザーの認証情報を検証し、必要に応じて修正するスクリプト

このスクリプトは以下を実行します:
1. データベース内のデモユーザーを確認
2. パスワードハッシュが正しいか検証
3. 必要に応じてパスワードを再設定
"""
import sys
from pathlib import Path

# ルートディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from auth import get_password_hash, verify_password


def verify_and_fix_demo_users():
    """デモユーザーの検証と修正"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("デモユーザー検証スクリプト")
        print("=" * 60)
        
        # 期待されるユーザーとパスワード
        expected_users = [
            {"username": "admin", "password": "admin@123", "role": "store"},
            {"username": "store1", "password": "password123", "role": "store"},
            {"username": "store2", "password": "password123", "role": "store"},
            {"username": "customer1", "password": "password123", "role": "customer"},
            {"username": "customer2", "password": "password123", "role": "customer"},
            {"username": "customer3", "password": "password123", "role": "customer"},
            {"username": "customer4", "password": "password123", "role": "customer"},
            {"username": "customer5", "password": "password123", "role": "customer"},
        ]
        
        fixed_count = 0
        verified_count = 0
        missing_count = 0
        
        for expected in expected_users:
            username = expected["username"]
            password = expected["password"]
            
            # データベースからユーザーを取得
            user = db.query(User).filter(User.username == username).first()
            
            if not user:
                print(f"\n❌ ユーザー '{username}' が見つかりません")
                missing_count += 1
                continue
            
            # パスワードを検証
            if verify_password(password, user.hashed_password):
                print(f"\n✅ ユーザー '{username}' のパスワードは正しいです")
                verified_count += 1
            else:
                print(f"\n⚠️  ユーザー '{username}' のパスワードが一致しません")
                print(f"   パスワードを再設定します...")
                
                # パスワードを再設定
                user.hashed_password = get_password_hash(password)
                db.commit()
                
                # 再検証
                if verify_password(password, user.hashed_password):
                    print(f"   ✅ パスワードを正常に再設定しました")
                    fixed_count += 1
                else:
                    print(f"   ❌ パスワードの再設定に失敗しました")
        
        print("\n" + "=" * 60)
        print("検証結果サマリー")
        print("=" * 60)
        print(f"検証成功: {verified_count} ユーザー")
        print(f"修正完了: {fixed_count} ユーザー")
        print(f"見つからない: {missing_count} ユーザー")
        print("=" * 60)
        
        if missing_count > 0:
            print("\n⚠️  見つからないユーザーがあります")
            print("   マイグレーションを実行してください:")
            print("   alembic upgrade head")
        
        if fixed_count > 0:
            print(f"\n✅ {fixed_count} ユーザーのパスワードを修正しました")
        
        if verified_count == len(expected_users) and missing_count == 0 and fixed_count == 0:
            print("\n🎉 すべてのデモユーザーの認証情報が正常です！")
        
        print("\n" + "=" * 60)
        print("デモログイン情報")
        print("=" * 60)
        print("店舗オーナー:")
        print("  ユーザー名: admin")
        print("  パスワード: admin@123")
        print("")
        print("店舗マネージャー:")
        print("  ユーザー名: store1")
        print("  パスワード: password123")
        print("")
        print("店舗スタッフ:")
        print("  ユーザー名: store2")
        print("  パスワード: password123")
        print("")
        print("顧客:")
        print("  ユーザー名: customer1")
        print("  パスワード: password123")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ エラーが発生しました: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    verify_and_fix_demo_users()
