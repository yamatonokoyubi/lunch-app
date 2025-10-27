"""add_guest_sessions_and_cart

Revision ID: bdc1811d302d
Revises: 2f4aeea60b82
Create Date: 2025-10-19 09:38:54.769866

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bdc1811d302d"
down_revision: Union[str, None] = "2f4aeea60b82"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # guest_sessions テーブル作成
    op.create_table(
        "guest_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("selected_store_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("converted_to_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "last_accessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["converted_to_user_id"], ["users.id"], name="fk_guest_sessions_user"
        ),
        sa.ForeignKeyConstraint(
            ["selected_store_id"], ["stores.id"], name="fk_guest_sessions_store"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_guest_sessions_id", "guest_sessions", ["id"], unique=False)
    op.create_index(
        "ix_guest_sessions_session_id",
        "guest_sessions",
        ["session_id"],
        unique=True,
    )
    op.create_index(
        "ix_guest_sessions_expires_at",
        "guest_sessions",
        ["expires_at"],
        unique=False,
    )

    # guest_cart_items テーブル作成
    op.create_table(
        "guest_cart_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("menu_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["menu_id"], ["menus.id"], name="fk_guest_cart_items_menu"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["guest_sessions.session_id"],
            name="fk_guest_cart_items_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guest_cart_items_id", "guest_cart_items", ["id"], unique=False)
    op.create_index(
        "ix_guest_cart_items_session_id",
        "guest_cart_items",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    # テーブル削除（逆順）
    op.drop_index("ix_guest_cart_items_session_id", table_name="guest_cart_items")
    op.drop_index("ix_guest_cart_items_id", table_name="guest_cart_items")
    op.drop_table("guest_cart_items")

    op.drop_index("ix_guest_sessions_expires_at", table_name="guest_sessions")
    op.drop_index("ix_guest_sessions_session_id", table_name="guest_sessions")
    op.drop_index("ix_guest_sessions_id", table_name="guest_sessions")
    op.drop_table("guest_sessions")
