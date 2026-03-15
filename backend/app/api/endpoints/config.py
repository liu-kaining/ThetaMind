"""Public config endpoints (no auth). Reserved for future feature flags."""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])
