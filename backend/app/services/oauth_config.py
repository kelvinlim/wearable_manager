from dataclasses import dataclass
from typing import Literal

from app.config import settings
from app.models import Study


@dataclass(frozen=True)
class ParticipantOAuthConfig:
    client_id: str
    client_secret: str
    google_cloud_project_id: str
    webhook_authorization_value: str
    source: Literal["study", "fallback"]


def resolve_participant_oauth_config(study: Study) -> ParticipantOAuthConfig | None:
    if (
        study.google_oauth_client_id
        and study.google_oauth_client_secret
        and study.google_cloud_project_id
        and study.webhook_authorization_value
    ):
        return ParticipantOAuthConfig(
            client_id=study.google_oauth_client_id,
            client_secret=study.google_oauth_client_secret,
            google_cloud_project_id=study.google_cloud_project_id,
            webhook_authorization_value=study.webhook_authorization_value,
            source="study",
        )

    if (
        settings.participant_google_client_id
        and settings.participant_google_client_secret
        and settings.participant_google_cloud_project_id
        and settings.webhook_secret
    ):
        return ParticipantOAuthConfig(
            client_id=settings.participant_google_client_id,
            client_secret=settings.participant_google_client_secret,
            google_cloud_project_id=settings.participant_google_cloud_project_id,
            webhook_authorization_value=settings.webhook_secret,
            source="fallback",
        )

    return None
