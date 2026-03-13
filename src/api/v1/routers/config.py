"""Public config endpoint for frontend."""

from fastapi import APIRouter

router = APIRouter(tags=["config"])


@router.get("/config")
async def get_config() -> dict:
    """Return public config for frontend. No auth required."""
    return {}
