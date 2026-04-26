from datetime import UTC, datetime, timedelta

from authlib.jose import jwt

from app.config import settings


def _secret() -> str:
    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY is not configured.")
    return settings.secret_key


def mint_token(user_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.auth_token_ttl_minutes)).timestamp()
        ),
    }
    token = jwt.encode({"alg": "HS256"}, payload, _secret())
    return token.decode() if isinstance(token, bytes) else token


def verify_token(token: str) -> dict:
    claims = jwt.decode(token, _secret())
    claims.validate()
    return dict(claims)
