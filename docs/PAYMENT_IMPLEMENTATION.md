# Payment System Implementation (Lemon Squeezy)

**Date:** 2025-01-XX  
**Status:** ✅ Complete

---

## 📋 Overview

Implemented complete Lemon Squeezy payment integration with strict audit trail, idempotency, and webhook signature verification.

---

## ✅ Implementation Details

### 1. Payment Schemas ✅

**Location:** `backend/app/api/schemas/payment.py`

**Models:**
- `CheckoutCustomData` - Custom data passed to checkout (user_id)
- `CheckoutAttributes` - Checkout attributes for API
- `CheckoutRequest` - Request model for creating checkout
- `CheckoutResponse` - Response with checkout URL and ID
- `WebhookMeta` - Webhook meta data (contains custom_data)
- `WebhookAttributes` - Event attributes (status, renews_at, etc.)
- `WebhookData` - Webhook data object
- `WebhookPayload` - Complete webhook payload
- `CustomerPortalResponse` - Customer portal URL response

### 2. Payment Service ✅

**Location:** `backend/app/services/payment_service.py`

**Functions:**

#### `verify_signature(raw_body, signature, secret)`
- Verifies HMAC SHA256 signature from `X-Signature` header
- Uses `hmac.compare_digest` for constant-time comparison
- Returns `True` if valid, `False` otherwise

#### `create_checkout_link(user_id, email)`
- Creates Lemon Squeezy checkout via API
- Passes `user_id` in `checkout_data.custom` (accessible in webhook)
- Returns checkout URL and ID
- Uses `httpx.AsyncClient` for async HTTP requests

#### `get_customer_portal_url(subscription_id)`
- Retrieves customer portal URL for subscription management
- Falls back to manual URL construction if needed

#### `process_webhook(event_name, event_data, raw_payload, db)`
- **Idempotency Check:** Queries `payment_events` table by `lemon_squeezy_id`
- **Audit Log:** Inserts raw JSON into `payment_events` with `processed=False`
- **Business Logic:**
  - `subscription_created/updated`: Sets `user.is_pro=True`, updates `subscription_id`, `plan_expiry_date`
  - `subscription_expired`: Sets `user.is_pro=False`, clears `plan_expiry_date`
  - `subscription_cancelled`: Logs cancellation (keeps Pro until expiry)
- **Commit:** Marks event as `processed=True` after successful update

### 3. Payment Endpoints ✅

**Location:** `backend/app/api/endpoints/payment.py`

#### `POST /api/v1/payment/checkout` (Protected)
- Requires authentication (`get_current_user`)
- Creates checkout link for current user
- Returns checkout URL and ID

#### `POST /api/v1/payment/webhook` (Public)
- **Critical:** Reads `request.body()` as bytes for signature verification
- Verifies HMAC signature from `X-Signature` header
- Parses JSON payload
- Processes webhook with idempotency and audit trail
- **Error Handling:** Always returns 200 to prevent Lemon Squeezy retries
- Logs errors heavily for manual review

#### `GET /api/v1/payment/portal` (Protected)
- Requires authentication
- Returns customer portal URL for subscription management
- Returns 404 if no active subscription

### 4. Configuration ✅

**Location:** `backend/app/core/config.py`

**Added Settings:**
- `lemon_squeezy_api_key` - API key for Lemon Squeezy API
- `lemon_squeezy_webhook_secret` - Secret for webhook signature verification
- `lemon_squeezy_store_id` - Store ID for checkout creation
- `lemon_squeezy_variant_id` - Product variant ID for Pro subscription

---

## 🔐 Security Features

1. **Signature Verification:**
   - HMAC SHA256 verification of all webhook requests
   - Constant-time comparison to prevent timing attacks
   - Rejects requests with invalid signatures

2. **Idempotency:**
   - Checks `payment_events` table before processing
   - Prevents duplicate processing of same event
   - Returns immediately if event already processed

3. **Audit Trail:**
   - All webhook events stored in `payment_events` table
   - Raw JSON payload preserved for audit
   - `processed` flag tracks processing status
   - Failed events remain with `processed=False` for review

---

## 📊 Webhook Event Processing

### Event Types Handled:

1. **`subscription_created`**
   - Activates Pro subscription
   - Sets `user.is_pro = True`
   - Updates `subscription_id` and `plan_expiry_date`

2. **`subscription_updated`**
   - Updates subscription details
   - Refreshes `plan_expiry_date` from `renews_at`

3. **`subscription_expired`**
   - Deactivates Pro subscription
   - Sets `user.is_pro = False`
   - Clears `plan_expiry_date`

4. **`subscription_cancelled`**
   - Logs cancellation
   - Keeps Pro active until expiry date

---

## 🔄 Webhook Flow

```
1. Lemon Squeezy sends webhook
   ↓
2. Read raw body as bytes
   ↓
3. Verify HMAC signature
   ↓
4. Parse JSON payload
   ↓
5. Check idempotency (payment_events table)
   ↓
6. Insert audit log (processed=False)
   ↓
7. Process business logic (update user)
   ↓
8. Mark as processed (processed=True)
   ↓
9. Commit transaction
   ↓
10. Return 200 OK (even on errors)
```

---

## 🛡️ Error Handling

### Webhook Endpoint:
- **Always returns 200** to prevent Lemon Squeezy retries
- Logs errors heavily for manual review
- Failed events remain in `payment_events` with `processed=False`
- Allows manual reprocessing if needed

### Checkout Endpoint:
- Returns 500 on configuration errors
- Returns 500 on API failures
- Logs all errors with full context

### Portal Endpoint:
- Returns 404 if no subscription found
- Returns 500 on API failures

---

## 📝 Environment Variables

Required in `.env`:

```env
LEMON_SQUEEZY_API_KEY=your_api_key_here
LEMON_SQUEEZY_WEBHOOK_SECRET=your_webhook_secret_here
LEMON_SQUEEZY_STORE_ID=your_store_id_here
LEMON_SQUEEZY_VARIANT_ID=your_variant_id_here
```

---

## 🧪 Testing

### Manual Testing:

1. **Create Checkout:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/payment/checkout \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json"
   ```

2. **Webhook Testing:**
   - Use Lemon Squeezy webhook testing tool
   - Or send POST request with proper signature
   - Check `payment_events` table for audit log

3. **Customer Portal:**
   ```bash
   curl http://localhost:8000/api/v1/payment/portal \
     -H "Authorization: Bearer <token>"
   ```

---

## 📋 Database Schema

**`payment_events` table:**
- `id` (UUID, PK)
- `lemon_squeezy_id` (String, Index, Unique) - For idempotency
- `event_name` (String) - Event type
- `payload` (JSONB) - Raw webhook payload
- `processed` (Boolean, Default: False) - Processing status
- `created_at` (DateTime, UTC)

---

## ✅ Compliance with Tech Spec

- ✅ **Audit Trail:** All webhook events logged to `payment_events`
- ✅ **Idempotency:** Check `payment_events` before processing
- ✅ **Signature Verification:** HMAC SHA256 verification
- ✅ **Error Handling:** Returns 200 even on errors (prevents retries)
- ✅ **User Updates:** Updates `is_pro`, `subscription_id`, `plan_expiry_date`
- ✅ **Custom Data:** Passes `user_id` in checkout for webhook processing

---

**Status:** ✅ **COMPLETE** - Payment system ready for integration testing

