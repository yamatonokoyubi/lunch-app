"""add_converted_to_user_id_to_guest_session

Revision ID: 8b546c2313bb
Revises: 1e66e7c5f3d4
Create Date: 2025-10-19 23:44:45.267585

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b546c2313bb"
down_revision: Union[str, None] = "1e66e7c5f3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # カラムが既に存在するかチェック
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("guest_sessions")]

    if "converted_to_user_id" not in columns:
        op.add_column(
            "guest_sessions",
            sa.Column("converted_to_user_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_guest_sessions_converted_to_user_id",
            "guest_sessions",
            "users",
            ["converted_to_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            "ix_guest_sessions_converted_to_user_id",
            "guest_sessions",
            ["converted_to_user_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_guest_sessions_converted_to_user_id", table_name="guest_sessions")
    op.drop_constraint(
        "fk_guest_sessions_converted_to_user_id", "guest_sessions", type_="foreignkey"
    )
    op.drop_column("guest_sessions", "converted_to_user_id")
