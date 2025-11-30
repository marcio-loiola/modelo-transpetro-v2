# =============================================================================
# FASTAPI MAIN APPLICATION
# =============================================================================
"""
Main FastAPI application entry point.
Biofouling Prediction API for Transpetro Fleet Management.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .schemas import HealthCheck, ModelInfo, FeatureImportance
from .services import get_biofouling_service, get_data_service
from .integration_service import get_orchestrator
from .routes import (
    predictions_router,
    ships_router,
    reports_router,
    operational_router,
)
from .routes.integrations import router as integrations_router
from .ocean_cache import ocean_cache

# =============================================================================
# LOGGING SETUP
# =============================================================================
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# LIFESPAN CONTEXT MANAGER
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)
    
    # Initialize database
    try:
        from .database import ensure_db_initialized
        ensure_db_initialized()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.warning(f"⚠️ Database initialization failed: {e}")
    
    # Pre-load services
    biofouling_service = get_biofouling_service()
    data_service = get_data_service()
    
    if biofouling_service.model_loaded:
        logger.info("✅ Model loaded successfully")
    else:
        logger.warning("⚠️ Model not loaded - predictions will be unavailable")
    
    # Initialize service orchestrator (external APIs)
    orchestrator = get_orchestrator()
    await orchestrator.initialize()
    logger.info("✅ Service orchestrator initialized")
    ocean_cache.start()
    
    logger.info(f"📂 Data directory: {settings.DATA_RAW_DIR}")
    logger.info(f"🧠 Models directory: {settings.MODELS_DIR}")
    logger.info("=" * 60)
    logger.info(f"🚀 API ready at http://{settings.HOST}:{settings.PORT}")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await ocean_cache.stop()
    await orchestrator.shutdown()


# =============================================================================
# CREATE APPLICATION
# =============================================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# =============================================================================
# MIDDLEWARE
# =============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = datetime.now()
    response = await call_next(request)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s"
    )
    
    return response


# =============================================================================
# INCLUDE ROUTERS
# =============================================================================
app.include_router(predictions_router, prefix="/api/v1")
app.include_router(ships_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(operational_router)


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================

@app.get(
    "/",
    summary="Root endpoint",
    description="Welcome message and API information"
)
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


@app.get(
    "/health",
    response_model=HealthCheck,
    summary="Health check",
    description="Check API health and model status"
)
async def health_check() -> HealthCheck:
    """
    Health check endpoint.
    
    Returns:
    - API status
    - Model loading status
    - Current timestamp
    """
    service = get_biofouling_service()
    
    return HealthCheck(
        status="healthy",
        version=settings.APP_VERSION,
        model_loaded=service.model_loaded,
        timestamp=datetime.now()
    )


@app.get(
    "/api/v1/model/info",
    response_model=ModelInfo,
    summary="Model information",
    description="Get information about the loaded prediction model",
    tags=["Model"]
)
async def get_model_info() -> ModelInfo:
    """
    Get detailed information about the loaded model.
    
    Returns:
    - Model name and version
    - Feature list
    - Model parameters
    - Feature importances
    """
    service = get_biofouling_service()
    info = service.get_model_info()
    
    return ModelInfo(
        model_name=info.get("model_name", "unknown"),
        version=info.get("version", "unknown"),
        trained_at=None,
        features=info.get("features", []),
        metrics={},
        parameters=info.get("parameters", {})
    )


@app.get(
    "/api/v1/model/features",
    response_model=list[FeatureImportance],
    summary="Feature importances",
    description="Get feature importance rankings from the model",
    tags=["Model"]
)
async def get_feature_importances() -> list[FeatureImportance]:
    """
    Get feature importance rankings.
    
    Shows which features have the most impact on predictions.
    """
    service = get_biofouling_service()
    info = service.get_model_info()
    
    importances = info.get("feature_importances", {})
    sorted_features = sorted(
        importances.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    return [
        FeatureImportance(
            feature=feature,
            importance=round(importance, 4),
            rank=i + 1
        )
        for i, (feature, importance) in enumerate(sorted_features)
    ]


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )


# =============================================================================
# RUN APPLICATION (for development)
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS
    )
