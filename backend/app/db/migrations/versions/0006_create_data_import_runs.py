"""create data import runs

Revision ID: 0006_data_import_runs
Revises: 0005_recipe_tables
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_data_import_runs"
down_revision: str | None = "0005_recipe_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _ = op.create_table(
        "data_import_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_key", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("record_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_data_import_runs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_data_import_runs_data_key"),
        "data_import_runs",
        ["data_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_data_import_runs_status"),
        "data_import_runs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_data_import_runs_status"), table_name="data_import_runs")
    op.drop_index(op.f("ix_data_import_runs_data_key"), table_name="data_import_runs")
    op.drop_table("data_import_runs")
