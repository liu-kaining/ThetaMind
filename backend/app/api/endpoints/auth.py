"""Authentication API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import create_access_token
from app.services.auth_service import authenticate_user, verify_google_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleTokenRequest(BaseModel):
    """Google token authentication request model."""

    token: str = Field(..., description="Google ID token from client")


class TokenResponse(BaseModel):
    """JWT token response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


@router.post("/google", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def authenticate_with_google(request: GoogleTokenRequest) -> TokenResponse:
    """
    Authenticate user with Google OAuth2 token.

    Flow:
    1. Verify Google ID token
    2. Extract user information (email, google_sub)
    3. Upsert user in database
    4. Generate JWT access token
    5. Return token to client

    Args:
        request: GoogleTokenRequest containing Google ID token

    Returns:
        TokenResponse with JWT access token

    Raises:
        HTTPException: If token verification fails or authentication error occurs
    """
    try:
        # Step 1: Verify Google token
        user_info = await verify_google_token(request.token)
        email = user_info["email"]
        google_sub = user_info["google_sub"]

        # Step 2: Authenticate user (upsert logic)
        user = await authenticate_user(email=email, google_sub=google_sub)

        # Step 3: Generate JWT access token
        # Use user.id as the subject (sub) claim
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = create_access_token(data=token_data)

        logger.info(f"User {user.email} authenticated successfully")

        return TokenResponse(access_token=access_token, token_type="bearer")

    except ValueError as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication",
        )

