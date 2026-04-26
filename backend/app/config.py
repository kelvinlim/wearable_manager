from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_path: str = "/wearablemgr/"
    database_url: str
    admin_email: str | None = None

    secret_key: str | None = None
    researcher_google_client_id: str | None = None
    researcher_google_client_secret: str | None = None

    participant_google_client_id: str | None = None
    participant_google_client_secret: str | None = None
    participant_google_cloud_project_id: str | None = None
    webhook_secret: str | None = None

    study_creds_key: str | None = None

    auth_cookie_name: str = "wm_auth"
    auth_cookie_secure: bool = True
    auth_token_ttl_minutes: int = 60 * 24 * 7

    post_login_redirect_url: str = "/"


settings = Settings()
