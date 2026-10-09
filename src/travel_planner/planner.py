"""Plan a trip in three steps, reporting progress as events:

1. fetch the weather forecast (plain API call),
2. research: five searches run in parallel, then a tool-calling agent reviews them and fills any gaps,
3. write the itinerary as structured data (one LLM call, plus one revision if it goes over budget).
"""

import logging
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import timedelta

from langchain.agents import create_agent
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from travel_planner.llm import create_llm
from travel_planner.models import ForecastDay, PlanResult, TripPlan, TripRequest, Usage
from travel_planner.prompts import RESEARCH_PROMPT, WRITER_PROMPT
from travel_planner.services.budget import budget_targets
from travel_planner.services.weather import get_forecast
from travel_planner.tools import TOOLS

logger = logging.getLogger(__name__)

# The review step normally takes 1 step; the cap leaves room for a few gap-filling tool calls.
RECURSION_LIMIT = 10


@dataclass(frozen=True)
class ForecastReady:
    forecast: list[ForecastDay]


@dataclass(frozen=True)
class ToolStarted:
    name: str
    args: dict


@dataclass(frozen=True)
class ToolFinished:
    name: str
    output: str


@dataclass(frozen=True)
class Writing:
    pass


@dataclass(frozen=True)
class Revising:
    total: float
    budget: float


@dataclass(frozen=True)
class Finished:
    result: PlanResult


PlannerEvent = ForecastReady | ToolStarted | ToolFinished | Writing | Revising | Finished


def format_forecast(forecast: list[ForecastDay]) -> str:
    if not forecast:
        return "No forecast available; use typical weather for the season."
    return "\n".join(
        f"{day.date.isoformat()}: {day.summary}, {day.temp_min:.0f}-{day.temp_max:.0f}°C, "
        f"rain chance {day.rain_chance}%"
        for day in forecast
    )


def format_research(findings: list[ToolFinished]) -> str:
    return "\n\n".join(f"### {finding.name}\n{finding.output}" for finding in findings)


def core_tool_calls(request: TripRequest) -> list[dict]:
    """The five searches every trip needs, as tool calls with fixed arguments."""
    end = request.start_date + timedelta(days=request.days - 1)
    calls = [
        (
            "search_flights",
            {
                "origin": request.origin,
                "destination": request.destination,
                "depart_date": request.start_date.isoformat(),
                "return_date": end.isoformat(),
            },
        ),
        ("search_hotels", {"city": request.destination, "style": request.style}),
        ("search_attractions", {"city": request.destination, "interests": ", ".join(request.interests)}),
        ("search_restaurants", {"city": request.destination}),
        ("search_local_transport", {"city": request.destination}),
    ]
    return [{"name": name, "args": args, "id": f"core_{i}"} for i, (name, args) in enumerate(calls)]


def run_core_searches(calls: list[dict]) -> Iterator[ToolStarted | ToolFinished | ToolMessage]:
    """Run the searches in parallel; yield events as they start and finish, then the ToolMessages."""
    tools = {tool.name: tool for tool in TOOLS}
    for call in calls:
        yield ToolStarted(call["name"], call["args"])
    messages = {}
    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures = {pool.submit(tools[call["name"]].invoke, call["args"]): call for call in calls}
        for future in as_completed(futures):
            call = futures[future]
            output = str(future.result())
            messages[call["id"]] = ToolMessage(content=output, tool_call_id=call["id"], name=call["name"])
            yield ToolFinished(call["name"], output)
    yield from (messages[call["id"]] for call in calls)


def research(llm: BaseChatModel, request: TripRequest, config: dict) -> Iterator[ToolStarted | ToolFinished]:
    """Run the core searches, then let the agent review them and fill any gaps with more tool calls."""
    calls = core_tool_calls(request)
    history = [HumanMessage(content=request.to_prompt()), AIMessage(content="", tool_calls=calls)]
    for item in run_core_searches(calls):
        if isinstance(item, ToolMessage):
            history.append(item)
        else:
            yield item

    agent = create_agent(llm, tools=TOOLS, system_prompt=RESEARCH_PROMPT)
    for update in agent.stream({"messages": history}, config=config, stream_mode="updates"):
        for payload in update.values():
            for message in payload.get("messages", []):
                if isinstance(message, AIMessage):
                    for call in message.tool_calls:
                        yield ToolStarted(call["name"], call["args"])
                elif isinstance(message, ToolMessage):
                    yield ToolFinished(message.name, str(message.content))


def build_brief(request: TripRequest, forecast: list[ForecastDay], findings: list[ToolFinished]) -> str:
    targets = "\n".join(
        f"- {name}: {amount:,.0f}" for name, amount in budget_targets(request.budget, request.style).items()
    )
    return (
        f"{request.to_prompt()}\n\n"
        f"## Budget targets ({request.currency})\n{targets}\n\n"
        f"## Weather forecast\n{format_forecast(forecast)}\n\n"
        f"## Research notes\n{format_research(findings)}"
    )


def write_plan(llm: BaseChatModel, brief: str, config: dict) -> TripPlan:
    writer = llm.with_structured_output(TripPlan)
    return writer.invoke([SystemMessage(content=WRITER_PROMPT), HumanMessage(content=brief)], config=config)


def revise_plan(llm: BaseChatModel, brief: str, plan: TripPlan, request: TripRequest, config: dict) -> TripPlan:
    """Ask the writer to redo a plan whose total went over budget."""
    complaint = (
        f"Your plan totals {plan.total_cost:,.0f} {request.currency}, above the budget of "
        f"{request.budget:,.0f} {request.currency}. Rewrite the complete plan with cheaper choices "
        "(lower-priced stay, food and activities) so the total is within the budget. Do not mention revisions or "
        "earlier drafts anywhere in the plan."
    )
    writer = llm.with_structured_output(TripPlan)
    messages = [
        SystemMessage(content=WRITER_PROMPT),
        HumanMessage(content=brief),
        AIMessage(content=plan.model_dump_json()),
        HumanMessage(content=complaint),
    ]
    return writer.invoke(messages, config=config)


def sum_usage(handler: UsageMetadataCallbackHandler, seconds: float) -> Usage:
    per_model = handler.usage_metadata.values()
    return Usage(
        input_tokens=sum(m.get("input_tokens", 0) for m in per_model),
        output_tokens=sum(m.get("output_tokens", 0) for m in per_model),
        seconds=seconds,
    )


def plan_trip(request: TripRequest, llm: BaseChatModel | None = None) -> Iterator[PlannerEvent]:
    """Plan a trip, yielding progress events; the last event is Finished with the full result."""
    started = time.perf_counter()
    llm = llm or create_llm()
    usage_handler = UsageMetadataCallbackHandler()
    config = {"callbacks": [usage_handler], "recursion_limit": RECURSION_LIMIT}

    forecast = get_forecast(request.destination, request.start_date, request.days)
    yield ForecastReady(forecast)

    findings: list[ToolFinished] = []
    try:
        for event in research(llm, request, config):
            if isinstance(event, ToolFinished):
                findings.append(event)
            yield event
    except GraphRecursionError:
        # The agent kept searching; write the plan from what it found so far instead of failing.
        logger.warning("Research hit the step limit with %d result(s)", len(findings))

    yield Writing()
    brief = build_brief(request, forecast, findings)
    plan = write_plan(llm, brief, config)
    if plan.total_cost > request.budget:
        yield Revising(total=plan.total_cost, budget=request.budget)
        plan = revise_plan(llm, brief, plan, request, config)

    usage = sum_usage(usage_handler, time.perf_counter() - started)
    yield Finished(PlanResult(request=request, plan=plan, forecast=forecast, usage=usage))
