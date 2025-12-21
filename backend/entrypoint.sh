#!/bin/bash
set -e

echo "=========================================="
echo "ThetaMind Backend Startup Script"
echo "=========================================="

# Check if using Cloud SQL Unix socket (Cloud Run)
# Format: postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/...
if [ -n "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -q "/cloudsql/"; then
  echo "Detected Cloud SQL Unix socket connection - skipping pg_isready check"
else
  # Extract database connection info for TCP connections (Docker Compose)
  # Format: postgresql+asyncpg://user:pass@host:port/dbname
  DB_HOST="${DB_HOST:-db}"
  DB_USER="${DB_USER:-thetamind}"
  DB_NAME="${DB_NAME:-thetamind}"

  # Wait for database to be ready (only for TCP connections)
  echo "Waiting for database to be ready..."
  echo "Connecting to: host=$DB_HOST user=$DB_USER database=$DB_NAME"
  until pg_isready -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; do
    echo "Database is unavailable - sleeping"
    sleep 1
  done
  echo "Database is ready!"
fi

# Run database migrations (with error handling)
# Temporarily disable exit on error for migrations
set +e
echo "Running database migrations..."
alembic upgrade head
MIGRATION_EXIT_CODE=$?
set -e

if [ $MIGRATION_EXIT_CODE -ne 0 ]; then
  echo "WARNING: Database migrations failed (exit code: $MIGRATION_EXIT_CODE), but continuing startup..."
  echo "The application will attempt to start anyway. Please check the migration logs above."
else
  echo "Migrations completed successfully!"
fi

# Start the application
echo "Starting application..."
# Use PORT environment variable (Cloud Run sets this, typically 8080) or default to 8000
PORT=${PORT:-8000}
echo "Using port: $PORT"
echo "Environment variables check:"
echo "  PORT=$PORT"
echo "  DATABASE_URL present: $([ -n "$DATABASE_URL" ] && echo 'yes' || echo 'no')"
echo "  CLOUDSQL_CONNECTION_NAME: ${CLOUDSQL_CONNECTION_NAME:-not set}"
echo "  DB_USER: ${DB_USER:-not set}"
echo "  DB_NAME: ${DB_NAME:-not set}"
echo "  DB_PASSWORD: $([ -n "$DB_PASSWORD" ] && echo 'set (hidden)' || echo 'not set')"
echo "  ENVIRONMENT: ${ENVIRONMENT:-not set}"

# Check if we're in Cloud Run (has CLOUDSQL_CONNECTION_NAME)
if [ -n "$CLOUDSQL_CONNECTION_NAME" ]; then
  echo "Cloud Run environment detected"
  if [ -z "$DB_PASSWORD" ]; then
    echo "ERROR: DB_PASSWORD is not set in Cloud Run environment!"
    echo "Please ensure DB_PASSWORD secret is configured in Secret Manager"
    echo "and included in --update-secrets for Cloud Run deployment."
    exit 1
  fi
  if [ -z "$DB_USER" ]; then
    echo "WARNING: DB_USER is not set, using default: thetamind"
  fi
  if [ -z "$DB_NAME" ]; then
    echo "WARNING: DB_NAME is not set, using default: thetamind_prod"
  fi
else
  echo "Local/Docker Compose environment detected"
fi

# Always use uvicorn with dynamic port from environment variable
# Cloud Run will provide PORT, default to 8000 for local development
echo "Starting uvicorn server on 0.0.0.0:$PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1

