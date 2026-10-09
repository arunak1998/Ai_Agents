"""Turn planner events into the one-line status messages shown while planning."""

from travel_planner.planner import ForecastReady, PlannerEvent, Revising, ToolFinished, ToolStarted, Writing

TOOL_LABELS = {
    "search_flights": "✈️ Flights",
    "search_hotels": "🏨 Hotels",
    "search_attractions": "🎟️ Attractions",
    "search_restaurants": "🍽️ Restaurants",
    "search_local_transport": "🚇 Local transport",
    "convert_currency": "💱 Currency conversion",
}


def describe_event(event: PlannerEvent) -> str | None:
    if isinstance(event, ForecastReady):
        if event.forecast:
            return f"🌦️ Weather forecast loaded for {len(event.forecast)} day(s)"
        return "🌦️ No forecast yet for these dates, using typical seasonal weather"
    if isinstance(event, ToolStarted):
        return f"🔎 Researching: {TOOL_LABELS.get(event.name, event.name)}..."
    if isinstance(event, ToolFinished):
        return f"✅ Found: {TOOL_LABELS.get(event.name, event.name)}"
    if isinstance(event, Writing):
        return "✍️ Writing your itinerary..."
    if isinstance(event, Revising):
        return f"♻️ First draft cost {event.total:,.0f}, over your {event.budget:,.0f} budget. Revising to fit..."
    return None
