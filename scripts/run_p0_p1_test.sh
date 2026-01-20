#!/bin/bash
# Simple test runner for P0 & P1 features

cd "$(dirname "$0")/.."

echo "=========================================="
echo "Testing MarketDataService P0 & P1 Features"
echo "=========================================="

# Check if backend container is running
if docker-compose ps backend 2>/dev/null | grep -q "Up"; then
    echo "✅ Backend container is running"
    echo ""
    echo "Running test inside container..."
    docker-compose exec backend python -m pytest /app/tests/services/test_market_data_service_p0_p1.py -v
else
    echo "⚠️  Backend container is not running"
    echo ""
    echo "Please start the backend container first:"
    echo "  docker-compose up -d backend"
    echo ""
    echo "Or run the test directly if you have Python environment:"
    echo "  cd backend && python -m pytest tests/services/test_market_data_service_p0_p1.py -v"
fi
