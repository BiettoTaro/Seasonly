import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import SchemaItem

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class RecipeCategory(Base):
    __tablename__: str = "recipe_categories"
    __table_args__: tuple[SchemaItem, ...] = (
        UniqueConstraint(
            "provider",
            "provider_category_id",
            name="uq_recipe_categories_provider_id",
        ),
        UniqueConstraint("provider", "name", name="uq_recipe_categories_provider_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_category_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    recipes: Mapped[list["Recipe"]] = relationship(back_populates="category")


class Ingredient(Base):
    __tablename__: str = "ingredients"
    __table_args__: tuple[SchemaItem, ...] = (
        UniqueConstraint("provider", "provider_ingredient_id", name="uq_ingredients_provider_id"),
        UniqueConstraint("provider", "normalized_name", name="uq_ingredients_provider_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_ingredient_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(String(120))
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(back_populates="ingredient")


class Recipe(Base):
    __tablename__: str = "recipes"
    __table_args__: tuple[SchemaItem, ...] = (
        UniqueConstraint("provider", "provider_recipe_id", name="uq_recipes_provider_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_recipe_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    alternate_name: Mapped[str | None] = mapped_column(String(200))
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipe_categories.id", ondelete="SET NULL"),
        index=True,
    )
    category_name_raw: Mapped[str | None] = mapped_column(String(200))
    area: Mapped[str | None] = mapped_column(String(120), index=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(120), index=True)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    youtube_url: Mapped[str | None] = mapped_column(Text)
    image_source_url: Mapped[str | None] = mapped_column(Text)
    creative_commons_confirmed: Mapped[str | None] = mapped_column(String(50))
    provider_modified_at: Mapped[datetime | None] = mapped_column(DateTime())
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    category: Mapped[RecipeCategory | None] = relationship(back_populates="recipes")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RecipeIngredient.position",
    )
    tags: Mapped[list["RecipeTag"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RecipeIngredient(Base):
    __tablename__: str = "recipe_ingredients"
    __table_args__: tuple[SchemaItem, ...] = (
        CheckConstraint(
            "position BETWEEN 1 AND 20",
            name="ck_recipe_ingredients_position",
        ),
    )

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    ingredient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id", ondelete="SET NULL"),
        index=True,
    )
    ingredient_name_raw: Mapped[str] = mapped_column(String(200), nullable=False)
    measure_raw: Mapped[str | None] = mapped_column(String(200))

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
    ingredient: Mapped[Ingredient | None] = relationship(back_populates="recipe_ingredients")


class Tag(Base):
    __tablename__: str = "tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
        nullable=False,
    )

    recipes: Mapped[list["RecipeTag"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RecipeTag(Base):
    __tablename__: str = "recipe_tags"

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

    recipe: Mapped[Recipe] = relationship(back_populates="tags")
    tag: Mapped[Tag] = relationship(back_populates="recipes")
