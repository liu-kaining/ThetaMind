"""Security utilities for JWT token creation and verification."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings

# JWT Configuration
ALGORITHM = settings.jwt_algorithm  # "HS256"
SECRET_KEY = settings.jwt_secret_key


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing claims to encode in the token (e.g., {"sub": user_id})
        expires_delta: Optional expiration time delta. If not provided, uses default from settings.

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiration_hours)
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict[str, Any]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string to verify

    Returns:
        Decoded token payload (claims)

    Raises:
        JWTError: If token is invalid, expired, or cannot be decoded
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}") from e

