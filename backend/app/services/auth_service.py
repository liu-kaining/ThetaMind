"""Authentication service for Google OAuth2 and user management."""

import logging
from datetime import datetime, timezone
from typing import Any

from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings
from app.db.models import User
from app.db.session import AsyncSessionLocal
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def verify_google_token(token: str) -> dict[str, Any]:
    """
    Verify Google ID token and extract user information.

    Args:
        token: Google ID token string

    Returns:
        Dictionary containing user information from Google (email, sub, etc.)

    Raises:
        ValueError: If token is invalid or verification fails
    """
    try:
        # Validate Google Client ID is set
        if not settings.google_client_id or not settings.google_client_id.strip():
            raise ValueError(
                "GOOGLE_CLIENT_ID must be set in environment variables or .env file. "
                "This is required for Google OAuth token verification."
            )
        
        # Verify the token using Google's public keys
        # According to Google OAuth2 docs, we need to specify the client_id
        request = requests.Request()
        idinfo = id_token.verify_oauth2_token(
            token,
            request,
            settings.google_client_id,
        )

        # Verify the issuer
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer.")

        # Extract user information
        user_info = {
            "email": idinfo.get("email"),
            "google_sub": idinfo.get("sub"),  # Google's unique user ID
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
        }

        if not user_info["email"] or not user_info["google_sub"]:
            raise ValueError("Missing required user information from Google token")

        logger.info("Successfully verified Google token (do not log PII)")
        return user_info

    except ValueError as e:
        logger.error(f"Google token verification failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during Google token verification: {e}", exc_info=True)
        raise ValueError(f"Token verification failed: {str(e)}") from e


async def authenticate_user(email: str, google_sub: str) -> User:
    """
    Authenticate user by email (Upsert logic).

    If user exists, return existing user.
    If user doesn't exist, create new user.

    Args:
        email: User email address
        google_sub: Google's unique user identifier (sub claim)

    Returns:
        User model instance

    Raises:
        ValueError: If email or google_sub is missing
    """
    if not email or not google_sub:
        raise ValueError("Email and google_sub are required")

    async with AsyncSessionLocal() as session:
        try:
            # Try to find existing user by email or google_sub
            result = await session.execute(
                select(User).where(
                    (User.email == email) | (User.google_sub == google_sub)
                )
            )
            user = result.scalar_one_or_none()

            if user:
                # Update google_sub if it changed (shouldn't happen, but handle edge cases)
                if user.google_sub != google_sub:
                    logger.warning(
                        f"User {user.email} google_sub changed from {user.google_sub} to {google_sub}"
                    )
                    user.google_sub = google_sub
                    await session.commit()
                    await session.refresh(user)

                logger.info(f"Authenticated existing user: {user.email}")
                return user

            # Create new user
            from uuid import uuid4

            new_user = User(
                id=uuid4(),
                email=email,
                google_sub=google_sub,
                is_pro=False,
                is_superuser=False,
                daily_ai_usage=0,
                created_at=datetime.now(timezone.utc),
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)

            logger.info(f"Created new user: {new_user.email}")
            return new_user

        except Exception as e:
            logger.error(f"Error during user authentication: {e}", exc_info=True)
            await session.rollback()
            raise

