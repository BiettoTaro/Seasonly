import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import SchemaItem

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class RecommendationEvent(Base):
    __tablename__: str = "recommendation_events"
    __table_args__: tuple[SchemaItem, ...] = (
        CheckConstraint(
            "event_type IN ('impression', 'open', 'favourite', 'unfavourite', 'plan', 'unplan')",
            name="ck_recommendation_events_event_type",
        ),
        CheckConstraint(
            "source IN ('seasonal_feed', 'recipe_detail', 'planner')",
            name="ck_recommendation_events_source",
        ),
        CheckConstraint(
            "position IS NULL OR position BETWEEN 1 AND 100",
            name="ck_recommendation_events_position",
        ),
        CheckConstraint(
            "event_type != 'impression' OR slate_id IS NOT NULL",
            name="ck_recommendation_events_impression_slate",
        ),
        CheckConstraint(
            "expires_at > occurred_at",
            name="ck_recommendation_events_expiry",
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
    consent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_consents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    slate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        index=True,
    )
    position: Mapped[int | None] = mapped_column(SmallInteger)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
