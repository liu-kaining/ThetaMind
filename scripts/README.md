# Backend Test Scripts

## Smoke Test Script

### `test_backend_flow.py`

A comprehensive smoke test script that verifies critical backend API paths according to Tech Spec v2.0.

### Prerequisites

1. **Backend server running:**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```
   Or using Docker:
   ```bash
   docker-compose up backend
   ```

2. **Dependencies installed:**
   ```bash
   pip install httpx python-dotenv
   ```

3. **Environment variables:**
   - `JWT_SECRET_KEY` must be set in `.env` file (for token generation)

### Usage

```bash
# From project root
python scripts/test_backend_flow.py
```

Or make it executable:
```bash
chmod +x scripts/test_backend_flow.py
./scripts/test_backend_flow.py
```

### What It Tests

The script follows the "Happy Path" test sequence:

1. **Health Check** (`GET /health` or `GET /`)
   - Verifies server is running
   - Asserts status 200

2. **Market Data (Pro User)** (`GET /api/v1/market/chain`)
   - Tests option chain endpoint with Pro user token
   - Asserts status 200
   - Asserts response contains `calls` and `puts` fields
   - Checks cache status

3. **Create Strategy** (`POST /api/v1/strategies`)
   - Creates a sample Iron Condor strategy
   - Asserts response contains `id` field
   - Asserts status 201

4. **List Strategies** (`GET /api/v1/strategies`)
   - Lists user's strategies
   - Asserts the newly created strategy ID is in the list

5. **Generate AI Report** (`POST /api/v1/ai/report`)
   - Tests AI report generation
   - Handles graceful error responses (500/503) if external APIs are missing
   - Verifies structured error messages (not crashes)

### Mock Authentication

The script uses **Mock Authentication** (not browser login):
- Directly imports `app.core.security.create_access_token`
- Generates a valid JWT token for a mock Pro user:
  - `user_id`: Random UUID
  - `email`: "test_pro@example.com"
  - `is_pro`: True (implicit via token)
- Injects token into headers: `{"Authorization": f"Bearer {token}"}`

### Test User

The script generates a mock Pro user with:
- Email: `test_pro@example.com`
- User ID: Random UUID (generated each run)
- Tier: Pro user (for testing Pro features)

**Note:** This is a mock user - no database record is created. The token is valid but the user may not exist in the database. For full testing, ensure the user exists or update the script to create the user.

### API Routes

The script uses `/api/v1/` prefix for all endpoints:
- `/api/v1/market/chain`
- `/api/v1/strategies`
- `/api/v1/ai/report`

**Note:** If your backend routes don't have the `/api/v1/` prefix, you may need to:
1. Update `backend/app/main.py` to add versioned router prefix, OR
2. Update the script to use actual routes (e.g., `/market/chain`)

### Output

The script prints:
- ✅ Success indicators
- ❌ Error messages
- 📊 Response status codes
- 📋 Response data summaries
- 💾 Cache status

### Example Output

```
============================================================
🧪 ThetaMind Backend Smoke Test - Tech Spec v2.0
============================================================

📍 Target: http://localhost:8000
🔑 Mock Pro User: test_pro@example.com
   User ID: abc12345-...

✅ Generated JWT token for Pro user: test_pro@example.com
   User ID: abc12345-...

============================================================
🏥 Step 1: Health Check
============================================================

🔍 Request: GET http://localhost:8000/health

📥 Response Status: 200
✅ Health Check PASSED
   Status: healthy
   Environment: development

============================================================
📊 Step 2: Market Data (Pro User)
============================================================

🔍 Request: GET http://localhost:8000/api/v1/market/chain
   Params: symbol=AAPL, expiration_date=2024-06-21
   Headers: Authorization: Bearer <token>

📥 Response Status: 200
✅ Market Data Test PASSED
   Symbol: AAPL
   Expiration: 2024-06-21
   Calls: 50 options
   Puts: 50 options
   Spot Price: $150.25
   Source: api
   💾 Cache: MISS (fetched from API)

============================================================
📝 Step 3: Create Strategy
============================================================

✅ Strategy Creation PASSED
   Strategy ID: xyz67890-...
   Name: Iron Condor Test abc12345

============================================================
📋 Step 4: List Strategies
============================================================

✅ List Strategies Test PASSED
   Total Strategies: 1
   Strategy ID Found: ✅

============================================================
🤖 Step 5: Generate AI Report
============================================================

✅ AI Report Generation PASSED
   Report ID: def45678-...
   Model Used: gemini-2.5-pro
   Content Length: 1234 characters

============================================================
📊 Test Summary
============================================================

   ✅ PASS - Health Check
   ✅ PASS - Market Data
   ✅ PASS - Create Strategy
   ✅ PASS - List Strategies
   ✅ PASS - AI Report

   Total: 5/5 tests passed

✅ All tests passed!
```

### Error Handling

The script handles various error scenarios gracefully:

- **Connection Errors:** Clear message if server is not running
- **Missing Environment Variables:** Error message if JWT_SECRET_KEY is missing
- **API Errors (500/503):** Verifies structured error responses (not crashes)
- **Quota Exceeded (429):** Accepts as valid test result
- **Timeouts:** Handles gracefully for external API calls

### Troubleshooting

**Connection Error:**
```
❌ Health Check FAILED: Cannot connect to http://localhost:8000
```
- Make sure backend is running on `localhost:8000`
- Check if port 8000 is available

**JWT Token Error:**
```
❌ Failed to generate token: ...
```
- Verify `JWT_SECRET_KEY` is set in `.env` file
- Check that `backend/.env` exists and is readable

**404 Not Found:**
```
❌ Market Data Test FAILED: Status 404
```
- Check if routes have `/api/v1/` prefix
- If not, update `backend/app/main.py` to add versioned router, OR
- Update script to use actual routes

**Import Error:**
```
ModuleNotFoundError: No module named 'app'
```
- Make sure you're running from project root
- Check that `backend/` directory exists
- Verify Python path is set correctly in script

### Notes

- The script runs **outside** the Docker container
- It connects to `localhost:8000` (adjust `BASE_URL` if needed)
- Mock user token is generated using the same security module as the backend
- The script uses actual backend code imports (not mocked)
- All assertions are explicit and provide clear error messages
- Date:20251209