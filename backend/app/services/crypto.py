from functools import lru_cache

import sqlalchemy as sa
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator

from app.config import settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    if not settings.study_creds_key:
        raise RuntimeError(
            "STUDY_CREDS_KEY is not configured; cannot encrypt or decrypt study credentials."
        )
    return Fernet(settings.study_creds_key.encode())


def encrypt_str(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_str(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise RuntimeError(
            "Failed to decrypt study credential — wrong STUDY_CREDS_KEY or corrupted ciphertext."
        ) from e


class EncryptedText(TypeDecorator):
    impl = sa.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_str(value)
