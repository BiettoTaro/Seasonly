import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import SchemaItem

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__: str = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    refresh_tokens: Mapped[list["UserRefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    password_reset_tokens: Mapped[list["UserPasswordResetToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserProfile(Base):
    __tablename__: str = "user_profiles"
    __table_args__: tuple[SchemaItem, ...] = (
        CheckConstraint(
            "onboarding_status IN ('not_started', 'in_progress', 'completed')",
            name="ck_user_profiles_onboarding_status",
        ),
        CheckConstraint(
            "location_source IS NULL OR location_source IN ('device', 'manual', 'coarse_header')",
            name="ck_user_profiles_location_source",
        ),
        CheckConstraint(
            "diet_pattern IS NULL OR diet_pattern IN "
            + "('omnivore', 'flexitarian', 'pescatarian', 'vegetarian', 'vegan')",
            name="ck_user_profiles_diet_pattern",
        ),
        CheckConstraint(
            "allergy_status IN ('not_provided', 'no_known_allergies', 'provided')",
            name="ck_user_profiles_allergy_status",
        ),
        CheckConstraint(
            "cuisine_preference_status IN ('not_provided', 'no_preference', 'provided')",
            name="ck_user_profiles_cuisine_preference_status",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    display_name: Mapped[str | None] = mapped_column(String(100))
    country_code: Mapped[str | None] = mapped_column(String(2))
    region_code: Mapped[str | None] = mapped_column(String(20))
    location_source: Mapped[str | None] = mapped_column(String(30))
    onboarding_status: Mapped[str] = mapped_column(
        String(30),
        default="not_started",
        nullable=False,
    )
    privacy_notice_version: Mapped[str | None] = mapped_column(String(50))
    privacy_notice_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    diet_pattern: Mapped[str | None] = mapped_column(String(30))
    allergy_status: Mapped[str] = mapped_column(
        String(30),
        default="not_provided",
        nullable=False,
    )
    allergy_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dietary_rules_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cuisine_preference_status: Mapped[str] = mapped_column(
        String(30),
        default="not_provided",
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="profile")
    allergens: Mapped[list["UserAllergen"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    dietary_rules: Mapped[list["UserDietaryRule"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    cuisine_preferences: Mapped[list["UserCuisinePreference"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="UserCuisinePreference.preference_rank",
    )
    protein_preferences: Mapped[list["UserProteinPreference"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="UserProteinPreference.preference_rank",
    )
    consents: Mapped[list["UserConsent"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserAllergen(Base):
    __tablename__: str = "user_allergens"
    __table_args__: tuple[SchemaItem, ...] = (
        CheckConstraint(
            "allergen IN ("
            + "'celery', 'cereals_containing_gluten', 'crustaceans', 'eggs', 'fish', "
            + "'lupin', 'milk', 'molluscs', 'mustard', 'peanuts', 'sesame', 'soybeans', "
            + "'sulphur_dioxide_and_sulphites', 'tree_nuts'"
            + ")",
            name="ck_user_allergens_allergen",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    allergen: Mapped[str] = mapped_column(String(80), primary_key=True)

    profile: Mapped[UserProfile] = relationship(back_populates="allergens")


class UserDietaryRule(Base):
    __tablename__: str = "user_dietary_rules"
    __table_args__: tuple[SchemaItem, ...] = (
        CheckConstraint(
            "dietary_rule IN ('avoid_pork', 'avoid_beef', 'avoid_alcohol', 'avoid_shellfish')",
            name="ck_user_dietary_rules_dietary_rule",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    dietary_rule: Mapped[str] = mapped_column(String(50), primary_key=True)

    profile: Mapped[UserProfile] = relationship(back_populates="dietary_rules")


class UserCuisinePreference(Base):
    __tablename__: str = "user_cuisine_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    area: Mapped[str] = mapped_column(String(120), primary_key=True)
    preference_rank: Mapped[int | None] = mapped_column(Integer)

    profile: Mapped[UserProfile] = relationship(back_populates="cuisine_preferences")


class UserProteinPreference(Base):
    __tablename__: str = "user_protein_preferences"
    __table_args__: tuple[SchemaItem, ...] = (
        CheckConstraint(
            "protein IN ("
            + "'chicken', 'turkey', 'beef', 'pork', 'lamb', 'fish', 'seafood', "
            + "'eggs', 'tofu', 'legumes'"
            + ")",
            name="ck_user_protein_preferences_protein",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    protein: Mapped[str] = mapped_column(String(50), primary_key=True)
    preference_rank: Mapped[int | None] = mapped_column(Integer)

    profile: Mapped[UserProfile] = relationship(back_populates="protein_preferences")


class UserConsent(Base):
    __tablename__: str = "user_consents"
    __table_args__: tuple[SchemaItem, ...] = (
        CheckConstraint(
            "consent_type IN ('allergy_storage', 'personalization')",
            name="ck_user_consents_consent_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    consent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    notice_version: Mapped[str] = mapped_column(String(50), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped[UserProfile] = relationship(back_populates="consents")


class UserRefreshToken(Base):
    __tablename__: str = "user_refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        index=True,
        nullable=False,
        default=uuid.uuid4,
    )
    parent_token_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_refresh_tokens.id", ondelete="SET NULL"),
        unique=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class UserPasswordResetToken(Base):
    __tablename__: str = "user_password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="password_reset_tokens")
