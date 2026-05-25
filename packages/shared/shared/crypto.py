from __future__ import annotations

from cryptography.fernet import Fernet

from shared.config import get_settings


def _get_key() -> str:
    settings = get_settings()
    key = settings.secret_encryption_key
    return key


def encrypt(plaintext: str) -> str:
    return Fernet(_get_key().encode()).encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return Fernet(_get_key().encode()).decrypt(ciphertext.encode()).decode()
