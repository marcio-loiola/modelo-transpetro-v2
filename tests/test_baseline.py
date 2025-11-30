from src.pipeline.baseline import calculate_theoretical_power, compute_baseline_consumption

def test_theoretical_power_zero():
    assert calculate_theoretical_power(0, 10) == 0.0

def test_baseline_positive():
    p = calculate_theoretical_power(10000, 10)
    b = compute_baseline_consumption(p, 2, 1e-4)
    assert b >= 0.0