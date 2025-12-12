#!/bin/bash
set -e

echo "=========================================="
echo "ThetaMind Backend Startup Script"
echo "=========================================="

# Extract database connection info from DATABASE_URL if available
# Format: postgresql+asyncpg://user:pass@host:port/dbname
if [ -n "$DATABASE_URL" ]; then
  # Parse DATABASE_URL to extract components (basic parsing)
  DB_HOST="${DB_HOST:-db}"
  DB_USER="${DB_USER:-thetamind}"
  DB_NAME="${DB_NAME:-thetamind}"
else
  # Fallback to defaults
  DB_HOST="${DB_HOST:-db}"
  DB_USER="${DB_USER:-thetamind}"
  DB_NAME="${DB_NAME:-thetamind}"
fi

# Wait for database to be ready
echo "Waiting for database to be ready..."
echo "Connecting to: host=$DB_HOST user=$DB_USER database=$DB_NAME"
until pg_isready -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; do
  echo "Database is unavailable - sleeping"
  sleep 1
done
echo "Database is ready!"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Migrations completed successfully!"

# Start the application
echo "Starting application..."
exec "$@"

