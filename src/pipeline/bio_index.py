"""Translate excess ratios into normalized biofouling scores and buckets."""

import numpy as np

SIGMOID_K = 10.0
SIGMOID_MIDPOINT = 0.10


def bio_index_from_excess_ratio(
    excess_ratio: float,
    use_sigmoid: bool = True,
    k: float = SIGMOID_K,
    midpoint: float = SIGMOID_MIDPOINT,
) -> float:
    """Convert a target excess ratio into a [0, 1] biofouling signal.

    Args:
        excess_ratio: Ratio of real over baseline consumption (-.5 to 1.0 range expected).
        use_sigmoid: Use sigmoid scaling when True, linear clipping otherwise.
        k: Sigmoid steepness parameter.
        midpoint: Sigmoid center point corresponding to index 0.5.

    Returns:
        Normalized biofouling index within 0-1.
    """
    if not use_sigmoid:
        return float(np.clip(excess_ratio, 0.0, 1.0))
    x = excess_ratio
    val = 1.0 / (1.0 + np.exp(-k * (x - midpoint)))
    return float(np.clip(val, 0.0, 1.0))


def bio_index_0_10(excess_ratio: float, **kwargs) -> float:
    """Scale the normalized index onto a 0-10 reporting scale."""
    return float(np.round(bio_index_from_excess_ratio(excess_ratio, **kwargs) * 10.0, 1))


def bio_class_from_excess_ratio(er: float) -> str:
    """Map an excess ratio into a qualitative classification."""
    if np.isnan(er):
        return 'Unknown'
    if er < 0.10:
        return 'Leve'
    if er < 0.20:
        return 'Moderada'
    return 'Severa'