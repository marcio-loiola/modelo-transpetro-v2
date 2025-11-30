"""Time-windowed feature engineering for fouling risk estimations."""

import numpy as np
import pandas as pd

IDLE_SPEED_THRESHOLD = 5.0


def compute_idle_hours(df: pd.DataFrame, speed_col: str = 'speed', duration_col: str = 'duration') -> pd.DataFrame:
    """Mutate a DataFrame in place and store the duration where the vessel was nearly stationary."""
    df['idle_hours'] = np.where(df[speed_col] < IDLE_SPEED_THRESHOLD, df[duration_col], 0.0)
    return df


def pct_idle_recent(df: pd.DataFrame, ship_col: str = 'shipName', date_col: str = 'startGMTDate') -> pd.Series:
    """Return the percentage of idle time per ship over the trailing 30-day window."""
    df[date_col] = pd.to_datetime(df[date_col], utc=True)
    df = df.sort_values([ship_col, date_col])
    indexer = df.set_index(date_col).groupby(ship_col)
    rolling_idle_sum = indexer['idle_hours'].rolling('30D', min_periods=1).sum().shift(1)
    rolling_total_sum = indexer['duration'].rolling('30D', min_periods=1).sum().shift(1)
    pct = rolling_idle_sum / (rolling_total_sum + 1e-9)
    return pct.reset_index(level=0, drop=True)


def accumulated_fouling_risk(pct_idle_series: pd.Series, days_since_cleaning_series: pd.Series) -> pd.Series:
    """Estimate risk accumulation as the product of idle percentage and days since cleaning."""
    return pct_idle_series * days_since_cleaning_series