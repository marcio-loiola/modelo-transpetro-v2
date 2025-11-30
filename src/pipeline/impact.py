"""Convert excess consumption into economic and emissions impacts."""

CO2_PER_TON = 3.114
FUEL_PRICE_USD_PER_TON = 500.0


def compute_additional_impacts(
    baseline: float,
    excess_ratio: float,
    fuel_price_usd_per_ton: float = FUEL_PRICE_USD_PER_TON,
) -> dict[str, float]:
    """Return additional fuel, cost, and CO₂ for a given excess ratio.

    Args:
        baseline: Baseline fuel estimate (tons) without fouling.
        excess_ratio: Estimated percentage above baseline (+/-).
        fuel_price_usd_per_ton: Unit cost of fuel (default from config).

    Returns:
        Dict with extra tons and harmonized USD/CO₂ values.
    """
    additional_fuel = baseline * excess_ratio
    additional_cost = additional_fuel * fuel_price_usd_per_ton
    additional_co2 = additional_fuel * CO2_PER_TON
    return {
        "additional_fuel_tons": float(additional_fuel),
        "additional_cost_usd": float(additional_cost),
        "additional_co2_tons": float(additional_co2),
    }