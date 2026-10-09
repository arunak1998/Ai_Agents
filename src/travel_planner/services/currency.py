"""Live exchange rates from open.er-api.com (free, no API key)."""

import requests

RATES_URL = "https://open.er-api.com/v6/latest"
TIMEOUT_SECONDS = 10


class CurrencyError(Exception):
    pass


def convert(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert an amount between currencies; raises CurrencyError instead of guessing a rate."""
    source, target = from_currency.upper(), to_currency.upper()
    try:
        response = requests.get(f"{RATES_URL}/{source}", timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return amount * response.json()["rates"][target]
    except (requests.RequestException, KeyError, ValueError) as error:
        raise CurrencyError(f"Could not convert {source} to {target}: {error}") from error
