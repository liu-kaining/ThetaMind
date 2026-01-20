# MarketDataService Usage Guide

## Overview

`MarketDataService` integrates FinanceToolkit and FinanceDatabase to provide:
- **Discovery**: Screen and filter tickers by sector, industry, market cap, country
- **Financial Analysis**: Get financial ratios, technical indicators, volatility
- **Options Intelligence**: Extract options chain data and Greeks

## Configuration

**⚠️ Important**: The system depends on FMP (Financial Modeling Prep) API key for accurate financial data.

Add to your `.env` file (required for production):

```bash
# Financial Modeling Prep API Key (Required for production)
# Get your free API key at: https://site.financialmodelingprep.com/developer/docs/
# Free tier: 250 calls/day, 5 years of data, US exchanges only
FINANCIAL_MODELING_PREP_KEY=your_api_key_here
```

**Note**: 
- Without FMP API key, the system will fall back to Yahoo Finance, but:
  - Data quality may be reduced
  - Some financial ratios may be unavailable
  - Data accuracy may vary
- FMP is the **Primary** data source and is strongly recommended for production use.

## Basic Usage

### 1. Discovery (Screening Tickers)

```python
from app.services.market_data_service import MarketDataService

service = MarketDataService()

# Find tech stocks in US
tech_tickers = service.search_tickers(
    sector="Information Technology",
    market_cap="Large Cap",
    country="United States",
    limit=10
)
# Returns: ['AAPL', 'MSFT', 'GOOGL', 'NVDA', ...]
```

### 2. Financial Profile

```python
# Get comprehensive financial data for a ticker
profile = service.get_financial_profile("AAPL")

# Structure:
# {
#   "ticker": "AAPL",
#   "ratios": {
#     "profitability": {...},  # ROE, ROA, margins, etc.
#     "valuation": {...},       # PE, PB, EV/EBITDA, etc.
#     "solvency": {...},        # Debt/Equity, Interest Coverage, etc.
#     "liquidity": {...}        # Current Ratio, Quick Ratio, etc.
#   },
#   "technical_indicators": {
#     "rsi": {...},
#     "macd": {...},
#     "bollinger_bands": {...}
#   },
#   "volatility": {...},
#   "profile": {...}            # Company info, market cap, etc.
# }
```

### 3. Options Data

```python
# Get options chain and Greeks
options = service.get_options_data("AAPL")

# Structure:
# {
#   "ticker": "AAPL",
#   "option_chains": {...},
#   "greeks": {
#     "first_order": {...},     # Delta, Theta, Vega, Rho
#     "second_order": {...}      # Gamma, Vanna, etc.
#   },
#   "implied_volatility": {...}
# }
```

## Integration with AI Service

Example: Enhance AI reports with fundamental data

```python
from app.services.market_data_service import MarketDataService
from app.services.ai_service import AIService

market_service = MarketDataService()
ai_service = AIService()

# Get financial profile
profile = market_service.get_financial_profile("AAPL")

# Use in AI report generation
report = await ai_service.generate_report(
    strategy_summary={
        "symbol": "AAPL",
        "strategy_type": "Iron Condor",
        "fundamental_data": profile  # Add fundamental context
    }
)
```

## Integration with Market Scanner

Example: Enhance market scanner with discovery

```python
from app.services.market_data_service import MarketDataService
from app.services.market_scanner import MarketScanner

market_service = MarketDataService()
scanner = MarketScanner()

# Find high-quality tech stocks
tech_tickers = market_service.search_tickers(
    sector="Information Technology",
    market_cap="Large Cap",
    country="United States"
)

# Filter by IV using scanner
high_iv_stocks = []
for ticker in tech_tickers[:20]:  # Limit to avoid rate limits
    try:
        chain = await scanner.get_option_chain(ticker)
        if chain and calculate_iv_rank(chain) > 70:
            high_iv_stocks.append(ticker)
    except Exception as e:
        logger.warning(f"Error scanning {ticker}: {e}")
```

## Error Handling

The service handles errors gracefully:

- **Missing API Key**: Falls back to Yahoo Finance automatically
- **Invalid Ticker**: Returns error dict with error message
- **Data Unavailable**: Returns empty dict or error dict
- **Network Issues**: Logs warning and returns error dict

All DataFrames are automatically converted to dictionaries (no raw DataFrames returned).

## Data Sanitization

- NaN and Infinite values are converted to `None`
- All DataFrames are converted to dictionaries
- Multi-index DataFrames are properly extracted by ticker

## Performance Notes

- FinanceDatabase queries are fast (in-memory)
- FinanceToolkit API calls may take 5-15 seconds per ticker
- Consider caching results for frequently accessed tickers
- Use `limit` parameter in `search_tickers()` to avoid large result sets

## Singleton Pattern

You can use the singleton function for shared instances:

```python
from app.services.market_data_service import get_market_data_service

service = get_market_data_service()  # Reuses same instance
```

Or instantiate directly:

```python
from app.services.market_data_service import MarketDataService

service = MarketDataService()  # New instance
```
