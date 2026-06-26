"""create recipe tables

Revision ID: 0005_recipe_tables
Revises: 0004_produce_tables
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_recipe_tables"
down_revision: str | None = "0004_produce_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _ = op.create_table(
        "recipe_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_category_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_category_id",
            name="uq_recipe_categories_provider_id",
        ),
        sa.UniqueConstraint("provider", "name", name="uq_recipe_categories_provider_name"),
    )
    op.create_index(
        op.f("ix_recipe_categories_name"),
        "recipe_categories",
        ["name"],
        unique=False,
    )

    _ = op.create_table(
        "ingredients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_ingredient_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("normalized_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=120), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_ingredient_id",
            name="uq_ingredients_provider_id",
        ),
        sa.UniqueConstraint("provider", "normalized_name", name="uq_ingredients_provider_name"),
    )
    op.create_index(op.f("ix_ingredients_name"), "ingredients", ["name"], unique=False)

    _ = op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tags_normalized_name"), "tags", ["normalized_name"], unique=True)

    _ = op.create_table(
        "recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_recipe_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("alternate_name", sa.String(length=200), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category_name_raw", sa.String(length=200), nullable=True),
        sa.Column("area", sa.String(length=120), nullable=True),
        sa.Column("country_of_origin", sa.String(length=120), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("youtube_url", sa.Text(), nullable=True),
        sa.Column("image_source_url", sa.Text(), nullable=True),
        sa.Column("creative_commons_confirmed", sa.String(length=50), nullable=True),
        sa.Column("provider_modified_at", sa.DateTime(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["recipe_categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_recipe_id", name="uq_recipes_provider_id"),
    )
    op.create_index(op.f("ix_recipes_area"), "recipes", ["area"], unique=False)
    op.create_index(op.f("ix_recipes_category_id"), "recipes", ["category_id"], unique=False)
    op.create_index(
        op.f("ix_recipes_country_of_origin"),
        "recipes",
        ["country_of_origin"],
        unique=False,
    )
    op.create_index(op.f("ix_recipes_name"), "recipes", ["name"], unique=False)

    _ = op.create_table(
        "recipe_ingredients",
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ingredient_name_raw", sa.String(length=200), nullable=False),
        sa.Column("measure_raw", sa.String(length=200), nullable=True),
        sa.CheckConstraint("position BETWEEN 1 AND 20", name="ck_recipe_ingredients_position"),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("recipe_id", "position"),
    )
    op.create_index(
        op.f("ix_recipe_ingredients_ingredient_id"),
        "recipe_ingredients",
        ["ingredient_id"],
        unique=False,
    )

    _ = op.create_table(
        "recipe_tags",
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("recipe_id", "tag_id"),
    )
    op.create_index(op.f("ix_recipe_tags_tag_id"), "recipe_tags", ["tag_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_recipe_tags_tag_id"), table_name="recipe_tags")
    op.drop_table("recipe_tags")
    op.drop_index(op.f("ix_recipe_ingredients_ingredient_id"), table_name="recipe_ingredients")
    op.drop_table("recipe_ingredients")
    op.drop_index(op.f("ix_recipes_name"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_country_of_origin"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_category_id"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_area"), table_name="recipes")
    op.drop_table("recipes")
    op.drop_index(op.f("ix_tags_normalized_name"), table_name="tags")
    op.drop_table("tags")
    op.drop_index(op.f("ix_ingredients_name"), table_name="ingredients")
    op.drop_table("ingredients")
    op.drop_index(op.f("ix_recipe_categories_name"), table_name="recipe_categories")
    op.drop_table("recipe_categories")
