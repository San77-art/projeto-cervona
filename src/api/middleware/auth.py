"""
JWT authentication against the single admin account in settings
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from src.config.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage (e.g. ADMIN_PASSWORD_HASH)"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def authenticate_admin(username: str, password: str) -> bool:
    """Check credentials against the single admin account configured in settings"""
    if username != settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD_HASH:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), settings.ADMIN_PASSWORD_HASH.encode("utf-8"))


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Dependency that validates the bearer token and returns the subject (username)"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise _CREDENTIALS_EXCEPTION

    username: Optional[str] = payload.get("sub")
    if username is None:
        raise _CREDENTIALS_EXCEPTION
    return username
