# =============================================================================
# API ROUTES - OPERATIONAL
# =============================================================================
"""
Operational endpoints for system management and monitoring.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime
import logging
import sys
import os

from ..config import settings
from ..services import get_biofouling_service, get_data_service
from ..ocean_cache import ocean_cache

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Operational"])


@router.get(
    "/status",
    summary="System status",
    description="Get detailed system status and configuration"
)
async def get_system_status() -> Dict[str, Any]:
    """
    Get comprehensive system status.
    
    Includes:
    - API configuration
    - Model status
    - Data availability
    - Cache status
    - System info
    """
    biofouling_service = get_biofouling_service()
    data_service = get_data_service()
    
    # Check data availability
    try:
        events = data_service.load_events()
        events_count = len(events) if not events.empty else 0
    except:
        events_count = 0
    
    try:
        consumption = data_service.load_consumption()
        consumption_count = len(consumption) if not consumption.empty else 0
    except:
        consumption_count = 0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "api": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
            "host": settings.HOST,
            "port": settings.PORT,
        },
        "model": {
            "loaded": biofouling_service.model_loaded,
            "file": settings.MODEL_FILE,
            "encoder": settings.ENCODER_FILE,
        },
        "data": {
            "events_loaded": events_count,
            "consumption_loaded": consumption_count,
            "data_dir": str(settings.DATA_RAW_DIR),
        },
        "cache": ocean_cache.get_status(),
        "system": {
            "python_version": sys.version,
            "platform": sys.platform,
            "pid": os.getpid(),
        }
    }


@router.get(
    "/config",
    summary="Get configuration",
    description="Get current API configuration (non-sensitive)"
)
async def get_config() -> Dict[str, Any]:
    """
    Get current configuration settings (excluding sensitive data).
    """
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "host": settings.HOST,
        "port": settings.PORT,
        "cors_origins": settings.CORS_ORIGINS,
        "model_file": settings.MODEL_FILE,
        "data_files": {
            "events": settings.FILE_EVENTS,
            "consumption": settings.FILE_CONSUMPTION,
        },
        "biofouling_params": {
            "idle_speed_threshold": settings.IDLE_SPEED_THRESHOLD,
            "admiralty_scale_factor": settings.ADMIRALTY_SCALE_FACTOR,
            "fuel_price_usd_per_ton": settings.FUEL_PRICE_USD_PER_TON,
            "co2_ton_per_fuel_ton": settings.CO2_TON_PER_FUEL_TON,
        },
        "rate_limiting": {
            "requests": settings.RATE_LIMIT_REQUESTS,
            "period_seconds": settings.RATE_LIMIT_PERIOD,
        }
    }


@router.get(
    "/metrics",
    summary="Get metrics",
    description="Get basic operational metrics"
)
async def get_metrics() -> Dict[str, Any]:
    """
    Get operational metrics.
    
    Note: For production, consider using Prometheus/OpenTelemetry.
    """
    biofouling_service = get_biofouling_service()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "model_loaded": biofouling_service.model_loaded,
        "cache_entries": ocean_cache.get_status().get("entries", 0),
        "uptime_info": "Check /status for system details",
    }


@router.get(
    "/ready",
    summary="Readiness check",
    description="Kubernetes-style readiness probe"
)
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness probe for container orchestration.
    
    Returns 200 if the service is ready to receive traffic.
    """
    service = get_biofouling_service()
    
    if not service.model_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded, service not ready"
        )
    
    return {
        "status": "ready",
        "timestamp": datetime.now().isoformat()
    }


@router.get(
    "/live",
    summary="Liveness check",
    description="Kubernetes-style liveness probe"
)
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness probe for container orchestration.
    
    Returns 200 if the service is alive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }
