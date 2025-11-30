"""Minimal helpers used to stage or load the production-level XGBoost artifact."""

import joblib
from xgboost import XGBRegressor


def build_stub_model() -> XGBRegressor:
    """Return an XGBoost regressor with the production hyperparameters for smoke tests."""
    model = XGBRegressor(
        objective='reg:squarederror',
        n_estimators=10,
        learning_rate=0.1,
        max_depth=3,
        random_state=42,
    )
    return model


def save_stub_model(path: str = "models/modelo_final_v13.pkl") -> str:
    """Serialize the stub model to disk so downstream services can load it."""
    model = build_stub_model()
    joblib.dump(model, path)
    return path


def load_model(path: str = "models/modelo_final_v13.pkl") -> XGBRegressor | None:
    """Attempt to load a serialized model artifact, returning None on failure."""
    try:
        return joblib.load(path)
    except Exception:
        return None