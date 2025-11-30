# =============================================================================
# API CONFIGURATION
# =============================================================================
"""
Configuration settings for the FastAPI application.
Loads from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ==========================================================================
    # API Settings
    # ==========================================================================
    APP_NAME: str = "Biofouling Prediction API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "API para predição de biofouling e consumo de combustível da frota Transpetro"
    DEBUG: bool = False
    
    # ==========================================================================
    # Server Settings
    # ==========================================================================
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = True
    
    # ==========================================================================
    # CORS Settings
    # ==========================================================================
    CORS_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]
    
    # ==========================================================================
    # Path Settings
    # ==========================================================================
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_RAW_DIR: Path = BASE_DIR / "data" / "raw"
    DATA_PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    MODELS_DIR: Path = BASE_DIR / "models"
    CONFIG_DIR: Path = BASE_DIR / "config"
    
    # ==========================================================================
    # Model Files
    # ==========================================================================
    MODEL_FILE: str = "modelo_final_v13.pkl"
    ENCODER_FILE: str = "encoder_final_v13.pkl"
    
    # ==========================================================================
    # Data Files
    # ==========================================================================
    FILE_EVENTS: str = "ResultadoQueryEventos.csv"
    FILE_CONSUMPTION: str = "ResultadoQueryConsumo.csv"
    FILE_DRYDOCK: str = "Dados navios Hackathon.xlsx"
    SHEET_DRYDOCK: str = "Lista de docagens"
    
    # ==========================================================================
    # Biofouling Parameters
    # ==========================================================================
    IDLE_SPEED_THRESHOLD: float = 5.0
    ADMIRALTY_SCALE_FACTOR: float = 10000.0
    MIN_CONSUMPTION_THRESHOLD: float = 0.1
    FUEL_PRICE_USD_PER_TON: float = 500.0
    CO2_TON_PER_FUEL_TON: float = 3.114
    SIGMOID_K: float = 10.0
    SIGMOID_MIDPOINT: float = 0.10
    
    # ==========================================================================
    # Column Mappings
    # ==========================================================================
    COL_SHIP_NAME: str = "shipName"
    COL_START_DATE: str = "startGMTDate"
    COL_SESSION_ID: str = "sessionId"
    COL_CONSUMPTION: str = "CONSUMED_QUANTITY"
    COL_SPEED: str = "speed"
    COL_DURATION: str = "duration"
    COL_DISPLACEMENT: str = "displacement"
    COL_DRAFT: str = "midDraft"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
