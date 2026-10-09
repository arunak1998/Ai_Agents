from datetime import date, timedelta

import pytest
import requests

from travel_planner.services import currency, search, weather
from travel_planner.services.budget import SHARES, budget_targets


def test_budget_shares_sum_to_one_for_every_style():
    for style, shares in SHARES.items():
        assert sum(shares.values()) == pytest.approx(1.0), style


def test_budget_targets_split_the_total():
    targets = budget_targets(100000, "standard")
    assert targets["Stay"] == 32000
    assert sum(targets.values()) == pytest.approx(100000)


# ---- weather -----------------------------------------------------------------------------------------------------

DAILY = {
    "time": ["2026-10-19", "2026-10-20", "2026-10-21"],
    "weathercode": [61, 3, 0],
    "temperature_2m_min": [9.0, 10.0, None],
    "temperature_2m_max": [14.0, 15.0, None],
    "precipitation_probability_max": [70, None, None],
}


def test_parse_forecast_maps_codes_and_drops_empty_days():
    days = weather.parse_forecast(DAILY)
    assert [d.summary for d in days] == ["Light rain", "Overcast"]
    assert days[1].rain_chance == 0


def test_get_forecast_skips_the_network_beyond_the_window(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail("network should not be used"))
    assert weather.get_forecast("London", date.today() + timedelta(days=40), 3) == []


def test_get_forecast_returns_only_trip_days(monkeypatch):
    class Reply:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    def fake_get(url, **kwargs):
        if url == weather.GEOCODE_URL:
            return Reply({"results": [{"latitude": 1, "longitude": 2}]})
        return Reply({"daily": DAILY})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(weather, "date", type("D", (date,), {"today": staticmethod(lambda: date(2026, 10, 15))}))

    days = weather.get_forecast("London", date(2026, 10, 20), 1)

    assert [d.date for d in days] == [date(2026, 10, 20)]


def test_get_forecast_returns_empty_when_the_api_fails(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", boom)
    assert weather.get_forecast("London", date.today(), 3) == []


# ---- currency ----------------------------------------------------------------------------------------------------


def test_convert_uses_the_live_rate(monkeypatch):
    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return {"rates": {"INR": 105.0}}

    monkeypatch.setattr(requests, "get", lambda *a, **k: Reply())
    assert currency.convert(10, "gbp", "inr") == 1050


def test_convert_raises_instead_of_guessing(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", boom)
    with pytest.raises(currency.CurrencyError):
        currency.convert(10, "GBP", "INR")


# ---- search ------------------------------------------------------------------------------------------------------


def test_format_results_is_truncated():
    results = [{"title": "T" * 800, "body": "B" * 800, "href": "http://x"}]
    assert len(search.format_results(results)) == search.MAX_CHARS


def test_search_falls_back_to_the_next_backend(monkeypatch):
    tried = []

    class FakeDDGS:
        def text(self, query, max_results, backend):
            tried.append(backend)
            if backend == "bing":
                raise RuntimeError("No results found.")
            return [{"title": "Hotel", "body": "Nice", "href": "http://h"}]

    monkeypatch.setattr(search, "DDGS", FakeDDGS)

    assert "Hotel" in search.web_search("hotels in London")
    assert tried == ["bing", "yahoo"]


def test_search_reports_unavailable_when_every_backend_fails(monkeypatch):
    class FakeDDGS:
        def text(self, query, max_results, backend):
            raise RuntimeError("No results found.")

    monkeypatch.setattr(search, "DDGS", FakeDDGS)
    assert "Search unavailable" in search.web_search("hotels in London")
