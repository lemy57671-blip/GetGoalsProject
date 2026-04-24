from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from app.core.config import settings

# Đổi từ bcrypt sang pbkdf2_sha256 để tránh lỗi runtime với bcrypt backend
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Swagger sẽ hiện nút Authorize nhờ security scheme này
bearer_scheme = HTTPBearer(
    auto_error=False,
    bearerFormat="JWT",
    description="Dán JWT theo format: Bearer <token>"
)

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    if password is None:
        raise ValueError("Password is required")

    password = str(password)

    if not password.strip():
        raise ValueError("Password must not be empty")

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False


def create_access_token(
    *,
    subject: str,
    email: str,
    name: str,
    provider: str = "local",
    onboarding_completed: bool = False,
    expires_delta: Optional[timedelta] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=7))

    payload = {
        "sub": str(subject),
        "email": email,
        "name": name,
        "provider": provider,
        "onboardingCompleted": str(onboarding_completed).lower(),
        "iss": settings.AUTH_ISSUER,
        "aud": settings.AUTH_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    token = jwt.encode(payload, settings.AUTH_JWT_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_JWT_KEY,
            algorithms=[ALGORITHM],
            audience=settings.AUTH_AUDIENCE,
            issuer=settings.AUTH_ISSUER,
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def extract_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return credentials.credentials
