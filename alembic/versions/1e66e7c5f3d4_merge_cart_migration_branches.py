"""merge_cart_migration_branches

Revision ID: 1e66e7c5f3d4
Revises: 8b8905e3b726, bdc1811d302d
Create Date: 2025-10-19 23:18:38.810683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e66e7c5f3d4'
down_revision: Union[str, None] = ('8b8905e3b726', 'bdc1811d302d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
