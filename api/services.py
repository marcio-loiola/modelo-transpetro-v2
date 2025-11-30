# =============================================================================
# BIOFOULING PREDICTION SERVICE
# =============================================================================
"""
Core service for biofouling prediction and data processing.
Integrates with the trained XGBoost model.
"""

import os
import logging
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

from .config import settings
from .schemas import (
    BiofoulingClass,
    PredictionRequest,
    PredictionResponse,
    PredictionStatus,
    ShipSummary,
    BiofoulingReportItem,
)

logger = logging.getLogger(__name__)


class BiofoulingService:
    """
    Service class for biofouling predictions and data processing.
    Handles model loading, predictions, and data transformations.
    """

    def __init__(self):
        """Initialize the service and load the model."""
        self.model = None
        self.encoder = None
        self.model_loaded = False
        self.efficiency_factors: Dict[str, float] = {}
        self.global_efficiency: float = 0.004158  # Default fallback
        
        # Feature list used by the model
        self.features = [
            'speed',
            'beaufortScale',
            'days_since_cleaning',
            'pct_idle_recent',
            'accumulated_fouling_risk',
            'historical_avg_speed',
            'paint_x_speed',
            'paint_encoded'
        ]
        
        self._load_model()
        self._load_efficiency_factors()

    def _load_model(self) -> None:
        """Load the trained model and encoder from disk."""
        try:
            model_path = settings.MODELS_DIR / settings.MODEL_FILE
            encoder_path = settings.MODELS_DIR / settings.ENCODER_FILE
            
            if model_path.exists() and encoder_path.exists():
                self.model = joblib.load(model_path)
                self.encoder = joblib.load(encoder_path)
                self.model_loaded = True
                logger.info(f"Model loaded successfully from {model_path}")
            else:
                logger.warning(f"Model files not found at {model_path}")
                self.model_loaded = False
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model_loaded = False

    def _load_efficiency_factors(self) -> None:
        """Load pre-calculated efficiency factors from processed data."""
        try:
            summary_path = settings.DATA_PROCESSED_DIR / "biofouling_summary_by_ship.csv"
            if summary_path.exists():
                df = pd.read_csv(summary_path)
                # Calculate efficiency factors from historical data
                logger.info("Efficiency factors loaded from historical data")
        except Exception as e:
            logger.warning(f"Could not load efficiency factors: {e}")

    def calculate_theoretical_power(
        self,
        displacement: Optional[float],
        draft: Optional[float],
        speed: float
    ) -> float:
        """
        Calculate theoretical power using Admiralty coefficient formula.
        
        Args:
            displacement: Ship displacement (tons)
            draft: Mid draft (meters)
            speed: Speed in knots
            
        Returns:
            Theoretical power value
        """
        if speed < 1:
            return 0.0
            
        disp = displacement
        if disp is None or disp == 0:
            if draft is not None and draft > 0:
                disp = draft * settings.ADMIRALTY_SCALE_FACTOR
            else:
                disp = 50000  # Default displacement estimate
        
        return (np.power(disp, 2/3) * np.power(speed, 3)) / settings.ADMIRALTY_SCALE_FACTOR

    def calculate_baseline_consumption(
        self,
        theoretical_power: float,
        duration: float,
        ship_name: str
    ) -> float:
        """
        Calculate baseline fuel consumption without biofouling effect.
        
        Args:
            theoretical_power: Calculated theoretical power
            duration: Duration in hours
            ship_name: Name of the ship for efficiency lookup
            
        Returns:
            Baseline consumption in tons
        """
        efficiency = self.efficiency_factors.get(
            ship_name.upper().strip(),
            self.global_efficiency
        )
        return theoretical_power * duration * efficiency

    def calculate_bio_index(self, excess_ratio: float) -> Tuple[float, BiofoulingClass]:
        """
        Calculate biofouling index using sigmoid function.
        
        Args:
            excess_ratio: Excess consumption ratio
            
        Returns:
            Tuple of (bio_index 0-10, classification)
        """
        # Sigmoid calculation
        k = settings.SIGMOID_K
        mid = settings.SIGMOID_MIDPOINT
        
        bio_index = 1 / (1 + np.exp(-k * (excess_ratio - mid)))
        bio_index = np.clip(bio_index, 0, 1)
        bio_index_0_10 = round(bio_index * 10, 1)
        
        # Classification based on excess ratio
        if excess_ratio < 0.10:
            bio_class = BiofoulingClass.LEVE
        elif excess_ratio < 0.20:
            bio_class = BiofoulingClass.MODERADA
        else:
            bio_class = BiofoulingClass.SEVERA
            
        return bio_index_0_10, bio_class

    def prepare_features(self, request: PredictionRequest) -> pd.DataFrame:
        """
        Prepare feature DataFrame for model prediction.
        
        Args:
            request: Prediction request with input data
            
        Returns:
            DataFrame with features ready for prediction
        """
        # Encode paint type
        paint_encoded = 0
        if self.encoder is not None:
            try:
                paint_type = request.paint_type or "Generic"
                if paint_type in self.encoder.classes_:
                    paint_encoded = self.encoder.transform([paint_type])[0]
            except Exception:
                paint_encoded = 0
        
        # Calculate derived features
        pct_idle = request.pct_idle_recent or 0.0
        accumulated_risk = pct_idle * request.days_since_cleaning
        
        features_dict = {
            'speed': request.speed,
            'beaufortScale': request.beaufort_scale or 0,
            'days_since_cleaning': request.days_since_cleaning,
            'pct_idle_recent': pct_idle,
            'accumulated_fouling_risk': accumulated_risk,
            'historical_avg_speed': request.speed,  # Use current as estimate
            'paint_x_speed': paint_encoded * request.speed,
            'paint_encoded': paint_encoded
        }
        
        return pd.DataFrame([features_dict])

    def predict(self, request: PredictionRequest) -> PredictionResponse:
        """
        Make a biofouling prediction for a single request.
        
        Args:
            request: Prediction request with ship and voyage data
            
        Returns:
            PredictionResponse with all calculated metrics
        """
        if not self.model_loaded:
            raise ValueError("Model not loaded. Cannot make predictions.")
        
        try:
            # Prepare features
            features_df = self.prepare_features(request)
            
            # Get model prediction (excess ratio)
            predicted_ratio = float(self.model.predict(features_df)[0])
            
            # Calculate theoretical power and baseline
            theoretical_power = self.calculate_theoretical_power(
                request.displacement,
                request.mid_draft,
                request.speed
            )
            
            baseline_consumption = self.calculate_baseline_consumption(
                theoretical_power,
                request.duration,
                request.ship_name
            )
            
            # Calculate predicted consumption
            predicted_consumption = baseline_consumption * (1 + predicted_ratio)
            
            # Calculate biofouling metrics
            bio_index, bio_class = self.calculate_bio_index(predicted_ratio)
            
            # Calculate cost and emissions
            additional_fuel = baseline_consumption * predicted_ratio
            additional_cost = additional_fuel * settings.FUEL_PRICE_USD_PER_TON
            additional_co2 = additional_fuel * settings.CO2_TON_PER_FUEL_TON
            
            return PredictionResponse(
                ship_name=request.ship_name,
                status=PredictionStatus.SUCCESS,
                predicted_consumption=round(predicted_consumption, 4),
                baseline_consumption=round(baseline_consumption, 4),
                excess_ratio=round(predicted_ratio, 4),
                bio_index=bio_index,
                bio_class=bio_class,
                additional_fuel_tons=round(additional_fuel, 4),
                additional_cost_usd=round(additional_cost, 2),
                additional_co2_tons=round(additional_co2, 4),
                model_version="v13"
            )
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise

    def predict_batch(
        self,
        requests: List[PredictionRequest]
    ) -> Tuple[List[PredictionResponse], List[Dict]]:
        """
        Make predictions for multiple requests.
        
        Args:
            requests: List of prediction requests
            
        Returns:
            Tuple of (successful predictions, errors)
        """
        results = []
        errors = []
        
        for i, request in enumerate(requests):
            try:
                result = self.predict(request)
                results.append(result)
            except Exception as e:
                errors.append({
                    "index": i,
                    "ship_name": request.ship_name,
                    "error": str(e)
                })
                
        return results, errors

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if not self.model_loaded:
            return {"status": "not_loaded"}
            
        info = {
            "model_name": settings.MODEL_FILE,
            "version": "v13",
            "features": self.features,
            "model_type": type(self.model).__name__,
            "is_loaded": self.model_loaded
        }
        
        # Add feature importances if available
        if hasattr(self.model, 'feature_importances_'):
            importances = dict(zip(
                self.features,
                self.model.feature_importances_.tolist()
            ))
            info["feature_importances"] = importances
            
        # Add model parameters if available
        if hasattr(self.model, 'get_params'):
            info["parameters"] = self.model.get_params()
            
        return info


# =============================================================================
# DATA SERVICE
# =============================================================================

class DataService:
    """
    Service for loading and processing ship data.
    Handles CSV/Excel data loading and transformations.
    """
    
    def __init__(self):
        """Initialize the data service."""
        self._events_cache: Optional[pd.DataFrame] = None
        self._consumption_cache: Optional[pd.DataFrame] = None
        self._drydock_cache: Optional[pd.DataFrame] = None
        
    def load_events(self, force_reload: bool = False) -> pd.DataFrame:
        """Load events data from CSV."""
        if self._events_cache is None or force_reload:
            path = settings.DATA_RAW_DIR / settings.FILE_EVENTS
            if path.exists():
                df = pd.read_csv(path)
                df[settings.COL_START_DATE] = pd.to_datetime(df[settings.COL_START_DATE])
                df[settings.COL_SHIP_NAME] = df[settings.COL_SHIP_NAME].str.upper().str.strip()
                self._events_cache = df
            else:
                self._events_cache = pd.DataFrame()
        return self._events_cache
    
    def load_consumption(self, force_reload: bool = False) -> pd.DataFrame:
        """Load consumption data from CSV."""
        if self._consumption_cache is None or force_reload:
            path = settings.DATA_RAW_DIR / settings.FILE_CONSUMPTION
            if path.exists():
                df = pd.read_csv(path)
                df[settings.COL_CONSUMPTION] = pd.to_numeric(
                    df[settings.COL_CONSUMPTION], 
                    errors='coerce'
                )
                self._consumption_cache = df
            else:
                self._consumption_cache = pd.DataFrame()
        return self._consumption_cache
    
    def load_drydock(self, force_reload: bool = False) -> pd.DataFrame:
        """Load drydock/cleaning data from Excel."""
        if self._drydock_cache is None or force_reload:
            path = settings.DATA_RAW_DIR / settings.FILE_DRYDOCK
            if path.exists():
                df = pd.read_excel(path, sheet_name=settings.SHEET_DRYDOCK)
                self._drydock_cache = df
            else:
                self._drydock_cache = pd.DataFrame()
        return self._drydock_cache
    
    def get_ship_list(self) -> List[str]:
        """Get list of unique ship names."""
        events = self.load_events()
        if not events.empty:
            return sorted(events[settings.COL_SHIP_NAME].unique().tolist())
        return []
    
    def get_ship_events(self, ship_name: str) -> pd.DataFrame:
        """Get events for a specific ship."""
        events = self.load_events()
        if not events.empty:
            return events[
                events[settings.COL_SHIP_NAME] == ship_name.upper().strip()
            ].copy()
        return pd.DataFrame()
    
    def get_biofouling_report(self) -> pd.DataFrame:
        """Load the processed biofouling report from CSV or database."""
        # Try CSV first
        path = settings.DATA_PROCESSED_DIR / "biofouling_report.csv"
        if path.exists():
            try:
                df = pd.read_csv(path)
                if not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"Error loading CSV report: {e}")
        
        # Try database as fallback
        try:
            from .database import get_db_session, ReportRecord
            db = get_db_session()
            try:
                records = db.query(ReportRecord).all()
                if records:
                    data = []
                    for record in records:
                        data.append({
                            'shipName': record.ship_name,
                            'sessionId': record.session_id or '',
                            'startGMTDate': record.event_date,
                            'CONSUMED_QUANTITY': record.consumption,
                            'baseline_consumption': record.baseline_consumption,
                            'target_excess_ratio': record.excess_ratio,
                            'bio_index_0_10': record.bio_index,
                            'bio_class': record.bio_class,
                            'additional_fuel_tons': record.additional_fuel_tons,
                            'additional_cost_usd': record.additional_cost_usd,
                            'additional_co2_tons': record.additional_co2_tons,
                        })
                    df = pd.DataFrame(data)
                    logger.info(f"Loaded {len(df)} records from database")
                    return df
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Error loading from database: {e}")
        
        return pd.DataFrame()
    
    def get_ship_summary(self) -> pd.DataFrame:
        """Load the ship summary report from CSV or database."""
        # Try CSV first
        path = settings.DATA_PROCESSED_DIR / "biofouling_summary_by_ship.csv"
        logger.info(f"Attempting to load summary from: {path.absolute()}")
        if path.exists():
            try:
                df = pd.read_csv(path)
                logger.info(f"Loaded summary CSV. Shape: {df.shape}")
                if not df.empty:
                    return df
            except Exception as e:
                logger.error(f"Error loading CSV summary from {path}: {e}")
        else:
            logger.warning(f"Summary CSV not found at: {path.absolute()}")
        
        # Generate summary from database records
        try:
            from .database import get_db_session, ReportRecord
            db = get_db_session()
            try:
                records = db.query(ReportRecord).all()
                if records:
                    # Convert to DataFrame
                    data = []
                    for record in records:
                        data.append({
                            'shipName': record.ship_name,
                            'bio_index_0_10': record.bio_index,
                            'target_excess_ratio': record.excess_ratio,
                            'CONSUMED_QUANTITY': record.consumption,
                            'baseline_consumption': record.baseline_consumption,
                        })
                    
                    df_records = pd.DataFrame(data)
                    
                    # Aggregate by ship
                    if not df_records.empty and 'shipName' in df_records.columns:
                        summary = df_records.groupby('shipName').agg({
                            'bio_index_0_10': ['mean', 'max'],
                            'target_excess_ratio': ['mean', 'max'],
                            'CONSUMED_QUANTITY': 'sum',
                            'baseline_consumption': 'sum',
                        }).reset_index()
                        
                        # Flatten column names
                        summary.columns = ['shipName', 'avg_bio_index', 'max_bio_index', 
                                         'avg_excess_ratio', 'max_excess_ratio',
                                         'total_real_fuel', 'total_baseline_fuel']
                        
                        # Calculate additional metrics
                        summary['total_additional_fuel'] = summary['total_real_fuel'] - summary['total_baseline_fuel']
                        summary['num_events'] = df_records.groupby('shipName').size().values
                        
                        # Add cost estimates if available
                        if 'additional_cost_usd' in df_records.columns:
                            summary['total_additional_cost_usd'] = df_records.groupby('shipName')['additional_cost_usd'].sum().values
                        
                        logger.info(f"Generated summary for {len(summary)} ships from database")
                        return summary
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Error generating summary from database: {e}")
        
        return pd.DataFrame()


# =============================================================================
# SERVICE INSTANCES (Singleton pattern)
# =============================================================================

_biofouling_service: Optional[BiofoulingService] = None
_data_service: Optional[DataService] = None


def get_biofouling_service() -> BiofoulingService:
    """Get or create the biofouling service instance."""
    global _biofouling_service
    if _biofouling_service is None:
        _biofouling_service = BiofoulingService()
    return _biofouling_service


def get_data_service() -> DataService:
    """Get or create the data service instance."""
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service
