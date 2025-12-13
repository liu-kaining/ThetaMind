"""Payment service for Lemon Squeezy integration."""

import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import PaymentEvent, User

logger = logging.getLogger(__name__)

# Lemon Squeezy API base URL
LEMON_SQUEEZY_API_BASE = "https://api.lemonsqueezy.com/v1"


async def verify_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """
    Verify Lemon Squeezy webhook signature using HMAC SHA256.

    Args:
        raw_body: Raw request body as bytes
        signature: Signature from X-Signature header
        secret: Webhook secret from settings

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}", exc_info=True)
        return False


async def create_checkout_link(
    user_id: uuid.UUID,
    email: str,
    variant_type: str = "monthly",
) -> dict[str, Any]:
    """
    Create a Lemon Squeezy checkout link.

    Args:
        user_id: User UUID
        email: User email address
        variant_type: Subscription type - "monthly" or "yearly" (default: "monthly")

    Returns:
        Dictionary with checkout_url and checkout_id

    Raises:
        Exception: If checkout creation fails
    """
    # Select variant ID based on type
    if variant_type.lower() == "yearly":
        variant_id = settings.lemon_squeezy_variant_id_yearly
        if not variant_id:
            logger.warning("Yearly variant ID not configured, falling back to monthly")
            variant_id = settings.lemon_squeezy_variant_id
    else:
        variant_id = settings.lemon_squeezy_variant_id
    
    # In development, allow empty store_id and variant_id (payment features will be disabled)
    if settings.environment == "production" and (not settings.lemon_squeezy_store_id or not variant_id):
        raise ValueError("Lemon Squeezy store_id and variant_id must be configured in production")
    
    # In development, return a mock checkout URL if not configured
    if not settings.lemon_squeezy_store_id or not variant_id:
        logger.warning(f"Lemon Squeezy not configured (variant_type={variant_type}) - returning mock checkout URL")
        return {
            "checkout_url": f"https://lemonsqueezy.com/checkout/buy/not-configured-{variant_type}",
            "checkout_id": f"mock-checkout-id-{variant_type}",
        }

    url = f"{LEMON_SQUEEZY_API_BASE}/checkouts"
    headers = {
        "Authorization": f"Bearer {settings.lemon_squeezy_api_key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }

    # Pass user_id in checkout_data.custom (accessible in webhook meta.custom)
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "store_id": settings.lemon_squeezy_store_id,
                "variant_id": variant_id,
                "checkout_data": {
                    "custom": {
                        "user_id": str(user_id),
                        "email": email,
                    },
                },
            },
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract checkout URL and ID from response
            checkout_data = data.get("data", {})
            checkout_id = checkout_data.get("id", "")
            attributes = checkout_data.get("attributes", {})
            checkout_url = attributes.get("url", "")

            if not checkout_url:
                raise ValueError("Checkout URL not found in response")

            logger.info(f"Created checkout for user {user_id}: {checkout_id}")

            return {
                "checkout_url": checkout_url,
                "checkout_id": checkout_id,
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Lemon Squeezy API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to create checkout: {e}", exc_info=True)
            raise


async def get_customer_portal_url(subscription_id: str) -> str:
    """
    Get customer portal URL for managing subscription.

    Args:
        subscription_id: Lemon Squeezy subscription ID

    Returns:
        Customer portal URL

    Raises:
        Exception: If portal URL retrieval fails
    """
    url = f"{LEMON_SQUEEZY_API_BASE}/subscriptions/{subscription_id}"
    headers = {
        "Authorization": f"Bearer {settings.lemon_squeezy_api_key}",
        "Accept": "application/vnd.api+json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Extract customer portal URL from response
            subscription_data = data.get("data", {})
            attributes = subscription_data.get("attributes", {})
            portal_url = attributes.get("urls", {}).get("customer_portal", "")

            if not portal_url:
                # Fallback: construct portal URL manually
                store_id = attributes.get("store_id", "")
                if store_id:
                    portal_url = f"https://app.lemonsqueezy.com/my-orders"
                else:
                    raise ValueError("Unable to construct customer portal URL")

            return portal_url
        except httpx.HTTPStatusError as e:
            logger.error(f"Lemon Squeezy API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to get customer portal URL: {e}", exc_info=True)
            raise


async def process_webhook(
    event_name: str,
    event_data: dict[str, Any],
    raw_payload: dict[str, Any],
    db: AsyncSession,
) -> None:
    """
    Process Lemon Squeezy webhook event with idempotency and audit trail.

    Flow:
    1. Check idempotency (payment_events table)
    2. Insert audit log (processed=False)
    3. Process business logic (update user)
    4. Mark as processed (processed=True)

    Args:
        event_name: Event name (e.g., 'subscription_created')
        event_data: Event data from webhook
        raw_payload: Complete raw webhook payload for audit
        db: Database session

    Raises:
        Exception: If processing fails
    """
    # Extract Lemon Squeezy event ID for idempotency
    lemon_squeezy_id = event_data.get("id", "")
    if not lemon_squeezy_id:
        raise ValueError("Event ID not found in webhook data")

    # Step 1: Idempotency check
    result = await db.execute(
        select(PaymentEvent).where(PaymentEvent.lemon_squeezy_id == lemon_squeezy_id)
    )
    existing_event = result.scalar_one_or_none()

    if existing_event and existing_event.processed:
        logger.info(f"Webhook event {lemon_squeezy_id} already processed, skipping")
        return

    # Step 2: Insert audit log (transaction will be committed after business logic)
    if not existing_event:
        payment_event = PaymentEvent(
            lemon_squeezy_id=lemon_squeezy_id,
            event_name=event_name,
            payload=raw_payload,
            processed=False,
        )
        db.add(payment_event)
        await db.flush()  # Get ID without committing
    else:
        payment_event = existing_event

    # Step 3: Business logic - update user based on event type
    try:
        attributes = event_data.get("attributes", {})
        meta = raw_payload.get("meta", {})
        custom_data = meta.get("custom", {})

        # Extract user_id from custom data (passed during checkout)
        user_id_str = custom_data.get("user_id")
        if not user_id_str:
            logger.warning(f"No user_id in custom data for event {lemon_squeezy_id}")
            # Try to find user by email as fallback
            user_email = attributes.get("user_email")
            if user_email:
                result = await db.execute(select(User).where(User.email == user_email))
                user = result.scalar_one_or_none()
            else:
                user = None
        else:
            try:
                user_id = uuid.UUID(user_id_str)
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
            except ValueError:
                logger.error(f"Invalid user_id format: {user_id_str}")
                user = None

        if not user:
            logger.error(f"User not found for event {lemon_squeezy_id}")
            # Still mark as processed to prevent retries
            payment_event.processed = True
            await db.commit()
            return

        # Process different event types
        if event_name in ("subscription_created", "subscription_updated"):
            # Activate Pro subscription
            user.is_pro = True
            user.subscription_id = lemon_squeezy_id

            # Parse renewal date
            renews_at_str = attributes.get("renews_at")
            if renews_at_str:
                try:
                    renews_at = datetime.fromisoformat(renews_at_str.replace("Z", "+00:00"))
                    user.plan_expiry_date = renews_at
                except Exception as e:
                    logger.warning(f"Failed to parse renews_at: {e}")

            logger.info(f"Activated Pro subscription for user {user.id}")

        elif event_name == "subscription_expired":
            # Deactivate Pro subscription
            user.is_pro = False
            user.plan_expiry_date = None
            logger.info(f"Deactivated Pro subscription for user {user.id}")

        elif event_name == "subscription_cancelled":
            # Mark subscription as cancelled (keep Pro until expiry)
            # Don't set is_pro=False immediately, let it expire naturally
            logger.info(f"Subscription cancelled for user {user.id}")

        # Step 4: Mark as processed and commit
        payment_event.processed = True
        await db.commit()

        logger.info(f"Successfully processed webhook event {lemon_squeezy_id}")

    except Exception as e:
        logger.error(f"Error processing webhook business logic: {e}", exc_info=True)
        await db.rollback()
        # Don't mark as processed on error - allow retry
        raise

