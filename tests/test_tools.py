from travel_planner import tools
from travel_planner.services.currency import CurrencyError


def test_the_agent_gets_the_expected_tools():
    assert [t.name for t in tools.TOOLS] == [
        "search_flights",
        "search_hotels",
        "search_attractions",
        "search_restaurants",
        "search_local_transport",
        "convert_currency",
    ]


def test_search_tools_build_queries_from_their_arguments(monkeypatch):
    queries = []
    monkeypatch.setattr(tools, "web_search", lambda query: queries.append(query) or "results")

    tools.search_flights.invoke(
        {"origin": "Chennai", "destination": "London", "depart_date": "2026-10-19", "return_date": "2026-10-24"}
    )
    tools.search_hotels.invoke({"city": "London", "style": "luxury"})

    assert "Chennai to London 2026-10-19 to 2026-10-24" in queries[0]
    assert "luxury hotels in London" in queries[1]


def test_convert_currency_formats_the_result(monkeypatch):
    monkeypatch.setattr(tools, "convert", lambda amount, source, target: 1050.0)
    result = tools.convert_currency.invoke({"amount": 10, "from_currency": "gbp", "to_currency": "inr"})
    assert result == "10.00 GBP = 1,050.00 INR"


def test_convert_currency_reports_errors_to_the_agent(monkeypatch):
    def fail(*args):
        raise CurrencyError("rate unavailable")

    monkeypatch.setattr(tools, "convert", fail)
    result = tools.convert_currency.invoke({"amount": 1, "from_currency": "GBP", "to_currency": "INR"})
    assert result == "rate unavailable"
