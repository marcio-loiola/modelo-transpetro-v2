from datetime import datetime
import time
from typing import Any

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...src.models import load_model
from ...src.pipeline import prepare_and_predict
from ..ocean_cache import ocean_cache
from ..config import settings
from ..schemas import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ErrorResponse,
)

router = APIRouter(tags=["Operational"])

VESSEL_REGISTRY: dict[str, dict[str, Any]] = {}


def _read_model_version() -> dict[str, str]:
    try:
        with open(settings.MODEL_VERSION_PATH, "r", encoding="utf-8") as handle:
            import json

            return json.load(handle)
    except Exception:
        return {"model_version": "unknown", "hash": settings.MODEL_SHA256 or ""}


def _normalize_request(request: PredictionRequest) -> dict[str, Any]:
    paint = request.paint_type or "generic"
    paint_encoded = float(hash(paint) % 100) / 100

    return {
        "shipName": request.ship_name,
        "sessionId": request.session_id or f"{request.ship_name}-{int(request.start_date.timestamp())}",
        "startGMTDate": request.start_date.isoformat(),
        "speed": request.speed,
        "duration": request.duration,
        "displacement": request.displacement,
        "midDraft": request.mid_draft,
        "beaufortScale": request.beaufort_scale,
        "days_since_cleaning": request.days_since_cleaning,
        "pct_idle_recent": request.pct_idle_recent or 0.0,
        "paint_encoded": paint_encoded,
        "paint_x_speed": paint_encoded * request.speed,
        "historical_avg_speed": request.speed,
    }


def _format_prediction(record: pd.Series, model_version: str) -> PredictionResponse:
    baseline = record.get("baseline_consumption", 0.0)
    excess = record.get("target_excess_ratio", 0.0)
    return PredictionResponse(
        ship_name=record.get("shipName", "unknown"),
        predicted_consumption=float(baseline * (1 + excess)),
        baseline_consumption=float(baseline),
        excess_ratio=float(excess),
        bio_index=float(record.get("bio_index_0_10", 0.0)),
        bio_class=record.get("bio_class", "Unknown"),
        additional_fuel_tons=float(record.get("additional_fuel_tons", 0.0)),
        additional_cost_usd=float(record.get("additional_cost_usd", 0.0)),
        additional_co2_tons=float(record.get("additional_co2_tons", 0.0)),
        prediction_timestamp=datetime.now(),
        model_version=model_version,
    )


def _prepare_dataframe(payload: dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame([payload])
    return df


def _inject_environment(row: dict[str, Any], env: dict[str, Any], ship_name: str) -> dict[str, Any]:
    payload = row.copy()
    payload.setdefault("water_temperature", env.get("temperature"))
    payload.setdefault("water_density", env.get("density"))
    payload.setdefault("water_viscosity", 1.0e-3)
    payload.setdefault("wave_height", env.get("wave_height"))
    payload.setdefault("current_speed", env.get("current_speed"))
    payload.setdefault("chlorophyll", env.get("chlorophyll"))
    payload.setdefault("zone", env.get("zone"))
    vessel = VESSEL_REGISTRY.get(ship_name)
    if vessel:
        payload.setdefault("ship_length", vessel.get("ship_length"))
        payload.setdefault("clean_friction", vessel.get("clean_friction", 0.003))
    return payload


def _load_prediction_model():
    model_path = (settings.MODELS_DIR / settings.MODEL_FILE).as_posix()
    return load_model(model_path)


@router.post("/prediction/biofouling", response_model=PredictionResponse)
async def predict_biofouling(payload: PredictionRequest) -> PredictionResponse:
    env = await ocean_cache.get_data()
    normalized = _normalize_request(payload)
    data_payload = _inject_environment(normalized, env["environment"], payload.ship_name)
    df = _prepare_dataframe(data_payload)
    model = _load_prediction_model()
    predictions = prepare_and_predict(df, model)
    result = predictions.iloc[0]
    version_info = _read_model_version()
    model_version = version_info.get("model_version", "unknown")
    return _format_prediction(result, model_version)


@router.post("/prediction/biofouling/batch", response_model=BatchPredictionResponse)
async def predict_biofouling_batch(payload: BatchPredictionRequest) -> BatchPredictionResponse:
    env = await ocean_cache.get_data()
    model = _load_prediction_model()
    results = []
    errors = []
    for request in payload.predictions:
        try:
            normalized = _normalize_request(request)
            data_payload = _inject_environment(normalized, env["environment"], request.ship_name)
            df = _prepare_dataframe(data_payload)
            predictions = prepare_and_predict(df, model)
            result = predictions.iloc[0]
            version_info = _read_model_version()
            model_version = version_info.get("model_version", "unknown")
            results.append(_format_prediction(result, model_version))
        except Exception as exc:
            errors.append(ErrorResponse(detail=str(exc)))
    return BatchPredictionResponse(
        total=len(payload.predictions),
        successful=len(results),
        failed=len(errors),
        results=results,
        errors=errors,
    )


class VesselMetadataUpdate(BaseModel):
    ship_name: str
    draft: float | None = None
    hull_type: str | None = None
    paint_type: str | None = None
    ship_length: float | None = None
    clean_friction: float = 0.003
    last_cleaning_date: datetime | None = None


class VesselMetadataResponse(BaseModel):
    ship_name: str
    updated_at: datetime = Field(default_factory=datetime.now)


@router.post("/vessel/data", response_model=VesselMetadataResponse)
async def register_vessel_metadata(payload: VesselMetadataUpdate) -> VesselMetadataResponse:
    VESSEL_REGISTRY[payload.ship_name] = payload.dict()
    return VesselMetadataResponse(ship_name=payload.ship_name)


class OceanEnvResponse(BaseModel):
    temperature: float
    salinity: float
    density: float
    chlorophyll: float
    wave_height: float
    current_speed: float
    zone: str
    updated_at: datetime


@router.get("/ocean/env", response_model=OceanEnvResponse)
async def get_ocean_environment() -> OceanEnvResponse:
    env = await ocean_cache.get_data()
    payload = env["environment"].copy()
    return OceanEnvResponse(
        temperature=float(payload.get("temperature", 0.0)),
        salinity=float(payload.get("salinity", 0.0)),
        density=float(payload.get("density", 0.0)),
        chlorophyll=float(payload.get("chlorophyll", 0.0)),
        wave_height=float(payload.get("wave_height", 0.0)),
        current_speed=float(payload.get("current_speed", 0.0)),
        zone=payload.get("zone", "unknown"),
        updated_at=datetime.fromtimestamp(env.get("updated_at", time.time())),
    )
