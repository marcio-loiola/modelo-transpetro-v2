# =============================================================================
# INTEGRATION ROUTES
# =============================================================================
"""
API routes for external service integrations.
Provides endpoints for:
- Enhanced predictions with external data
- Fleet optimization reports
- Emissions reporting
- Maintenance scheduling
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from ..integration_service import get_orchestrator
from ..external_clients import get_api_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["Integrations"])


# =============================================================================
# SCHEMAS
# =============================================================================

class EnhancedPredictionRequest(BaseModel):
    """Request for enhanced prediction with external data."""
    vessel_id: str
    speed: float = Field(..., ge=0, description="Vessel speed in knots")
    displacement: float = Field(..., ge=0, description="Displacement in tons")
    draft: float = Field(..., ge=0, description="Mid draft in meters")
    days_since_cleaning: float = Field(..., ge=0)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    port: Optional[str] = None


class EnhancedPredictionResponse(BaseModel):
    """Response with enhanced prediction data."""
    predicted_consumption: float
    biofouling_index: float
    fuel_cost_usd: float
    co2_emissions_tons: float
    sea_state_adjustment: Optional[float] = None
    beaufort_scale: Optional[int] = None
    enriched_data: dict = {}
    data_sources: List[str] = []


class VoyageEmissionsRequest(BaseModel):
    """Request to submit voyage emissions."""
    voyage_id: str
    departure_port: str
    arrival_port: str
    departure_date: datetime
    arrival_date: datetime
    distance_nm: float
    fuel_type: str = "VLSFO"
    fuel_consumed_tons: float
    cargo_carried_tons: Optional[float] = None
    transport_work: Optional[float] = None


class CleaningRecommendationResponse(BaseModel):
    """Cleaning recommendation response."""
    vessel_id: str
    biofouling_index: float
    cleaning_urgency: str
    recommended_action: Optional[str]
    estimated_savings: float
    next_available_slot: Optional[datetime] = None
    last_cleaning_date: Optional[str] = None
    days_since_cleaning: Optional[int] = None


class FleetOptimizationRequest(BaseModel):
    """Request for fleet optimization report."""
    vessel_ids: List[str]


class ExternalServiceStatus(BaseModel):
    """Status of external services."""
    service: str
    available: bool
    last_check: datetime


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/health", summary="Check integration services health")
async def check_integrations_health():
    """
    Check the health status of all external service integrations.
    
    Returns:
        Status of each configured external API
    """
    try:
        orchestrator = get_orchestrator()
        if orchestrator._initialized:
            return orchestrator.get_health_status()
        else:
            # Return basic status if not initialized
            return {
                "status": "uninitialized",
                "message": "Service orchestrator not initialized",
                "services": {
                    "external_apis": {
                        "weather": False,
                        "vessel_tracking": False,
                        "fuel_prices": False,
                        "maintenance": False,
                        "emissions": False
                    }
                }
            }
    except Exception as e:
        logger.error(f"Error getting integrations health: {e}")
        return {
            "status": "error",
            "message": str(e),
            "services": {
                "external_apis": {}
            }
        }


@router.post(
    "/predictions/enhanced",
    response_model=EnhancedPredictionResponse,
    summary="Get enhanced prediction with external data"
)
async def get_enhanced_prediction(request: EnhancedPredictionRequest):
    """
    Get a biofouling prediction enhanced with external data sources.
    
    This endpoint combines:
    - ML model prediction
    - Real-time weather/sea conditions (if configured)
    - Current fuel prices (if configured)
    - Vessel tracking data (if configured)
    - Maintenance history (if configured)
    
    Args:
        request: Prediction request with vessel and voyage parameters
        
    Returns:
        Enhanced prediction with data from multiple sources
    """
    orchestrator = get_orchestrator()
    
    if not orchestrator._initialized:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized"
        )
        
    try:
        result = await orchestrator.integrated_service.get_enhanced_prediction(
            vessel_id=request.vessel_id,
            prediction_request=request.model_dump()
        )
        return result
    except Exception as e:
        logger.error(f"Enhanced prediction error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction error: {str(e)}"
        )


@router.post(
    "/fleet/optimization",
    summary="Generate fleet optimization report"
)
async def generate_fleet_optimization_report(request: FleetOptimizationRequest):
    """
    Generate a fleet-wide optimization report.
    
    Analyzes all vessels and provides:
    - Biofouling status for each vessel
    - Recommended cleaning schedule
    - Cost optimization opportunities
    - Emissions reduction potential
    
    Args:
        request: List of vessel IDs to analyze
        
    Returns:
        Comprehensive fleet optimization report
    """
    orchestrator = get_orchestrator()
    
    if not orchestrator._initialized:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized"
        )
        
    try:
        result = await orchestrator.integrated_service.get_fleet_optimization_report(
            vessel_ids=request.vessel_ids
        )
        return result
    except Exception as e:
        logger.error(f"Fleet optimization error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Report generation error: {str(e)}"
        )


@router.post(
    "/vessels/{vessel_id}/emissions",
    summary="Submit voyage emissions"
)
async def submit_voyage_emissions(
    vessel_id: str,
    request: VoyageEmissionsRequest
):
    """
    Submit voyage emissions to regulatory reporting API.
    
    Automatically calculates CO2 emissions based on fuel consumption
    and submits to IMO DCS / EU MRV reporting system.
    
    Args:
        vessel_id: IMO number or vessel identifier
        request: Voyage emissions data
        
    Returns:
        Submission confirmation and calculated emissions
    """
    orchestrator = get_orchestrator()
    
    if not orchestrator._initialized:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized"
        )
        
    api_manager = get_api_manager()
    if not api_manager.is_available("emissions"):
        raise HTTPException(
            status_code=503,
            detail="Emissions API not configured"
        )
        
    try:
        result = await orchestrator.integrated_service.submit_voyage_emissions(
            vessel_id=vessel_id,
            voyage_data=request.model_dump()
        )
        return result
    except Exception as e:
        logger.error(f"Emissions submission error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Submission error: {str(e)}"
        )


@router.get(
    "/vessels/{vessel_id}/cleaning-recommendation",
    response_model=CleaningRecommendationResponse,
    summary="Get cleaning recommendation"
)
async def get_cleaning_recommendation(
    vessel_id: str,
    current_biofouling_index: float = Query(..., ge=0, le=1)
):
    """
    Get cleaning recommendation for a vessel.
    
    Considers:
    - Current biofouling index
    - Time since last cleaning
    - Upcoming voyages
    - Available drydock slots
    
    Args:
        vessel_id: IMO number or vessel identifier
        current_biofouling_index: Current biofouling level (0-1)
        
    Returns:
        Cleaning recommendation with urgency level
    """
    orchestrator = get_orchestrator()
    
    if not orchestrator._initialized:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized"
        )
        
    try:
        result = await orchestrator.integrated_service.get_cleaning_recommendation(
            vessel_id=vessel_id,
            current_biofouling_index=current_biofouling_index
        )
        return result
    except Exception as e:
        logger.error(f"Cleaning recommendation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation error: {str(e)}"
        )


# =============================================================================
# EXTERNAL API PROXY ENDPOINTS
# =============================================================================

@router.get(
    "/weather/sea-conditions",
    summary="Get sea conditions"
)
async def get_sea_conditions(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180)
):
    """
    Get current sea conditions from weather API.
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        
    Returns:
        Sea state, wave height, wind speed/direction
    """
    api_manager = get_api_manager()
    
    if not api_manager.is_available("weather"):
        raise HTTPException(
            status_code=503,
            detail="Weather API not configured"
        )
        
    try:
        result = await api_manager.weather.get_sea_conditions(latitude, longitude)
        return result
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Weather API error: {str(e)}"
        )


@router.get(
    "/fuel-prices",
    summary="Get current fuel prices"
)
async def get_fuel_prices(
    port: Optional[str] = None,
    fuel_type: str = "VLSFO"
):
    """
    Get current bunker fuel prices.
    
    Args:
        port: Port code (e.g., "BRSSZ" for Santos)
        fuel_type: Fuel type (VLSFO, HSFO, MGO)
        
    Returns:
        Current fuel price in USD per ton
    """
    api_manager = get_api_manager()
    
    if not api_manager.is_available("fuel_prices"):
        raise HTTPException(
            status_code=503,
            detail="Fuel Prices API not configured"
        )
        
    try:
        result = await api_manager.fuel_prices.get_current_prices(port, fuel_type)
        return result
    except Exception as e:
        logger.error(f"Fuel prices API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Fuel prices API error: {str(e)}"
        )


@router.get(
    "/vessels/{imo}/position",
    summary="Get vessel current position"
)
async def get_vessel_position(imo: str):
    """
    Get current position of a vessel by IMO number.
    
    Args:
        imo: IMO number of the vessel
        
    Returns:
        Current vessel position and status
    """
    api_manager = get_api_manager()
    
    if not api_manager.is_available("vessel_tracking"):
        raise HTTPException(
            status_code=503,
            detail="Vessel Tracking API not configured"
        )
        
    try:
        result = await api_manager.vessel_tracking.get_vessel_position(imo)
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Vessel {imo} not found"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vessel tracking API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Vessel tracking API error: {str(e)}"
        )


@router.post(
    "/vessels/{vessel_id}/schedule-cleaning",
    summary="Schedule hull cleaning"
)
async def schedule_hull_cleaning(
    vessel_id: str,
    proposed_date: datetime = Body(...),
    priority: str = Body("normal")
):
    """
    Schedule a hull cleaning through maintenance API.
    
    Args:
        vessel_id: Vessel identifier
        proposed_date: Proposed date for cleaning
        priority: Priority level (low, normal, high, critical)
        
    Returns:
        Scheduling confirmation
    """
    api_manager = get_api_manager()
    
    if not api_manager.is_available("maintenance"):
        raise HTTPException(
            status_code=503,
            detail="Maintenance API not configured"
        )
        
    try:
        result = await api_manager.maintenance.schedule_cleaning(
            vessel_id,
            proposed_date,
            priority
        )
        return result
    except Exception as e:
        logger.error(f"Maintenance API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Scheduling error: {str(e)}"
        )
