"""Rough split of a trip budget by category, passed to the writer as a target."""

# Shares of the total budget; each row sums to 1.0
SHARES = {
    "budget": {"Flights": 0.30, "Stay": 0.30, "Food": 0.20, "Local transport": 0.08, "Activities": 0.12},
    "standard": {"Flights": 0.30, "Stay": 0.32, "Food": 0.18, "Local transport": 0.08, "Activities": 0.12},
    "luxury": {"Flights": 0.28, "Stay": 0.40, "Food": 0.15, "Local transport": 0.07, "Activities": 0.10},
}


def budget_targets(total: float, style: str) -> dict[str, float]:
    return {category: round(total * share, 2) for category, share in SHARES[style].items()}
