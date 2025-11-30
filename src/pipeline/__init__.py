"""Pipeline utilities that compute hydrodynamics, fouling indices, and prediction-ready features."""
from .baseline import calculate_theoretical_power, compute_baseline_consumption
from .bio_index import bio_index_0_10, bio_class_from_excess_ratio
from .feature_engineering import compute_idle_hours, pct_idle_recent, accumulated_fouling_risk
from .hydrodynamics import (
    compute_reynolds_number,
    friction_coefficient_cf,
    delta_roughness,
    power_penalty,
)
from .impact import compute_additional_impacts
from .prediction import prepare_and_predict
