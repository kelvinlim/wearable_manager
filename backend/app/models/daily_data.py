import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DataSource(str, enum.Enum):
    fitbit = "fitbit"
    garmin = "garmin"


class DailyData(Base):
    __tablename__ = "daily_data"
    __table_args__ = (
        UniqueConstraint(
            "participant_id",
            "date",
            "source",
            name="uq_daily_data_participant_date_source",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    source: Mapped[DataSource] = mapped_column(Enum(DataSource, name="data_source"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
