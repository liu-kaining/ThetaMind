FROM python:3.10-slim

WORKDIR /app

# Install system dependencies with retry logic
# Retry up to 3 times to handle temporary network issues
RUN for i in 1 2 3; do \
        apt-get update && \
        apt-get install -y --no-install-recommends curl && \
        break || sleep 5; \
    done && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install development dependencies (for testing)
RUN pip install --no-cache-dir pytest pytest-asyncio

# Copy application code
COPY ./app /app/app

# Copy Alembic configuration and migrations
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic/

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Install postgresql-client for pg_isready check
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Health check (Cloud Run manages health checks, this is for local Docker)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port (Cloud Run will use PORT env var)
EXPOSE 8000

# Use entrypoint for migrations, then run command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

