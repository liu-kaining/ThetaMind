# ThetaMind Backend

FastAPI backend for the ThetaMind US Stock Option Strategy Analysis Platform.

## Setup

### Prerequisites

- Python 3.10+
- Poetry (recommended) or pip

### Installation

```bash
# Using Poetry
poetry install

# Or using pip
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in all required values:

```bash
cp .env.example .env
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `TIGER_API_KEY`, `TIGER_API_SECRET`: Tiger Brokers API credentials
- `GOOGLE_API_KEY`: Google Gemini API key
- `JWT_SECRET_KEY`: Secret key for JWT tokens

### Running Locally

```bash
# Using Poetry
poetry run uvicorn app.main:app --reload

# Or using pip
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Running with Docker

```bash
docker-compose up backend
```

## Project Structure

```
backend/
├── app/
│   ├── core/          # Core configuration and utilities
│   ├── db/            # Database session and models
│   ├── api/           # API routes
│   └── services/      # Business logic services
├── pyproject.toml     # Poetry dependencies
├── requirements.txt   # Pip dependencies
└── Dockerfile         # Docker configuration
```

## Database

The application uses PostgreSQL with SQLAlchemy (async). Connection pool is configured as:
- `pool_size=20`
- `max_overflow=10`

All timestamps are stored in UTC.

### Syncing stock symbols (Strategy Lab / search)

The `stock_symbols` table powers Strategy Lab search and `/api/v1/market/search`. To fill it with a full list from FMP (so users can find more tickers):

```bash
# From backend directory; requires FINANCIAL_MODELING_PREP_KEY and DATABASE_URL in .env
poetry run python scripts/sync_symbols_from_fmp.py --us-only
```

Run this from a machine that can reach FMP (e.g. your laptop or a server with outbound). You can run it once after deploy or on a schedule (e.g. weekly). See script docstring for Docker usage.

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

