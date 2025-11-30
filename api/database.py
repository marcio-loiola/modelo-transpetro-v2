# =============================================================================
# DATABASE SETUP
# =============================================================================
"""
Database configuration and setup for storing predictions and reports.
Uses SQLite for simplicity and portability.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

from .config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# =============================================================================
# DATABASE MODELS
# =============================================================================

class PredictionRecord(Base):
    """Model for storing prediction records."""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    ship_name = Column(String, index=True, nullable=False)
    speed = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    days_since_cleaning = Column(Integer, nullable=False)
    displacement = Column(Float, nullable=True)
    mid_draft = Column(Float, nullable=True)
    beaufort_scale = Column(Integer, nullable=True)
    
    # Prediction results
    predicted_consumption = Column(Float, nullable=False)
    baseline_consumption = Column(Float, nullable=False)
    excess_ratio = Column(Float, nullable=False)
    bio_index = Column(Float, nullable=False)
    bio_class = Column(String, nullable=False)
    additional_fuel_tons = Column(Float, nullable=True)
    additional_cost_usd = Column(Float, nullable=True)
    additional_co2_tons = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    model_version = Column(String, default="v13", nullable=False)
    
    # Additional data as JSON
    additional_data = Column(Text, nullable=True)


class ReportRecord(Base):
    """Model for storing report records."""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    ship_name = Column(String, index=True, nullable=False)
    session_id = Column(String, index=True, nullable=True)
    event_date = Column(DateTime, nullable=False, index=True)
    
    # Consumption data
    consumption = Column(Float, nullable=False)
    baseline_consumption = Column(Float, nullable=False)
    excess_ratio = Column(Float, nullable=False)
    
    # Biofouling metrics
    bio_index = Column(Float, nullable=False, index=True)
    bio_class = Column(String, nullable=False)
    
    # Cost & emissions
    additional_fuel_tons = Column(Float, nullable=True)
    additional_cost_usd = Column(Float, nullable=True)
    additional_co2_tons = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    source = Column(String, default="api", nullable=False)  # api, csv_import, etc.
    
    # Additional data as JSON
    additional_data = Column(Text, nullable=True)


# =============================================================================
# DATABASE ENGINE AND SESSION
# =============================================================================

# Database file location
DB_DIR = settings.BASE_DIR / "data" / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DB_DIR / "biofouling.db"
DATABASE_URL = f"sqlite:///{DB_FILE}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database initialized at {DB_FILE}")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def get_db() -> Session:
    """
    Dependency for getting database session.
    Use this in FastAPI dependencies.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_db_session() -> Session:
    """Get a database session (for use outside FastAPI dependencies)."""
    return SessionLocal()


def ensure_db_initialized():
    """Ensure database is initialized."""
    if not DB_FILE.exists():
        init_db()
    else:
        # Verify tables exist
        Base.metadata.create_all(bind=engine)
