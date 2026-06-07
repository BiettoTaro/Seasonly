"""create produce tables

Revision ID: 0004_produce_tables
Revises: 0003_password_reset_tokens
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_produce_tables"
down_revision: str | None = "0003_password_reset_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _ = op.create_table(
        "produce",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("mealdb_name", sa.String(length=120), nullable=True),
        sa.CheckConstraint("type IN ('fruit', 'vegetable')", name="ck_produce_type"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "type", name="uq_produce_name_type"),
    )
    op.create_index(op.f("ix_produce_name"), "produce", ["name"], unique=False)

    _ = op.create_table(
        "produce_seasons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("produce_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("country_name", sa.String(length=120), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.CheckConstraint("month BETWEEN 1 AND 12", name="ck_produce_seasons_month"),
        sa.ForeignKeyConstraint(["produce_id"], ["produce.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "produce_id",
            "country_code",
            "month",
            "source_name",
            name="uq_produce_seasons_produce_country_month_source",
        ),
    )
    op.create_index(
        op.f("ix_produce_seasons_country_code"),
        "produce_seasons",
        ["country_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_produce_seasons_month"),
        "produce_seasons",
        ["month"],
        unique=False,
    )
    op.create_index(
        op.f("ix_produce_seasons_produce_id"),
        "produce_seasons",
        ["produce_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_produce_seasons_produce_id"), table_name="produce_seasons")
    op.drop_index(op.f("ix_produce_seasons_month"), table_name="produce_seasons")
    op.drop_index(op.f("ix_produce_seasons_country_code"), table_name="produce_seasons")
    op.drop_table("produce_seasons")
    op.drop_index(op.f("ix_produce_name"), table_name="produce")
    op.drop_table("produce")
