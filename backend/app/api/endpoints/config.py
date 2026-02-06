"""Public config/feature-flag endpoints (no auth)."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/config", tags=["config"])


class FeaturesResponse(BaseModel):
    """Feature flags for frontend (controls UI visibility and API behavior)."""

    anomaly_radar_enabled: bool
    daily_picks_enabled: bool


@router.get("/features", response_model=FeaturesResponse)
async def get_features() -> FeaturesResponse:
    """
    Get feature flags. Public endpoint (no auth).
    Frontend uses this to show/hide 异动雷达 and 每日精选.
    """
    return FeaturesResponse(
        anomaly_radar_enabled=settings.enable_anomaly_radar,
        daily_picks_enabled=settings.enable_daily_picks,
    )
