"""Strict Pydantic models for strategy data to replace dict[str, Any]."""

from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, Field, validator


class OptionLeg(BaseModel):
    """Option leg with strict typing and validation."""
    
    action: str = Field(..., pattern="^(buy|sell)$", description="Action: 'buy' or 'sell'")
    quantity: int = Field(..., gt=0, description="Number of contracts")
    strike: Decimal = Field(..., gt=0, description="Strike price")
    type: str = Field(..., pattern="^(call|put)$", description="Option type: 'call' or 'put'")
    premium: Decimal = Field(default=Decimal('0'), ge=0, description="Option premium")
    
    # Greeks (optional, but validated if provided)
    delta: Optional[Decimal] = Field(None, description="Delta Greek")
    gamma: Optional[Decimal] = Field(None, description="Gamma Greek")
    theta: Optional[Decimal] = Field(None, description="Theta Greek")
    vega: Optional[Decimal] = Field(None, description="Vega Greek")
    rho: Optional[Decimal] = Field(None, description="Rho Greek")
    
    # Additional fields
    implied_volatility: Optional[Decimal] = Field(None, alias="implied_vol", ge=0, description="Implied volatility")
    open_interest: Optional[int] = Field(None, ge=0, description="Open interest")
    expiration_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Expiration date (YYYY-MM-DD)")
    
    @validator('implied_volatility', pre=True)
    def validate_implied_vol(cls, v):
        """Handle both 'implied_volatility' and 'implied_vol' field names."""
        if v is None:
            return None
        return Decimal(str(v)) if v is not None else None
    
    class Config:
        populate_by_name = True  # Allow both field name and alias


class PortfolioGreeks(BaseModel):
    """Portfolio Greeks with strict typing and Decimal precision."""
    
    delta: Decimal = Field(default=Decimal('0'), description="Portfolio delta")
    gamma: Decimal = Field(default=Decimal('0'), description="Portfolio gamma")
    theta: Decimal = Field(default=Decimal('0'), description="Portfolio theta")
    vega: Decimal = Field(default=Decimal('0'), description="Portfolio vega")
    rho: Decimal = Field(default=Decimal('0'), description="Portfolio rho")


class StrategyMetrics(BaseModel):
    """Strategy metrics with strict typing."""
    
    max_profit: Decimal = Field(default=Decimal('0'), description="Maximum profit")
    max_loss: Decimal = Field(default=Decimal('0'), description="Maximum loss")
    breakeven_points: List[Decimal] = Field(default_factory=list, description="Breakeven points")
    net_cost: Optional[Decimal] = Field(None, description="Net cost of strategy")
    net_credit: Optional[Decimal] = Field(None, description="Net credit received")


class TradeExecution(BaseModel):
    """Trade execution details."""
    
    net_cost: Decimal = Field(default=Decimal('0'), description="Net cost")
    total_premium_paid: Optional[Decimal] = Field(None, description="Total premium paid")
    total_premium_received: Optional[Decimal] = Field(None, description="Total premium received")


class StrategySummary(BaseModel):
    """Strategy summary with strict validation - replaces dict[str, Any]."""
    
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    strategy_name: str = Field(..., min_length=1, description="Strategy name")
    spot_price: Decimal = Field(..., gt=0, description="Current spot price")
    expiration_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Expiration date (YYYY-MM-DD)")
    
    legs: List[OptionLeg] = Field(..., min_items=1, description="Strategy legs")
    portfolio_greeks: PortfolioGreeks = Field(default_factory=PortfolioGreeks, description="Portfolio Greeks")
    strategy_metrics: StrategyMetrics = Field(default_factory=StrategyMetrics, description="Strategy metrics")
    trade_execution: TradeExecution = Field(default_factory=TradeExecution, description="Trade execution details")
    
    # Optional fields
    historical_prices: Optional[List[dict[str, Any]]] = Field(None, description="Historical price data")
    option_chain: Optional[dict[str, Any]] = Field(None, description="Full option chain data")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('legs')
    def validate_legs(cls, v):
        """Ensure at least one leg exists."""
        if not v or len(v) == 0:
            raise ValueError("Strategy must have at least one leg")
        return v
    
    class Config:
        # Allow extra fields for backward compatibility, but validate known fields strictly
        extra = "allow"
        json_encoders = {
            Decimal: lambda v: float(v)  # Convert Decimal to float for JSON serialization
        }
