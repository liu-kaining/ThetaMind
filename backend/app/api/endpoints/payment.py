"""Payment API endpoints for Lemon Squeezy integration."""

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas.payment import (
    CheckoutResponse,
    CustomerPortalResponse,
    WebhookPayload,
)
from pydantic import BaseModel, Field
from app.core.config import settings
from app.db.models import User
from app.services.payment_service import (
    create_checkout_link,
    get_customer_portal_url,
    process_webhook,
    verify_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["payment"])


class CheckoutRequest(BaseModel):
    """Checkout request model."""
    variant_type: str = Field(default="monthly", description="Subscription type: 'monthly' or 'yearly'")


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_200_OK)
async def create_checkout(
    request: CheckoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CheckoutResponse:
    """
    Create a Lemon Squeezy checkout link for Pro subscription.

    Protected endpoint - requires authentication.

    Args:
        request: Checkout request with variant_type ("monthly" or "yearly")

    Returns:
        CheckoutResponse with checkout URL and ID
    """
    # Validate variant_type
    if request.variant_type.lower() not in ("monthly", "yearly"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="variant_type must be 'monthly' or 'yearly'",
        )
    
    try:
        result = await create_checkout_link(
            user_id=current_user.id,
            email=current_user.email,
            variant_type=request.variant_type,
        )

        return CheckoutResponse(
            checkout_url=result["checkout_url"],
            checkout_id=result["checkout_id"],
        )
    except ValueError as e:
        logger.error(f"Checkout creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment configuration error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Failed to create checkout: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout link",
        )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_webhook(request: Request) -> dict[str, str]:
    """
    Handle Lemon Squeezy webhook events with enhanced security.

    Public endpoint (no auth required) - secured by:
    1. HMAC signature verification (timing-safe)
    2. Rate limiting (10 requests per minute per IP)
    3. Returns 200 for success; 500 for processing errors (allows LS retry)

    Flow:
    1. Rate limit check (simple in-memory tracking)
    2. Read raw body for signature verification
    3. Verify HMAC signature (timing-safe)
    4. Parse JSON payload
    5. Process webhook (idempotent, with audit trail)
    6. Return 200 on success, 500 on processing error

    Returns:
        Success/error message with appropriate HTTP status
    """
    from app.core.constants import RateLimits
    from collections import defaultdict
    from time import time

    # ⚠️ LIMITATION: In-memory rate limiter — only effective for single-process deployments.
    # Each gunicorn worker / K8s replica maintains its own counter, so an attacker
    # can bypass the limit by distributing requests across workers.
    # TODO(scaling): Before scaling to multi-worker or multi-replica, migrate to
    # Redis-based sliding window rate limiting (e.g., cache_service.incr with TTL).
    client_ip = request.client.host if request.client else "unknown"

    if not hasattr(handle_webhook, '_rate_limit_store'):
        handle_webhook._rate_limit_store: dict[str, list[float]] = defaultdict(list)
    
    current_time = time()
    request_times = handle_webhook._rate_limit_store[client_ip]
    
    # Remove requests older than 1 minute
    request_times[:] = [t for t in request_times if current_time - t < 60]
    
    # Check rate limit
    if len(request_times) >= RateLimits.WEBHOOK_REQUESTS_PER_MINUTE:
        logger.warning(
            f"Webhook rate limit exceeded for IP {client_ip}: {len(request_times)} requests in last minute"
        )
        return JSONResponse(status_code=429, content={"status": "error", "message": "Rate limit exceeded"})
    
    # Record this request
    request_times.append(current_time)
    
    # Read raw body as bytes for signature verification
    # CRITICAL: Read body once - cannot be read again after this
    raw_body = await request.body()

    # Get signature from header
    signature = request.headers.get("X-Signature", "")
    if not signature:
        logger.warning(f"Webhook missing X-Signature header from IP {client_ip}")
        return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid request"})

    # Verify signature using raw_body (timing-safe comparison)
    if not await verify_signature(raw_body, signature, settings.lemon_squeezy_webhook_secret):
        logger.warning(f"Webhook signature verification failed from IP {client_ip}")
        return JSONResponse(status_code=403, content={"status": "error", "message": "Invalid request"})

    # Parse JSON payload from raw_body bytes
    # CRITICAL FIX: Cannot call request.json() after reading request.body()
    # Must parse JSON manually from the bytes we already read
    try:
        payload: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to parse webhook JSON: {e}", exc_info=True)
        return {"status": "error", "message": "Invalid JSON"}

    # Extract event name and data
    event_name = payload.get("meta", {}).get("event_name", "")
    event_data = payload.get("data", {})

    if not event_name:
        logger.error("Webhook missing event_name in meta")
        return {"status": "error", "message": "Missing event_name"}

    if not event_data:
        logger.error("Webhook missing data")
        return {"status": "error", "message": "Missing data"}

    # Process webhook in database transaction
    # Use a new database session for webhook processing
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            await process_webhook(
                event_name=event_name,
                event_data=event_data,
                raw_payload=payload,
                db=db,
            )
            logger.info(f"Successfully processed webhook: {event_name}")
            return {"status": "success", "message": "Webhook processed"}

        except Exception as e:
            logger.error(
                "Webhook processing failed: event=%s event_id=%s error=%s",
                event_name,
                event_data.get("id", "unknown"),
                str(e),
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Processing failed, will retry"},
            )


@router.get("/pricing", status_code=status.HTTP_200_OK)
async def get_pricing() -> dict[str, Any]:
    """
    Get subscription pricing information.
    
    Public endpoint - no authentication required.
    
    Returns:
        Dictionary with monthly and yearly prices
    """
    return {
        "monthly_price": settings.subscription_price_monthly,
        "yearly_price": settings.subscription_price_yearly,
    }


@router.get("/portal", response_model=CustomerPortalResponse, status_code=status.HTTP_200_OK)
async def get_customer_portal(
    current_user: Annotated[User, Depends(get_current_user)],
) -> CustomerPortalResponse:
    """
    Get customer portal URL for managing subscription.

    Protected endpoint - requires authentication.

    Returns:
        CustomerPortalResponse with portal URL
    """
    if not current_user.subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found",
        )

    try:
        portal_url = await get_customer_portal_url(current_user.subscription_id)
        return CustomerPortalResponse(portal_url=portal_url)
    except Exception as e:
        logger.error(f"Failed to get customer portal URL: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer portal URL",
        )

