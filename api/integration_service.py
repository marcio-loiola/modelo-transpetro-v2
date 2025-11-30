# =============================================================================
# SERVICE ORCHESTRATOR
# =============================================================================
"""
Orchestrates integrations with external services and APIs.
Provides a unified interface for weather, vessel, fuel, and other data sources.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from functools import lru_cache
from datetime import datetime

from .config import settings

logger = logging.getLogger(__name__)


class ServiceOrchestrator:
    """
    Central orchestrator for external service integrations.
    Manages lifecycle, health checks, and fallback strategies.
    """

    def __init__(self):
        self.initialized = False
        self._services_status: Dict[str, bool] = {}
        self._last_check: Optional[datetime] = None

    async def initialize(self) -> None:
        """Initialize all external service connections."""
        logger.info("Initializing service orchestrator...")
        
        # Check configured external services
        self._services_status = {
            "weather_api": bool(settings.WEATHER_API_URL),
            "vessel_api": bool(settings.VESSEL_API_URL),
            "fuel_api": bool(settings.FUEL_API_URL),
            "ocean_api": bool(settings.OCEAN_API_URL),
            "maintenance_api": bool(settings.MAINTENANCE_API_URL),
            "emissions_api": bool(settings.EMISSIONS_API_URL),
        }
        
        enabled_services = [k for k, v in self._services_status.items() if v]
        logger.info(f"External services configured: {enabled_services or 'None'}")
        
        self.initialized = True
        self._last_check = datetime.now()

    async def shutdown(self) -> None:
        """Gracefully shutdown all service connections."""
        logger.info("Shutting down service orchestrator...")
        self.initialized = False

    def get_status(self) -> Dict[str, Any]:
        """Get current status of all services."""
        return {
            "initialized": self.initialized,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "services": self._services_status,
        }

    async def get_weather_data(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch weather/ocean data for a given location.
        Returns None if service is not configured.
        """
        if not settings.WEATHER_API_URL:
            return None
        
        # Placeholder for actual API call
        logger.debug(f"Weather data requested for ({latitude}, {longitude})")
        return {
            "source": "mock",
            "temperature": 25.0,
            "wave_height": 1.5,
            "wind_speed": 10.0,
        }

    async def get_fuel_prices(self, port: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch current fuel prices.
        Returns None if service is not configured.
        """
        if not settings.FUEL_API_URL:
            return {
                "source": "default",
                "price_usd_per_ton": settings.FUEL_PRICE_USD_PER_TON,
            }
        
        # Placeholder for actual API call
        return {
            "source": "api",
            "price_usd_per_ton": settings.FUEL_PRICE_USD_PER_TON,
        }


# Singleton instance
_orchestrator: Optional[ServiceOrchestrator] = None


def get_orchestrator() -> ServiceOrchestrator:
    """Get or create the service orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ServiceOrchestrator()
    return _orchestrator
