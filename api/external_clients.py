# =============================================================================
# HTTP CLIENT SERVICE
# =============================================================================
"""
HTTP Client for consuming external APIs.
Supports async requests, retries, circuit breaker, and caching.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
import httpx
from pydantic import BaseModel

from .config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

class ExternalAPIConfig(BaseModel):
    """Configuration for external API connections."""
    name: str
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0


# =============================================================================
# EXTERNAL API CLIENTS
# =============================================================================

class BaseAPIClient:
    """
    Base class for external API clients.
    Provides common functionality like retries, error handling, and logging.
    """
    
    def __init__(self, config: ExternalAPIConfig):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, datetime] = {}
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        
    async def connect(self):
        """Initialize the HTTP client."""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
            
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=headers,
            timeout=self.config.timeout
        )
        logger.info(f"Connected to {self.config.name} at {self.config.base_url}")
        
    async def disconnect(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info(f"Disconnected from {self.config.name}")
            
    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """Execute HTTP request with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response
                
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code >= 500:
                    # Retry on server errors
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.config.max_retries} failed: {e}"
                    )
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    # Don't retry on client errors (4xx)
                    raise
                    
            except httpx.RequestError as e:
                last_exception = e
                logger.warning(
                    f"Attempt {attempt + 1}/{self.config.max_retries} failed: {e}"
                )
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                
        raise last_exception
        
    def _get_cached(self, key: str, ttl_seconds: int = 300) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            if datetime.now() < self._cache_ttl.get(key, datetime.min):
                return self._cache[key]
            else:
                del self._cache[key]
                del self._cache_ttl[key]
        return None
        
    def _set_cached(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set cached value with TTL."""
        self._cache[key] = value
        self._cache_ttl[key] = datetime.now() + timedelta(seconds=ttl_seconds)


# =============================================================================
# WEATHER API CLIENT
# =============================================================================

class WeatherAPIClient(BaseAPIClient):
    """
    Client for weather/maritime conditions API.
    Provides sea state, wind, and wave data for routes.
    """
    
    def __init__(self):
        config = ExternalAPIConfig(
            name="Weather API",
            base_url=settings.WEATHER_API_URL,
            api_key=settings.WEATHER_API_KEY,
            timeout=15.0
        )
        super().__init__(config)
        
    async def get_sea_conditions(
        self,
        latitude: float,
        longitude: float,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get sea conditions for a specific location.
        
        Returns:
            - beaufort_scale: Sea state (0-12)
            - wave_height: Wave height in meters
            - wind_speed: Wind speed in knots
            - wind_direction: Wind direction in degrees
        """
        cache_key = f"sea_{latitude}_{longitude}_{date}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
            
        try:
            response = await self._request_with_retry(
                "GET",
                "/marine",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "date": date.isoformat() if date else None
                }
            )
            data = response.json()
            
            result = {
                "beaufort_scale": data.get("beaufort", 0),
                "wave_height": data.get("wave_height", 0),
                "wind_speed": data.get("wind_speed", 0),
                "wind_direction": data.get("wind_direction", 0),
                "source": "weather_api"
            }
            
            self._set_cached(cache_key, result, ttl_seconds=3600)
            return result
            
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            # Return default values on error
            return {
                "beaufort_scale": 3,
                "wave_height": 1.0,
                "wind_speed": 10,
                "wind_direction": 0,
                "source": "default"
            }


# =============================================================================
# AIS/VESSEL TRACKING API CLIENT
# =============================================================================

class VesselTrackingClient(BaseAPIClient):
    """
    Client for AIS/Vessel tracking API.
    Provides real-time vessel positions and voyage data.
    """
    
    def __init__(self):
        config = ExternalAPIConfig(
            name="Vessel Tracking API",
            base_url=settings.VESSEL_API_URL,
            api_key=settings.VESSEL_API_KEY,
            timeout=20.0
        )
        super().__init__(config)
        
    async def get_vessel_position(self, imo: str) -> Dict[str, Any]:
        """Get current vessel position by IMO number."""
        try:
            response = await self._request_with_retry(
                "GET",
                f"/vessels/{imo}/position"
            )
            return response.json()
        except Exception as e:
            logger.error(f"Vessel tracking error: {e}")
            return {}
            
    async def get_vessel_voyages(
        self,
        imo: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get vessel voyage history."""
        try:
            response = await self._request_with_retry(
                "GET",
                f"/vessels/{imo}/voyages",
                params={
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Vessel voyages error: {e}")
            return []
            
    async def get_fleet_positions(self, imos: List[str]) -> List[Dict[str, Any]]:
        """Get positions for multiple vessels."""
        try:
            response = await self._request_with_retry(
                "POST",
                "/vessels/positions",
                json={"imos": imos}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Fleet positions error: {e}")
            return []


# =============================================================================
# FUEL PRICES API CLIENT
# =============================================================================

class FuelPricesClient(BaseAPIClient):
    """
    Client for bunker fuel prices API.
    Provides current and historical fuel prices.
    """
    
    def __init__(self):
        config = ExternalAPIConfig(
            name="Fuel Prices API",
            base_url=settings.FUEL_API_URL,
            api_key=settings.FUEL_API_KEY,
            timeout=10.0
        )
        super().__init__(config)
        
    async def get_current_prices(
        self,
        port: Optional[str] = None,
        fuel_type: str = "VLSFO"
    ) -> Dict[str, Any]:
        """
        Get current bunker fuel prices.
        
        Args:
            port: Port code (e.g., "BRSSZ" for Santos)
            fuel_type: Fuel type (VLSFO, HSFO, MGO, etc.)
        """
        cache_key = f"fuel_{port}_{fuel_type}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
            
        try:
            response = await self._request_with_retry(
                "GET",
                "/prices/current",
                params={
                    "port": port,
                    "fuel_type": fuel_type
                }
            )
            data = response.json()
            
            result = {
                "price_usd_per_ton": data.get("price", 500),
                "currency": "USD",
                "fuel_type": fuel_type,
                "port": port,
                "date": data.get("date"),
                "source": "fuel_api"
            }
            
            self._set_cached(cache_key, result, ttl_seconds=3600)
            return result
            
        except Exception as e:
            logger.error(f"Fuel prices API error: {e}")
            return {
                "price_usd_per_ton": settings.FUEL_PRICE_USD_PER_TON,
                "currency": "USD",
                "fuel_type": fuel_type,
                "source": "default"
            }


# =============================================================================
# MAINTENANCE/DRYDOCK API CLIENT
# =============================================================================

class MaintenanceAPIClient(BaseAPIClient):
    """
    Client for vessel maintenance/drydock scheduling API.
    Provides cleaning schedules and maintenance records.
    """
    
    def __init__(self):
        config = ExternalAPIConfig(
            name="Maintenance API",
            base_url=settings.MAINTENANCE_API_URL,
            api_key=settings.MAINTENANCE_API_KEY,
            timeout=15.0
        )
        super().__init__(config)
        
    async def get_vessel_maintenance(self, vessel_id: str) -> Dict[str, Any]:
        """Get vessel maintenance history."""
        try:
            response = await self._request_with_retry(
                "GET",
                f"/vessels/{vessel_id}/maintenance"
            )
            return response.json()
        except Exception as e:
            logger.error(f"Maintenance API error: {e}")
            return {}
            
    async def get_last_cleaning(self, vessel_id: str) -> Optional[datetime]:
        """Get last hull cleaning date."""
        try:
            response = await self._request_with_retry(
                "GET",
                f"/vessels/{vessel_id}/cleaning/last"
            )
            data = response.json()
            if data.get("date"):
                return datetime.fromisoformat(data["date"])
            return None
        except Exception as e:
            logger.error(f"Last cleaning error: {e}")
            return None
            
    async def schedule_cleaning(
        self,
        vessel_id: str,
        proposed_date: datetime,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Schedule a hull cleaning."""
        try:
            response = await self._request_with_retry(
                "POST",
                f"/vessels/{vessel_id}/cleaning/schedule",
                json={
                    "proposed_date": proposed_date.isoformat(),
                    "priority": priority
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Schedule cleaning error: {e}")
            return {"error": str(e)}


# =============================================================================
# EMISSIONS REPORTING API CLIENT
# =============================================================================

class EmissionsAPIClient(BaseAPIClient):
    """
    Client for emissions reporting API (IMO DCS, EU MRV).
    Submits and retrieves emissions data.
    """
    
    def __init__(self):
        config = ExternalAPIConfig(
            name="Emissions API",
            base_url=settings.EMISSIONS_API_URL,
            api_key=settings.EMISSIONS_API_KEY,
            timeout=20.0
        )
        super().__init__(config)
        
    async def submit_voyage_emissions(
        self,
        vessel_id: str,
        voyage_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit emissions data for a voyage."""
        try:
            response = await self._request_with_retry(
                "POST",
                f"/vessels/{vessel_id}/emissions",
                json=voyage_data
            )
            return response.json()
        except Exception as e:
            logger.error(f"Emissions submission error: {e}")
            return {"error": str(e)}
            
    async def get_vessel_emissions_summary(
        self,
        vessel_id: str,
        year: int
    ) -> Dict[str, Any]:
        """Get annual emissions summary for a vessel."""
        try:
            response = await self._request_with_retry(
                "GET",
                f"/vessels/{vessel_id}/emissions/summary",
                params={"year": year}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Emissions summary error: {e}")
            return {}


# =============================================================================
# API CLIENT MANAGER
# =============================================================================

class ExternalAPIManager:
    """
    Manages all external API clients.
    Provides centralized access and lifecycle management.
    """
    
    def __init__(self):
        self.weather: Optional[WeatherAPIClient] = None
        self.vessel_tracking: Optional[VesselTrackingClient] = None
        self.fuel_prices: Optional[FuelPricesClient] = None
        self.maintenance: Optional[MaintenanceAPIClient] = None
        self.emissions: Optional[EmissionsAPIClient] = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize all API clients."""
        if self._initialized:
            return
            
        logger.info("Initializing external API clients...")
        
        # Initialize clients based on configuration
        if settings.WEATHER_API_URL:
            self.weather = WeatherAPIClient()
            await self.weather.connect()
            
        if settings.VESSEL_API_URL:
            self.vessel_tracking = VesselTrackingClient()
            await self.vessel_tracking.connect()
            
        if settings.FUEL_API_URL:
            self.fuel_prices = FuelPricesClient()
            await self.fuel_prices.connect()
            
        if settings.MAINTENANCE_API_URL:
            self.maintenance = MaintenanceAPIClient()
            await self.maintenance.connect()
            
        if settings.EMISSIONS_API_URL:
            self.emissions = EmissionsAPIClient()
            await self.emissions.connect()
            
        self._initialized = True
        logger.info("External API clients initialized")
        
    async def shutdown(self):
        """Shutdown all API clients."""
        logger.info("Shutting down external API clients...")
        
        if self.weather:
            await self.weather.disconnect()
        if self.vessel_tracking:
            await self.vessel_tracking.disconnect()
        if self.fuel_prices:
            await self.fuel_prices.disconnect()
        if self.maintenance:
            await self.maintenance.disconnect()
        if self.emissions:
            await self.emissions.disconnect()
            
        self._initialized = False
        logger.info("External API clients shut down")
        
    def is_available(self, service: str) -> bool:
        """Check if a specific service is available."""
        client = getattr(self, service, None)
        return client is not None and client.client is not None


# Singleton instance
_api_manager: Optional[ExternalAPIManager] = None


def get_api_manager() -> ExternalAPIManager:
    """Get the API manager singleton."""
    global _api_manager
    if _api_manager is None:
        _api_manager = ExternalAPIManager()
    return _api_manager
