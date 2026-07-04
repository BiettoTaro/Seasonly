"""create user recipe tables

Revision ID: 0008_user_recipe_tables
Revises: 0007_onboarding_tables
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_user_recipe_tables"
down_revision: str | None = "0007_onboarding_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _ = op.create_table(
        "user_recipe_favourites",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "recipe_id"),
    )
    _ = op.create_table(
        "user_recipe_history",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "recipe_id"),
    )
    _ = op.create_table(
        "user_planned_meals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
        sa.Column("meal_slot", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("day_of_week BETWEEN 1 AND 7", name="ck_user_planned_meals_day"),
        sa.CheckConstraint(
            "meal_slot IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_user_planned_meals_slot",
        ),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "recipe_id",
            "day_of_week",
            "meal_slot",
            name="uq_user_planned_meals_entry",
        ),
    )
    op.create_index(
        op.f("ix_user_planned_meals_recipe_id"),
        "user_planned_meals",
        ["recipe_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_planned_meals_user_id"),
        "user_planned_meals",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_planned_meals_user_id"), table_name="user_planned_meals")
    op.drop_index(op.f("ix_user_planned_meals_recipe_id"), table_name="user_planned_meals")
    op.drop_table("user_planned_meals")
    op.drop_table("user_recipe_history")
    op.drop_table("user_recipe_favourites")
