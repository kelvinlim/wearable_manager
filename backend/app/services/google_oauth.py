from authlib.integrations.starlette_client import OAuth

from app.config import settings


oauth = OAuth()

if settings.researcher_google_client_id and settings.researcher_google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.researcher_google_client_id,
        client_secret=settings.researcher_google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
