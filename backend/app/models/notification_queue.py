import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NotificationOperation(str, enum.Enum):
    UPSERT = "UPSERT"
    DELETE = "DELETE"


class NotificationQueue(Base):
    __tablename__ = "notification_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    google_health_user_id: Mapped[str] = mapped_column(String(128), index=True)
    data_type: Mapped[str] = mapped_column(String(64))
    operation: Mapped[NotificationOperation] = mapped_column(
        Enum(NotificationOperation, name="notification_operation")
    )
    interval_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    interval_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)
