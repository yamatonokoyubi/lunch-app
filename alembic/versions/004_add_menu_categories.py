"""add menu categories table

Revision ID: 004_menu_categories
Revises: 003_simplify_status
Create Date: 2025-10-17

メニューカテゴリ機能の追加:
- menu_categories テーブルの作成
- menus テーブルに category_id カラムを追加
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_menu_categories'
down_revision: Union[str, None] = '003_simplify_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """メニューカテゴリテーブルを作成"""
    
    # menu_categories テーブルを作成
    op.create_table(
        'menu_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # インデックスを作成
    op.create_index('ix_menu_categories_store_id', 'menu_categories', ['store_id'])
    op.create_index('ix_menu_categories_is_active', 'menu_categories', ['is_active'])
    op.create_index('ix_menu_categories_display_order', 'menu_categories', ['display_order'])
    
    # 外部キー制約を追加
    op.create_foreign_key(
        'fk_menu_categories_store_id',
        'menu_categories', 'stores',
        ['store_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # menus テーブルに category_id カラムを追加
    op.add_column('menus', sa.Column('category_id', sa.Integer(), nullable=True))
    op.create_index('ix_menus_category_id', 'menus', ['category_id'])
    
    # 外部キー制約を追加
    op.create_foreign_key(
        'fk_menus_category_id',
        'menus', 'menu_categories',
        ['category_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """メニューカテゴリテーブルを削除"""
    
    # menus テーブルから category_id を削除
    op.drop_constraint('fk_menus_category_id', 'menus', type_='foreignkey')
    op.drop_index('ix_menus_category_id', table_name='menus')
    op.drop_column('menus', 'category_id')
    
    # menu_categories テーブルを削除
    op.drop_constraint('fk_menu_categories_store_id', 'menu_categories', type_='foreignkey')
    op.drop_index('ix_menu_categories_display_order', table_name='menu_categories')
    op.drop_index('ix_menu_categories_is_active', table_name='menu_categories')
    op.drop_index('ix_menu_categories_store_id', table_name='menu_categories')
    op.drop_table('menu_categories')
