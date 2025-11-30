# =============================================================================
# PYDANTIC SCHEMAS / MODELS
# =============================================================================
"""
Data models and schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class BiofoulingClass(str, Enum):
    """Classification levels for biofouling severity."""
    LEVE = "Leve"
    MODERADA = "Moderada"
    SEVERA = "Severa"
    UNKNOWN = "Unknown"


class PredictionStatus(str, Enum):
    """Status of prediction requests."""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


# =============================================================================
# BASE SCHEMAS
# =============================================================================

class HealthCheck(BaseModel):
    """Health check response schema."""
    status: str = "healthy"
    version: str
    model_loaded: bool
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# =============================================================================
# SHIP SCHEMAS
# =============================================================================

class ShipBase(BaseModel):
    """Base ship information."""
    ship_name: str = Field(..., description="Nome do navio")
    

class ShipInfo(ShipBase):
    """Detailed ship information."""
    total_events: int = Field(..., description="Total de eventos registrados")
    last_event_date: Optional[datetime] = Field(None, description="Data do último evento")
    last_cleaning_date: Optional[datetime] = Field(None, description="Data da última docagem")
    days_since_cleaning: Optional[int] = Field(None, description="Dias desde última limpeza")
    paint_type: Optional[str] = Field(None, description="Tipo de tinta do casco")


class ShipList(BaseModel):
    """List of ships response."""
    total: int
    ships: List[ShipInfo]


# =============================================================================
# EVENT SCHEMAS
# =============================================================================

class EventBase(BaseModel):
    """Base event data."""
    session_id: str = Field(..., description="ID da sessão")
    ship_name: str = Field(..., description="Nome do navio")
    start_date: datetime = Field(..., description="Data de início")
    speed: float = Field(..., ge=0, description="Velocidade em nós")
    duration: float = Field(..., ge=0, description="Duração em horas")


class EventCreate(EventBase):
    """Schema for creating new events."""
    displacement: Optional[float] = Field(None, description="Deslocamento")
    mid_draft: Optional[float] = Field(None, description="Calado médio")
    beaufort_scale: Optional[int] = Field(None, ge=0, le=12, description="Escala Beaufort")
    consumption: Optional[float] = Field(None, ge=0, description="Consumo de combustível")


class EventResponse(EventBase):
    """Event response with calculated fields."""
    displacement: Optional[float] = None
    mid_draft: Optional[float] = None
    beaufort_scale: Optional[int] = None
    consumption: Optional[float] = None
    days_since_cleaning: Optional[int] = None
    theoretical_power: Optional[float] = None
    baseline_consumption: Optional[float] = None


# =============================================================================
# PREDICTION SCHEMAS
# =============================================================================

class PredictionRequest(BaseModel):
    """Request schema for biofouling prediction."""
    ship_name: str = Field(..., description="Nome do navio")
    speed: float = Field(..., ge=0, le=30, description="Velocidade em nós")
    duration: float = Field(..., ge=0, description="Duração da viagem em horas")
    days_since_cleaning: int = Field(..., ge=0, description="Dias desde última limpeza")
    displacement: Optional[float] = Field(None, description="Deslocamento do navio")
    mid_draft: Optional[float] = Field(None, description="Calado médio")
    beaufort_scale: Optional[int] = Field(0, ge=0, le=12, description="Escala Beaufort")
    pct_idle_recent: Optional[float] = Field(0.0, ge=0, le=1, description="% tempo parado recente")
    paint_type: Optional[str] = Field("Generic", description="Tipo de tinta")


class PredictionResponse(BaseModel):
    """Response schema for biofouling prediction."""
    ship_name: str
    status: PredictionStatus = PredictionStatus.SUCCESS
    
    # Prediction results
    predicted_consumption: float = Field(..., description="Consumo previsto (tons)")
    baseline_consumption: float = Field(..., description="Consumo base teórico (tons)")
    excess_ratio: float = Field(..., description="Razão de excesso de consumo")
    
    # Biofouling metrics
    bio_index: float = Field(..., ge=0, le=10, description="Índice de biofouling (0-10)")
    bio_class: BiofoulingClass = Field(..., description="Classificação do biofouling")
    
    # Cost & emissions estimates
    additional_fuel_tons: float = Field(..., description="Combustível adicional (tons)")
    additional_cost_usd: float = Field(..., description="Custo adicional (USD)")
    additional_co2_tons: float = Field(..., description="Emissões adicionais CO2 (tons)")
    
    # Metadata
    prediction_timestamp: datetime = Field(default_factory=datetime.now)
    model_version: str = "v13"


class BatchPredictionRequest(BaseModel):
    """Request schema for batch predictions."""
    predictions: List[PredictionRequest]


class BatchPredictionResponse(BaseModel):
    """Response schema for batch predictions."""
    total: int
    successful: int
    failed: int
    results: List[PredictionResponse]
    errors: List[ErrorResponse] = []


# =============================================================================
# BIOFOULING REPORT SCHEMAS
# =============================================================================

class BiofoulingReportItem(BaseModel):
    """Individual biofouling report item."""
    ship_name: str
    event_date: datetime
    session_id: str
    consumption: float
    baseline_consumption: float
    excess_ratio: float
    bio_index: float
    bio_class: BiofoulingClass
    additional_fuel_tons: Optional[float] = None
    additional_cost_usd: Optional[float] = None
    additional_co2_tons: Optional[float] = None


class BiofoulingReport(BaseModel):
    """Full biofouling report response."""
    generated_at: datetime = Field(default_factory=datetime.now)
    total_records: int
    records: List[BiofoulingReportItem]


# =============================================================================
# SHIP SUMMARY SCHEMAS
# =============================================================================

class ShipSummary(BaseModel):
    """Summary statistics for a single ship."""
    ship_name: str
    num_events: int
    avg_excess_ratio: float
    max_excess_ratio: float
    avg_bio_index: float
    max_bio_index: float
    total_baseline_fuel: float
    total_real_fuel: float
    total_additional_fuel: Optional[float] = None
    total_additional_cost_usd: Optional[float] = None
    total_additional_co2: Optional[float] = None


class FleetSummary(BaseModel):
    """Fleet-wide summary statistics."""
    generated_at: datetime = Field(default_factory=datetime.now)
    total_ships: int
    total_events: int
    fleet_avg_bio_index: float
    fleet_total_additional_fuel: float
    fleet_total_additional_cost_usd: float
    fleet_total_additional_co2: float
    ships: List[ShipSummary]


# =============================================================================
# ANALYTICS SCHEMAS
# =============================================================================

class TimeSeriesPoint(BaseModel):
    """Single point in a time series."""
    date: datetime
    value: float


class ShipAnalytics(BaseModel):
    """Analytics data for a specific ship."""
    ship_name: str
    period_start: datetime
    period_end: datetime
    bio_index_trend: List[TimeSeriesPoint]
    consumption_trend: List[TimeSeriesPoint]
    avg_bio_index: float
    avg_excess_consumption: float
    recommendation: str


# =============================================================================
# MODEL INFO SCHEMAS
# =============================================================================

class ModelInfo(BaseModel):
    """Information about the loaded model."""
    model_name: str
    version: str
    trained_at: Optional[datetime] = None
    features: List[str]
    metrics: dict
    parameters: dict


class FeatureImportance(BaseModel):
    """Feature importance from the model."""
    feature: str
    importance: float
    rank: int
