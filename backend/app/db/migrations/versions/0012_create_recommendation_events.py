"""create recommendation events

Revision ID: 0012_recommendation_events
Revises: 0011_recipe_allergen_assessments
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_recommendation_events"
down_revision: str | None = "0011_recipe_allergen_assessments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_user_consents_consent_type",
        "user_consents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_user_consents_consent_type",
        "user_consents",
        "consent_type IN ('allergy_storage', 'personalization')",
    )

    _ = op.create_table(
        "recommendation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('impression', 'open', 'favourite', 'unfavourite', 'plan', 'unplan')",
            name="ck_recommendation_events_event_type",
        ),
        sa.CheckConstraint(
            "source IN ('seasonal_feed', 'recipe_detail', 'planner')",
            name="ck_recommendation_events_source",
        ),
        sa.CheckConstraint(
            "position IS NULL OR position BETWEEN 1 AND 100",
            name="ck_recommendation_events_position",
        ),
        sa.CheckConstraint(
            "expires_at > occurred_at",
            name="ck_recommendation_events_expiry",
        ),
        sa.ForeignKeyConstraint(["consent_id"], ["user_consents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column_name in (
        "consent_id",
        "event_type",
        "expires_at",
        "occurred_at",
        "recipe_id",
        "user_id",
    ):
        op.create_index(
            op.f(f"ix_recommendation_events_{column_name}"),
            "recommendation_events",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in (
        "user_id",
        "recipe_id",
        "occurred_at",
        "expires_at",
        "event_type",
        "consent_id",
    ):
        op.drop_index(
            op.f(f"ix_recommendation_events_{column_name}"),
            table_name="recommendation_events",
        )
    op.drop_table("recommendation_events")

    _ = op.execute(sa.text("DELETE FROM user_consents WHERE consent_type = 'personalization'"))
    op.drop_constraint(
        "ck_user_consents_consent_type",
        "user_consents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_user_consents_consent_type",
        "user_consents",
        "consent_type IN ('allergy_storage')",
    )
