#!/usr/bin/env python
# =============================================================================
# RUN API SERVER
# =============================================================================
"""
Script to run the FastAPI server.
Usage: python run_api.py
"""

import uvicorn
from api.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print(f"Starting {settings.APP_NAME}")
    print("=" * 60)
    print(f"URL: http://{settings.HOST}:{settings.PORT}")
    print(f"Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"ReDoc: http://{settings.HOST}:{settings.PORT}/redoc")
    print("=" * 60)
    
    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS,
        log_level="info" if not settings.DEBUG else "debug"
    )
