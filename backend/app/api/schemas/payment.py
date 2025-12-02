"""Payment schemas for Lemon Squeezy integration."""

from typing import Any
from pydantic import BaseModel, Field


class CheckoutCustomData(BaseModel):
    """Custom data passed to checkout (stored in meta.custom)."""

    user_id: str = Field(..., description="User UUID as string")


class CheckoutAttributes(BaseModel):
    """Checkout attributes for Lemon Squeezy API."""

    store_id: str = Field(..., description="Lemon Squeezy store ID")
    variant_id: str = Field(..., description="Product variant ID")
    custom_price: int | None = Field(None, description="Custom price in cents")
    expires_at: str | None = Field(None, description="Checkout expiration ISO datetime")
    checkout_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom data to pass to checkout (stored in meta.custom)",
    )


class CheckoutRequest(BaseModel):
    """Request model for creating checkout."""

    data: CheckoutAttributes = Field(..., description="Checkout attributes")


class CheckoutResponse(BaseModel):
    """Response model for checkout creation."""

    checkout_url: str = Field(..., description="Checkout URL to redirect user")
    checkout_id: str = Field(..., description="Lemon Squeezy checkout ID")


class WebhookMeta(BaseModel):
    """Webhook meta data (contains custom_data)."""

    custom: dict[str, Any] = Field(default_factory=dict, description="Custom data from checkout")


class WebhookAttributes(BaseModel):
    """Webhook event attributes."""

    store_id: str | None = None
    customer_id: str | None = None
    order_id: str | None = None
    order_item_id: str | None = None
    product_id: str | None = None
    variant_id: str | None = None
    product_name: str | None = None
    variant_name: str | None = None
    user_name: str | None = None
    user_email: str | None = None
    status: str | None = None
    status_formatted: str | None = None
    card_brand: str | None = None
    card_last_four: str | None = None
    renews_at: str | None = Field(None, description="Subscription renewal date (ISO datetime)")
    ends_at: str | None = Field(None, description="Subscription end date (ISO datetime)")
    trial_ends_at: str | None = None
    price: int | None = None
    currency: str | None = None
    test_mode: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class WebhookData(BaseModel):
    """Webhook data object."""

    id: str = Field(..., description="Lemon Squeezy event ID")
    type: str = Field(..., description="Event type (e.g., 'subscriptions')")
    attributes: WebhookAttributes = Field(..., description="Event attributes")
    meta: WebhookMeta = Field(default_factory=WebhookMeta, description="Meta data with custom fields")


class WebhookPayload(BaseModel):
    """Lemon Squeezy webhook payload."""

    meta: WebhookMeta = Field(..., description="Webhook meta data")
    data: WebhookData = Field(..., description="Webhook event data")


class CustomerPortalResponse(BaseModel):
    """Response model for customer portal URL."""

    portal_url: str = Field(..., description="Customer portal URL")

