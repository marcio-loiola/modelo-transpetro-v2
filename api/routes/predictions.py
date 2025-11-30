# =============================================================================
# API ROUTES - PREDICTIONS
# =============================================================================
"""
Endpoints for biofouling predictions.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from ..schemas import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ErrorResponse,
)
from ..services import BiofoulingService, get_biofouling_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.post(
    "/",
    response_model=PredictionResponse,
    summary="Predict biofouling impact",
    description="Make a single biofouling prediction for a ship voyage"
)
async def predict_biofouling(
    request: PredictionRequest,
    service: BiofoulingService = Depends(get_biofouling_service)
) -> PredictionResponse:
    """
    Predict biofouling impact and fuel consumption for a voyage.
    
    - **ship_name**: Name of the ship
    - **speed**: Voyage speed in knots
    - **duration**: Voyage duration in hours
    - **days_since_cleaning**: Days since last hull cleaning
    - **displacement**: Ship displacement (optional)
    - **mid_draft**: Mid draft in meters (optional)
    - **beaufort_scale**: Sea state 0-12 (optional)
    - **pct_idle_recent**: Recent idle time percentage 0-1 (optional)
    - **paint_type**: Hull paint type (optional)
    """
    if not service.model_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service unavailable."
        )
    
    try:
        result = service.predict(request)
        logger.info(f"Prediction made for ship: {request.ship_name}")
        return result
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/batch",
    response_model=BatchPredictionResponse,
    summary="Batch predictions",
    description="Make multiple biofouling predictions in a single request"
)
async def predict_batch(
    request: BatchPredictionRequest,
    service: BiofoulingService = Depends(get_biofouling_service)
) -> BatchPredictionResponse:
    """
    Make batch predictions for multiple voyages.
    
    Useful for:
    - Fleet-wide analysis
    - Historical data processing
    - Scenario comparisons
    """
    if not service.model_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service unavailable."
        )
    
    try:
        results, errors = service.predict_batch(request.predictions)
        
        return BatchPredictionResponse(
            total=len(request.predictions),
            successful=len(results),
            failed=len(errors),
            results=results,
            errors=[ErrorResponse(detail=e["error"]) for e in errors]
        )
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/scenario",
    response_model=List[PredictionResponse],
    summary="Compare scenarios",
    description="Compare clean vs dirty hull scenarios"
)
async def compare_scenarios(
    request: PredictionRequest,
    service: BiofoulingService = Depends(get_biofouling_service)
) -> List[PredictionResponse]:
    """
    Compare biofouling impact for different cleaning scenarios.
    
    Returns predictions for:
    1. Clean hull (30 days since cleaning)
    2. Current state (as specified)
    3. Dirty hull (400 days since cleaning)
    """
    if not service.model_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service unavailable."
        )
    
    scenarios = []
    
    # Scenario 1: Clean hull
    clean_request = request.model_copy()
    clean_request.days_since_cleaning = 30
    scenarios.append(service.predict(clean_request))
    
    # Scenario 2: Current state
    scenarios.append(service.predict(request))
    
    # Scenario 3: Dirty hull
    dirty_request = request.model_copy()
    dirty_request.days_since_cleaning = 400
    scenarios.append(service.predict(dirty_request))
    
    return scenarios
