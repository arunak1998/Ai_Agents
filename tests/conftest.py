from datetime import date

import pytest

from travel_planner.models import (
    Activity,
    BudgetLine,
    DayPlan,
    ForecastDay,
    PlanResult,
    TripPlan,
    TripRequest,
    Usage,
)


def make_request(**overrides) -> TripRequest:
    fields = {
        "origin": "Chennai",
        "destination": "London",
        "start_date": date(2026, 10, 19),
        "days": 2,
        "travelers": 2,
        "budget": 100000,
        "currency": "INR",
        "style": "standard",
        "interests": ["History"],
    }
    return TripRequest(**{**fields, **overrides})


def make_plan(total: float = 90000) -> TripPlan:
    def day(number: int) -> DayPlan:
        return DayPlan(
            day=number,
            title=f"Theme {number}",
            activities=[
                Activity(time="Morning", title="British Museum", details="Ancient history.", est_cost=0),
                Activity(time="Afternoon", title="Tower of London", details="Crown Jewels.", est_cost=5000),
                Activity(time="Evening", title="Borough Market", details="Street food.", est_cost=2000),
            ],
            meals="Pub lunch ~1500 INR/person.",
            tip="Carry an umbrella.",
        )

    return TripPlan(
        title="2 days in London",
        summary="A short history trip.",
        flights="MAA-LHR with Emirates, 60,000 INR.",
        stay="Bloomsbury hotel, 8,000 INR/night.",
        local_transport="Oyster card.",
        days=[day(1), day(2)],
        budget=[
            BudgetLine(category="Flights", amount=total * 0.6, notes="Round trip"),
            BudgetLine(category="Stay", amount=total * 0.4, notes="1 night"),
        ],
        notes=["Prices are estimates."],
    )


def make_result(total: float = 90000) -> PlanResult:
    return PlanResult(
        request=make_request(),
        plan=make_plan(total),
        forecast=[
            ForecastDay(date=date(2026, 10, 19), summary="Light rain", temp_min=9, temp_max=14, rain_chance=60),
        ],
        usage=Usage(input_tokens=5000, output_tokens=1500, seconds=30),
    )


@pytest.fixture
def request_factory():
    return make_request


@pytest.fixture
def result_factory():
    return make_result
