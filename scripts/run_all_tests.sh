#!/bin/bash
# Run all MarketDataService tests (P0, P1, P2, P3)

cd "$(dirname "$0")/.."

echo "=========================================="
echo "Testing MarketDataService - All Features"
echo "=========================================="

# Check if backend container is running
if docker-compose ps backend 2>/dev/null | grep -q "Up"; then
    echo "✅ Backend container is running"
    echo ""
    
    echo "Running P0 & P1 tests..."
    docker-compose exec backend python /app/tests/services/test_market_data_service_p0_p1.py
    
    echo ""
    echo "Running P2 & P3 tests..."
    docker-compose exec backend python /app/tests/services/test_market_data_service_p2_p3.py
else
    echo "⚠️  Backend container is not running"
    echo ""
    echo "Please start the backend container first:"
    echo "  docker-compose up -d backend"
fi
