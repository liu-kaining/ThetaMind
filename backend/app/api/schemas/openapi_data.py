from typing import Optional
from pydantic import BaseModel, Field


class StockOverviewDTO(BaseModel):
    """Basic stock overview for reporting."""
    symbol: str
    current_price: float
    low_52w: float
    high_52w: float
    pe_ratio: Optional[float] = None
    analyst_target: Optional[float] = None


class FundamentalHardcoreDTO(BaseModel):
    """Advanced fundamental metrics."""
    fcf_yield: Optional[float] = Field(None, description="Free Cash Flow Yield TTM")
    roic: Optional[float] = Field(None, description="Return on Invested Capital TTM")
    gross_margin: Optional[float] = Field(None, description="Gross Profit Margin TTM")


class OptionsContextDTO(BaseModel):
    """Implied vs Historical Volatility context."""
    symbol: str
    implied_volatility: float = Field(..., description="Average or representative IV from current chain")
    historical_volatility: float = Field(..., description="Historical Volatility (usually 30d or 252d)")
    iv_hv_ratio: float = Field(..., description="Calculated IV/HV ratio")


class CompanyFundamentalsResponse(BaseModel):
    """Combined fundamental data for a company."""
    overview: StockOverviewDTO
    hardcore: FundamentalHardcoreDTO
