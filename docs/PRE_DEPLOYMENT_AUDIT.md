# ThetaMind Pre-Deployment Audit Report

**Date:** 2025-12-10  
**Auditor:** DevOps Engineer  
**Status:** ⚠️ **REQUIRES FIXES BEFORE PRODUCTION**

---

## Executive Summary

The codebase is **mostly ready** for production deployment, but **critical security and configuration issues** must be addressed. The application uses async task processing (not Celery), which simplifies deployment but requires proper production configuration.

**Critical Blockers:** 3  
**Warnings:** 4  
**Recommendations:** 2

---

## 1. Environment Configuration

**Component:** `backend/app/core/config.py`

**Status:** ⚠️ **WARNING**

### Issues Found:

1. ✅ **All required keys are present:**
   - `LEMON_SQUEEZY_STORE_ID` - ✅ Defined (line 41)
   - `TIGER_PRIVATE_KEY` - ✅ Defined (line 27)
   - `GOOGLE_CLIENT_ID` - ✅ Defined (line 35)

2. ❌ **Missing `DOMAIN` or `ALLOWED_ORIGINS` environment variable:**
   - CORS configuration in `main.py` uses hardcoded localhost URLs
   - No way to configure production domain via environment variable

3. ⚠️ **Default values that could be dangerous:**
   - `debug: bool = False` - ✅ Safe default
   - `environment: str = "development"` - ⚠️ Should default to "production" or require explicit setting
   - `use_mock_data: bool = False` - ✅ Safe default

### Action Required:

1. **Add `DOMAIN` and `ALLOWED_ORIGINS` to `config.py`:**
   ```python
   # Frontend Domain Configuration
   domain: str = ""  # Production domain (e.g., https://thetamind.com)
   allowed_origins: list[str] = []  # Comma-separated list of allowed origins
   ```

2. **Update `docker-compose.yml` to include:**
   ```yaml
   - DOMAIN=${DOMAIN:-}
   - ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-}
   ```

---

## 2. Docker & Build Optimization

**Component:** Dockerfiles

**Status:** ❌ **BLOCKER** (Backend) / ✅ **READY** (Frontend)

### Backend Dockerfile Issues:

**File:** `backend/Dockerfile`

1. ❌ **Line 31: Using `--reload` flag in production:**
   ```dockerfile
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
   ```
   - `--reload` is for development only
   - Should use production ASGI server with workers

2. ⚠️ **No production ASGI server configuration:**
   - Should use `gunicorn` with `uvicorn workers` or `uvicorn` with `--workers` flag
   - No process manager for production

### Frontend Dockerfile:

**File:** `frontend/Dockerfile`

✅ **Status: READY**
- Multi-stage build ✅
- Nginx serving static files ✅
- SPA fallback configured ✅ (line 41: `try_files $uri $uri/ /index.html;`)

### Action Required:

**Update `backend/Dockerfile` line 31:**
```dockerfile
# Production command (remove --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**OR use Gunicorn (recommended for production):**
```dockerfile
# Install gunicorn in requirements.txt first
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000"]
```

---

## 3. Database & Migrations

**Component:** Alembic & Database Initialization

**Status:** ❌ **BLOCKER**

### Issues Found:

1. ❌ **No `entrypoint.sh` script for automatic migrations:**
   - Migrations must be run manually: `alembic upgrade head`
   - Container startup does not ensure database schema is up-to-date

2. ⚠️ **`alembic.ini` has placeholder database URL (line 61):**
   ```ini
   sqlalchemy.url = driver://user:pass@localhost/dbname
   ```
   - This is OK (Alembic reads from environment), but should be documented

3. ✅ **Alembic is properly configured:**
   - `alembic/` directory exists
   - Migration files present: `001_add_superuser_and_system_configs.py`, `002_add_stock_symbols.py`

### Action Required:

**Create `backend/entrypoint.sh`:**
```bash
#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"
```

**Update `backend/Dockerfile` to use entrypoint:**
```dockerfile
# Add after line 21 (COPY ./app /app/app)
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Change CMD to use entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 4. Security & Hardcoding

**Component:** CORS, Swagger UI, Hardcoded URLs

**Status:** ❌ **BLOCKER**

### Issues Found:

1. ❌ **Hardcoded localhost URLs in CORS (`backend/app/main.py` lines 161-174):**
   ```python
   allowed_origins = [
       "http://localhost:3000",
       "http://localhost:5173",
       # ... more localhost URLs
   ]
   ```
   - Production must use environment variable for allowed origins
   - No `DOMAIN` configuration support

2. ❌ **Swagger UI not disabled in production:**
   - FastAPI automatically enables `/docs` and `/redoc` endpoints
   - No check for `ENVIRONMENT=production` to disable them

3. ⚠️ **Frontend API URL hardcoded fallback (`frontend/src/services/api/client.ts` line 3):**
   ```typescript
   const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5300"
   ```
   - Fallback is OK for development, but ensure `VITE_API_URL` is set in production

4. ⚠️ **Nginx config uses `server_name localhost` (`nginx/conf.d/thetamind.conf` line 11):**
   - Should use `server_name _;` or environment variable

### Action Required:

**1. Update `backend/app/core/config.py`:**
```python
# Add to Settings class
domain: str = ""
allowed_origins: list[str] = Field(default_factory=list)
```

**2. Update `backend/app/main.py` CORS configuration:**
```python
# Replace lines 161-174 with:
if settings.is_production:
    if settings.allowed_origins:
        # Parse comma-separated string or use list
        allowed_origins = [origin.strip() for origin in settings.allowed_origins]
    elif settings.domain:
        allowed_origins = [settings.domain, f"https://{settings.domain}", f"http://{settings.domain}"]
    else:
        # Production requires explicit origins
        logger.warning("No ALLOWED_ORIGINS or DOMAIN set in production! Using empty list.")
        allowed_origins = []
else:
    # Development: allow localhost
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:80",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:80",
    ]
```

**3. Disable Swagger in production (`backend/app/main.py` line 151):**
```python
app = FastAPI(
    title="ThetaMind API",
    description="US Stock Option Strategy Analysis Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)
```

**4. Update `docker-compose.yml` backend environment:**
```yaml
- DOMAIN=${DOMAIN:-}
- ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-}
```

---

## 5. Nginx Configuration

**Component:** `nginx/conf.d/thetamind.conf`

**Status:** ⚠️ **WARNING**

### Issues Found:

1. ⚠️ **Missing SPA fallback for React Router:**
   - Frontend routes (line 33) proxy to frontend container, but no `try_files` fallback
   - React Router client-side routes will 404 on direct access

2. ⚠️ **`server_name localhost` should be configurable:**
   - Hardcoded to `localhost` (line 11)
   - Should use `_` (catch-all) or environment variable

3. ✅ **Security headers present:**
   - X-Content-Type-Options ✅
   - X-Frame-Options ✅
   - X-XSS-Protection ✅

### Action Required:

**Update `nginx/conf.d/thetamind.conf` line 33-39:**
```nginx
# Frontend routes with SPA fallback
location / {
    proxy_pass http://frontend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # SPA fallback - if file not found, serve index.html
    try_files $uri $uri/ /index.html;
}
```

**Note:** The frontend Dockerfile already has SPA fallback in its nginx config, but the gateway nginx should also handle it.

**Update line 11:**
```nginx
server_name _;  # Catch-all, or use ${NGINX_SERVER_NAME} if needed
```

---

## 6. Task Queue

**Component:** Task Processing

**Status:** ✅ **READY** (No Celery Worker Needed)

### Findings:

1. ✅ **Tasks use `asyncio.create_task()` (not Celery):**
   - File: `backend/app/api/endpoints/tasks.py` line 62
   - Tasks are processed in the same FastAPI process
   - No separate worker service required

2. ⚠️ **Consideration for production:**
   - Long-running tasks (AI reports) run in the same process
   - If tasks become heavy, consider moving to Celery + Redis
   - Current implementation is acceptable for MVP

### Action Required:

**None** - Current implementation is acceptable. Monitor task performance in production.

---

## Summary of Required Changes

### Critical (Must Fix Before Production):

1. ✅ **Create `backend/entrypoint.sh`** for automatic migrations
2. ✅ **Update `backend/Dockerfile`** to remove `--reload` and use entrypoint
3. ✅ **Add `DOMAIN` and `ALLOWED_ORIGINS` to `config.py`**
4. ✅ **Update CORS in `main.py`** to use environment variables
5. ✅ **Disable Swagger UI in production**
6. ✅ **Add SPA fallback to nginx config**

### Recommended (Should Fix):

1. ⚠️ **Use Gunicorn with Uvicorn workers** for better production performance
2. ⚠️ **Add health check endpoint** for nginx (already exists at `/health` ✅)

---

## Pre-Deployment Checklist

Before pushing to production:

- [ ] Create and test `entrypoint.sh`
- [ ] Remove `--reload` from Dockerfile
- [ ] Add `DOMAIN` and `ALLOWED_ORIGINS` env vars
- [ ] Update CORS configuration
- [ ] Disable Swagger in production
- [ ] Update nginx SPA fallback
- [ ] Test database migrations on fresh database
- [ ] Verify all environment variables are set in production `.env`
- [ ] Test OAuth redirect URLs with production domain
- [ ] Verify Lemon Squeezy webhook URL is configured for production domain

---

## Files to Generate

The following files will be generated in the next section:
1. `backend/entrypoint.sh` - Auto-migration script
2. Updated `backend/Dockerfile` - Production-ready
3. Updated `backend/app/core/config.py` - Add DOMAIN/ALLOWED_ORIGINS
4. Updated `backend/app/main.py` - Production CORS & Swagger disable
5. Updated `nginx/conf.d/thetamind.conf` - SPA fallback

---

**Report Generated:** 2025-12-10  
**Next Steps:** Review and apply fixes, then re-audit before deployment.

