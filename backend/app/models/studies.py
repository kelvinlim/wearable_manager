from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.services.crypto import EncryptedText


class Study(Base):
    __tablename__ = "studies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    wearable_type_id: Mapped[int] = mapped_column(ForeignKey("wearable_types.id"))
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    google_oauth_client_id: Mapped[str | None] = mapped_column(Text)
    google_oauth_client_secret: Mapped[str | None] = mapped_column(EncryptedText)
    google_cloud_project_id: Mapped[str | None] = mapped_column(Text)
    webhook_authorization_value: Mapped[str | None] = mapped_column(EncryptedText)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StudyMember(Base):
    __tablename__ = "study_members"

    study_id: Mapped[int] = mapped_column(ForeignKey("studies.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(32))
