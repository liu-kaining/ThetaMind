# 📚 Official Documentation Reference

**Purpose:** This document tracks official documentation sources for critical dependencies to ensure accurate implementation.

---

## 🔑 Critical Dependencies & Documentation

### 1. Tiger Brokers Python SDK (tigeropen)

**Official Docs:** https://docs.itigerup.com/docs/intro

**Key Methods:**
- `quote_client.get_option_chain`
- `quote_client.get_stock_briefs`

**Current Implementation Status:**
- ✅ Using `QuoteClient` from `tigeropen.quote.quote_client`
- ⚠️ **NEEDS VERIFICATION:**
  - Initialization: Currently using `get_client_config()` - verify correct method
  - `get_option_chain()` parameter name: Currently using `expiry=` - verify if correct or should be `expiration_date=`
  - `get_market_status()` method: Verify if this method exists and correct parameters
  - Config parameters: Verify if `private_key`, `tiger_id`, `account` are correct

**Action Required:** Please verify the exact method signatures from the official docs.

---

### 2. Google Gemini SDK (google-generativeai)

**Official Docs:** https://ai.google.dev/api/python/google/generativeai

**Key Features:**
- `tools='google_search'` - Google Search grounding
- `response_mime_type='application/json'` - JSON output format

**Current Implementation Status:**
- ✅ Using `genai.GenerativeModel()` with `tools="google_search"`
- ✅ Using `GenerationConfig(response_mime_type="application/json")`
- ⚠️ **NEEDS VERIFICATION:**
  - `tools="google_search"` - Verify if this is a string or list/array format
  - `response_mime_type` - Verify if this is the correct parameter name in `GenerationConfig`
  - `generate_content_async()` - Verify if this is the correct async method name

**Action Required:** Please verify the exact parameter formats from the official docs.

---

### 3. Lemon Squeezy API

**Official Docs:** https://docs.lemonsqueezy.com/api

**Key Logic:**
- Webhook signature verification using HMAC SHA256

**Current Implementation Status:**
- ❌ **NOT YET IMPLEMENTED**
- Payment service needs to be created
- Webhook endpoint needs HMAC SHA256 signature verification

**Action Required:** Implement payment service with webhook verification when ready.

---

### 4. TradingView Lightweight Charts

**Official Docs:** https://tradingview.github.io/lightweight-charts/

**Context:** React wrapper implementation

**Current Implementation Status:**
- ❌ **NOT YET IMPLEMENTED** (Frontend)
- Will be used for candlestick charts in frontend

**Action Required:** Implement when building frontend charting components.

---

## ⚠️ Verification Checklist

### Tiger SDK (`tiger_service.py`)

- [ ] Verify `get_client_config()` is the correct initialization method
- [ ] Verify `get_option_chain()` method signature:
  - Parameter name: `expiry` vs `expiration_date` vs `expiration`?
  - Parameter format: String (YYYY-MM-DD) or timestamp?
- [ ] Verify `get_market_status()` method exists and parameters
- [ ] Verify config initialization parameters match SDK requirements

### Gemini SDK (`gemini_provider.py`)

- [ ] Verify `tools="google_search"` format (string vs list)
- [ ] Verify `GenerationConfig(response_mime_type="application/json")` syntax
- [ ] Verify `generate_content_async()` is the correct async method
- [ ] Verify error handling for API responses

### Lemon Squeezy (Future)

- [ ] Implement webhook signature verification (HMAC SHA256)
- [ ] Verify webhook payload structure
- [ ] Implement idempotency checks

---

## 📝 Code Review Notes

### Current Assumptions (Need Verification):

1. **Tiger SDK:**
   ```python
   # Assumed method call:
   await self._call_tiger_api_async(
       "get_option_chain", 
       symbol=symbol, 
       expiry=expiration_date  # ⚠️ Verify parameter name
   )
   ```

2. **Gemini SDK:**
   ```python
   # Assumed format:
   tools="google_search"  # ⚠️ Verify if string or list
   
   GenerationConfig(response_mime_type="application/json")  # ⚠️ Verify syntax
   ```

---

## 🎯 Action Items

1. **Immediate:** Verify Tiger SDK method signatures and parameters
2. **Immediate:** Verify Gemini SDK parameter formats
3. **Future:** Implement Lemon Squeezy webhook verification
4. **Future:** Implement TradingView charts in frontend

---

## 📌 Usage Guidelines

**When implementing or modifying code that uses these libraries:**

1. ✅ **Always** refer to the official documentation first
2. ✅ **Verify** parameter names and types match the docs
3. ✅ **Ask** for clarification if documentation is unclear
4. ✅ **Update** this document if you find discrepancies
5. ❌ **Never** assume method signatures without verification

---

**Last Updated:** 2025-01-XX  
**Status:** Awaiting verification of Tiger and Gemini SDK implementations

