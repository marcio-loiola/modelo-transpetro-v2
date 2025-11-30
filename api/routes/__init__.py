# =============================================================================
# API ROUTES PACKAGE
# =============================================================================
"""
Routes package - exports all routers.
"""

from .predictions import router as predictions_router
from .ships import router as ships_router
from .reports import router as reports_router

__all__ = [
    "predictions_router",
    "ships_router",
    "reports_router",
]
