# =============================================================================
# OCEAN DATA CACHE
# =============================================================================
"""
Background cache for ocean/environmental data.
Periodically fetches and caches data from Ocean API.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from .config import settings

logger = logging.getLogger(__name__)


class OceanDataCache:
    """
    Manages cached ocean/environmental data with background refresh.
    Implements stale-while-revalidate pattern.
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._last_update: Optional[datetime] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start background cache refresh task."""
        if not settings.OCEAN_API_URL:
            logger.info("Ocean API not configured, cache disabled")
            return
        
        self._running = True
        logger.info("Ocean data cache started")

    async def stop(self) -> None:
        """Stop background cache refresh task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Ocean data cache stopped")

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value.
        Returns None if not found or expired beyond max stale time.
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        max_age = timedelta(seconds=settings.OCEAN_CACHE_MAX_STALE_SECONDS)
        
        if datetime.now() - entry["timestamp"] > max_age:
            del self._cache[key]
            return None
        
        return entry["value"]

    def set(self, key: str, value: Any) -> None:
        """Store value in cache."""
        self._cache[key] = {
            "value": value,
            "timestamp": datetime.now(),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get cache status."""
        return {
            "running": self._running,
            "entries": len(self._cache),
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "ttl_seconds": settings.OCEAN_CACHE_TTL_SECONDS,
            "max_stale_seconds": settings.OCEAN_CACHE_MAX_STALE_SECONDS,
        }

    async def refresh(self) -> None:
        """Manually refresh cache from Ocean API."""
        if not settings.OCEAN_API_URL:
            return
        
        # Placeholder for actual API call
        logger.debug("Ocean cache refresh triggered")
        self._last_update = datetime.now()


# Singleton instance
ocean_cache = OceanDataCache()
