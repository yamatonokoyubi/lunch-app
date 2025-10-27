"""create_user_cart_items_table

Revision ID: c6242ed82ea7
Revises: 8b546c2313bb
Create Date: 2025-10-19 23:51:04.728722

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6242ed82ea7"
down_revision: Union[str, None] = "8b546c2313bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # テーブルが既に存在するかチェック
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "user_cart_items" not in inspector.get_table_names():
        op.create_table(
            "user_cart_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("menu_id", sa.Integer(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "created_at",
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
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["menu_id"], ["menus.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_user_cart_items_user_id", "user_cart_items", ["user_id"])
        op.create_index("ix_user_cart_items_id", "user_cart_items", ["id"])


def downgrade() -> None:
    op.drop_index("ix_user_cart_items_id", table_name="user_cart_items")
    op.drop_index("ix_user_cart_items_user_id", table_name="user_cart_items")
    op.drop_table("user_cart_items")
