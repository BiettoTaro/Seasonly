"""create recipe allergen assessments

Revision ID: 0011_recipe_allergen_assessments
Revises: 0010_refresh_token_families
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_recipe_allergen_assessments"
down_revision: str | None = "0010_refresh_token_families"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALLERGENS: tuple[str, ...] = (
    "celery",
    "cereals_containing_gluten",
    "crustaceans",
    "eggs",
    "fish",
    "lupin",
    "milk",
    "molluscs",
    "mustard",
    "peanuts",
    "sesame",
    "soybeans",
    "sulphur_dioxide_and_sulphites",
    "tree_nuts",
)


def upgrade() -> None:
    _ = op.create_table(
        "recipe_allergen_assessments",
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("allergen", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("method", sa.String(length=30), nullable=False),
        sa.Column("assessment_version", sa.String(length=80), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "allergen IN (" + ", ".join(f"'{allergen}'" for allergen in ALLERGENS) + ")",
            name="ck_recipe_allergen_assessments_allergen",
        ),
        sa.CheckConstraint(
            "status IN ('contains', 'does_not_contain', 'unknown')",
            name="ck_recipe_allergen_assessments_status",
        ),
        sa.CheckConstraint(
            "method IN ('unassessed', 'rules', 'reviewed_dataset', 'manual_review')",
            name="ck_recipe_allergen_assessments_method",
        ),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("recipe_id", "allergen"),
    )
    op.create_index(
        op.f("ix_recipe_allergen_assessments_status"),
        "recipe_allergen_assessments",
        ["status"],
        unique=False,
    )

    allergen_values = ", ".join(f"('{allergen}')" for allergen in ALLERGENS)
    op.execute(
        sa.text(
            """
            INSERT INTO recipe_allergen_assessments (
                recipe_id,
                allergen,
                status,
                method,
                assessment_version,
                assessed_at
            )
            SELECT
                recipes.id,
                allergens.allergen,
                'unknown',
                'unassessed',
                'initial-v1',
                CURRENT_TIMESTAMP
            FROM recipes
            CROSS JOIN (VALUES """
            + allergen_values
            + """) AS allergens(allergen)
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_recipe_allergen_assessments_status"),
        table_name="recipe_allergen_assessments",
    )
    op.drop_table("recipe_allergen_assessments")
