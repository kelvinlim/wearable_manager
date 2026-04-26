from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.auth_google import router as auth_router
from app.config import settings


app = FastAPI(root_path=settings.app_path.rstrip("/"))

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

if settings.secret_key:
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        https_only=settings.auth_cookie_secure,
        same_site="lax",
    )

app.include_router(auth_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
