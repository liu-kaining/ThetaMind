#!/bin/bash
# Test MarketDataService in Docker container
# This script runs the test inside the Docker container where dependencies are installed

set -e

echo "=========================================="
echo "Testing MarketDataService with AAPL"
echo "=========================================="

cd "$(dirname "$0")/.."

# Check if Docker is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Desktop."
    exit 1
fi

# Check if backend container is running
if docker-compose ps backend | grep -q "Up"; then
    echo "✅ Backend container is running"
    echo ""
    echo "Running test inside container..."
    docker-compose exec backend python -c "
import sys
sys.path.insert(0, '/app')
from app.services.market_data_service import MarketDataService

print('=' * 80)
print('  MarketDataService Test - AAPL')
print('=' * 80)

# Initialize service
print('\n[1/4] Initializing service...')
service = MarketDataService()
print('✅ Service initialized')

# Test financial profile
print('\n[2/4] Fetching financial profile for AAPL...')
profile = service.get_financial_profile('AAPL')
if 'error' in profile:
    print(f'❌ Error: {profile[\"error\"]}')
else:
    print('✅ Financial profile retrieved')
    print(f'   Keys: {list(profile.keys())}')
    if 'ratios' in profile and profile['ratios']:
        print(f'   Ratios available: {list(profile[\"ratios\"].keys())}')
    if 'profile' in profile and profile['profile']:
        # Try different possible field names
        company = (
            profile['profile'].get('Company Name') or
            profile['profile'].get('name') or
            profile['profile'].get('Name') or
            'N/A'
        )
        print(f'   Company: {company}')
        # Debug: print first few profile keys if company is N/A
        if company == 'N/A' and profile['profile']:
            keys_list = list(profile['profile'].keys())[:5]
            print(f'   Profile keys (first 5): {keys_list}...')

# Test search
print('\n[3/4] Testing ticker search...')
tickers = service.search_tickers(
    sector='Information Technology',
    market_cap='Large Cap',
    country='United States',
    limit=5
)
print(f'✅ Found {len(tickers)} tickers')
print(f'   Sample: {tickers[:5]}')

# Test historical data
print('\n[4/4] Fetching historical data for AAPL...')
historical = service.get_historical_data('AAPL', period='monthly')
if 'error' in historical:
    print(f'⚠️  Warning: {historical[\"error\"]}')
else:
    data = historical.get('data', {})
    print(f'✅ Historical data retrieved: {len(data)} data points')

print('\n' + '=' * 80)
print('  Test completed!')
print('=' * 80)
"
else
    echo "⚠️  Backend container is not running"
    echo ""
    echo "Starting containers and running test..."
    docker-compose run --rm backend python -c "
import sys
sys.path.insert(0, '/app')
from app.services.market_data_service import MarketDataService

print('=' * 80)
print('  MarketDataService Test - AAPL')
print('=' * 80)

# Initialize service
print('\n[1/4] Initializing service...')
service = MarketDataService()
print('✅ Service initialized')

# Test financial profile
print('\n[2/4] Fetching financial profile for AAPL...')
profile = service.get_financial_profile('AAPL')
if 'error' in profile:
    print(f'❌ Error: {profile[\"error\"]}')
else:
    print('✅ Financial profile retrieved')
    print(f'   Keys: {list(profile.keys())}')
    if 'ratios' in profile and profile['ratios']:
        print(f'   Ratios available: {list(profile[\"ratios\"].keys())}')
    if 'profile' in profile and profile['profile']:
        # Try different possible field names
        company = (
            profile['profile'].get('Company Name') or
            profile['profile'].get('name') or
            profile['profile'].get('Name') or
            'N/A'
        )
        print(f'   Company: {company}')
        # Debug: print first few profile keys if company is N/A
        if company == 'N/A' and profile['profile']:
            keys_list = list(profile['profile'].keys())[:5]
            print(f'   Profile keys (first 5): {keys_list}...')

# Test search
print('\n[3/4] Testing ticker search...')
tickers = service.search_tickers(
    sector='Information Technology',
    market_cap='Large Cap',
    country='United States',
    limit=5
)
print(f'✅ Found {len(tickers)} tickers')
print(f'   Sample: {tickers[:5]}')

# Test historical data
print('\n[4/4] Fetching historical data for AAPL...')
historical = service.get_historical_data('AAPL', period='monthly')
if 'error' in historical:
    print(f'⚠️  Warning: {historical[\"error\"]}')
else:
    data = historical.get('data', {})
    print(f'✅ Historical data retrieved: {len(data)} data points')

print('\n' + '=' * 80)
print('  Test completed!')
print('=' * 80)
"
fi
