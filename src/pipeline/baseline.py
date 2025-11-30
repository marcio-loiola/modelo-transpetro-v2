"""Physics-driven helpers for translating ship status into clean-hull consumption."""

import numpy as np

ADMIRALTY_SCALE_FACTOR = 10000.0


def calculate_theoretical_power(displacement: float, speed: float, draft: float | None = None) -> float:
    """Apply the Admiralty power formula to get a base consumption estimate.

    Args:
        displacement: Current vessel displacement (tons or kg, depending on telemetry).
        speed: Vessel speed in knots.
        draft: Optional fallback when displacement is missing (no logic applied here).

    Returns:
        Estimated theoretical power output used downstream for baseline fuel.
    """
    if displacement is None or displacement == 0 or speed <= 0:
        return 0.0
    try:
        return (np.power(displacement, 2.0 / 3.0) * np.power(speed, 3.0)) / ADMIRALTY_SCALE_FACTOR
    except Exception:
        return 0.0


def compute_baseline_consumption(theoretical_power: float, duration_hours: float, efficiency_factor: float) -> float:
    """Multiply power, time, and efficiency to return clean-hull fuel (tons).

    Args:
        theoretical_power: Output from calculate_theoretical_power.
        duration_hours: Event duration in hours.
        efficiency_factor: Calibrated constant derived from low-biofouling cruises.

    Returns:
        Baseline fuel (tons) without biofouling penalties.
    """
    if theoretical_power <= 0 or duration_hours <= 0 or efficiency_factor <= 0:
        return 0.0
    return theoretical_power * duration_hours * efficiency_factor