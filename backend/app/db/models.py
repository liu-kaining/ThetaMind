"""Database models for ThetaMind."""

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """User model with Google OAuth and Pro subscription support."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    google_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_pro: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "monthly" or "yearly"
    plan_expiry_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    daily_ai_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_image_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_quota_reset_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Track last date when quota was reset (UTC date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    strategies: Mapped[list["Strategy"]] = relationship("Strategy", back_populates="user")
    ai_reports: Mapped[list["AIReport"]] = relationship("AIReport", back_populates="user")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="user", cascade="all, delete-orphan")


class Strategy(Base):
    """Option strategy model storing multi-leg strategies as JSONB."""

    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legs_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="strategies")


class AIReport(Base):
    """AI-generated strategy analysis reports."""

    __tablename__ = "ai_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    report_content: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="ai_reports")


class PaymentEvent(Base):
    """Payment events from Lemon Squeezy webhooks (Audit Trail)."""

    __tablename__ = "payment_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lemon_squeezy_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, unique=True
    )
    event_name: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class DailyPick(Base):
    """Daily AI-generated strategy picks (Cold Start solution)."""

    __tablename__ = "daily_picks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    content_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class SystemConfig(Base):
    """System configuration table for dynamic prompt and settings management."""

    __tablename__ = "system_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class GeneratedImage(Base):
    """AI-generated strategy chart images."""

    __tablename__ = "generated_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True
    )
    base64_data: Mapped[str] = mapped_column(Text, nullable=True)  # Base64-encoded image data (legacy, kept for backward compatibility)
    r2_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, index=True
    )  # Cloudflare R2 URL (preferred storage method)
    strategy_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )  # Hash of strategy (symbol + expiration + legs) for caching
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    task: Mapped["Task"] = relationship("Task", foreign_keys=[task_id])

    # Indexes
    __table_args__ = (
        Index("ix_generated_images_user_created", "user_id", "created_at"),
        Index("ix_generated_images_user_strategy_hash", "user_id", "strategy_hash"),
    )


class StockSymbol(Base):
    """Stock symbol repository for fast search and autocomplete."""

    __tablename__ = "stock_symbols"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    market: Mapped[str] = mapped_column(String(10), default="US", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Indexes for fast search
    __table_args__ = (
        Index("ix_stock_symbols_name", "name"),
        Index("ix_stock_symbols_market_active", "market", "is_active"),
    )


class Task(Base):
    """Background task tracking model."""

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", index=True
    )  # PENDING, PROCESSING, SUCCESS, FAILED
    result_ref: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Reference to result (e.g., AI report ID)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Execution details
    execution_history: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)  # Timeline of execution events
    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)  # Full prompt sent to AI
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)  # AI model used
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # When processing started
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Number of retries
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="tasks")

    # Indexes
    __table_args__ = (
        Index("ix_tasks_user_status", "user_id", "status"),
        Index("ix_tasks_created_at", "created_at"),
    )

