"""Streamlit front end:  streamlit run src/travel_planner/ui/app.py"""

import os
from datetime import date, timedelta

import streamlit as st

from travel_planner.models import PlanResult, TripRequest
from travel_planner.planner import Finished, plan_trip
from travel_planner.ui.progress import describe_event
from travel_planner.ui.render import render_result

CURRENCIES = ["INR", "USD", "EUR", "GBP", "AUD", "SGD", "AED", "JPY"]
INTERESTS = ["History", "Food", "Nature", "Adventure", "Art & museums", "Shopping", "Nightlife", "Relaxation"]

st.set_page_config(page_title="AI Travel Planner", page_icon="🌍", layout="wide")


def render_form() -> TripRequest | None:
    """Show the trip form in the sidebar; return a request when the user submits it."""
    with st.sidebar:
        st.header("Plan your trip")
        with st.form("trip"):
            origin = st.text_input("From", "Chennai")
            destination = st.text_input("To", "London")
            start_date = st.date_input("Start date", date.today() + timedelta(days=14), min_value=date.today())
            days = st.slider("Days", 1, 14, 5)
            travelers = st.number_input("Travelers", 1, 20, 2)
            budget_column, currency_column = st.columns([2, 1])
            budget = budget_column.number_input("Total budget", min_value=1000, value=250000, step=5000)
            currency = currency_column.selectbox("Currency", CURRENCIES)
            style = st.select_slider("Style", ["budget", "standard", "luxury"], value="standard")
            interests = st.multiselect("Interests", INTERESTS, default=["History", "Food"])
            notes = st.text_area("Anything else?", placeholder="e.g. vegetarian food, travelling with kids")
            submitted = st.form_submit_button("🧭 Plan my trip", type="primary", width="stretch")

    if not submitted:
        return None
    return TripRequest(
        origin=origin.strip(),
        destination=destination.strip(),
        start_date=start_date,
        days=days,
        travelers=travelers,
        budget=budget,
        currency=currency,
        style=style,
        interests=interests,
        notes=notes,
    )


def run_planner(request: TripRequest) -> PlanResult | None:
    """Run the planner, showing each step as it happens."""
    with st.status(f"Planning your trip to {request.destination}...", expanded=True) as status:
        try:
            for event in plan_trip(request):
                if message := describe_event(event):
                    st.write(message)
                if isinstance(event, Finished):
                    status.update(label="Your itinerary is ready", state="complete", expanded=False)
                    return event.result
        except Exception as error:
            status.update(label="Planning failed", state="error")
            st.error(f"{error}")
    return None


def render_welcome() -> None:
    st.title("🌍 AI Travel Planner")
    st.write(
        "Fill in the form on the left. An AI agent researches live flights, hotels, places and weather, "
        "then writes a day-by-day itinerary that fits your budget."
    )
    steps = st.columns(3)
    steps[0].markdown("### 1. Research\nIt searches the web for flights, hotels, attractions, food and transport.")
    steps[1].markdown("### 2. Plan\nIt checks the forecast and writes a structured itinerary within your budget.")
    steps[2].markdown("### 3. Review\nBrowse the days, budget and weather, then download it as Markdown.")


def main() -> None:
    if not os.getenv("LLM_API_KEY"):
        st.error("LLM_API_KEY is not set. Copy `.env.example` to `.env`, add your key, and restart the app.")
        st.stop()

    request = render_form()
    if request:
        st.session_state.result = run_planner(request)

    result = st.session_state.get("result")
    if result:
        render_result(result)
    elif request is None:
        render_welcome()


main()
