"""add versioned terms acceptance

Revision ID: 0014_terms_acceptance
Revises: 0013_recommendation_slate_id
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_terms_acceptance"
down_revision: str | None = "0013_recommendation_slate_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("terms_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_users_terms_acceptance_complete",
        "users",
        "(terms_version IS NULL) = (terms_accepted_at IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_users_terms_acceptance_complete",
        "users",
        type_="check",
    )
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "terms_version")
