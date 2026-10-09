"""LangChain tools the research agent can call. Each is a thin wrapper over a service."""

from langchain_core.tools import tool

from travel_planner.services.currency import CurrencyError, convert
from travel_planner.services.search import web_search


@tool
def search_flights(origin: str, destination: str, depart_date: str, return_date: str) -> str:
    """Find round-trip flight options and typical prices. Dates are YYYY-MM-DD."""
    return web_search(f"round trip flights {origin} to {destination} {depart_date} to {return_date} price airline")


@tool
def search_hotels(city: str, style: str = "standard") -> str:
    """Find well-reviewed hotels in a city with nightly prices. Style: budget, standard or luxury."""
    return web_search(f"best {style} hotels in {city} price per night reviews")


@tool
def search_attractions(city: str, interests: str = "") -> str:
    """Find top attractions and activities in a city, optionally tailored to the traveler's interests."""
    return web_search(f"top attractions things to do in {city} {interests}".strip())


@tool
def search_restaurants(city: str) -> str:
    """Find popular restaurants and local food in a city with typical prices."""
    return web_search(f"best local restaurants to eat in {city} price")


@tool
def search_local_transport(city: str) -> str:
    """Find how to get around a city (metro, bus, taxi) with typical fares."""
    return web_search(f"getting around {city} public transport metro taxi fares tourists")


@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount between currencies using a live exchange rate (ISO codes such as USD, INR)."""
    try:
        converted = convert(amount, from_currency, to_currency)
        return f"{amount:,.2f} {from_currency.upper()} = {converted:,.2f} {to_currency.upper()}"
    except CurrencyError as error:
        return str(error)


TOOLS = [
    search_flights,
    search_hotels,
    search_attractions,
    search_restaurants,
    search_local_transport,
    convert_currency,
]
