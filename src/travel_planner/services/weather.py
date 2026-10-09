"""Daily forecast from Open-Meteo (free, no API key). Covers the next 16 days."""

import logging
from datetime import date, timedelta

import requests

from travel_planner.models import ForecastDay

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 10
MAX_FORECAST_DAYS = 16

# WMO weather interpretation codes, grouped
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with hail",
}


def describe(code: int) -> str:
    return WEATHER_CODES.get(code, "Mixed conditions")


def parse_forecast(daily: dict) -> list[ForecastDay]:
    return [
        ForecastDay(
            date=day,
            summary=describe(code),
            temp_min=low,
            temp_max=high,
            rain_chance=rain or 0,
        )
        for day, code, low, high, rain in zip(
            daily["time"],
            daily["weathercode"],
            daily["temperature_2m_min"],
            daily["temperature_2m_max"],
            daily["precipitation_probability_max"],
            strict=True,
        )
        if low is not None and high is not None  # the far end of the window can be empty
    ]


def get_forecast(city: str, start: date, days: int) -> list[ForecastDay]:
    """Forecast for the trip dates. Empty when the trip is beyond the 16-day window or the API fails."""
    if (start - date.today()).days >= MAX_FORECAST_DAYS:
        return []
    try:
        place = requests.get(GEOCODE_URL, params={"name": city, "count": 1}, timeout=TIMEOUT_SECONDS)
        place.raise_for_status()
        location = place.json()["results"][0]
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": MAX_FORECAST_DAYS,
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        forecast = parse_forecast(response.json()["daily"])
    except (requests.RequestException, KeyError, IndexError, ValueError) as error:
        logger.warning("Forecast unavailable for %r: %s", city, error)
        return []
    end = start + timedelta(days=days - 1)
    return [day for day in forecast if start <= day.date <= end]
