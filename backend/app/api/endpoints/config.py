"""Public config/feature-flag endpoints (no auth)."""

import logging
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

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
    Reads from DB config if set, else from settings (env).
    """
    # Try DB first, fallback to settings
    anomaly_radar_db = await config_service.get("enable_anomaly_radar")
    daily_picks_db = await config_service.get("enable_daily_picks")
    
    def _parse_bool(value: str | None, default: bool) -> bool:
        if value is None:
            return default
        value_str = str(value).strip().lower()
        if value_str in ("true", "1", "yes", "on"):
            return True
        elif value_str in ("false", "0", "no", "off", ""):
            return False
        return default
    
    anomaly_radar = _parse_bool(anomaly_radar_db, settings.enable_anomaly_radar)
    daily_picks = _parse_bool(daily_picks_db, settings.enable_daily_picks)
    
    return FeaturesResponse(
        anomaly_radar_enabled=anomaly_radar,
        daily_picks_enabled=daily_picks,
    )
