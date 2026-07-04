"""create onboarding tables

Revision ID: 0007_onboarding_tables
Revises: 0006_data_import_runs
Create Date: 2026-06-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_onboarding_tables"
down_revision: str | None = "0006_data_import_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column(
            "onboarding_status",
            sa.String(length=30),
            server_default="not_started",
            nullable=False,
        ),
    )
    op.add_column(
        "user_profiles",
        sa.Column("privacy_notice_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("privacy_notice_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("diet_pattern", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column(
            "allergy_status",
            sa.String(length=30),
            server_default="not_provided",
            nullable=False,
        ),
    )
    op.add_column(
        "user_profiles",
        sa.Column("allergy_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("dietary_rules_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column(
            "cuisine_preference_status",
            sa.String(length=30),
            server_default="not_provided",
            nullable=False,
        ),
    )
    op.add_column(
        "user_profiles",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_user_profiles_onboarding_status",
        "user_profiles",
        "onboarding_status IN ('not_started', 'in_progress', 'completed')",
    )
    op.create_check_constraint(
        "ck_user_profiles_location_source",
        "user_profiles",
        "location_source IS NULL OR location_source IN ('device', 'manual', 'coarse_header')",
    )
    op.create_check_constraint(
        "ck_user_profiles_diet_pattern",
        "user_profiles",
        "diet_pattern IS NULL OR diet_pattern IN "
        + "('omnivore', 'flexitarian', 'pescatarian', 'vegetarian', 'vegan')",
    )
    op.create_check_constraint(
        "ck_user_profiles_allergy_status",
        "user_profiles",
        "allergy_status IN ('not_provided', 'no_known_allergies', 'provided')",
    )
    op.create_check_constraint(
        "ck_user_profiles_cuisine_preference_status",
        "user_profiles",
        "cuisine_preference_status IN ('not_provided', 'no_preference', 'provided')",
    )

    _ = op.create_table(
        "user_allergens",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("allergen", sa.String(length=80), nullable=False),
        sa.CheckConstraint(
            "allergen IN ("
            + "'celery', 'cereals_containing_gluten', 'crustaceans', 'eggs', 'fish', "
            + "'lupin', 'milk', 'molluscs', 'mustard', 'peanuts', 'sesame', 'soybeans', "
            + "'sulphur_dioxide_and_sulphites', 'tree_nuts'"
            + ")",
            name="ck_user_allergens_allergen",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "allergen"),
    )
    _ = op.create_table(
        "user_dietary_rules",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dietary_rule", sa.String(length=50), nullable=False),
        sa.CheckConstraint(
            "dietary_rule IN ('avoid_pork', 'avoid_beef', 'avoid_alcohol', 'avoid_shellfish')",
            name="ck_user_dietary_rules_dietary_rule",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "dietary_rule"),
    )
    _ = op.create_table(
        "user_cuisine_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("area", sa.String(length=120), nullable=False),
        sa.Column("preference_rank", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "area"),
    )
    _ = op.create_table(
        "user_protein_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("protein", sa.String(length=50), nullable=False),
        sa.Column("preference_rank", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "protein IN ("
            + "'chicken', 'turkey', 'beef', 'pork', 'lamb', 'fish', 'seafood', "
            + "'eggs', 'tofu', 'legumes'"
            + ")",
            name="ck_user_protein_preferences_protein",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "protein"),
    )
    _ = op.create_table(
        "user_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_type", sa.String(length=50), nullable=False),
        sa.Column("notice_version", sa.String(length=50), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "consent_type IN ('allergy_storage')",
            name="ck_user_consents_consent_type",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_consents_user_id"), "user_consents", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_consents_user_id"), table_name="user_consents")
    op.drop_table("user_consents")
    op.drop_table("user_protein_preferences")
    op.drop_table("user_cuisine_preferences")
    op.drop_table("user_dietary_rules")
    op.drop_table("user_allergens")
    op.drop_constraint(
        "ck_user_profiles_cuisine_preference_status",
        "user_profiles",
        type_="check",
    )
    op.drop_constraint("ck_user_profiles_allergy_status", "user_profiles", type_="check")
    op.drop_constraint("ck_user_profiles_diet_pattern", "user_profiles", type_="check")
    op.drop_constraint("ck_user_profiles_location_source", "user_profiles", type_="check")
    op.drop_constraint("ck_user_profiles_onboarding_status", "user_profiles", type_="check")
    op.drop_column("user_profiles", "updated_at")
    op.drop_column("user_profiles", "completed_at")
    op.drop_column("user_profiles", "cuisine_preference_status")
    op.drop_column("user_profiles", "dietary_rules_updated_at")
    op.drop_column("user_profiles", "allergy_updated_at")
    op.drop_column("user_profiles", "allergy_status")
    op.drop_column("user_profiles", "diet_pattern")
    op.drop_column("user_profiles", "privacy_notice_acknowledged_at")
    op.drop_column("user_profiles", "privacy_notice_version")
    op.drop_column("user_profiles", "onboarding_status")
