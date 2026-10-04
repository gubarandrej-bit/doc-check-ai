"""Аутентификация и авторизация (пароль + JWT)."""
import datetime

import bcrypt
from jose import jwt

from config import ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY

# bcrypt по спецификации учитывает только первые 72 байта пароля.
# Современные версии требуют усечения явно и падают на длинном пароле,
# поэтому делаем это сами — и при хешировании, и при проверке, иначе
# пользователь не сможет войти с тем же паролем, которым его создали.
_MAX_BYTES = 72


def _secret(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_BYTES]


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(_secret(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_secret(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # Хеш повреждён или создан другой реализацией — это не совпадение.
        return False


def create_access_token(data: dict, expires_minutes: int | None = None) -> str:
    to_encode = dict(data)
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None