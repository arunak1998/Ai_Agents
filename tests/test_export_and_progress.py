from tests.conftest import make_result
from travel_planner.export import plan_to_markdown
from travel_planner.planner import ForecastReady, Revising, ToolFinished, ToolStarted, Writing
from travel_planner.ui.progress import describe_event


def test_markdown_contains_every_section():
    markdown = plan_to_markdown(make_result(total=90000))

    assert markdown.startswith("# 2 days in London")
    for heading in ("## Flights", "## Stay", "## Itinerary", "### Day 1: Theme 1", "## Budget", "## Notes"):
        assert heading in markdown
    assert "| **Total** | **90,000 INR** | Budget: 100,000 |" in markdown
    assert "**Morning**: British Museum" in markdown


def test_progress_messages():
    assert "2 day(s)" in describe_event(ForecastReady([1, 2]))
    assert "typical seasonal weather" in describe_event(ForecastReady([]))
    assert "Hotels" in describe_event(ToolStarted("search_hotels", {}))
    assert "Found" in describe_event(ToolFinished("search_flights", "x"))
    assert "Writing" in describe_event(Writing())
    assert "Revising" in describe_event(Revising(total=150000, budget=100000))
