"""remove watermelon vegetable duplicate

Revision ID: 0009_remove_watermelon_vegetable
Revises: 0008_user_recipe_tables
Create Date: 2026-07-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_remove_watermelon_vegetable"
down_revision: str | None = "0008_user_recipe_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM produce WHERE name = 'watermelon' AND type = 'vegetable'"))


def downgrade() -> None:
    pass
