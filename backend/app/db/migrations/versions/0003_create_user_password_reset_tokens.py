"""create user password reset tokens

Revision ID: 0003_create_user_password_reset_tokens
Revises: 0002_create_user_refresh_tokens
Create Date: 2026-06-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_create_user_password_reset_tokens"
down_revision: str | None = "0002_create_user_refresh_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _ = op.create_table(
        "user_password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_password_reset_tokens_token_hash"),
        "user_password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_user_password_reset_tokens_user_id"),
        "user_password_reset_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_password_reset_tokens_user_id"),
        table_name="user_password_reset_tokens",
    )
    op.drop_index(
        op.f("ix_user_password_reset_tokens_token_hash"),
        table_name="user_password_reset_tokens",
    )
    op.drop_table("user_password_reset_tokens")
