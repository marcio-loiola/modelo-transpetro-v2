# =============================================================================
# API ROUTES - INTEGRATIONS
# =============================================================================
"""
Endpoints for external service integrations and health checks.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
import logging

from ..integration_service import get_orchestrator
from ..ocean_cache import ocean_cache
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get(
    "/status",
    summary="Get integration status",
    description="Check status of all external service integrations"
)
async def get_integrations_status() -> Dict[str, Any]:
    """
    Get status of all configured external integrations.
    
    Returns:
    - Service orchestrator status
    - Ocean cache status
    - Individual service configurations
    """
    orchestrator = get_orchestrator()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "orchestrator": orchestrator.get_status(),
        "ocean_cache": ocean_cache.get_status(),
        "configured_services": {
            "weather_api": bool(settings.WEATHER_API_URL),
            "vessel_api": bool(settings.VESSEL_API_URL),
            "fuel_api": bool(settings.FUEL_API_URL),
            "ocean_api": bool(settings.OCEAN_API_URL),
            "maintenance_api": bool(settings.MAINTENANCE_API_URL),
            "emissions_api": bool(settings.EMISSIONS_API_URL),
        }
    }


@router.get(
    "/weather",
    summary="Get weather data",
    description="Fetch current weather/ocean conditions for a location"
)
async def get_weather(
    latitude: float = -23.0,
    longitude: float = -43.0
) -> Dict[str, Any]:
    """
    Get weather/ocean data for a given location.
    
    Args:
    - latitude: Location latitude (-90 to 90)
    - longitude: Location longitude (-180 to 180)
    """
    orchestrator = get_orchestrator()
    
    data = await orchestrator.get_weather_data(latitude, longitude)
    
    if data is None:
        return {
            "status": "unavailable",
            "message": "Weather API not configured",
            "location": {"latitude": latitude, "longitude": longitude}
        }
    
    return {
        "status": "success",
        "location": {"latitude": latitude, "longitude": longitude},
        "data": data
    }


@router.get(
    "/fuel-prices",
    summary="Get fuel prices",
    description="Fetch current bunker fuel prices"
)
async def get_fuel_prices(port: str = None) -> Dict[str, Any]:
    """
    Get current fuel prices.
    
    Args:
    - port: Optional port code to get local prices
    """
    orchestrator = get_orchestrator()
    
    data = await orchestrator.get_fuel_prices(port)
    
    return {
        "status": "success",
        "port": port or "global",
        "data": data
    }


@router.post(
    "/cache/refresh",
    summary="Refresh ocean cache",
    description="Manually trigger ocean data cache refresh"
)
async def refresh_ocean_cache() -> Dict[str, Any]:
    """
    Manually refresh the ocean data cache.
    """
    await ocean_cache.refresh()
    
    return {
        "status": "success",
        "message": "Cache refresh triggered",
        "cache_status": ocean_cache.get_status()
    }
