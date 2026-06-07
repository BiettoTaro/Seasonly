import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import SchemaItem

from app.db.base import Base


class Produce(Base):
    __tablename__: str = "produce"
    __table_args__: tuple[SchemaItem, ...] = (
        CheckConstraint("type IN ('fruit', 'vegetable')", name="ck_produce_type"),
        UniqueConstraint("name", "type", name="uq_produce_name_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    mealdb_name: Mapped[str | None] = mapped_column(String(120))

    seasons: Mapped[list["ProduceSeason"]] = relationship(
        back_populates="produce",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProduceSeason(Base):
    __tablename__: str = "produce_seasons"
    __table_args__: tuple[SchemaItem, ...] = (
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_produce_seasons_month"),
        UniqueConstraint(
            "produce_id",
            "country_code",
            "month",
            "source_name",
            name="uq_produce_seasons_produce_country_month_source",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    produce_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("produce.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    country_code: Mapped[str] = mapped_column(String(2), index=True, nullable=False)
    country_name: Mapped[str] = mapped_column(String(120), nullable=False)
    month: Mapped[int] = mapped_column(index=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))

    produce: Mapped[Produce] = relationship(back_populates="seasons")
