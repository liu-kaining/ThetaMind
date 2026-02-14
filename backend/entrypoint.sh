#!/bin/bash
set -e

echo "=========================================="
echo "ThetaMind Backend Startup Script"
echo "=========================================="

# Wait for database (shared for both "run one-off command" and "start server")
# Check if using Cloud SQL Unix socket (Cloud Run)
if [ -n "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -q "/cloudsql/"; then
  echo "Detected Cloud SQL Unix socket connection - skipping pg_isready check"
else
  DB_HOST="${DB_HOST:-db}"
  DB_USER="${DB_USER:-thetamind}"
  DB_NAME="${DB_NAME:-thetamind}"
  echo "Waiting for database to be ready..."
  echo "Connecting to: host=$DB_HOST user=$DB_USER database=$DB_NAME"
  until pg_isready -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; do
    echo "Database is unavailable - sleeping"
    sleep 1
  done
  echo "Database is ready!"
fi

# One-off command (e.g. docker compose run --rm backend alembic upgrade head): wait DB, then run command and exit
if [ $# -ge 1 ] && [ "$1" = "alembic" ]; then
  echo "Running one-off command: $*"
  exec "$@"
fi

# Normal server start: run migrations then uvicorn
set +e
echo "Running database migrations..."
alembic upgrade head
MIGRATION_EXIT_CODE=$?
set -e

if [ $MIGRATION_EXIT_CODE -ne 0 ]; then
  echo "WARNING: Database migrations failed (exit code: $MIGRATION_EXIT_CODE), but continuing startup..."
else
  echo "Migrations completed successfully!"
fi

echo "Starting application..."
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

if [ -n "$CLOUDSQL_CONNECTION_NAME" ]; then
  echo "Cloud Run environment detected"
  if [ -z "$DB_PASSWORD" ]; then
    echo "ERROR: DB_PASSWORD is not set in Cloud Run environment!"
    exit 1
  fi
else
  echo "Local/Docker Compose environment detected"
fi

echo "Starting uvicorn server on 0.0.0.0:$PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1

