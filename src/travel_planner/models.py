"""Data models: what the user asks for, what the LLM must return, and what we measured."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Style = Literal["budget", "standard", "luxury"]
TimeOfDay = Literal["Morning", "Afternoon", "Evening"]


class TripRequest(BaseModel):
    origin: str
    destination: str
    start_date: date
    days: int = Field(ge=1, le=21)
    travelers: int = Field(default=1, ge=1, le=20)
    budget: float = Field(gt=0)
    currency: str = "INR"
    style: Style = "standard"
    interests: list[str] = []
    notes: str = ""

    @property
    def nights(self) -> int:
        return max(self.days - 1, 0)

    def to_prompt(self) -> str:
        lines = [
            f"Trip: {self.origin} -> {self.destination} -> {self.origin}",
            f"Start date: {self.start_date.isoformat()} ({self.days} days, {self.nights} nights)",
            f"Travelers: {self.travelers}",
            f"Total budget for the whole group: {self.budget:,.0f} {self.currency}",
            f"Travel style: {self.style}",
        ]
        if self.interests:
            lines.append(f"Interests: {', '.join(self.interests)}")
        if self.notes.strip():
            lines.append(f"Extra notes: {self.notes.strip()}")
        return "\n".join(lines)


class Activity(BaseModel):
    time: TimeOfDay
    title: str
    details: str = Field(description="One or two sentences: what to do and why it fits.")
    est_cost: float = Field(
        description="Entry fees, tours or transfers for the whole group, in the budget currency. 0 if free."
    )


class DayPlan(BaseModel):
    day: int
    title: str = Field(description="Short theme for the day, e.g. 'Old town and river walk'.")
    activities: list[Activity]
    meals: str = Field(description="Where to eat today, with cuisine and rough price per person.")
    tip: str = Field(description="One practical tip for the day, e.g. based on the weather.")


class BudgetLine(BaseModel):
    category: str = Field(description="Flights, Stay, Food, Local transport or Activities.")
    amount: float = Field(description="Estimated total for the whole group in the budget currency.")
    notes: str = Field(description="What the number is based on.")


class TripPlan(BaseModel):
    """The final itinerary. All money is in the budget currency, for the whole group."""

    title: str
    summary: str = Field(description="Two or three sentences describing the trip.")
    flights: str = Field(description="Outbound and return flight options with airline, timing and price.")
    stay: str = Field(description="Recommended hotel: name, area, price per night, why it fits.")
    local_transport: str
    days: list[DayPlan]
    budget: list[BudgetLine]
    notes: list[str] = Field(description="Assumptions and things to verify before booking.")

    @property
    def total_cost(self) -> float:
        return sum(line.amount for line in self.budget)


class ForecastDay(BaseModel):
    date: date
    summary: str
    temp_min: float
    temp_max: float
    rain_chance: int


class Usage(BaseModel):
    """Token usage and wall-clock time for one planning run."""

    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class PlanResult(BaseModel):
    request: TripRequest
    plan: TripPlan
    forecast: list[ForecastDay]
    usage: Usage
