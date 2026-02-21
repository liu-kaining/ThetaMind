"""Stock Screening Agent - Screens stocks based on criteria using MarketDataService."""

import logging
from typing import Any, Dict, List

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ai.base import BaseAIProvider
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class StockScreeningAgent(BaseAgent):
    """Stock Screening Agent - Screens stocks based on criteria.
    
    This agent uses MarketDataService to:
    - Search and filter stocks by sector, industry, market cap, country
    - Apply additional criteria (ratios, technical indicators)
    - Return candidate list for further analysis
    """
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: Dict[str, Any]):
        """Initialize Stock Screening Agent.
        
        Args:
            name: Agent name
            ai_provider: AI provider instance
            dependencies: Dictionary of dependencies (must include market_data_service)
        """
        super().__init__(
            name=name,
            agent_type=AgentType.STOCK_SCREENING,
            ai_provider=ai_provider,
            dependencies=dependencies,
        )
        self.market_data_service: MarketDataService = self._get_dependency("market_data_service")
    
    def _get_role_prompt(self) -> str:
        """Get role definition prompt."""
        return """You are a Stock Screening Specialist.

Your role is to filter and screen stocks based on criteria to identify
candidates for further analysis.

You work with:
- Sector and industry filters
- Market cap categories
- Country filters
- Additional criteria (ratios, technical indicators)

Provide a list of candidate stocks that meet the criteria."""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute stock screening.
        
        Args:
            context: Execution context containing criteria
            
        Returns:
            AgentResult with candidate stocks
        """
        try:
            criteria = context.input_data.get("criteria", {})
            
            if not criteria:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error="screening criteria not provided in context",
                )
            
            # Extract screening parameters
            sector = criteria.get("sector")
            industry = criteria.get("industry")
            market_cap = criteria.get("market_cap", "Large Cap")
            country = criteria.get("country", "United States")
            limit = criteria.get("limit", 20)
            min_volume = criteria.get("min_volume")
            earnings_days_ahead = criteria.get("earnings_days_ahead")
            
            # Use MarketDataService to search stocks
            logger.debug(f"Screening stocks: sector={sector}, industry={industry}, market_cap={market_cap}, country={country}")
            
            # Note: search_tickers accepts limit parameter, but we apply it after
            # to have more control and to report total_found vs filtered_count
            tickers = self.market_data_service.search_tickers(
                sector=sector,
                industry=industry,
                market_cap=market_cap,
                country=country,
                limit=None,  # Get all results first, then apply our limit
            )
            
            total_found = len(tickers) if tickers else 0
            
            if not tickers:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=True,
                    data={
                        "candidates": [],
                        "total_found": 0,
                        "filtered_count": 0,
                        "criteria": criteria,
                    },
                )
            
            # Apply min_volume filter
            if min_volume is not None:
                batch_size = 50
                liquid_symbols = []
                for i in range(0, len(tickers), batch_size):
                    batch = tickers[i:i + batch_size]
                    try:
                        quotes = await self.market_data_service.get_batch_quotes(batch)
                        for symbol, quote in quotes.items():
                            volume = quote.get('volume', 0)
                            if volume and volume >= min_volume:
                                liquid_symbols.append(symbol)
                    except Exception as e:
                        logger.warning(f"Failed to get batch quotes for batch {i}: {e}")
                        continue
                tickers = liquid_symbols
                logger.info(f"After min_volume filter ({min_volume}): {len(tickers)} symbols")

            # Apply earnings filter
            if earnings_days_ahead is not None and tickers:
                import pytz
                from datetime import datetime, timedelta
                EST = pytz.timezone("US/Eastern")
                try:
                    end_date = (datetime.now(EST) + timedelta(days=earnings_days_ahead)).strftime("%Y-%m-%d")
                    start_date = datetime.now(EST).strftime("%Y-%m-%d")
                    
                    earnings_data = await self.market_data_service._call_fmp_api(
                        "earnings-calendar",
                        params={"from": start_date, "to": end_date}
                    )
                    
                    if earnings_data and isinstance(earnings_data, list):
                        earnings_symbols = {item.get('symbol', '').upper() for item in earnings_data if item.get('symbol')}
                        tickers = [s for s in tickers if s in earnings_symbols]
                        logger.info(f"After earnings filter (next {earnings_days_ahead} days): {len(tickers)} symbols")
                except Exception as e:
                    logger.warning(f"Failed to filter by earnings: {e}")
            
            # Apply limit
            if limit and len(tickers) > limit:
                tickers = tickers[:limit]
            
            filtered_count = len(tickers)
            
            # Create candidate list with initial scores
            candidates = [
                {
                    "symbol": ticker,
                    "initial_score": 0.5,  # Default score, will be refined by ranking agent
                }
                for ticker in tickers
            ]
            
            logger.info(f"Stock screening found {len(candidates)} candidates")
            
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=True,
                data={
                    "candidates": candidates,
                    "total_found": total_found,
                    "filtered_count": filtered_count,
                    "criteria": criteria,
                },
            )
            
        except Exception as e:
            logger.error(f"StockScreeningAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=False,
                data={},
                error=str(e),
            )
