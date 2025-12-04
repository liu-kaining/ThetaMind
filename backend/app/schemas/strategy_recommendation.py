"""Pydantic schemas for strategy recommendation engine."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Outlook(str, Enum):
    """Market outlook for strategy selection."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    VOLATILE = "VOLATILE"


class RiskProfile(str, Enum):
    """Risk tolerance for strategy selection."""

    CONSERVATIVE = "CONSERVATIVE"  # High Probability
    AGGRESSIVE = "AGGRESSIVE"  # High Reward


class OptionType(str, Enum):
    """Option type."""

    CALL = "CALL"
    PUT = "PUT"


class OptionLeg(BaseModel):
    """Individual option leg in a strategy."""

    symbol: str = Field(..., description="Stock symbol")
    strike: float = Field(..., description="Strike price")
    ratio: int = Field(..., description="Position ratio (+1 for Buy, -1 for Sell)")
    type: OptionType = Field(..., description="Option type (CALL or PUT)")
    greeks: dict[str, float] = Field(
        default_factory=dict,
        description="Greeks: delta, gamma, theta, vega, rho",
    )
    bid: float = Field(..., description="Bid price")
    ask: float = Field(..., description="Ask price")
    mid_price: float = Field(..., description="Calculated mid price (bid + ask) / 2")
    expiration_date: str = Field(..., description="Expiration date (YYYY-MM-DD)")
    days_to_expiration: int = Field(..., description="Days to expiration (DTE)")

    def __init__(self, **data: Any) -> None:
        """Calculate mid_price if not provided."""
        if "mid_price" not in data and "bid" in data and "ask" in data:
            data["mid_price"] = (data["bid"] + data["ask"]) / 2.0
        super().__init__(**data)


class CalculatedStrategy(BaseModel):
    """Complete strategy recommendation with calculated metrics."""

    name: str = Field(..., description="Strategy name (e.g., 'High Theta Iron Condor')")
    description: str = Field(..., description="Strategy description")
    legs: list[OptionLeg] = Field(..., description="List of option legs")
    metrics: dict[str, Any] = Field(
        ...,
        description="Calculated metrics: max_profit, max_loss, risk_reward_ratio, pop, breakeven_points, net_greeks, theta_decay_per_day, liquidity_score",
    )

    class Config:
        """Pydantic config."""

        json_encoders = {
            float: lambda v: round(v, 4) if isinstance(v, float) else v,
        }


class StrategyRecommendationRequest(BaseModel):
    """Request model for strategy recommendations."""

    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)")
    outlook: Outlook = Field(..., description="Market outlook")
    risk_profile: RiskProfile = Field(
        default=RiskProfile.CONSERVATIVE, description="Risk tolerance"
    )
    capital: float = Field(
        default=10000.0, ge=1000.0, description="Available capital in USD"
    )
    expiration_date: str | None = Field(
        None, description="Preferred expiration date (YYYY-MM-DD). If None, engine selects optimal DTE."
    )

