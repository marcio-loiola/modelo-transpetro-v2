"""Hydrodynamic approximations that feed the prediction pipeline."""

import numpy as np

DEFAULT_DENSITY = 1025.0  # kg/m³
DEFAULT_VISCOSITY = 1.0e-3  # Pa·s (simplified water viscosity)
DEFAULT_LENGTH = 200.0  # typical ship length in meters


def compute_reynolds_number(
    velocity: float,
    length: float = DEFAULT_LENGTH,
    density: float = DEFAULT_DENSITY,
    viscosity: float = DEFAULT_VISCOSITY,
) -> float:
    """Compute the Reynolds number for the current speed and ship geometry.

    Args:
        velocity: Ship speed in meters per second (converted externally if needed).
        length: Characteristic length (hull length).
        density: Water density (kg/m³).
        viscosity: Dynamic viscosity (Pa·s).

    Returns:
        Dimensionless Reynolds number or 0 when inputs are invalid.
    """
    if velocity <= 0 or viscosity <= 0 or length <= 0:
        return 0.0
    return (density * velocity * length) / viscosity


def friction_coefficient_cf(reynolds: float) -> float:
    """Approximate the skin friction coefficient via the Prandtl-Schlichting formula."""
    if reynolds <= 0:
        return 0.0
    log_re = np.log10(reynolds)
    if log_re <= 2:
        return 0.0
    return 0.075 / np.power(log_re - 2.0, 2.0)


def delta_roughness(cf_dirty: float, cf_clean: float = 0.003) -> float:
    """Return the friction increase compared to a clean hull baseline."""
    delta = cf_dirty - cf_clean
    return float(np.clip(delta, 0.0, None))


def power_penalty(delta_roughness_value: float, velocity: float) -> float:
    """Estimate additional effective power proportional to ΔR × speed (nautical)."""
    if delta_roughness_value <= 0 or velocity <= 0:
        return 0.0
    return float(delta_roughness_value * velocity)
