"""Orchestrates feature synthesis and prediction output for operational payloads."""

from typing import Any

import numpy as np
import pandas as pd
from .baseline import calculate_theoretical_power, compute_baseline_consumption
from .feature_engineering import compute_idle_hours, pct_idle_recent, accumulated_fouling_risk
from .bio_index import bio_index_0_10, bio_class_from_excess_ratio
from .impact import compute_additional_impacts
from .hydrodynamics import (
    compute_reynolds_number,
    friction_coefficient_cf,
    delta_roughness,
    power_penalty,
    DEFAULT_DENSITY,
    DEFAULT_LENGTH,
    DEFAULT_VISCOSITY,
)


def prepare_and_predict(df_events: pd.DataFrame, model: Any | None, encoder: Any | None = None) -> pd.DataFrame:
    """Build features, handle clean-hull baselines, and return enriched predictions.

    Args:
        df_events: Operational events (one or more rows) as raw telemetry.
        model: XGBoost regressor or compatible .predict method. When None, defaults to zeros.
        encoder: Placeholder for future categorical encodings (currently unused).

    Returns:
        Input dataframe augmented with physics, prediction, and impact columns.
    """
    df = df_events.copy()
    df = compute_idle_hours(df)
    df['pct_idle_recent'] = pct_idle_recent(df)
    df['accumulated_fouling_risk'] = accumulated_fouling_risk(
        df['pct_idle_recent'],
        df.get('days_since_cleaning', pd.Series(np.nan, index=df.index)),
    )
    df['theoretical_power'] = df.apply(
        lambda r: calculate_theoretical_power(r.get('displacement', 0), r.get('speed', 0)),
        axis=1,
    )
    df['reynolds_number'] = df.apply(
        lambda r: compute_reynolds_number(
            r.get('speed', 0),
            r.get('ship_length', DEFAULT_LENGTH),
            r.get('water_density', DEFAULT_DENSITY),
            r.get('water_viscosity', DEFAULT_VISCOSITY),
        ),
        axis=1,
    )
    df['friction_coefficient'] = df['reynolds_number'].apply(friction_coefficient_cf)
    df['delta_roughness'] = df.apply(
        lambda r: delta_roughness(r['friction_coefficient'], r.get('clean_friction', 0.003)),
        axis=1,
    )
    df['power_penalty'] = df.apply(
        lambda r: power_penalty(r['delta_roughness'], r.get('speed', 0)),
        axis=1,
    )
    df['efficiency_factor'] = df.get('efficiency_factor', 1e-4)
    df['baseline_consumption'] = df.apply(
        lambda r: compute_baseline_consumption(r['theoretical_power'], r.get('duration', 0), r['efficiency_factor']),
        axis=1,
    )
    features = [
        'speed',
        'beaufortScale',
        'days_since_cleaning',
        'pct_idle_recent',
        'accumulated_fouling_risk',
        'historical_avg_speed',
        'paint_x_speed',
        'paint_encoded',
        'reynolds_number',
        'friction_coefficient',
        'delta_roughness',
        'power_penalty',
    ]
    X = df.reindex(columns=features).fillna(0)

    if model is not None:
        pred_ratio = model.predict(X)
    else:
        pred_ratio = np.zeros(len(df))

    df['target_excess_ratio'] = pred_ratio
    df['bio_index_0_10'] = df['target_excess_ratio'].apply(lambda x: bio_index_0_10(x))
    df['bio_class'] = df['target_excess_ratio'].apply(lambda x: bio_class_from_excess_ratio(x))
    impacts = df.apply(
        lambda r: compute_additional_impacts(r['baseline_consumption'], r['target_excess_ratio']),
        axis=1,
    )
    df[['additional_fuel_tons', 'additional_cost_usd', 'additional_co2_tons']] = pd.DataFrame(list(impacts), index=df.index)
    return df