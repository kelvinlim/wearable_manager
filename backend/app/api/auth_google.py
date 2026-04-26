from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db import get_session
from app.models import User, UserRole
from app.services.google_oauth import oauth
from app.services.jwt_auth import mint_token


router = APIRouter(prefix="/auth", tags=["auth"])


def _client():
    client = oauth.create_client("google")
    if client is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Researcher Google OAuth is not configured.",
        )
    return client


@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = request.url_for("auth_google_callback")
    return await _client().authorize_redirect(request, str(redirect_uri))


@router.get("/google/callback", name="auth_google_callback")
async def google_callback(
    request: Request, session: AsyncSession = Depends(get_session)
):
    token = await _client().authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Missing email in OIDC userinfo."
        )
    if not userinfo.get("email_verified", False):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Google email is not verified."
        )

    email = userinfo["email"].lower()
    name = userinfo.get("name")

    user = await _resolve_user(session, email=email, name=name)
    if user is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="This account is not authorized for the application.",
        )

    response = RedirectResponse(url=settings.post_login_redirect_url, status_code=302)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=mint_token(user.id),
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_token_ttl_minutes * 60,
        path="/",
    )
    return response


async def _resolve_user(
    session: AsyncSession, *, email: str, name: str | None
) -> User | None:
    is_admin = bool(settings.admin_email) and email == settings.admin_email.lower()

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None and not is_admin:
        return None

    if user is None:
        user = User(email=email, name=name, role=UserRole.admin)
        session.add(user)
    else:
        if is_admin and user.role != UserRole.admin:
            user.role = UserRole.admin
        if name and user.name != name:
            user.name = name

    await session.commit()
    await session.refresh(user)
    return user


@router.post("/logout")
async def logout():
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.auth_cookie_name, path="/")
    return response


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
    }
