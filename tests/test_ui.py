from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.conftest import make_result
from travel_planner import planner
from travel_planner.planner import Finished, ForecastReady, Writing

APP = str(Path(__file__).parents[1] / "src/travel_planner/ui/app.py")


def test_app_asks_for_an_api_key_when_missing(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    app = AppTest.from_file(APP).run()
    assert "LLM_API_KEY is not set" in app.error[0].value


def test_welcome_screen_shows_before_planning(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test")
    app = AppTest.from_file(APP).run()
    assert not app.exception
    assert app.title[0].value == "🌍 AI Travel Planner"


def test_planning_renders_every_part_of_the_result(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test")
    result = make_result(total=90000)
    monkeypatch.setattr(planner, "plan_trip", lambda request: iter([ForecastReady([]), Writing(), Finished(result)]))

    app = AppTest.from_file(APP, default_timeout=30).run()
    next(b for b in app.sidebar.button if "Plan" in b.label).click().run()

    assert not app.exception
    metrics = {m.label: m.value for m in app.metric}
    assert metrics["Estimated cost"] == "90,000 INR"
    assert metrics["Tokens used"] == "6,500"
    assert [e.label for e in app.expander] == ["Day 1: Theme 1", "Day 2: Theme 2"]
    assert [t.label for t in app.tabs][0] == "📅 Itinerary"
    assert "Within budget" in app.success[-1].value or any("Within budget" in s.value for s in app.success)


def test_planner_errors_are_shown_not_raised(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test")

    def broken(request):
        raise RuntimeError("gateway down")
        yield

    monkeypatch.setattr(planner, "plan_trip", broken)

    app = AppTest.from_file(APP, default_timeout=30).run()
    next(b for b in app.sidebar.button if "Plan" in b.label).click().run()

    assert not app.exception
    assert any("gateway down" in e.value for e in app.error)
