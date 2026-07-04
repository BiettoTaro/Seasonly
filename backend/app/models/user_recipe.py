import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import SchemaItem

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.recipe import Recipe


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserRecipeFavourite(Base):
    __tablename__: str = "user_recipe_favourites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    recipe: Mapped["Recipe"] = relationship()


class UserRecipeHistory(Base):
    __tablename__: str = "user_recipe_history"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    recipe: Mapped["Recipe"] = relationship()


class UserPlannedMeal(Base):
    __tablename__: str = "user_planned_meals"
    __table_args__: tuple[SchemaItem, ...] = (
        CheckConstraint("day_of_week BETWEEN 1 AND 7", name="ck_user_planned_meals_day"),
        CheckConstraint(
            "meal_slot IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_user_planned_meals_slot",
        ),
        UniqueConstraint(
            "user_id",
            "recipe_id",
            "day_of_week",
            "meal_slot",
            name="uq_user_planned_meals_entry",
        ),
    )

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
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    meal_slot: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    recipe: Mapped["Recipe"] = relationship()
