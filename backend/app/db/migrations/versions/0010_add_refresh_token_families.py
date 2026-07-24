"""add refresh token families

Revision ID: 0010_refresh_token_families
Revises: 0009_remove_watermelon_vegetable
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_refresh_token_families"
down_revision: str | None = "0009_remove_watermelon_vegetable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_refresh_tokens",
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "user_refresh_tokens",
        sa.Column("parent_token_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute("UPDATE user_refresh_tokens SET family_id = id WHERE family_id IS NULL")
    op.alter_column("user_refresh_tokens", "family_id", nullable=False)
    op.create_index(
        op.f("ix_user_refresh_tokens_family_id"),
        "user_refresh_tokens",
        ["family_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_user_refresh_tokens_parent_token_id",
        "user_refresh_tokens",
        ["parent_token_id"],
    )
    op.create_foreign_key(
        "fk_user_refresh_tokens_parent_token_id",
        "user_refresh_tokens",
        "user_refresh_tokens",
        ["parent_token_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_user_refresh_tokens_parent_token_id",
        "user_refresh_tokens",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_user_refresh_tokens_parent_token_id",
        "user_refresh_tokens",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_user_refresh_tokens_family_id"),
        table_name="user_refresh_tokens",
    )
    op.drop_column("user_refresh_tokens", "parent_token_id")
    op.drop_column("user_refresh_tokens", "family_id")
