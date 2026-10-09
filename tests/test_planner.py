from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from tests.conftest import make_plan, make_request
from travel_planner import planner, tools
from travel_planner.planner import (
    Finished,
    ForecastReady,
    Revising,
    ToolFinished,
    ToolStarted,
    Writing,
    core_tool_calls,
    format_forecast,
    sum_usage,
)

CORE = ["search_flights", "search_hotels", "search_attractions", "search_restaurants", "search_local_transport"]


class ScriptedModel(GenericFakeChatModel):
    """Plays back AI messages for the research reviewer and canned TripPlans for the writer."""

    plans: list = []

    def bind_tools(self, tools, **kwargs):
        return self

    def with_structured_output(self, schema, **kwargs):
        return RunnableLambda(lambda messages: self.plans.pop(0))


def complete() -> AIMessage:
    return AIMessage(content="Research complete.")


def convert_turn() -> AIMessage:
    call = {
        "name": "convert_currency",
        "args": {"amount": 10, "from_currency": "GBP", "to_currency": "INR"},
        "id": "c1",
    }
    return AIMessage(content="", tool_calls=[call])


def run(monkeypatch, replies, plans, request=None):
    monkeypatch.setattr(tools, "web_search", lambda query: f"results for: {query}")
    monkeypatch.setattr(tools, "convert", lambda amount, source, target: amount * 100)
    monkeypatch.setattr(planner, "get_forecast", lambda *args: [])
    llm = ScriptedModel(messages=iter(replies), plans=plans)
    return list(planner.plan_trip(request or make_request(), llm=llm))


def test_core_searches_are_built_from_the_request():
    calls = {c["name"]: c["args"] for c in core_tool_calls(make_request(days=3))}

    assert list(calls) == CORE
    assert calls["search_flights"] == {
        "origin": "Chennai",
        "destination": "London",
        "depart_date": "2026-10-19",
        "return_date": "2026-10-21",
    }
    assert calls["search_attractions"]["interests"] == "History"


def test_events_arrive_in_order_and_end_with_the_result(monkeypatch):
    events = run(monkeypatch, [complete()], [make_plan(total=90000)])

    kinds = [type(e) for e in events]
    assert kinds == [ForecastReady, *[ToolStarted] * 5, *[ToolFinished] * 5, Writing, Finished]
    assert sorted(e.name for e in events if isinstance(e, ToolFinished)) == sorted(CORE)
    assert events[-1].result.plan.total_cost == 90000


def test_the_agent_can_fill_a_gap_with_another_tool(monkeypatch):
    events = run(monkeypatch, [convert_turn(), complete()], [make_plan()])

    extra = [e for e in events if isinstance(e, ToolFinished) and e.name == "convert_currency"]
    assert len(extra) == 1
    assert extra[0].output == "10.00 GBP = 1,000.00 INR"


def test_a_plan_over_budget_is_revised_once(monkeypatch):
    events = run(monkeypatch, [complete()], [make_plan(total=150000), make_plan(total=95000)])

    revising = [e for e in events if isinstance(e, Revising)]
    assert len(revising) == 1 and revising[0].total == 150000 and revising[0].budget == 100000
    assert events[-1].result.plan.total_cost == 95000


def test_the_writer_receives_research_forecast_and_targets(monkeypatch):
    seen = []

    class SpyModel(ScriptedModel):
        def with_structured_output(self, schema, **kwargs):
            return RunnableLambda(lambda messages: seen.append(messages) or self.plans.pop(0))

    monkeypatch.setattr(tools, "web_search", lambda query: f"results for: {query}")
    monkeypatch.setattr(planner, "get_forecast", lambda *args: [])
    llm = SpyModel(messages=iter([complete()]), plans=[make_plan()])

    list(planner.plan_trip(make_request(), llm=llm))

    brief = seen[0][1].content
    assert "results for: best standard hotels in London" in brief
    assert "Budget targets (INR)" in brief
    assert "No forecast available" in brief


def test_a_runaway_review_loop_still_produces_a_plan(monkeypatch):
    monkeypatch.setattr(planner, "RECURSION_LIMIT", 4)
    # the model keeps asking for the same conversion, so the agent never finishes
    event_list = run(monkeypatch, [convert_turn() for _ in range(50)], [make_plan()])

    assert isinstance(event_list[-1], Finished)


def test_format_forecast_without_data_says_so():
    assert "typical weather" in format_forecast([])


def test_sum_usage_adds_every_model():
    class Handler:
        usage_metadata = {
            "gpt-5-mini": {"input_tokens": 100, "output_tokens": 20},
            "other": {"input_tokens": 5, "output_tokens": 1},
        }

    usage = sum_usage(Handler(), seconds=2.5)

    assert (usage.input_tokens, usage.output_tokens, usage.total_tokens, usage.seconds) == (105, 21, 126, 2.5)
