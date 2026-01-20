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
from typing import Any, Dict, List, Optional

import financedatabase as fd
import numpy as np
import pandas as pd
from financetoolkit import Toolkit

from app.core.config import settings

logger = logging.getLogger(__name__)


class MarketDataService:
    """Market data service with FinanceToolkit and FinanceDatabase integration."""

    def __init__(self) -> None:
        """Initialize MarketDataService.
        
        Sets up FinanceDatabase instances for discovery and configures
        FinanceToolkit with FMP API key (required for production use).
        
        Note: System depends on FMP API key for accurate financial data.
        Falls back to Yahoo Finance if not set, but data quality may be reduced.
        """
        # Initialize FinanceDatabase instances (lazy loading, no API key needed)
        self._equities_db: Optional[fd.Equities] = None
        self._etfs_db: Optional[fd.ETFs] = None
        
        # Get FMP API key from config (required for production, falls back to Yahoo Finance)
        self._fmp_api_key: Optional[str] = None
        if settings.financial_modeling_prep_key:
            self._fmp_api_key = settings.financial_modeling_prep_key
            logger.info("MarketDataService: Using Financial Modeling Prep API (Primary data source)")
        else:
            logger.warning(
                "MarketDataService: FMP API key not set! "
                "System depends on FMP API for accurate financial data. "
                "Falling back to Yahoo Finance (data quality may be reduced). "
                "Please set FINANCIAL_MODELING_PREP_KEY in .env file."
            )
        
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
        """Create FinanceToolkit instance for given tickers.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Toolkit instance configured with FMP API key (Primary) or Yahoo Finance fallback
            
        Note: System depends on FMP API key for accurate financial data.
        If FMP API key is not set, Toolkit will automatically fall back to Yahoo Finance,
        but data quality and availability may be reduced.
        """
        toolkit_kwargs = {
            "tickers": tickers,
            "start_date": "2020-01-01",  # 5 years of historical data
        }
        
        # Add FMP API key if available (Primary data source)
        # If not set, Toolkit automatically falls back to Yahoo Finance
        if self._fmp_api_key:
            toolkit_kwargs["api_key"] = self._fmp_api_key
            logger.debug(f"Using FMP API for tickers: {tickers}")
        else:
            logger.debug(
                f"FMP API key not set, Toolkit will use Yahoo Finance fallback for: {tickers}"
            )
        
        return Toolkit(**toolkit_kwargs)

    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize numeric values: replace NaN/Inf with None.
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value (None for NaN/Inf, original value otherwise)
        """
        if isinstance(value, (float, np.floating)):
            if math.isnan(value) or math.isinf(value):
                return None
        elif isinstance(value, (int, np.integer)):
            # Check for numpy integer NaN (rare but possible)
            if isinstance(value, np.integer) and (math.isnan(float(value)) or math.isinf(float(value))):
                return None
        return value

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
        
        P1: This enables batch historical data analysis for multiple tickers.
        
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

    # ==================== Part B: Deep Analysis (The Data Engine) ====================

    def get_financial_profile(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive financial profile for a ticker.
        
        Fetches:
        - Key financial ratios (PE, Debt/Equity, ROE, etc.) - All 5 categories
        - Technical indicators (RSI, MACD, SMA, EMA, ATR, OBV, etc.) - Complete set
        - Risk metrics (Sharpe, Sortino, VaR, Beta, Alpha, etc.) - Complete set
        - Performance metrics (CAPM, Information Ratio, etc.) - Complete set
        - Financial statements (Income, Balance Sheet, Cash Flow)
        - Historical volatility
        - Company profile
        
        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            Dictionary containing financial profile data (all DataFrames converted to dicts)
            
        Example:
            >>> service = MarketDataService()
            >>> profile = service.get_financial_profile("AAPL")
            >>> # Returns: {
            >>> #   "ratios": {...},  # All 5 categories
            >>> #   "technical_indicators": {...},  # Complete set
            >>> #   "risk_metrics": {...},  # Complete set
            >>> #   "performance_metrics": {...},  # Complete set
            >>> #   "financial_statements": {...},  # All 3 statements
            >>> #   "volatility": {...},
            >>> #   "profile": {...}
            >>> # }
        """
        try:
            toolkit = self._get_toolkit([ticker])
            
            profile: Dict[str, Any] = {
                "ticker": ticker,
                "ratios": {},
                "technical_indicators": {},
                "risk_metrics": {},
                "performance_metrics": {},
                "financial_statements": {},
                "valuation": {},  # P2: 估值模型
                "dupont_analysis": {},  # P2: 杜邦分析
                "analysis": {},  # P2: 数据分析（信号、评分等）
                "volatility": {},
                "profile": {},
            }
            
            # 1. Get key financial ratios
            try:
                # Profitability ratios
                profitability = toolkit.ratios.collect_profitability_ratios()
                if profitability is not None and not profitability.empty:
                    profile["ratios"]["profitability"] = self._dataframe_to_dict(
                        profitability, ticker
                    )
                
                # Valuation ratios
                valuation = toolkit.ratios.collect_valuation_ratios()
                if valuation is not None and not valuation.empty:
                    profile["ratios"]["valuation"] = self._dataframe_to_dict(
                        valuation, ticker
                    )
                
                # Solvency ratios (Debt/Equity, etc.)
                solvency = toolkit.ratios.collect_solvency_ratios()
                if solvency is not None and not solvency.empty:
                    profile["ratios"]["solvency"] = self._dataframe_to_dict(
                        solvency, ticker
                    )
                
                # Liquidity ratios
                liquidity = toolkit.ratios.collect_liquidity_ratios()
                if liquidity is not None and not liquidity.empty:
                    profile["ratios"]["liquidity"] = self._dataframe_to_dict(
                        liquidity, ticker
                    )
                
                # Efficiency ratios (P0 - 新增)
                try:
                    efficiency = toolkit.ratios.collect_efficiency_ratios()
                    if efficiency is not None:
                        # Handle both DataFrame and Series
                        if hasattr(efficiency, 'empty') and not efficiency.empty:
                            if isinstance(efficiency, pd.DataFrame):
                                profile["ratios"]["efficiency"] = self._dataframe_to_dict(
                                    efficiency, ticker
                                )
                            elif isinstance(efficiency, pd.Series):
                                # Convert Series to dict
                                profile["ratios"]["efficiency"] = {
                                    k: self._sanitize_value(v)
                                    for k, v in efficiency.to_dict().items()
                                }
                        elif isinstance(efficiency, pd.Series):
                            # Series might not have empty attribute
                            profile["ratios"]["efficiency"] = {
                                k: self._sanitize_value(v)
                                for k, v in efficiency.to_dict().items()
                            }
                except Exception as e:
                    logger.debug(f"Error fetching efficiency ratios for {ticker}: {e}")
                    
            except Exception as e:
                error_msg = str(e)
                if "Excess Return" in error_msg or "multiple columns" in error_msg.lower():
                    logger.debug(f"Error fetching ratios for {ticker} (Excess Return conflict): {e}")
                else:
                    logger.warning(f"Error fetching ratios for {ticker}: {e}")
                if "error" not in profile["ratios"]:
                    profile["ratios"]["error"] = str(e)
            
            # 2. Get technical indicators
            try:
                # Use collect_momentum_indicators to get RSI and MACD together
                momentum_indicators = toolkit.technicals.collect_momentum_indicators()
                if momentum_indicators is not None and not momentum_indicators.empty:
                    profile["technical_indicators"]["momentum"] = self._dataframe_to_dict(
                        momentum_indicators, ticker
                    )
                
                # Get individual indicators as fallback if collect doesn't work
                try:
                    # RSI (correct method name)
                    rsi = toolkit.technicals.get_relative_strength_index()
                    if rsi is not None and not rsi.empty:
                        profile["technical_indicators"]["rsi"] = self._dataframe_to_dict(
                            rsi, ticker
                        )
                except AttributeError:
                    logger.debug(f"get_relative_strength_index not available, using collect_momentum_indicators")
                
                try:
                    # MACD (correct method name)
                    macd_result = toolkit.technicals.get_moving_average_convergence_divergence()
                    if macd_result is not None:
                        # MACD may return tuple or DataFrame
                        if isinstance(macd_result, tuple):
                            # Unpack tuple (macd_line, signal_line)
                            macd_line, signal_line = macd_result
                            if macd_line is not None and not macd_line.empty:
                                profile["technical_indicators"]["macd_line"] = self._dataframe_to_dict(
                                    macd_line, ticker
                                )
                            if signal_line is not None and not signal_line.empty:
                                profile["technical_indicators"]["macd_signal"] = self._dataframe_to_dict(
                                    signal_line, ticker
                                )
                        elif not macd_result.empty:
                            profile["technical_indicators"]["macd"] = self._dataframe_to_dict(
                                macd_result, ticker
                            )
                except AttributeError:
                    logger.debug(f"get_moving_average_convergence_divergence not available")
                
                try:
                    # Bollinger Bands
                    bollinger = toolkit.technicals.get_bollinger_bands()
                    if bollinger is not None and not bollinger.empty:
                        profile["technical_indicators"]["bollinger_bands"] = (
                            self._dataframe_to_dict(bollinger, ticker)
                        )
                except AttributeError:
                    logger.debug(f"get_bollinger_bands not available")
                
                # P1: Complete Technical Indicators Set
                # Trend indicators
                try:
                    trend_indicators = toolkit.technicals.collect_trend_indicators()
                    if trend_indicators is not None and not trend_indicators.empty:
                        profile["technical_indicators"]["trend"] = self._dataframe_to_dict(
                            trend_indicators, ticker
                        )
                except Exception as e:
                    logger.debug(f"Error fetching trend indicators for {ticker}: {e}")
                
                # Individual trend indicators (fallback)
                try:
                    sma = toolkit.technicals.get_simple_moving_average()
                    if sma is not None and not sma.empty:
                        profile["technical_indicators"]["sma"] = self._dataframe_to_dict(
                            sma, ticker
                        )
                except AttributeError:
                    logger.debug(f"get_simple_moving_average not available")
                
                try:
                    ema = toolkit.technicals.get_exponential_moving_average()
                    if ema is not None and not ema.empty:
                        profile["technical_indicators"]["ema"] = self._dataframe_to_dict(
                            ema, ticker
                        )
                except AttributeError:
                    logger.debug(f"get_exponential_moving_average not available")
                
                try:
                    adx = toolkit.technicals.get_average_directional_index()
                    if adx is not None and not adx.empty:
                        profile["technical_indicators"]["adx"] = self._dataframe_to_dict(
                            adx, ticker
                        )
                except AttributeError:
                    logger.debug(f"get_average_directional_index not available")
                
                # Volatility indicators
                try:
                    volatility_indicators = toolkit.technicals.collect_volatility_indicators()
                    if volatility_indicators is not None and not volatility_indicators.empty:
                        profile["technical_indicators"]["volatility"] = self._dataframe_to_dict(
                            volatility_indicators, ticker
                        )
                except Exception as e:
                    logger.debug(f"Error fetching volatility indicators for {ticker}: {e}")
                
                try:
                    atr = toolkit.technicals.get_average_true_range()
                    if atr is not None and not atr.empty:
                        profile["technical_indicators"]["atr"] = self._dataframe_to_dict(
                            atr, ticker
                        )
                except AttributeError:
                    logger.debug(f"get_average_true_range not available")
                
                # Volume indicators
                try:
                    volume_indicators = toolkit.technicals.collect_volume_indicators()
                    if volume_indicators is not None and not volume_indicators.empty:
                        profile["technical_indicators"]["volume"] = self._dataframe_to_dict(
                            volume_indicators, ticker
                        )
                except Exception as e:
                    logger.debug(f"Error fetching volume indicators for {ticker}: {e}")
                
                try:
                    obv = toolkit.technicals.get_on_balance_volume()
                    if obv is not None and not obv.empty:
                        profile["technical_indicators"]["obv"] = self._dataframe_to_dict(
                            obv, ticker
                        )
                except AttributeError:
                    logger.debug(f"get_on_balance_volume not available")
                    
            except Exception as e:
                error_msg = str(e)
                if "Excess Return" in error_msg or "multiple columns" in error_msg.lower():
                    logger.debug(f"Error fetching technical indicators for {ticker} (Excess Return conflict): {e}")
                else:
                    logger.warning(f"Error fetching technical indicators for {ticker}: {e}")
                if "error" not in profile["technical_indicators"]:
                    profile["technical_indicators"]["error"] = str(e)
            
            # 3. P0: Get risk metrics (最高优先级)
            try:
                # Collect all risk metrics
                risk_metrics = toolkit.risk.collect_all_metrics()
                if risk_metrics is not None and not risk_metrics.empty:
                    profile["risk_metrics"]["all"] = self._dataframe_to_dict(
                        risk_metrics, ticker
                    )
                
                # Individual risk metrics (fallback if collect_all_metrics doesn't work)
                try:
                    var = toolkit.risk.get_value_at_risk()
                    if var is not None and not var.empty:
                        profile["risk_metrics"]["var"] = self._dataframe_to_dict(
                            var, ticker
                        )
                except AttributeError:
                    logger.debug(f"get_value_at_risk not available")
                
                try:
                    cvar = toolkit.risk.get_conditional_value_at_risk()
                    if cvar is not None and not cvar.empty:
                        profile["risk_metrics"]["cvar"] = self._dataframe_to_dict(
                            cvar, ticker
                        )
                except AttributeError:
                    logger.debug(f"get_conditional_value_at_risk not available")
                
                try:
                    max_drawdown = toolkit.risk.get_maximum_drawdown()
                    if max_drawdown is not None and not max_drawdown.empty:
                        profile["risk_metrics"]["max_drawdown"] = self._dataframe_to_dict(
                            max_drawdown, ticker
                        )
                except AttributeError:
                    logger.debug(f"get_maximum_drawdown not available")
                
                try:
                    skewness = toolkit.risk.get_skewness()
                    if skewness is not None and not skewness.empty:
                        profile["risk_metrics"]["skewness"] = self._dataframe_to_dict(
                            skewness, ticker
                        )
                except AttributeError:
                    logger.debug(f"get_skewness not available")
                
                try:
                    kurtosis = toolkit.risk.get_kurtosis()
                    if kurtosis is not None and not kurtosis.empty:
                        profile["risk_metrics"]["kurtosis"] = self._dataframe_to_dict(
                            kurtosis, ticker
                        )
                except AttributeError:
                    logger.debug(f"get_kurtosis not available")
                    
            except Exception as e:
                error_msg = str(e)
                if "Excess Return" in error_msg or "multiple columns" in error_msg.lower():
                    logger.debug(f"Error fetching risk metrics for {ticker} (Excess Return conflict): {e}")
                else:
                    logger.warning(f"Error fetching risk metrics for {ticker}: {e}")
                if "error" not in profile["risk_metrics"]:
                    profile["risk_metrics"]["error"] = str(e)
            
            # 4. P0: Get performance metrics (最高优先级)
            try:
                # Get historical data first (required for performance metrics)
                historical_data = toolkit.get_historical_data()
                if historical_data is None or historical_data.empty:
                    logger.debug(f"No historical data available for performance metrics for {ticker}")
                else:
                    # Ensure historical data is properly initialized
                    # Some performance metrics require "Excess Return" column which may cause conflicts
                    # We'll catch specific errors related to this
                    
                    # Sharpe Ratio
                    try:
                        sharpe = toolkit.performance.get_sharpe_ratio()
                        if sharpe is not None:
                            if isinstance(sharpe, pd.DataFrame) and not sharpe.empty:
                                profile["performance_metrics"]["sharpe_ratio"] = self._dataframe_to_dict(
                                    sharpe, ticker
                                )
                            elif isinstance(sharpe, pd.Series):
                                profile["performance_metrics"]["sharpe_ratio"] = {
                                    k: self._sanitize_value(v)
                                    for k, v in sharpe.to_dict().items()
                                }
                    except (AttributeError, ValueError) as e:
                        # ValueError may occur if "Excess Return" column conflict exists
                        error_msg = str(e)
                        if "Excess Return" in error_msg or "multiple columns" in error_msg.lower():
                            logger.debug(f"get_sharpe_ratio failed due to Excess Return conflict for {ticker}: {e}")
                        else:
                            logger.debug(f"get_sharpe_ratio not available or failed: {e}")
                    except Exception as e:
                        logger.debug(f"get_sharpe_ratio failed: {e}")
                    
                    # Sortino Ratio
                    try:
                        sortino = toolkit.performance.get_sortino_ratio()
                        if sortino is not None:
                            if isinstance(sortino, pd.DataFrame) and not sortino.empty:
                                profile["performance_metrics"]["sortino_ratio"] = self._dataframe_to_dict(
                                    sortino, ticker
                                )
                            elif isinstance(sortino, pd.Series):
                                profile["performance_metrics"]["sortino_ratio"] = {
                                    k: self._sanitize_value(v)
                                    for k, v in sortino.to_dict().items()
                                }
                    except (AttributeError, ValueError) as e:
                        error_msg = str(e)
                        if "Excess Return" in error_msg or "multiple columns" in error_msg.lower():
                            logger.debug(f"get_sortino_ratio failed due to Excess Return conflict for {ticker}: {e}")
                        else:
                            logger.debug(f"get_sortino_ratio not available or failed: {e}")
                    except Exception as e:
                        logger.debug(f"get_sortino_ratio failed: {e}")
                    
                    # Treynor Ratio
                    try:
                        treynor = toolkit.performance.get_treynor_ratio()
                        if treynor is not None:
                            if isinstance(treynor, pd.DataFrame) and not treynor.empty:
                                profile["performance_metrics"]["treynor_ratio"] = self._dataframe_to_dict(
                                    treynor, ticker
                                )
                            elif isinstance(treynor, pd.Series):
                                profile["performance_metrics"]["treynor_ratio"] = {
                                    k: self._sanitize_value(v)
                                    for k, v in treynor.to_dict().items()
                                }
                    except (AttributeError, ValueError) as e:
                        error_msg = str(e)
                        if "Excess Return" in error_msg or "multiple columns" in error_msg.lower():
                            logger.debug(f"get_treynor_ratio failed due to Excess Return conflict for {ticker}: {e}")
                        else:
                            logger.debug(f"get_treynor_ratio not available or failed: {e}")
                    except Exception as e:
                        logger.debug(f"get_treynor_ratio failed: {e}")
                    
                    # CAPM (Capital Asset Pricing Model)
                    try:
                        capm = toolkit.performance.get_capital_asset_pricing_model()
                        if capm is not None:
                            if isinstance(capm, pd.DataFrame) and not capm.empty:
                                profile["performance_metrics"]["capm"] = self._dataframe_to_dict(
                                    capm, ticker
                                )
                            elif isinstance(capm, pd.Series):
                                profile["performance_metrics"]["capm"] = {
                                    k: self._sanitize_value(v)
                                    for k, v in capm.to_dict().items()
                                }
                    except (AttributeError, ValueError) as e:
                        error_msg = str(e)
                        if "Excess Return" in error_msg or "multiple columns" in error_msg.lower():
                            logger.debug(f"get_capital_asset_pricing_model failed due to Excess Return conflict for {ticker}: {e}")
                        else:
                            logger.debug(f"get_capital_asset_pricing_model not available or failed: {e}")
                    except Exception as e:
                        logger.debug(f"get_capital_asset_pricing_model failed: {e}")
                    
                    # Jensen's Alpha
                    try:
                        alpha = toolkit.performance.get_jensens_alpha()
                        if alpha is not None:
                            if isinstance(alpha, pd.DataFrame) and not alpha.empty:
                                profile["performance_metrics"]["jensens_alpha"] = self._dataframe_to_dict(
                                    alpha, ticker
                                )
                            elif isinstance(alpha, pd.Series):
                                profile["performance_metrics"]["jensens_alpha"] = {
                                    k: self._sanitize_value(v)
                                    for k, v in alpha.to_dict().items()
                                }
                    except (AttributeError, ValueError) as e:
                        error_msg = str(e)
                        if "Excess Return" in error_msg or "multiple columns" in error_msg.lower():
                            logger.debug(f"get_jensens_alpha failed due to Excess Return conflict for {ticker}: {e}")
                        else:
                            logger.debug(f"get_jensens_alpha not available or failed: {e}")
                    except Exception as e:
                        logger.debug(f"get_jensens_alpha failed: {e}")
                    
                    # Information Ratio
                    try:
                        info_ratio = toolkit.performance.get_information_ratio()
                        if info_ratio is not None:
                            if isinstance(info_ratio, pd.DataFrame) and not info_ratio.empty:
                                profile["performance_metrics"]["information_ratio"] = self._dataframe_to_dict(
                                    info_ratio, ticker
                                )
                            elif isinstance(info_ratio, pd.Series):
                                profile["performance_metrics"]["information_ratio"] = {
                                    k: self._sanitize_value(v)
                                    for k, v in info_ratio.to_dict().items()
                                }
                    except (AttributeError, ValueError) as e:
                        error_msg = str(e)
                        if "Excess Return" in error_msg or "multiple columns" in error_msg.lower():
                            logger.debug(f"get_information_ratio failed due to Excess Return conflict for {ticker}: {e}")
                        else:
                            logger.debug(f"get_information_ratio not available or failed: {e}")
                    except Exception as e:
                        logger.debug(f"get_information_ratio failed: {e}")
                    
            except Exception as e:
                logger.warning(f"Error fetching performance metrics for {ticker}: {e}")
                profile["performance_metrics"] = {"error": str(e)}
            
            # 5. P1: Get financial statements
            try:
                # Income Statement
                try:
                    income_statement = toolkit.get_income_statement()
                    if income_statement is not None and not income_statement.empty:
                        profile["financial_statements"]["income"] = self._dataframe_to_dict(
                            income_statement, ticker
                        )
                except (AttributeError, Exception) as e:
                    logger.debug(f"get_income_statement not available or failed: {e}")
                
                # Balance Sheet
                try:
                    balance_sheet = toolkit.get_balance_sheet()
                    if balance_sheet is not None and not balance_sheet.empty:
                        profile["financial_statements"]["balance"] = self._dataframe_to_dict(
                            balance_sheet, ticker
                        )
                    else:
                        logger.debug(f"Balance sheet is empty or None for {ticker}")
                except (AttributeError, Exception) as e:
                    logger.debug(f"get_balance_sheet not available or failed: {e}")
                
                # Cash Flow Statement
                try:
                    cash_flow = toolkit.get_cash_flow_statement()
                    if cash_flow is not None and not cash_flow.empty:
                        profile["financial_statements"]["cash_flow"] = self._dataframe_to_dict(
                            cash_flow, ticker
                        )
                except (AttributeError, Exception) as e:
                    logger.debug(f"get_cash_flow_statement not available or failed: {e}")
                    
            except Exception as e:
                logger.warning(f"Error fetching financial statements for {ticker}: {e}")
                profile["financial_statements"] = {"error": str(e)}
            
            # 6. P2: Get valuation models (估值模型)
            try:
                # DCF (Discounted Cash Flow) - Intrinsic Valuation
                try:
                    dcf = toolkit.models.intrinsic_valuation()
                    if dcf is not None:
                        if isinstance(dcf, pd.DataFrame) and not dcf.empty:
                            profile["valuation"]["dcf"] = self._dataframe_to_dict(
                                dcf, ticker
                            )
                        elif isinstance(dcf, pd.Series):
                            profile["valuation"]["dcf"] = {
                                k: self._sanitize_value(v)
                                for k, v in dcf.to_dict().items()
                            }
                        elif isinstance(dcf, dict):
                            profile["valuation"]["dcf"] = {
                                k: self._sanitize_value(v)
                                for k, v in dcf.items()
                            }
                except (AttributeError, Exception) as e:
                    logger.debug(f"intrinsic_valuation not available or failed: {e}")
                
                # DDM (Dividend Discount Model)
                try:
                    ddm = toolkit.models.get_dividend_discount_model()
                    if ddm is not None:
                        if isinstance(ddm, pd.DataFrame) and not ddm.empty:
                            profile["valuation"]["ddm"] = self._dataframe_to_dict(
                                ddm, ticker
                            )
                        elif isinstance(ddm, pd.Series):
                            profile["valuation"]["ddm"] = {
                                k: self._sanitize_value(v)
                                for k, v in ddm.to_dict().items()
                            }
                except (AttributeError, Exception) as e:
                    logger.debug(f"get_dividend_discount_model not available or failed: {e}")
                
                # WACC (Weighted Average Cost of Capital)
                try:
                    wacc = toolkit.models.get_wacc()
                    if wacc is not None:
                        if isinstance(wacc, pd.DataFrame) and not wacc.empty:
                            profile["valuation"]["wacc"] = self._dataframe_to_dict(
                                wacc, ticker
                            )
                        elif isinstance(wacc, pd.Series):
                            profile["valuation"]["wacc"] = {
                                k: self._sanitize_value(v)
                                for k, v in wacc.to_dict().items()
                            }
                except (AttributeError, Exception) as e:
                    logger.debug(f"get_wacc not available or failed: {e}")
                
                # Enterprise Value Breakdown
                try:
                    ev_breakdown = toolkit.models.get_enterprise_value_breakdown()
                    if ev_breakdown is not None:
                        if isinstance(ev_breakdown, pd.DataFrame) and not ev_breakdown.empty:
                            profile["valuation"]["enterprise_value"] = self._dataframe_to_dict(
                                ev_breakdown, ticker
                            )
                        elif isinstance(ev_breakdown, pd.Series):
                            profile["valuation"]["enterprise_value"] = {
                                k: self._sanitize_value(v)
                                for k, v in ev_breakdown.to_dict().items()
                            }
                except (AttributeError, Exception) as e:
                    logger.debug(f"get_enterprise_value_breakdown not available or failed: {e}")
                    
            except Exception as e:
                logger.warning(f"Error fetching valuation models for {ticker}: {e}")
                profile["valuation"] = {"error": str(e)}
            
            # 7. P2: Get DuPont Analysis (杜邦分析)
            try:
                # Standard DuPont Analysis
                try:
                    dupont = toolkit.models.get_dupont_analysis()
                    if dupont is not None:
                        if isinstance(dupont, pd.DataFrame) and not dupont.empty:
                            profile["dupont_analysis"]["standard"] = self._dataframe_to_dict(
                                dupont, ticker
                            )
                        elif isinstance(dupont, pd.Series):
                            profile["dupont_analysis"]["standard"] = {
                                k: self._sanitize_value(v)
                                for k, v in dupont.to_dict().items()
                            }
                except (AttributeError, Exception) as e:
                    logger.debug(f"get_dupont_analysis not available or failed: {e}")
                
                # Extended DuPont Analysis
                try:
                    extended_dupont = toolkit.models.get_extended_dupont_analysis()
                    if extended_dupont is not None:
                        if isinstance(extended_dupont, pd.DataFrame) and not extended_dupont.empty:
                            profile["dupont_analysis"]["extended"] = self._dataframe_to_dict(
                                extended_dupont, ticker
                            )
                        elif isinstance(extended_dupont, pd.Series):
                            profile["dupont_analysis"]["extended"] = {
                                k: self._sanitize_value(v)
                                for k, v in extended_dupont.to_dict().items()
                            }
                except (AttributeError, Exception) as e:
                    logger.debug(f"get_extended_dupont_analysis not available or failed: {e}")
                    
            except Exception as e:
                logger.warning(f"Error fetching DuPont analysis for {ticker}: {e}")
                profile["dupont_analysis"] = {"error": str(e)}
            
            # 8. P2: Generate analysis (数据分析功能)
            try:
                analysis = self._generate_analysis(profile, ticker)
                if analysis:
                    profile["analysis"] = analysis
            except Exception as e:
                logger.warning(f"Error generating analysis for {ticker}: {e}")
                profile["analysis"] = {"error": str(e)}
            
            # 9. Get historical volatility
            try:
                historical_data = toolkit.get_historical_data()
                if historical_data is not None and not historical_data.empty:
                    # Extract volatility column if available
                    if "Volatility" in historical_data.columns:
                        volatility_data = historical_data[["Volatility"]]
                        profile["volatility"] = self._dataframe_to_dict(
                            volatility_data, ticker
                        )
                    else:
                        # Calculate from returns if volatility not directly available
                        if "Return" in historical_data.columns:
                            returns = historical_data["Return"]
                            if not returns.empty:
                                # Annualized volatility (assuming daily returns)
                                vol = returns.std() * (252 ** 0.5)  # 252 trading days
                                profile["volatility"] = {
                                    "annualized": self._sanitize_value(float(vol))
                                }
            except Exception as e:
                logger.warning(f"Error fetching volatility for {ticker}: {e}")
                profile["volatility"] = {"error": str(e)}
            
            # 10. Get company profile
            try:
                company_profile = toolkit.get_profile()
                if company_profile is not None and not company_profile.empty:
                    # Profile DataFrame structure:
                    # - Index (rows): Field names (e.g., "Company Name", "Market Capitalization")
                    # - Columns: Tickers (e.g., "AAPL")
                    # So we need to extract the ticker column, then convert index to dict
                    if ticker in company_profile.columns:
                        # Extract the column for this ticker, convert to dict
                        ticker_profile = company_profile[ticker].to_dict()
                        profile["profile"] = {
                            k: self._sanitize_value(v)
                            for k, v in ticker_profile.items()
                        }
                    else:
                        # Fallback: if ticker not in columns, take first column
                        logger.warning(
                            f"Ticker {ticker} not found in profile columns: {list(company_profile.columns)}"
                        )
                        first_col = company_profile.iloc[:, 0]
                        ticker_profile = first_col.to_dict()
                        profile["profile"] = {
                            k: self._sanitize_value(v)
                            for k, v in ticker_profile.items()
                        }
            except Exception as e:
                logger.warning(f"Error fetching profile for {ticker}: {e}")
                profile["profile"] = {"error": str(e)}
            
            logger.info(f"Financial profile retrieved for {ticker}")
            return profile
            
        except Exception as e:
            logger.error(f"Error getting financial profile for {ticker}: {e}", exc_info=True)
            return {
                "ticker": ticker,
                "error": str(e),
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

    # ==================== Part C: Options Intelligence ====================

    def get_options_data(self, ticker: str) -> Dict[str, Any]:
        """Get options chain data and Greeks for a ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            Dictionary containing options chain summary and Greeks
            
        Example:
            >>> service = MarketDataService()
            >>> options = service.get_options_data("AAPL")
            >>> # Returns: {
            >>> #   "option_chains": {...},
            >>> #   "greeks": {...},
            >>> #   "implied_volatility": {...}
            >>> # }
        """
        try:
            toolkit = self._get_toolkit([ticker])
            
            options_data: Dict[str, Any] = {
                "ticker": ticker,
                "option_chains": {},
                "greeks": {},
                "implied_volatility": {},
            }
            
            # 1. Get option chains
            try:
                option_chains = toolkit.options.get_option_chains()
                if option_chains is not None and not option_chains.empty:
                    options_data["option_chains"] = self._dataframe_to_dict(
                        option_chains, ticker
                    )
            except Exception as e:
                logger.warning(f"Error fetching option chains for {ticker}: {e}")
                options_data["option_chains"] = {"error": str(e)}
            
            # 2. Get Greeks (Delta, Gamma, Theta, Vega)
            try:
                # Collect all first-order Greeks
                first_order_greeks = toolkit.options.collect_first_order_greeks()
                if first_order_greeks is not None and not first_order_greeks.empty:
                    options_data["greeks"]["first_order"] = self._dataframe_to_dict(
                        first_order_greeks, ticker
                    )
                
                # Collect second-order Greeks (Gamma, etc.)
                second_order_greeks = toolkit.options.collect_second_order_greeks()
                if second_order_greeks is not None and not second_order_greeks.empty:
                    options_data["greeks"]["second_order"] = self._dataframe_to_dict(
                        second_order_greeks, ticker
                    )
                    
            except Exception as e:
                logger.warning(f"Error fetching Greeks for {ticker}: {e}")
                options_data["greeks"] = {"error": str(e)}
            
            # 3. Get implied volatility
            try:
                implied_vol = toolkit.options.get_implied_volatility()
                if implied_vol is not None and not implied_vol.empty:
                    options_data["implied_volatility"] = self._dataframe_to_dict(
                        implied_vol, ticker
                    )
            except Exception as e:
                logger.warning(f"Error fetching implied volatility for {ticker}: {e}")
                options_data["implied_volatility"] = {"error": str(e)}
            
            logger.info(f"Options data retrieved for {ticker}")
            return options_data
            
        except Exception as e:
            logger.error(f"Error getting options data for {ticker}: {e}", exc_info=True)
            return {
                "ticker": ticker,
                "error": str(e),
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
        """Get historical price data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            period: Data period ("daily", "weekly", "monthly", "quarterly", "yearly")
            
        Returns:
            Dictionary containing historical OHLCV data
        """
        try:
            toolkit = self._get_toolkit([ticker])
            historical = toolkit.get_historical_data(period=period)
            
            if historical is None or historical.empty:
                return {"ticker": ticker, "data": {}}
            
            return {
                "ticker": ticker,
                "period": period,
                "data": self._dataframe_to_dict(historical, ticker),
            }
        except Exception as e:
            logger.error(f"Error getting historical data for {ticker}: {e}", exc_info=True)
            return {"ticker": ticker, "error": str(e), "data": {}}


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
