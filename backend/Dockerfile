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

# Copy application code
COPY ./app /app/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

