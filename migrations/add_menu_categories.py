"""
メニューカテゴリ機能の追加マイグレーション

- menu_categories テーブルの作成
- menus テーブルに category_id カラムを追加
"""

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Boolean, text
from sqlalchemy.sql import func
import os

# データベース接続設定
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/bento_order")
engine = create_engine(DATABASE_URL)


def upgrade():
    """マイグレーションを適用"""
    with engine.connect() as conn:
        # トランザクション開始
        trans = conn.begin()
        
        try:
            print("Creating menu_categories table...")
            
            # menu_categories テーブルを作成
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS menu_categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    display_order INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    store_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_menu_categories_store
                        FOREIGN KEY (store_id)
                        REFERENCES stores(id)
                        ON DELETE CASCADE,
                    CONSTRAINT uq_menu_category_name_per_store
                        UNIQUE (store_id, name)
                )
            """))
            
            print("Adding category_id column to menus table...")
            
            # menus テーブルに category_id カラムを追加
            conn.execute(text("""
                ALTER TABLE menus
                ADD COLUMN IF NOT EXISTS category_id INTEGER,
                ADD CONSTRAINT fk_menus_category
                    FOREIGN KEY (category_id)
                    REFERENCES menu_categories(id)
                    ON DELETE SET NULL
            """))
            
            print("Creating indexes...")
            
            # インデックスを作成
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_menu_categories_store_id
                ON menu_categories(store_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_menu_categories_is_active
                ON menu_categories(is_active)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_menus_category_id
                ON menus(category_id)
            """))
            
            # トランザクションをコミット
            trans.commit()
            print("Migration completed successfully!")
            
        except Exception as e:
            # エラーが発生した場合はロールバック
            trans.rollback()
            print(f"Migration failed: {e}")
            raise


def downgrade():
    """マイグレーションをロールバック"""
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            print("Rolling back migration...")
            
            # インデックスを削除
            conn.execute(text("""
                DROP INDEX IF EXISTS idx_menus_category_id
            """))
            
            conn.execute(text("""
                DROP INDEX IF EXISTS idx_menu_categories_is_active
            """))
            
            conn.execute(text("""
                DROP INDEX IF EXISTS idx_menu_categories_store_id
            """))
            
            # menus テーブルから category_id カラムを削除
            conn.execute(text("""
                ALTER TABLE menus
                DROP CONSTRAINT IF EXISTS fk_menus_category,
                DROP COLUMN IF EXISTS category_id
            """))
            
            # menu_categories テーブルを削除
            conn.execute(text("""
                DROP TABLE IF EXISTS menu_categories
            """))
            
            trans.commit()
            print("Rollback completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"Rollback failed: {e}")
            raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
