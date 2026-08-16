"""add recommendation slate id

Revision ID: 0013_recommendation_slate_id
Revises: 0012_recommendation_events
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_recommendation_slate_id"
down_revision: str | None = "0012_recommendation_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "recommendation_events",
        sa.Column(
            "slate_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    _ = op.execute(
        sa.text("UPDATE recommendation_events SET slate_id = id WHERE event_type = 'impression'")
    )
    op.create_check_constraint(
        "ck_recommendation_events_impression_slate",
        "recommendation_events",
        "event_type != 'impression' OR slate_id IS NOT NULL",
    )
    op.create_index(
        op.f("ix_recommendation_events_slate_id"),
        "recommendation_events",
        ["slate_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_recommendation_events_slate_id"),
        table_name="recommendation_events",
    )
    op.drop_constraint(
        "ck_recommendation_events_impression_slate",
        "recommendation_events",
        type_="check",
    )
    op.drop_column("recommendation_events", "slate_id")
