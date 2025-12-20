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

# Always use uvicorn with dynamic port from environment variable
# Cloud Run will provide PORT, default to 8000 for local development
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1

