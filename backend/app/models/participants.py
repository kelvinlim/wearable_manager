import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ParticipantStatus(str, enum.Enum):
    pending = "pending"
    registered = "registered"
    revoked = "revoked"


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("studies.id"), index=True)
    wearable_type_id: Mapped[int] = mapped_column(ForeignKey("wearable_types.id"))
    entry_code: Mapped[str] = mapped_column(String(5), unique=True, index=True)
    status: Mapped[ParticipantStatus] = mapped_column(
        Enum(ParticipantStatus, name="participant_status"),
        default=ParticipantStatus.pending,
    )
    google_health_user_id: Mapped[str | None] = mapped_column(String(128), index=True)
    oauth_access_token: Mapped[str | None] = mapped_column(Text)
    oauth_refresh_token: Mapped[str | None] = mapped_column(Text)
    oauth_scopes: Mapped[str | None] = mapped_column(Text)
    oauth_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
