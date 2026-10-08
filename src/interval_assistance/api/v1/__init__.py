"""Version 1 routes. Phase 1 exposes health/status only."""

from fastapi import APIRouter

from interval_assistance.api.v1 import health

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
