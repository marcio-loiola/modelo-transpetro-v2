"""Async client helper to fetch environmental variables from the Ocean API."""

import os
from datetime import datetime
from typing import Optional

import httpx

OCEAN_API_URL = os.getenv("OCEAN_API_URL", "https://api.amentum.io/ocean")
OCEAN_API_KEY = os.getenv("OCEAN_API_KEY", "")


async def fetch_ocean_variable(
    lat: float,
    lon: float,
    dt: datetime,
    variable: str,
    depth: int = 0,
) -> Optional[float]:
    """Return a single variable value from the Ocean API for a specific point in time."""

    params = {
        "latitude": lat,
        "longitude": lon,
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "hour": dt.hour,
        "depth": depth,
        "variable": variable,
    }
    headers = {}
    if OCEAN_API_KEY:
        headers["Authorization"] = f"Bearer {OCEAN_API_KEY}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(OCEAN_API_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data.get("value")