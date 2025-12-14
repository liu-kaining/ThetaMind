# Project Structure

## Directory Organization

```
ThetaMind/
├── backend/                    # Backend FastAPI application
│   ├── app/                    # Application code
│   │   ├── api/                # API endpoints
│   │   ├── core/               # Core configuration
│   │   ├── db/                 # Database models and session
│   │   └── services/           # Business logic services
│   ├── alembic/                # Database migrations
│   ├── scripts/                # Utility scripts
│   ├── tests/                  # ⭐ All test files go here
│   │   ├── services/           # Unit tests for services
│   │   └── test_*.py           # Integration tests
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md               # Backend-specific README
│
├── frontend/                   # Frontend React application
│   ├── src/                    # Source code
│   ├── public/                 # Static assets
│   └── README.md               # Frontend-specific README
│
├── docs/                       # ⭐ All documentation (.md files) go here
│   ├── README.md               # Documentation index
│   ├── PROJECT_STRUCTURE.md    # This file
│   ├── CONFIGURATION_GUIDE.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── ...                     # Other documentation files
│
├── scripts/                    # Project-level scripts
│   └── test_backend_flow.py
│
├── spec/                       # Project specifications
│   ├── prd.md                  # Product requirements
│   └── tech.md                 # Technical specifications
│
├── nginx/                      # Nginx configuration
├── docker-compose.yml          # Docker orchestration
└── README.md                   # Project root README
```

## File Placement Rules

### Test Files (`*.py` starting with `test_` or in `tests/`)
- **Location**: `backend/tests/`
- **Naming**: `test_*.py` or `tests/**/test_*.py`
- **Examples**:
  - `backend/tests/test_gemini_image.py`
  - `backend/tests/services/test_strategy_engine.py`

### Documentation Files (`.md` files)
- **Location**: `docs/` (project root level)
- **Exceptions**:
  - `README.md` files can exist in any directory to document that directory
  - `spec/*.md` files belong in `spec/` directory
- **Examples**:
  - `docs/CONFIGURATION_GUIDE.md`
  - `docs/DEPLOYMENT_GUIDE.md`
  - `backend/README.md` (backend-specific docs)

### Scripts
- **Backend utility scripts**: `backend/scripts/`
- **Project-level scripts**: `scripts/` (root level)

### Configuration Files
- **Backend config**: `backend/app/core/config.py`
- **Docker config**: `docker-compose.yml`, `*.dockerfile`
- **Nginx config**: `nginx/`

## Best Practices

1. **Test Files**: Always place test files in `backend/tests/`, organized by the module they test
2. **Documentation**: Keep all project documentation in `docs/`, except README files which document their immediate directory
3. **Clean Root**: Keep the project root clean with only essential files (README, docker-compose.yml, etc.)

