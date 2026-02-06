"""Market data service integrating FinanceToolkit and FinanceDatabase.

This service provides comprehensive market data analysis capabilities:

**Discovery (FinanceDatabase)**:
- Screen and filter tickers by sector, industry, market cap, country
- Search tickers by company name
- Get available filter options for dynamic UI
- Convert filtered results to FinanceToolkit for batch analysis
- Search ETFs by category, country (P3)

**Financial Analysis (FinanceToolkit)**:
- Financial Ratios: Profitability, Valuation, Solvency, Liquidity, Efficiency (5 categories)
- Technical Indicators: Momentum, Trend, Volume, Volatility (30+ indicators)
- Risk Metrics: VaR, CVaR, Maximum Drawdown, Skewness, Kurtosis, etc.
- Performance Metrics: Sharpe Ratio, Sortino Ratio, CAPM, Alpha, Information Ratio
- Financial Statements: Income Statement, Balance Sheet, Cash Flow Statement
- Valuation Models: DCF, DDM, WACC, Enterprise Value Breakdown (P2)
- DuPont Analysis: Standard and Extended DuPont Analysis (P2)
- Analysis: Technical signals, Risk scores, Health scores, Warnings (P2)
- Chart Generation: Financial ratios charts, Technical indicator charts (P3)
- Company Profile: Basic information, market cap, etc.

**Options Intelligence**:
- Option chains and Greeks (Delta, Gamma, Theta, Vega)
- Implied volatility analysis

All data is sanitized (NaN/Inf → None) and converted to clean dictionaries
for LLM compatibility and API responses.
"""

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

import financedatabase as fd
import httpx
import numpy as np
import pandas as pd
import pytz
from financetoolkit import Toolkit

from app.core.config import settings
from app.services.cache import cache_service

logger = logging.getLogger(__name__)
EST = pytz.timezone("US/Eastern")


class MarketDataService:
    """Market data service with FinanceToolkit and FinanceDatabase integration."""

    def __init__(self) -> None:
        """Initialize MarketDataService.
        
        Sets up FinanceDatabase instances for discovery and configures
        FinanceToolkit with FMP API key. Data is sourced from FMP only (no Yahoo Finance).
        """
        # Initialize FinanceDatabase instances (lazy loading, no API key needed)
        self._equities_db: Optional[fd.Equities] = None
        self._etfs_db: Optional[fd.ETFs] = None
        
        # FMP API key (required for market data via FinanceToolkit; no Yahoo Finance fallback)
        self._fmp_api_key: Optional[str] = None
        if settings.financial_modeling_prep_key:
            self._fmp_api_key = settings.financial_modeling_prep_key
            logger.info("MarketDataService: Using Financial Modeling Prep API (FMP only, no Yahoo Finance)")
        else:
            logger.warning(
                "MarketDataService: FMP API key not set. "
                "Market data via FinanceToolkit requires FMP; set FINANCIAL_MODELING_PREP_KEY in .env."
            )
        
        # FMP API base URL for direct API calls
        self._fmp_base_url: str = "https://financialmodelingprep.com/stable"
        
        # HTTP client for direct FMP API calls (lazy initialization)
        self._http_client: Optional[httpx.AsyncClient] = None
        
        logger.info("MarketDataService initialized")

    @property
    def equities_db(self) -> fd.Equities:
        """Lazy-load Equities database."""
        if self._equities_db is None:
            self._equities_db = fd.Equities()
        return self._equities_db

    @property
    def etfs_db(self) -> fd.ETFs:
        """Lazy-load ETFs database."""
        if self._etfs_db is None:
            self._etfs_db = fd.ETFs()
        return self._etfs_db

    def _get_toolkit(self, tickers: List[str]) -> Toolkit:
        """Create FinanceToolkit instance for given tickers (FMP only; no Yahoo Finance).
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Toolkit instance configured with FMP API key
            
        Raises:
            ValueError: If FMP API key is not set (market data requires FMP).
        """
        if not self._fmp_api_key:
            raise ValueError(
                "FMP API key is required for market data. "
                "Set FINANCIAL_MODELING_PREP_KEY in .env. Yahoo Finance is not used."
            )
        toolkit_kwargs = {
            "tickers": tickers,
            "start_date": "2020-01-01",  # 5 years of historical data
            "api_key": self._fmp_api_key,
        }
        logger.debug(f"Using FMP API for tickers: {tickers}")
        return Toolkit(**toolkit_kwargs)

    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize values: replace NaN/Inf and non-serializable types.
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value (None for NaN/Inf, original value otherwise)
        """
        if isinstance(value, pd.Period):
            return str(value)
        if isinstance(value, (float, np.floating)):
            if math.isnan(value) or math.isinf(value):
                return None
        elif isinstance(value, (int, np.integer)):
            # Check for numpy integer NaN (rare but possible)
            if isinstance(value, np.integer) and (math.isnan(float(value)) or math.isinf(float(value))):
                return None
        return value

    def _sanitize_mapping(self, data: Any) -> Any:
        """Recursively sanitize mapping/list data for JSON serialization."""
        if isinstance(data, dict):
            return {str(k): self._sanitize_mapping(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._sanitize_mapping(item) for item in data]
        return self._sanitize_value(data)

    def _dataframe_to_dict(self, df: pd.DataFrame, ticker: Optional[str] = None) -> Dict[str, Any]:
        """Convert DataFrame to clean dictionary format.
        
        Args:
            df: Pandas DataFrame to convert
            ticker: Optional ticker symbol to extract from multi-index DataFrame
            
        Returns:
            Dictionary representation of DataFrame
        """
        if df is None or df.empty:
            return {}
        
        try:
            # If multi-index (multiple tickers), extract specific ticker
            if ticker and isinstance(df.columns, pd.MultiIndex):
                try:
                    df = df.xs(ticker, level=1, axis=1)
                except (KeyError, IndexError):
                    logger.warning(f"Ticker {ticker} not found in DataFrame columns")
                    return {}
            
            # Convert to dict, handling different orientations
            # Try 'index' first (dates as keys), then 'records'
            result = df.to_dict(orient="index")
            
            # Sanitize all values
            sanitized = {}
            for key, value in result.items():
                if isinstance(value, dict):
                    sanitized[str(key)] = {
                        k: self._sanitize_value(v) for k, v in value.items()
                    }
                else:
                    sanitized[str(key)] = self._sanitize_value(value)
            
            return sanitized
        except Exception as e:
            logger.error(f"Error converting DataFrame to dict: {e}", exc_info=True)
            return {}

    # ==================== Part A: Discovery (The Screener) ====================

    def get_filter_options(
        self,
        selection: Optional[str] = None,
        country: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """Get available filter options for FinanceDatabase.
        
        P1: This helps build dynamic filters in the frontend.
        
        Args:
            selection: Specific field to get options for (e.g., 'industry', 'sector')
            country: Filter by country first, then get options
            sector: Filter by sector first, then get options
            
        Returns:
            Dictionary mapping field names to lists of available values
            
        Example:
            >>> service = MarketDataService()
            >>> options = service.get_filter_options(country="United States")
            >>> # Returns: {"sector": ["Technology", "Healthcare", ...], ...}
        """
        try:
            if selection:
                # Get options for a specific field
                if hasattr(self.equities_db, 'options'):
                    # Use options() method if available
                    options = self.equities_db.options(
                        selection=selection,
                        country=country,
                        sector=sector
                    )
                    return {selection: options.tolist() if hasattr(options, 'tolist') else list(options)}
                elif hasattr(self.equities_db, 'show_options'):
                    # Fallback to show_options()
                    all_options = self.equities_db.show_options(
                        country=country,
                        sector=sector
                    )
                    if selection in all_options:
                        return {selection: list(all_options[selection])}
            else:
                # Get all options
                if hasattr(self.equities_db, 'show_options'):
                    options = self.equities_db.show_options(
                        country=country,
                        sector=sector
                    )
                    # Convert to dict of lists
                    return {
                        k: list(v) if isinstance(v, (list, pd.Series, pd.Index)) else v
                        for k, v in options.items()
                    }
            
            logger.warning("show_options or options method not available")
            return {}
        except Exception as e:
            logger.error(f"Error getting filter options: {e}", exc_info=True)
            return {}

    def search_tickers_by_name(
        self,
        query: str,
        country: Optional[str] = None,
        sector: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        """Search tickers by company name or other text fields.
        
        P1: Free-text search functionality.
        
        Args:
            query: Search query (company name, industry keyword, etc.)
            country: Optional country filter
            sector: Optional sector filter
            limit: Maximum number of results
            
        Returns:
            List of ticker symbols matching the search query
            
        Example:
            >>> service = MarketDataService()
            >>> tickers = service.search_tickers_by_name("Apple", country="United States")
            >>> # Returns: ['AAPL']
        """
        try:
            # Build search parameters
            search_params: Dict[str, Any] = {}
            if country:
                search_params["country"] = country
            if sector:
                search_params["sector"] = sector
            
            # Use search method if available
            if hasattr(self.equities_db, 'search'):
                try:
                    # Try search method with proper parameters
                    # Note: FinanceDatabase search may have different parameter names
                    if country:
                        # First filter by country, then search
                        filtered = self.equities_db.select(country=country)
                        if filtered is not None and not filtered.empty:
                            # Search within filtered results
                            if hasattr(filtered, 'search'):
                                results = filtered.search(query=query, search='name', case_sensitive=False)
                            else:
                                # Manual search in DataFrame
                                if "name" in filtered.columns:
                                    results = filtered[filtered["name"].str.contains(query, case=False, na=False)]
                                else:
                                    results = filtered
                        else:
                            results = None
                    else:
                        # Search without country filter
                        results = self.equities_db.search(
                            query=query,
                            search='name',
                            case_sensitive=False
                        )
                except Exception as e:
                    logger.debug(f"search method failed, using fallback: {e}")
                    # Fallback to select + filter
                    results = self.equities_db.select(**search_params)
                    if results is not None and not results.empty:
                        if "name" in results.columns:
                            results = results[results["name"].str.contains(query, case=False, na=False)]
            else:
                # Fallback: use select and filter
                logger.debug("search method not available, using select as fallback")
                results = self.equities_db.select(**search_params)
                if results is not None and not results.empty:
                    # Filter by name containing query
                    if "name" in results.columns:
                        results = results[results["name"].str.contains(query, case=False, na=False)]
            
            if results is None or results.empty:
                logger.info(f"No tickers found for search query: {query}")
                return []
            
            # Extract ticker symbols
            if "symbol" in results.columns:
                tickers = results["symbol"].tolist()
            elif hasattr(results, 'index') and len(results.index) > 0:
                tickers = results.index.tolist()
            else:
                logger.warning(f"Could not extract symbols from search results")
                return []
            
            # Additional filtering: ensure country filter is applied if specified
            if country and "country" in results.columns:
                # Filter by country column if available
                country_filtered = results[results["country"] == country]
                if not country_filtered.empty:
                    tickers = country_filtered["symbol"].tolist() if "symbol" in country_filtered.columns else country_filtered.index.tolist()
            
            # Apply limit
            if limit and len(tickers) > limit:
                tickers = tickers[:limit]
            
            logger.info(f"Found {len(tickers)} tickers matching search query: {query} (country={country})")
            return tickers
            
        except Exception as e:
            logger.error(f"Error searching tickers: {e}", exc_info=True)
            return []

    def search_tickers(
        self,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        market_cap: str = "Large Cap",
        country: str = "United States",
        limit: Optional[int] = None,
    ) -> List[str]:
        """Search and filter tickers using FinanceDatabase.
        
        ⚠️ OPTIMIZATION: FinanceDatabase's select() method is the standard way to filter.
        For batch analysis, consider using convert_database_results_to_toolkit() to
        directly convert results to FinanceToolkit.
        
        Args:
            sector: Sector filter (e.g., "Information Technology")
            industry: Industry filter (e.g., "Software")
            market_cap: Market cap category ("Large Cap", "Mid Cap", "Small Cap", "Micro Cap", "Nano Cap")
            country: Country filter (default: "United States")
            limit: Maximum number of results (None = no limit)
            
        Returns:
            List of ticker symbols matching the criteria
            
        Example:
            >>> service = MarketDataService()
            >>> tickers = service.search_tickers(
            ...     sector="Information Technology",
            ...     market_cap="Large Cap",
            ...     country="United States"
            ... )
            >>> # Returns: ['AAPL', 'MSFT', 'GOOGL', ...]
            >>> # For batch analysis:
            >>> toolkit = service.convert_database_results_to_toolkit(results)
        """
        try:
            # Build filter parameters
            filter_params: Dict[str, Any] = {
                "country": country,
                "market_cap": market_cap,
            }
            
            if sector:
                filter_params["sector"] = sector
            if industry:
                filter_params["industry"] = industry
            
            # Query FinanceDatabase
            # Use only_primary_listing=True to get only primary US listings (avoid .F, .L, etc.)
            filter_params["only_primary_listing"] = True
            results = self.equities_db.select(**filter_params)
            
            if results is None or results.empty:
                logger.warning(
                    f"No tickers found for filters: {filter_params}"
                )
                return []
            
            # Extract ticker symbols
            # FinanceDatabase returns DataFrame with 'symbol' as a column
            # Handle both column and index cases
            try:
                if "symbol" in results.columns:
                    tickers = results["symbol"].tolist()
                elif results.index.name == "symbol" or (hasattr(results.index, 'name') and results.index.name == "symbol"):
                    tickers = results.index.tolist()
                elif hasattr(results, 'index') and len(results.index) > 0:
                    # Last resort: use index values if they look like tickers
                    logger.warning(
                        f"FinanceDatabase DataFrame structure unexpected. "
                        f"Columns: {list(results.columns)}, "
                        f"Index: {results.index.name if hasattr(results.index, 'name') else 'unnamed'}"
                    )
                    # Try to extract from first column if it contains ticker-like strings
                    first_col = results.iloc[:, 0] if len(results.columns) > 0 else None
                    if first_col is not None:
                        tickers = first_col.tolist()
                    else:
                        tickers = []
                else:
                    logger.error(
                        f"Could not extract symbols from FinanceDatabase result. "
                        f"Columns: {list(results.columns) if hasattr(results, 'columns') else 'N/A'}"
                    )
                    return []
            except Exception as e:
                logger.error(f"Error extracting symbols from FinanceDatabase: {e}")
                logger.debug(f"DataFrame info: columns={list(results.columns) if hasattr(results, 'columns') else 'N/A'}, "
                           f"index={results.index.name if hasattr(results.index, 'name') else 'N/A'}")
                return []
            
            # Apply limit if specified
            if limit and len(tickers) > limit:
                tickers = tickers[:limit]
            
            logger.info(
                f"Found {len(tickers)} tickers matching filters: {filter_params}"
            )
            return tickers
            
        except Exception as e:
            logger.error(f"Error searching tickers: {e}", exc_info=True)
            return []

    def convert_to_toolkit(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
    ) -> Optional[Toolkit]:
        """Convert a list of tickers to FinanceToolkit instance for batch analysis.
        
        ⚠️ OPTIMIZATION: FinanceDatabase has a to_toolkit() method that can directly
        convert filtered results to FinanceToolkit. This method provides a fallback
        for when we already have a list of tickers.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date for historical data (default: "2020-01-01")
            
        Returns:
            Toolkit instance configured for the tickers, or None if conversion fails
            
        Example:
            >>> service = MarketDataService()
            >>> selected = service.search_tickers(sector="Technology", limit=10)
            >>> toolkit = service.convert_to_toolkit(selected)
            >>> hist_data = toolkit.get_historical_data()  # Batch analysis
        """
        try:
            if not tickers:
                logger.warning("No tickers provided for toolkit conversion")
                return None
            
            # Use the existing _get_toolkit method
            return self._get_toolkit(tickers)
            
        except Exception as e:
            logger.error(f"Error converting tickers to toolkit: {e}", exc_info=True)
            return None
    
    def convert_database_results_to_toolkit(
        self,
        database_results: Any,  # FinanceDatabase DataFrame result
        start_date: Optional[str] = None,
    ) -> Optional[Toolkit]:
        """Convert FinanceDatabase filter results directly to FinanceToolkit.
        
        ⚠️ OPTIMIZATION: Use FinanceDatabase's built-in to_toolkit() method.
        This is more efficient than extracting symbols and creating Toolkit separately.
        
        Args:
            database_results: DataFrame result from FinanceDatabase select() or search()
            start_date: Start date for historical data (default: "2020-01-01")
            
        Returns:
            Toolkit instance, or None if conversion fails
            
        Example:
            >>> service = MarketDataService()
            >>> filtered = service.equities_db.select(country="US", sector="Technology")
            >>> toolkit = service.convert_database_results_to_toolkit(filtered)
            >>> hist_data = toolkit.get_historical_data()  # Batch analysis
        """
        try:
            if database_results is None or (hasattr(database_results, 'empty') and database_results.empty):
                logger.warning("Empty database results provided for toolkit conversion")
                return None
            
            # Require FMP API key (no Yahoo Finance)
            if not self._fmp_api_key:
                logger.warning("FMP API key required for toolkit conversion; skipping.")
                return None

            # ⚠️ Use FinanceDatabase's built-in to_toolkit() method if available
            if hasattr(database_results, 'to_toolkit'):
                try:
                    toolkit_kwargs = {"api_key": self._fmp_api_key}
                    if start_date:
                        toolkit_kwargs["start_date"] = start_date
                    toolkit = database_results.to_toolkit(**toolkit_kwargs)
                    logger.debug("Converted FinanceDatabase results to Toolkit using to_toolkit() method")
                    return toolkit
                except Exception as e:
                    logger.debug(f"to_toolkit() method failed: {e}, using fallback")

            # Fallback: Extract symbols and create Toolkit manually (FMP only)
            if "symbol" in database_results.columns:
                tickers = database_results["symbol"].tolist()
            elif hasattr(database_results, 'index'):
                tickers = database_results.index.tolist()
            else:
                logger.warning("Could not extract symbols from database results")
                return None

            return self._get_toolkit(tickers)

        except ValueError as e:
            # FMP API key required
            logger.warning("Toolkit conversion skipped: %s", e)
            return None
        except Exception as e:
            logger.error(f"Error converting database results to toolkit: {e}", exc_info=True)
            return None

    # ==================== Part B: Deep Analysis (The Data Engine) ====================

    def get_financial_profile(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive financial profile for a ticker. FMP only (no Yahoo/FinanceToolkit).
        
        Fetches from FMP API only:
        - Company profile, ratios (TTM), key metrics (TTM)
        - Financial statements (income, balance sheet, cash flow)
        - Optional: historical volatility from FMP historical prices
        
        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            Dictionary containing financial profile data (FMP-only).
        """
        if not self._fmp_api_key:
            return self._sanitize_mapping({
                "ticker": ticker,
                "error": "FMP API key required. Set FINANCIAL_MODELING_PREP_KEY in .env.",
                "ratios": {}, "technical_indicators": {}, "risk_metrics": {},
                "performance_metrics": {}, "financial_statements": {},
                "valuation": {}, "dupont_analysis": {}, "analysis": {},
                "volatility": {}, "profile": {},
            })
        try:
            profile: Dict[str, Any] = {
                "ticker": ticker,
                "ratios": {},
                "technical_indicators": {},
                "risk_metrics": {},
                "performance_metrics": {},
                "financial_statements": {},
                "valuation": {},
                "dupont_analysis": {},
                "analysis": {},
                "volatility": {},
                "profile": {},
            }
            # 1. Ratios & key metrics (FMP only)
            ratios_ttm = self._call_fmp_api_sync("ratios-ttm", params={"symbol": ticker})
            metrics_ttm = self._call_fmp_api_sync("key-metrics-ttm", params={"symbol": ticker})
            ttm_row = None
            if isinstance(ratios_ttm, list) and ratios_ttm:
                ttm_row = ratios_ttm[0]
            elif isinstance(metrics_ttm, list) and metrics_ttm:
                ttm_row = metrics_ttm[0]
            if isinstance(ttm_row, dict):
                val_map = {}
                for fmp_k, our_k in [
                    ("peRatioTTM", "PE"), ("priceEarningsRatioTTM", "P/E"),
                    ("pbRatioTTM", "P/B"), ("priceToBookRatioTTM", "P/B"),
                ]:
                    if fmp_k in ttm_row and ttm_row[fmp_k] is not None:
                        val_map[our_k] = float(ttm_row[fmp_k])
                prof_map = {}
                for fmp_k, our_k in [
                    ("returnOnEquityTTM", "ROE"), ("roeTTM", "Return on Equity"),
                    ("returnOnAssetsTTM", "ROA"), ("roaTTM", "Return on Assets"),
                ]:
                    if fmp_k in ttm_row and ttm_row[fmp_k] is not None:
                        prof_map[our_k] = float(ttm_row[fmp_k])
                if val_map:
                    profile["ratios"]["valuation"] = {"TTM": val_map}
                if prof_map:
                    profile["ratios"]["profitability"] = {"TTM": prof_map}

            # 2. Financial statements (FMP only)
            for stmt_key, fmp_endpoint in [
                ("income", "income-statement"),
                ("balance", "balance-sheet-statement"),
                ("cash_flow", "cash-flow-statement"),
            ]:
                stmt = self._call_fmp_api_sync(fmp_endpoint, params={"symbol": ticker, "limit": 5})
                if isinstance(stmt, list) and stmt:
                    profile["financial_statements"][stmt_key] = {
                        str(i): self._sanitize_mapping(s) for i, s in enumerate(stmt[:5])
                    }

            # 3. Company profile (FMP only)
            fmp_profile = self._call_fmp_api_sync("profile", params={"symbol": ticker})
            if isinstance(fmp_profile, list) and fmp_profile:
                profile["profile"] = {k: self._sanitize_value(v) for k, v in fmp_profile[0].items()}
            elif isinstance(fmp_profile, dict) and "error" not in str(fmp_profile).lower():
                profile["profile"] = {k: self._sanitize_value(v) for k, v in fmp_profile.items()}

            # 4. Volatility from FMP historical (optional)
            hist = self._call_fmp_api_sync("historical-price-eod/full", params={"symbol": ticker})
            if isinstance(hist, list) and len(hist) >= 2:
                try:
                    closes = [float(h.get("close", 0)) for h in hist[:252] if h.get("close") is not None]
                    if len(closes) >= 2:
                        returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
                        vol = (sum((r - sum(returns) / len(returns)) ** 2 for r in returns) / len(returns)) ** 0.5 * (252 ** 0.5)
                        profile["volatility"] = {"annualized": self._sanitize_value(vol)}
                except Exception:
                    pass

            # 5. Analysis (uses profile we built)
            try:
                analysis = self._generate_analysis(profile, ticker)
                if analysis:
                    profile["analysis"] = analysis
            except Exception as e:
                logger.debug(f"Analysis generation for {ticker}: {e}")

            logger.info(f"Financial profile retrieved for {ticker} (FMP only)")
            return self._sanitize_mapping(profile)
            
        except Exception as e:
            err_str = str(e)
            # SSL/Yahoo/Currency errors are common in Docker or when FMP/Yahoo is flaky; log as warning
            if "SSL" in err_str or "SSLError" in err_str or "UNEXPECTED_EOF" in err_str or "Currency" in err_str or "query1.finance.yahoo" in err_str:
                logger.warning(f"Financial profile for {ticker} failed (SSL/Yahoo/Currency): {e}")
            else:
                logger.error(f"Error getting financial profile for {ticker}: {e}", exc_info=True)
            return self._sanitize_mapping({
                "ticker": ticker,
                "error": err_str,
                "ratios": {},
                "technical_indicators": {},
                "risk_metrics": {},
                "performance_metrics": {},
                "financial_statements": {},
                "valuation": {},
                "dupont_analysis": {},
                "analysis": {},
                "volatility": {},
                "profile": {},
            })

    # ==================== Part C: Options Intelligence ====================

    def get_options_data(self, ticker: str) -> Dict[str, Any]:
        """Get options chain / Greeks placeholder. 期权数据由 Tiger 提供，不在此处拉取。
        
        Option chain and Greeks are provided by Tiger (tiger_service.get_option_chain).
        Use tiger_service.get_option_chain(symbol, expiration_date) for real option data.
        This method returns empty structures so callers use Tiger for option chain.
        
        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            Dictionary with empty option_chains, greeks, implied_volatility
        """
        return {
            "ticker": ticker,
            "option_chains": {},
            "greeks": {},
            "implied_volatility": {},
        }

    # ==================== P2: Analysis Methods ====================
    
    def _generate_analysis(
        self, profile: Dict[str, Any], ticker: str
    ) -> Dict[str, Any]:
        """Generate analysis: signals, risk scores, health scores.
        
        P2: This analyzes the collected data and generates insights.
        
        Args:
            profile: Financial profile dictionary
            ticker: Ticker symbol
            
        Returns:
            Dictionary containing analysis results
        """
        analysis: Dict[str, Any] = {
            "technical_signals": {},
            "risk_score": {},
            "health_score": {},
            "warnings": [],
        }
        
        try:
            # 1. Technical Signals Analysis
            tech_indicators = profile.get("technical_indicators", {})
            
            # RSI Signal
            if "rsi" in tech_indicators:
                rsi_data = tech_indicators["rsi"]
                if isinstance(rsi_data, dict):
                    # Get latest RSI value
                    latest_rsi = None
                    for date_key, values in rsi_data.items():
                        if isinstance(values, dict):
                            rsi_value = values.get("RSI") or values.get("Relative Strength Index")
                            if rsi_value is not None:
                                latest_rsi = rsi_value
                                break
                    
                    if latest_rsi is not None:
                        if latest_rsi > 70:
                            analysis["technical_signals"]["rsi"] = "overbought"
                            analysis["warnings"].append(f"RSI {latest_rsi:.2f} indicates overbought condition")
                        elif latest_rsi < 30:
                            analysis["technical_signals"]["rsi"] = "oversold"
                        else:
                            analysis["technical_signals"]["rsi"] = "neutral"
                        analysis["technical_signals"]["rsi_value"] = self._sanitize_value(latest_rsi)
            
            # MACD Signal
            if "macd" in tech_indicators or "macd_line" in tech_indicators:
                macd_data = tech_indicators.get("macd") or tech_indicators.get("macd_line", {})
                if isinstance(macd_data, dict):
                    # Try to determine MACD trend
                    analysis["technical_signals"]["macd"] = "neutral"  # Default
                    # More complex MACD analysis would require MACD line vs signal line comparison
            
            # Trend Analysis
            if "trend" in tech_indicators or "sma" in tech_indicators or "ema" in tech_indicators:
                analysis["technical_signals"]["trend"] = "analyzed"
            
            # 2. Risk Score Calculation
            risk_metrics = profile.get("risk_metrics", {})
            risk_score = 50  # Default neutral score (0-100)
            risk_factors = []
            
            # VaR Analysis
            if "var" in risk_metrics:
                var_data = risk_metrics["var"]
                if isinstance(var_data, dict):
                    # Extract VaR value and adjust risk score
                    # Higher VaR = higher risk
                    risk_factors.append("VaR available")
            
            # Maximum Drawdown Analysis
            if "max_drawdown" in risk_metrics:
                mdd_data = risk_metrics["max_drawdown"]
                if isinstance(mdd_data, dict):
                    # Extract max drawdown value
                    # Higher drawdown = higher risk
                    risk_factors.append("Max Drawdown available")
            
            # Sharpe Ratio Analysis (from performance metrics)
            perf_metrics = profile.get("performance_metrics", {})
            if "sharpe_ratio" in perf_metrics:
                sharpe_data = perf_metrics["sharpe_ratio"]
                if isinstance(sharpe_data, dict):
                    # Extract Sharpe ratio
                    # Lower Sharpe = higher risk
                    risk_factors.append("Sharpe Ratio available")
            
            analysis["risk_score"]["overall"] = self._sanitize_value(risk_score)
            analysis["risk_score"]["factors"] = risk_factors
            analysis["risk_score"]["category"] = (
                "low" if risk_score < 40 else "medium" if risk_score < 70 else "high"
            )
            
            # 3. Financial Health Score Calculation
            ratios = profile.get("ratios", {})
            health_score = 50  # Default
            health_factors = []
            
            # Profitability Analysis
            if "profitability" in ratios:
                profitability = ratios["profitability"]
                if isinstance(profitability, dict):
                    # Check ROE, ROA, margins
                    health_factors.append("Profitability ratios available")
            
            # Solvency Analysis
            if "solvency" in ratios:
                solvency = ratios["solvency"]
                if isinstance(solvency, dict):
                    # Check debt ratios
                    # High debt = lower health score
                    health_factors.append("Solvency ratios available")
            
            # Liquidity Analysis
            if "liquidity" in ratios:
                liquidity = ratios["liquidity"]
                if isinstance(liquidity, dict):
                    # Check current ratio, quick ratio
                    health_factors.append("Liquidity ratios available")
            
            # Efficiency Analysis
            if "efficiency" in ratios:
                efficiency = ratios["efficiency"]
                if isinstance(efficiency, dict):
                    health_factors.append("Efficiency ratios available")
            
            analysis["health_score"]["overall"] = self._sanitize_value(health_score)
            analysis["health_score"]["factors"] = health_factors
            analysis["health_score"]["category"] = (
                "excellent" if health_score >= 80 else
                "good" if health_score >= 60 else
                "fair" if health_score >= 40 else
                "poor"
            )
            
        except Exception as e:
            logger.warning(f"Error generating analysis: {e}")
            return {"error": str(e)}
        
        return analysis

    # ==================== P3: Visualization Methods ====================
    
    def generate_ratios_chart(
        self, ticker: str, ratio_type: str = "all"
    ) -> Optional[str]:
        """Generate financial ratios chart as base64 image.
        
        P3: Chart generation functionality.
        
        Args:
            ticker: Stock ticker symbol
            ratio_type: Type of ratios to chart ("profitability", "valuation", "all", etc.)
            
        Returns:
            Base64 encoded image string, or None if generation fails
        """
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            import io
            import base64
            
            profile = self.get_financial_profile(ticker)
            ratios = profile.get("ratios", {})
            
            if not ratios:
                logger.warning(f"No ratios data available for {ticker}")
                return None
            
            # Create figure
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Collect ratio values for charting
            ratio_values = {}
            ratio_names = []
            
            if ratio_type == "all" or ratio_type == "profitability":
                if "profitability" in ratios:
                    prof = ratios["profitability"]
                    if isinstance(prof, dict):
                        # Get latest values
                        for date_key, values in prof.items():
                            if isinstance(values, dict):
                                for ratio_name, ratio_value in values.items():
                                    if ratio_value is not None:
                                        try:
                                            # Ensure value is numeric
                                            float_val = float(ratio_value)
                                            if not (math.isnan(float_val) or math.isinf(float_val)):
                                                ratio_values[ratio_name] = float_val
                                        except (ValueError, TypeError):
                                            continue
                                break
            
            if ratio_values:
                ratio_names = list(ratio_values.keys())[:10]  # Limit to 10 ratios
                # Convert values to float, handle None values
                ratio_values_list = []
                for name in ratio_names:
                    val = ratio_values.get(name, 0)
                    if val is None:
                        val = 0
                    try:
                        val = float(val)
                        # Ensure it's a valid number
                        if math.isnan(val) or math.isinf(val):
                            val = 0
                    except (ValueError, TypeError):
                        val = 0
                    ratio_values_list.append(val)
                
                # Filter out None/NaN/Inf values and ensure proper types
                filtered_data = []
                for name, val in zip(ratio_names, ratio_values_list):
                    if val is not None:
                        try:
                            float_val = float(val)
                            if not (math.isnan(float_val) or math.isinf(float_val)):
                                filtered_data.append((name, float_val))
                        except (ValueError, TypeError):
                            continue
                
                if filtered_data:
                    ratio_names, ratio_values_list = zip(*filtered_data)
                    # Ensure ratio_names is a list of pure strings
                    ratio_names = [str(name) for name in ratio_names]
                    # Ensure ratio_values_list is a list of pure floats (not object dtype)
                    ratio_values_list = [float(v) for v in ratio_values_list]
                    
                    # Ensure both lists have the same length
                    min_len = min(len(ratio_names), len(ratio_values_list))
                    ratio_names = ratio_names[:min_len]
                    ratio_values_list = ratio_values_list[:min_len]
                
                # Create bar chart
                if ratio_names and ratio_values_list and len(ratio_names) == len(ratio_values_list):
                    # Ensure types are correct for matplotlib
                    ax.barh(ratio_names, ratio_values_list)
                ax.set_xlabel("Ratio Value")
                ax.set_title(f"Financial Ratios - {ticker}")
                ax.grid(axis='x', alpha=0.3)
                
                plt.tight_layout()
                
                # Convert to base64
                buffer = io.BytesIO()
                fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                image_base64 = base64.b64encode(buffer.read()).decode()
                plt.close(fig)
                
                return f"data:image/png;base64,{image_base64}"
            else:
                plt.close(fig)
                return None
                
        except ImportError:
            logger.warning("matplotlib not available for chart generation")
            return None
        except Exception as e:
            logger.warning(f"Error generating ratios chart: {e}")
            return None
    
    def generate_technical_chart(
        self, ticker: str, indicator: str = "rsi"
    ) -> Optional[str]:
        """Generate technical indicator chart as base64 image.
        
        P3: Chart generation functionality.
        
        Args:
            ticker: Stock ticker symbol
            indicator: Indicator to chart ("rsi", "macd", "sma", etc.)
            
        Returns:
            Base64 encoded image string, or None if generation fails
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import io
            import base64
            
            profile = self.get_financial_profile(ticker)
            tech_indicators = profile.get("technical_indicators", {})
            
            if indicator not in tech_indicators:
                logger.warning(f"Indicator {indicator} not available for {ticker}")
                return None
            
            indicator_data = tech_indicators[indicator]
            if not isinstance(indicator_data, dict):
                return None
            
            # Extract time series data
            dates = []
            values = []
            
            for date_key, value_dict in indicator_data.items():
                if isinstance(value_dict, dict):
                    # Get the indicator value
                    for key, val in value_dict.items():
                        if val is not None:
                            try:
                                val_float = float(val)
                                if not (math.isnan(val_float) or math.isinf(val_float)):
                                    dates.append(date_key)
                                    values.append(val_float)
                                    break
                            except (ValueError, TypeError):
                                continue
            
            if not dates or not values:
                return None
            
            # Limit to last 60 data points for readability
            dates = dates[-60:]
            values = values[-60:]
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(range(len(dates)), values, label=indicator.upper())
            ax.set_xlabel("Data Point Index")
            ax.set_ylabel("Value")
            ax.set_title(f"{indicator.upper()} - {ticker} (Last {len(dates)} points)")
            ax.legend()
            ax.grid(alpha=0.3)
            
            # Set x-axis labels to show date range
            if len(dates) > 0:
                step = max(1, len(dates) // 10)  # Show ~10 labels
                ax.set_xticks(range(0, len(dates), step))
                ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=45)
            plt.tight_layout()
            
            # Convert to base64
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)
            
            return f"data:image/png;base64,{image_base64}"
            
        except ImportError:
            logger.warning("matplotlib not available for chart generation")
            return None
        except Exception as e:
            logger.warning(f"Error generating technical chart: {e}")
            return None

    # ==================== P3: ETF Support ====================
    
    def search_etfs(
        self,
        category_group: Optional[str] = None,
        category: Optional[str] = None,
        country: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        """Search ETFs using FinanceDatabase.
        
        P3: ETF support functionality.
        
        Args:
            category_group: ETF category group (e.g., "Equity", "Fixed Income")
            category: Specific category
            country: Country filter (Note: ETFs.select() may not support country parameter)
            limit: Maximum number of results
            
        Returns:
            List of ETF symbols
        """
        try:
            # First, check available category groups if category_group is provided
            if category_group:
                try:
                    available_options = self.etfs_db.show_options()
                    if isinstance(available_options, dict) and "category_group" in available_options:
                        available_groups = available_options["category_group"]
                        if isinstance(available_groups, (list, pd.Series, pd.Index)):
                            available_groups_list = list(available_groups) if not isinstance(available_groups, list) else available_groups
                            if category_group not in available_groups_list:
                                logger.warning(
                                    f"Category group '{category_group}' not available. "
                                    f"Available options: {available_groups_list[:10]}..."
                                )
                                # Try without category_group
                                category_group = None
                except Exception as e:
                    logger.debug(f"Could not check available category groups: {e}")
            
            filter_params: Dict[str, Any] = {}
            
            if category_group:
                filter_params["category_group"] = category_group
            if category:
                filter_params["category"] = category
            # Note: ETFs.select() may not support 'country' parameter
            # Filter by country after selection if needed
            
            try:
                results = self.etfs_db.select(**filter_params)
            except (TypeError, ValueError) as e:
                # ETFs.select() may not support all parameters or invalid category_group
                error_msg = str(e)
                if "not available" in error_msg.lower() or "category group" in error_msg.lower():
                    logger.debug(f"ETFs.select() failed with invalid category_group: {e}")
                    # Try without category_group
                    filter_params.pop("category_group", None)
                    if filter_params:
                        results = self.etfs_db.select(**filter_params)
                    else:
                        # Try with no filters (may return too many results)
                        results = self.etfs_db.select()
                else:
                    logger.debug(f"ETFs.select() failed with params {filter_params}: {e}")
                    # Try with minimal parameters
                    minimal_params = {}
                    if category:
                        minimal_params["category"] = category
                    if minimal_params:
                        results = self.etfs_db.select(**minimal_params)
                    else:
                        results = self.etfs_db.select()
            
            # Post-filter by country if specified and results have country column
            if country and results is not None and not results.empty:
                if "country" in results.columns:
                    results = results[results["country"] == country]
            
            if results is None or results.empty:
                logger.warning(f"No ETFs found for filters: {filter_params}")
                return []
            
            # Extract symbols
            if "symbol" in results.columns:
                symbols = results["symbol"].tolist()
            elif hasattr(results, 'index') and len(results.index) > 0:
                symbols = results.index.tolist()
            else:
                return []
            
            if limit and len(symbols) > limit:
                symbols = symbols[:limit]
            
            logger.info(f"Found {len(symbols)} ETFs matching filters: {filter_params}")
            return symbols
            
        except Exception as e:
            logger.error(f"Error searching ETFs: {e}", exc_info=True)
            return []

    # ==================== Utility Methods ====================

    def get_historical_data(
        self, ticker: str, period: str = "daily"
    ) -> Dict[str, Any]:
        """Get historical price data for a ticker. FMP only (no Yahoo/FinanceToolkit).
        
        Args:
            ticker: Stock ticker symbol
            period: Data period ("daily", "weekly", "monthly", "quarterly", "yearly"); FMP returns daily EOD, other periods use same data.
            
        Returns:
            Dictionary containing historical OHLCV data
        """
        if not self._fmp_api_key:
            return {"ticker": ticker, "period": period, "data": {}, "error": "FMP API key required."}
        try:
            raw = self._call_fmp_api_sync("historical-price-eod/full", params={"symbol": ticker})
            if not isinstance(raw, list) or not raw:
                return {"ticker": ticker, "period": period, "data": {}}
            # FMP returns list of {date, open, high, low, close, volume}; map to same shape as _dataframe_to_dict
            data: Dict[str, Dict[str, Any]] = {}
            for row in raw:
                d = row.get("date")
                if not d:
                    continue
                data[str(d)] = {
                    "Open": self._sanitize_value(row.get("open")),
                    "High": self._sanitize_value(row.get("high")),
                    "Low": self._sanitize_value(row.get("low")),
                    "Close": self._sanitize_value(row.get("close")),
                    "Volume": self._sanitize_value(row.get("volume")),
                }
            return {
                "ticker": ticker,
                "period": period,
                "data": data,
            }
        except Exception as e:
            err_str = str(e)
            logger.warning(f"Historical data for {ticker} failed: {e}")
            return {"ticker": ticker, "period": period, "data": {}, "error": err_str}

    def get_hv_rank_from_fmp(self, symbol: str) -> Optional[float]:
        """Compute 52-week historical volatility rank from FMP historical prices only.
        
        Fetches ~504 days of EOD, computes 252-day rolling annualized vol, then
        rank = (current_vol - min_vol) / (max_vol - min_vol) * 100.
        Returns None if insufficient data or FMP unavailable.
        """
        if not self._fmp_api_key:
            return None
        try:
            raw = self._call_fmp_api_sync("historical-price-eod/full", params={"symbol": symbol})
            if not isinstance(raw, list) or len(raw) < 253:
                return None
            # FMP returns newest first typically; take up to 504
            rows = raw[:504]
            closes = []
            for h in rows:
                c = h.get("close")
                if c is not None:
                    try:
                        closes.append(float(c))
                    except (TypeError, ValueError):
                        continue
            if len(closes) < 253:
                return None
            # Oldest first for rolling
            closes = list(reversed(closes))
            returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
            if len(returns) < 252:
                return None
            # 252-day rolling annualized vol
            rolling_vols = []
            for i in range(251, len(returns)):
                window = returns[i - 251 : i + 1]
                mean_r = sum(window) / len(window)
                var = sum((r - mean_r) ** 2 for r in window) / len(window)
                ann_vol = (var ** 0.5) * (252 ** 0.5)
                rolling_vols.append(ann_vol)
            if not rolling_vols:
                return None
            current = rolling_vols[-1]
            min_vol = min(rolling_vols)
            max_vol = max(rolling_vols)
            if max_vol <= min_vol:
                return 50.0
            return float(((current - min_vol) / (max_vol - min_vol)) * 100.0)
        except Exception as e:
            logger.debug(f"HV rank from FMP for {symbol}: {e}")
            return None

    # ==================== P1: Market Performance & Analyst Data ====================
    # Direct FMP API calls for real-time market data and analyst information
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for FMP API calls."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def _call_fmp_api(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Direct FMP API call with error handling.
        
        ⚠️ P1: Direct FMP API integration for market performance and analyst data.
        This method provides direct access to FMP APIs that are not available through FinanceToolkit.
        
        Args:
            endpoint: FMP API endpoint (e.g., "sector-performance-snapshot")
            params: Query parameters (API key will be added automatically)
            
        Returns:
            API response data (dict or list)
            
        Raises:
            ValueError: If FMP API key is not set
            httpx.HTTPError: If API request fails
        """
        if not self._fmp_api_key:
            raise ValueError(
                "FMP API key is required for this operation. "
                "Please set FINANCIAL_MODELING_PREP_KEY in .env file."
            )
        
        url = f"{self._fmp_base_url}/{endpoint}"
        request_params = params or {}
        request_params["apikey"] = self._fmp_api_key
        
        # Record API call count for monitoring
        try:
            today = datetime.now(EST).date().isoformat()
            usage_key = f"fmp_usage:{today}:{endpoint}"
            if cache_service._redis:
                await cache_service._redis.incr(usage_key)
                await cache_service._redis.expire(usage_key, 86400)  # 24 hours TTL
        except Exception as e:
            logger.debug(f"Failed to record FMP API usage: {e}")
        
        try:
            client = await self._get_http_client()
            response = await client.get(url, params=request_params)
            response.raise_for_status()
            data = response.json()
            
            # Sanitize response data
            return self._sanitize_mapping(data)
        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API error for {endpoint}: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"FMP API request error for {endpoint}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling FMP API {endpoint}: {e}", exc_info=True)
            raise

    def _call_fmp_api_sync(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Synchronous FMP API call for use in sync methods (e.g. get_financial_profile).
        Fallback when FinanceToolkit returns empty - ensures profile/ratios populated.
        """
        if not self._fmp_api_key:
            return None
        url = f"{self._fmp_base_url}/{endpoint}"
        request_params = dict(params or {})
        request_params["apikey"] = self._fmp_api_key
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(url, params=request_params)
                response.raise_for_status()
                data = response.json()
                return self._sanitize_mapping(data)
        except Exception as e:
            logger.debug(f"FMP sync API {endpoint} failed: {e}")
            return None
    
    # P1.1: Market Performance Data
    
    async def get_sector_performance(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sector performance snapshot.
        
        ⚠️ P1: Direct FMP API call for real-time sector performance data.
        
        Args:
            date: Date in YYYY-MM-DD format (optional, defaults to latest)
            
        Returns:
            Dictionary with sector performance data
            
        Example:
            >>> service = MarketDataService()
            >>> performance = await service.get_sector_performance()
            >>> # Returns: {"Technology": {"change": 1.5, "changePercent": 0.8}, ...}
        """
        try:
            params = {}
            if date:
                params["date"] = date
            
            return await self._call_fmp_api("sector-performance-snapshot", params)
        except Exception as e:
            logger.error(f"Error getting sector performance: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def get_industry_performance(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get industry performance snapshot.
        
        ⚠️ P1: Direct FMP API call for real-time industry performance data.
        
        Args:
            date: Date in YYYY-MM-DD format (optional, defaults to latest)
            
        Returns:
            Dictionary with industry performance data
        """
        try:
            params = {}
            if date:
                params["date"] = date
            
            return await self._call_fmp_api("industry-performance-snapshot", params)
        except Exception as e:
            logger.error(f"Error getting industry performance: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def get_biggest_gainers(self) -> List[Dict[str, Any]]:
        """
        Get biggest stock gainers.
        
        ⚠️ P1: Direct FMP API call for real-time market data.
        
        Returns:
            List of dictionaries with stock gainer data
        """
        try:
            return await self._call_fmp_api("biggest-gainers")
        except Exception as e:
            logger.error(f"Error getting biggest gainers: {e}", exc_info=True)
            return []
    
    async def get_biggest_losers(self) -> List[Dict[str, Any]]:
        """
        Get biggest stock losers.
        
        ⚠️ P1: Direct FMP API call for real-time market data.
        
        Returns:
            List of dictionaries with stock loser data
        """
        try:
            return await self._call_fmp_api("biggest-losers")
        except Exception as e:
            logger.error(f"Error getting biggest losers: {e}", exc_info=True)
            return []
    
    async def get_most_actives(self) -> List[Dict[str, Any]]:
        """
        Get most actively traded stocks.
        
        ⚠️ P1: Direct FMP API call for real-time market data.
        
        Returns:
            List of dictionaries with most active stocks data
        """
        try:
            return await self._call_fmp_api("most-actives")
        except Exception as e:
            logger.error(f"Error getting most actives: {e}", exc_info=True)
            return []
    
    # P1.2: Analyst Data
    
    async def get_analyst_estimates(
        self,
        symbol: str,
        period: str = "annual",  # "annual" or "quarter"
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Get analyst financial estimates.
        
        ⚠️ P1: Direct FMP API call for analyst estimates (EPS, Revenue, etc.).
        
        Args:
            symbol: Stock ticker symbol
            period: "annual" or "quarter"
            limit: Maximum number of estimates to return
            
        Returns:
            Dictionary with analyst estimates data
        """
        try:
            params = {
                "symbol": symbol.upper(),
                "period": period,
                "limit": limit,
            }
            
            return await self._call_fmp_api("analyst-estimates", params)
        except Exception as e:
            logger.error(f"Error getting analyst estimates for {symbol}: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def get_price_target_summary(self, symbol: str) -> Dict[str, Any]:
        """
        Get price target summary.
        
        ⚠️ P1: Direct FMP API call for analyst price targets.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with price target summary data
        """
        try:
            params = {"symbol": symbol.upper()}
            
            return await self._call_fmp_api("price-target-summary", params)
        except Exception as e:
            logger.error(f"Error getting price target summary for {symbol}: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def get_price_target_consensus(self, symbol: str) -> Dict[str, Any]:
        """
        Get price target consensus (high, low, median, consensus).
        
        ⚠️ P1: Direct FMP API call for analyst price target consensus.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with price target consensus data
        """
        try:
            params = {"symbol": symbol.upper()}
            
            return await self._call_fmp_api("price-target-consensus", params)
        except Exception as e:
            logger.error(f"Error getting price target consensus for {symbol}: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def get_stock_grades(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get stock grades/ratings from analysts.
        
        ⚠️ P1: Direct FMP API call for analyst grades.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            List of dictionaries with stock grade data
        """
        try:
            params = {"symbol": symbol.upper()}
            
            return await self._call_fmp_api("grades", params)
        except Exception as e:
            logger.error(f"Error getting stock grades for {symbol}: {e}", exc_info=True)
            return []
    
    async def get_ratings_snapshot(self, symbol: str) -> Dict[str, Any]:
        """
        Get ratings snapshot.
        
        ⚠️ P1: Direct FMP API call for financial ratings snapshot.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with ratings snapshot data
        """
        try:
            params = {"symbol": symbol.upper()}
            
            return await self._call_fmp_api("ratings-snapshot", params)
        except Exception as e:
            logger.error(f"Error getting ratings snapshot for {symbol}: {e}", exc_info=True)
            return {"error": str(e)}
    
    # P1.3: TTM Financial Data
    
    async def get_key_metrics_ttm(self, symbol: str) -> Dict[str, Any]:
        """
        Get trailing twelve months (TTM) key metrics.
        
        ⚠️ P1: Direct FMP API call for TTM financial metrics.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with TTM key metrics data
        """
        try:
            params = {"symbol": symbol.upper()}
            
            return await self._call_fmp_api("key-metrics-ttm", params)
        except Exception as e:
            logger.error(f"Error getting key metrics TTM for {symbol}: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def get_ratios_ttm(self, symbol: str) -> Dict[str, Any]:
        """
        Get trailing twelve months (TTM) financial ratios.
        
        ⚠️ P1: Direct FMP API call for TTM financial ratios.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with TTM financial ratios data
        """
        try:
            params = {"symbol": symbol.upper()}
            
            return await self._call_fmp_api("ratios-ttm", params)
        except Exception as e:
            logger.error(f"Error getting ratios TTM for {symbol}: {e}", exc_info=True)
            return {"error": str(e)}
    
    # ==================== P0: Real-time Trading Core ====================
    # Direct FMP API calls for real-time trading data (batch quotes, multi-interval historical, technical indicators)
    
    # P0.1: Batch Quote API
    
    async def get_batch_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get real-time quotes for multiple symbols.
        
        ⚠️ P0: Direct FMP API call for batch stock quotes.
        Essential for monitoring multiple positions simultaneously.
        
        Args:
            symbols: List of stock ticker symbols (e.g., ["AAPL", "MSFT", "GOOGL"])
            
        Returns:
            Dictionary with quotes for each symbol
            
        Example:
            >>> service = MarketDataService()
            >>> quotes = await service.get_batch_quotes(["AAPL", "MSFT"])
            >>> # Returns: {"AAPL": {...}, "MSFT": {...}}
        """
        try:
            if not symbols:
                return {}
            
            # FMP batch-quote endpoint accepts comma-separated symbols
            symbols_str = ",".join([s.upper() for s in symbols])
            params = {"symbols": symbols_str}
            
            result = await self._call_fmp_api("batch-quote", params)
            
            # FMP returns a list, convert to dict keyed by symbol for easier access
            if isinstance(result, list):
                quotes_dict = {}
                for quote in result:
                    if isinstance(quote, dict) and "symbol" in quote:
                        quotes_dict[quote["symbol"]] = quote
                return quotes_dict
            
            return result
        except Exception as e:
            logger.error(f"Error getting batch quotes for {symbols}: {e}", exc_info=True)
            return {"error": str(e)}
    
    # P0.2: Multi-interval Historical Price Data
    
    async def get_historical_price(
        self,
        symbol: str,
        interval: str = "1day",  # 1min, 5min, 15min, 30min, 1hour, 1day
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get historical price data with various intervals.
        
        ⚠️ P0: Direct FMP API call for multi-interval historical data.
        Essential for technical analysis and strategy backtesting.
        
        Supported intervals:
        - "1min": 1-minute intervals (intraday)
        - "5min": 5-minute intervals (intraday)
        - "15min": 15-minute intervals (intraday)
        - "30min": 30-minute intervals (intraday)
        - "1hour": 1-hour intervals (intraday)
        - "4hour": 4-hour intervals (intraday)
        - "1day": Daily intervals (EOD)
        
        Args:
            symbol: Stock ticker symbol
            interval: Time interval (default: "1day")
            limit: Maximum number of data points (optional)
            
        Returns:
            Dictionary with historical price data (OHLCV)
            
        Example:
            >>> service = MarketDataService()
            >>> data = await service.get_historical_price("AAPL", interval="1min", limit=100)
            >>> # Returns: {"symbol": "AAPL", "interval": "1min", "data": [...]}
        """
        try:
            # Map interval to FMP endpoint
            endpoint_map = {
                "1min": "historical-chart/1min",
                "5min": "historical-chart/5min",
                "15min": "historical-chart/15min",
                "30min": "historical-chart/30min",
                "1hour": "historical-chart/1hour",
                "4hour": "historical-chart/4hour",
                "1day": "historical-price-eod/full",  # End-of-day data
            }
            
            endpoint = endpoint_map.get(interval)
            if not endpoint:
                raise ValueError(
                    f"Unsupported interval: {interval}. "
                    f"Supported intervals: {', '.join(endpoint_map.keys())}"
                )
            
            params = {"symbol": symbol.upper()}
            if limit:
                params["limit"] = limit
            
            data = await self._call_fmp_api(endpoint, params)
            
            # Ensure data is in consistent format
            if isinstance(data, list):
                return {
                    "symbol": symbol.upper(),
                    "interval": interval,
                    "data": data,
                }
            elif isinstance(data, dict):
                # Some endpoints return dict with nested data
                return {
                    "symbol": symbol.upper(),
                    "interval": interval,
                    "data": data,
                }
            else:
                return {
                    "symbol": symbol.upper(),
                    "interval": interval,
                    "data": [],
                }
        except Exception as e:
            logger.error(f"Error getting historical price for {symbol} ({interval}): {e}", exc_info=True)
            return {
                "symbol": symbol.upper(),
                "interval": interval,
                "error": str(e),
                "data": [],
            }
    
    # P0.3: Technical Indicators API
    
    async def get_technical_indicator(
        self,
        symbol: str,
        indicator: str,  # sma, ema, rsi, adx, macd, bollinger_bands, etc.
        period_length: int = 10,
        timeframe: str = "1day",  # 1min, 5min, 15min, 30min, 1hour, 1day
    ) -> Dict[str, Any]:
        """
        Get technical indicator data.
        
        ⚠️ P0: Direct FMP API call for technical indicators.
        Essential for strategy signal generation.
        
        Supported indicators:
        - "sma": Simple Moving Average
        - "ema": Exponential Moving Average
        - "rsi": Relative Strength Index
        - "adx": Average Directional Index
        - "macd": Moving Average Convergence Divergence
        - "bollinger_bands": Bollinger Bands
        - "williams": Williams %R
        - "standarddeviation": Standard Deviation
        - "wma": Weighted Moving Average
        - "dema": Double Exponential Moving Average
        - "tema": Triple Exponential Moving Average
        
        Args:
            symbol: Stock ticker symbol
            indicator: Technical indicator name
            period_length: Period length for calculation (default: 10)
            timeframe: Time frame for data (default: "1day")
            
        Returns:
            Dictionary with technical indicator data
            
        Example:
            >>> service = MarketDataService()
            >>> rsi = await service.get_technical_indicator("AAPL", "rsi", period_length=14, timeframe="1day")
            >>> # Returns: {"symbol": "AAPL", "indicator": "rsi", "data": [...]}
        """
        try:
            # Map indicator name to FMP endpoint
            indicator_map = {
                "sma": "sma",
                "ema": "ema",
                "rsi": "rsi",
                "adx": "adx",
                "macd": "macd",
                "bollinger_bands": "bollinger_bands",
                "williams": "williams",
                "standarddeviation": "standarddeviation",
                "wma": "wma",
                "dema": "dema",
                "tema": "tema",
            }
            
            indicator_endpoint = indicator_map.get(indicator.lower())
            if not indicator_endpoint:
                raise ValueError(
                    f"Unsupported indicator: {indicator}. "
                    f"Supported indicators: {', '.join(indicator_map.keys())}"
                )
            
            endpoint = f"technical-indicators/{indicator_endpoint}"
            params = {
                "symbol": symbol.upper(),
                "periodLength": period_length,
                "timeframe": timeframe,
            }
            
            data = await self._call_fmp_api(endpoint, params)
            
            return {
                "symbol": symbol.upper(),
                "indicator": indicator.lower(),
                "period_length": period_length,
                "timeframe": timeframe,
                "data": data if isinstance(data, (list, dict)) else [],
            }
        except Exception as e:
            logger.error(
                f"Error getting technical indicator {indicator} for {symbol}: {e}",
                exc_info=True,
            )
            return {
                "symbol": symbol.upper(),
                "indicator": indicator.lower(),
                "error": str(e),
                "data": [],
            }
    
    def get_stock_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get real-time stock quote. FMP only (no Yahoo/FinanceToolkit).
        
        Uses FMP quote endpoint: GET /stable/quote?symbol=...
        
        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            Dictionary with quote data: price, change, change_percent, volume
            Returns empty dict if data unavailable
        """
        if not self._fmp_api_key:
            return {}
        try:
            raw = self._call_fmp_api_sync("quote", params={"symbol": ticker})
            if isinstance(raw, list) and raw:
                row = raw[0]
            elif isinstance(raw, dict) and raw.get("symbol"):
                row = raw
            else:
                return {}
            price = row.get("price") or row.get("close")
            change = row.get("change")
            change_percent = row.get("changesPercentage") or row.get("changePercent")
            volume = row.get("volume")
            return {
                "price": self._sanitize_value(price),
                "change": self._sanitize_value(change),
                "change_percent": self._sanitize_value(change_percent),
                "volume": self._sanitize_value(volume),
            }
        except Exception as e:
            logger.warning(f"Error getting stock quote for {ticker}: {e}")
            return {}


# Singleton instance (optional - can also instantiate directly)
_market_data_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    """Get singleton instance of MarketDataService.
    
    Returns:
        MarketDataService instance
    """
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
