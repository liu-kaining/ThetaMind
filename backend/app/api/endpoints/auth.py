"""Authentication API endpoints."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.models import AIReport, Strategy, User
from app.db.session import get_db
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


class UserMeResponse(BaseModel):
    """Current user details response model."""

    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    is_pro: bool = Field(..., description="Pro subscription status")
    is_superuser: bool = Field(..., description="Superuser status")
    subscription_id: str | None = Field(None, description="Subscription ID")
    subscription_type: str | None = Field(None, description="Subscription type: 'monthly' or 'yearly'")
    plan_expiry_date: str | None = Field(None, description="Plan expiry date (ISO format)")
    daily_ai_usage: int = Field(..., description="Daily AI report usage count")
    daily_ai_quota: int = Field(..., description="Daily AI report quota limit")
    daily_image_usage: int = Field(..., description="Daily image generation usage count")
    daily_image_quota: int = Field(..., description="Daily image generation quota limit")
    created_at: str = Field(..., description="Account creation date (ISO format)")


@router.get("/me", response_model=UserMeResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserMeResponse:
    """
    Get current authenticated user's information.

    Returns user details including subscription status and usage quota.

    Args:
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        UserMeResponse with user details
    """
    from app.api.endpoints.ai import get_ai_quota_limit, get_image_quota_limit

    try:
        # Calculate quota based on subscription type
        ai_quota = get_ai_quota_limit(current_user)
        image_quota = get_image_quota_limit(current_user)

        return UserMeResponse(
            id=str(current_user.id),
            email=current_user.email,
            is_pro=current_user.is_pro,
            is_superuser=current_user.is_superuser,
            subscription_id=current_user.subscription_id,
            plan_expiry_date=current_user.plan_expiry_date.isoformat() if current_user.plan_expiry_date else None,
            daily_ai_usage=current_user.daily_ai_usage,
            daily_ai_quota=ai_quota,
            daily_image_usage=current_user.daily_image_usage,
            daily_image_quota=image_quota,
            subscription_type=current_user.subscription_type,
            created_at=current_user.created_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Error fetching user info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user information",
        )

