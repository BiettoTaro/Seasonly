import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import SchemaItem

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class DataImportRun(Base):
    __tablename__: str = "data_import_runs"
    __table_args__: tuple[SchemaItem, ...] = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_data_import_runs_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    data_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    record_counts: Mapped[dict[str, int] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
