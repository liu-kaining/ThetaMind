"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service health status")
    environment: str = Field(..., description="Current environment")


class RootResponse(BaseModel):
    """Root endpoint response model."""

    message: str = Field(..., description="API message")
    version: str = Field(..., description="API version")
    docs: str = Field(..., description="API documentation path")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str = Field(..., description="Error message")
    code: str | None = Field(None, description="Error code")
    retry_after: int | None = Field(None, description="Retry after seconds")


class OptionChainResponse(BaseModel):
    """Option chain response model."""

    symbol: str = Field(..., description="Stock symbol")
    expiration_date: str = Field(..., description="Expiration date (YYYY-MM-DD)")
    calls: list[dict[str, Any]] = Field(default_factory=list, description="Call options")
    puts: list[dict[str, Any]] = Field(default_factory=list, description="Put options")
    spot_price: float | None = Field(None, description="Current spot price")
    source: str | None = Field(None, alias="_source", description="Data source (cache/api)")


class StrategyRequest(BaseModel):
    """Strategy creation request model."""

    name: str = Field(..., description="Strategy name")
    legs_json: dict[str, Any] = Field(..., description="Strategy legs configuration")


class StrategyResponse(BaseModel):
    """Strategy response model."""

    id: str = Field(..., description="Strategy UUID")
    name: str = Field(..., description="Strategy name")
    legs_json: dict[str, Any] = Field(..., description="Strategy legs")
    created_at: datetime = Field(..., description="Creation timestamp")


class AIReportResponse(BaseModel):
    """AI report response model."""

    id: str = Field(..., description="Report UUID")
    report_content: str = Field(..., description="Markdown report content")
    model_used: str = Field(..., description="AI model used")
    created_at: datetime = Field(..., description="Generation timestamp")


class DailyPickResponse(BaseModel):
    """Daily pick response model."""

    date: str = Field(..., description="Pick date (YYYY-MM-DD)")
    content_json: list[dict[str, Any]] = Field(..., description="List of strategy picks")
    created_at: datetime = Field(..., description="Generation timestamp")


class SymbolSearchResponse(BaseModel):
    """Symbol search response model."""

    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)")
    name: str = Field(..., description="Company name (e.g., Apple Inc.)")
    market: str = Field(..., description="Market (e.g., US)")
