import asyncio
import time
from typing import Any, Dict

import httpx

from .config import settings


DEFAULT_ENV_PAYLOAD = {
    "temperature": 26.0,
    "salinity": 35.0,
    "density": 1025.0,
    "chlorophyll": 1.5,
    "wave_height": 1.2,
    "current_speed": 0.6,
    "zone": "tropical",
}


class OceanCache:
    def __init__(self):
        self._url = settings.OCEAN_API_URL
        self._key = settings.OCEAN_API_KEY
        self._ttl = settings.OCEAN_CACHE_TTL_SECONDS
        self._max_stale = settings.OCEAN_CACHE_MAX_STALE_SECONDS
        self._backoff = settings.OCEAN_CACHE_BACKOFF_SECONDS
        self._data: Dict[str, Any] = DEFAULT_ENV_PAYLOAD.copy()
        self._last_updated = 0.0
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._client = httpx.AsyncClient(timeout=10.0)

    async def _fetch_remote(self) -> Dict[str, Any]:
        if not self._url:
            return DEFAULT_ENV_PAYLOAD.copy()
        params = {"variable": "all"}
        headers = {}
        if self._key:
            headers["Authorization"] = f"Bearer {self._key}"
        response = await self._client.get(self._url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        return {
            "temperature": payload.get("temperature", DEFAULT_ENV_PAYLOAD["temperature"]),
            "salinity": payload.get("salinity", DEFAULT_ENV_PAYLOAD["salinity"]),
            "density": payload.get("density", DEFAULT_ENV_PAYLOAD["density"]),
            "chlorophyll": payload.get("chlorophyll", DEFAULT_ENV_PAYLOAD["chlorophyll"]),
            "wave_height": payload.get("wave_height", DEFAULT_ENV_PAYLOAD["wave_height"]),
            "current_speed": payload.get("current_speed", DEFAULT_ENV_PAYLOAD["current_speed"]),
            "zone": payload.get("zone", DEFAULT_ENV_PAYLOAD["zone"],),
        }

    async def refresh(self) -> None:
        async with self._lock:
            try:
                data = await self._fetch_remote()
            except Exception:
                # keep previous data on failure
                return
            self._data = data
            self._last_updated = time.time()

    async def get_data(self, force: bool = False) -> Dict[str, Any]:
        async with self._lock:
            stale = time.time() - self._last_updated > self._max_stale
            if force or stale or self._last_updated == 0:
                await self.refresh()
            return {
                "environment": self._data,
                "updated_at": self._last_updated,
            }

    async def _loop(self) -> None:
        try:
            while True:
                await self.refresh()
                await asyncio.sleep(self._ttl)
        except asyncio.CancelledError:
            raise

    def start(self) -> None:
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._client.aclose()


ocean_cache = OceanCache()
