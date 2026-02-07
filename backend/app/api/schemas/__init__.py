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

    model_config = {"protected_namespaces": ()}  # Fix Pydantic warning for "model_used" field

    id: str = Field(..., description="Report UUID")
    report_content: str = Field(..., description="Markdown report content")
    model_used: str = Field(..., description="AI model used")
    created_at: datetime = Field(..., description="Generation timestamp")
    metadata: dict[str, Any] | None = Field(
        None,
        description="Execution metadata (mode, agent results, execution time, etc.)",
    )
    symbol: str | None = Field(None, description="Underlying symbol from the task that produced this report")


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


class TaskResponse(BaseModel):
    """Task response model."""

    model_config = {"protected_namespaces": ()}  # Fix Pydantic warning for "model_used" field

    id: str = Field(..., description="Task UUID")
    task_type: str = Field(..., description="Task type (e.g., 'ai_report')")
    status: str = Field(..., description="Task status: PENDING, PROCESSING, SUCCESS, FAILED")
    result_ref: str | None = Field(None, description="Reference to result (e.g., AI report ID)")
    error_message: str | None = Field(None, description="Error message if task failed")
    metadata: dict[str, Any] | None = Field(None, description="Additional task metadata")
    execution_history: list[dict[str, Any]] | None = Field(None, description="Timeline of execution events")
    prompt_used: str | None = Field(None, description="Full prompt sent to AI")
    model_used: str | None = Field(None, description="AI model used")
    started_at: datetime | None = Field(None, description="When processing started")
    retry_count: int = Field(0, description="Number of retries")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task last update timestamp")
    completed_at: datetime | None = Field(None, description="Task completion timestamp")


class AnomalyResponse(BaseModel):
    """Anomaly detection response model."""
    
    model_config = {"protected_namespaces": ()}  # Fix Pydantic warning for "model_used" field

    id: str = Field(..., description="Anomaly UUID")
    symbol: str = Field(..., description="Stock symbol")
    anomaly_type: str = Field(..., description="Type of anomaly (e.g., 'volume_surge', 'iv_spike')")
    score: int = Field(..., description="Anomaly score (higher = more significant)")
    details: dict[str, Any] = Field(..., description="Anomaly details (volume, OI, IV, etc.)")
    ai_insight: str | None = Field(None, description="AI-generated insight (if available)")
    detected_at: datetime = Field(..., description="Detection timestamp")
    prompt_used: str | None = Field(None, description="Full prompt sent to AI")
    model_used: str | None = Field(None, description="AI model used")
    started_at: datetime | None = Field(None, description="When processing started")
    retry_count: int = Field(0, description="Number of retries")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task last update timestamp")
    completed_at: datetime | None = Field(None, description="Task completion timestamp")
