# =============================================================================
# DATABASE HELPERS
# =============================================================================
"""
SQLite database initialization and helpers.
Used for local caching and persistence of processed data.
"""

import logging
from pathlib import Path
from typing import Optional
import sqlite3

from .config import settings

logger = logging.getLogger(__name__)

# Database path
DB_DIR = settings.BASE_DIR / "data" / "database"
DB_PATH = DB_DIR / "biofouling.db"


def get_db_path() -> Path:
    """Get the database file path."""
    return DB_PATH


def ensure_db_initialized() -> None:
    """
    Ensure the database directory exists and create tables if needed.
    """
    try:
        # Create directory if needed
        DB_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create database and tables
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Predictions cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_name TEXT NOT NULL,
                session_id TEXT,
                prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                input_json TEXT,
                output_json TEXT,
                model_version TEXT
            )
        """)
        
        # Events processed table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events_processed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                ship_name TEXT,
                processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bio_index REAL,
                bio_class TEXT,
                excess_ratio REAL
            )
        """)
        
        # Ocean data cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ocean_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE,
                data_json TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {DB_PATH}")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    ensure_db_initialized()
    return sqlite3.connect(DB_PATH)


def save_prediction(
    ship_name: str,
    session_id: Optional[str],
    input_data: str,
    output_data: str,
    model_version: str = "v13"
) -> None:
    """Save a prediction to the cache."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO predictions_cache 
            (ship_name, session_id, input_json, output_json, model_version)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ship_name, session_id, input_data, output_data, model_version)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to cache prediction: {e}")
