"""Streamlit rendering of a finished trip plan."""

import os

import pandas as pd
import streamlit as st

from travel_planner.export import plan_to_markdown
from travel_planner.models import DayPlan, ForecastDay, PlanResult

TIME_ICONS = {"Morning": "🌅", "Afternoon": "☀️", "Evening": "🌙"}


def forecast_for_day(result: PlanResult, day: DayPlan) -> ForecastDay | None:
    for entry in result.forecast:
        if (entry.date - result.request.start_date).days == day.day - 1:
            return entry
    return None


def render_summary(result: PlanResult) -> None:
    plan, request = result.plan, result.request
    st.header(plan.title)
    st.caption(
        f"{request.origin} → {request.destination} · {request.days} days from {request.start_date:%d %b %Y} · "
        f"{request.travelers} traveler(s) · {request.style} style"
    )
    st.write(plan.summary)

    saving = request.budget - plan.total_cost
    columns = st.columns(4)
    columns[0].metric("Estimated cost", f"{plan.total_cost:,.0f} {request.currency}")
    columns[1].metric(
        "Your budget",
        f"{request.budget:,.0f} {request.currency}",
        delta=f"{abs(saving):,.0f} {'under' if saving >= 0 else 'over'}",
        delta_color="normal" if saving >= 0 else "inverse",
    )
    columns[2].metric("Days", request.days)
    columns[3].metric("Tokens used", f"{result.usage.total_tokens:,}")

    st.download_button(
        "⬇️ Download as Markdown",
        plan_to_markdown(result),
        file_name=f"{request.destination.lower().replace(' ', '-')}-trip.md",
        mime="text/markdown",
    )


def render_itinerary(result: PlanResult) -> None:
    currency = result.request.currency
    for day in result.plan.days:
        with st.expander(f"Day {day.day}: {day.title}", expanded=day.day == 1):
            weather = forecast_for_day(result, day)
            if weather:
                st.caption(
                    f"🌦️ {weather.summary}, {weather.temp_min:.0f}–{weather.temp_max:.0f}°C, "
                    f"{weather.rain_chance}% chance of rain"
                )
            for activity in day.activities:
                cost = f" · {activity.est_cost:,.0f} {currency}" if activity.est_cost else " · free"
                st.markdown(f"**{TIME_ICONS[activity.time]} {activity.time}: {activity.title}**{cost}")
                st.write(activity.details)
            st.info(f"🍽️ {day.meals}")
            st.success(f"💡 {day.tip}")


def render_budget(result: PlanResult) -> None:
    plan, request = result.plan, result.request
    amount = f"Amount ({request.currency})"
    table = pd.DataFrame([{"Category": b.category, amount: round(b.amount), "Based on": b.notes} for b in plan.budget])
    left, right = st.columns([3, 2])
    left.dataframe(table, hide_index=True, width="stretch")
    right.bar_chart(table.set_index("Category")[amount])
    if plan.total_cost > request.budget:
        st.warning(f"Over budget by {plan.total_cost - request.budget:,.0f} {request.currency}.")
    else:
        st.success(f"Within budget, with {request.budget - plan.total_cost:,.0f} {request.currency} to spare.")


def render_travel_details(result: PlanResult) -> None:
    plan = result.plan
    st.subheader("✈️ Flights")
    st.write(plan.flights)
    st.subheader("🏨 Where to stay")
    st.write(plan.stay)
    st.subheader("🚇 Getting around")
    st.write(plan.local_transport)
    if plan.notes:
        st.subheader("📝 Before you book")
        for note in plan.notes:
            st.markdown(f"- {note}")


def render_weather(result: PlanResult) -> None:
    if not result.forecast:
        st.info("No live forecast yet: forecasts cover the next 16 days. The plan uses typical seasonal weather.")
        return
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Date": f"{day.date:%a %d %b}",
                    "Conditions": day.summary,
                    "Low °C": round(day.temp_min),
                    "High °C": round(day.temp_max),
                    "Rain chance %": day.rain_chance,
                }
                for day in result.forecast
            ]
        ),
        hide_index=True,
        width="stretch",
    )


def render_usage(result: PlanResult) -> None:
    usage = result.usage
    columns = st.columns(4)
    columns[0].metric("Input tokens", f"{usage.input_tokens:,}")
    columns[1].metric("Output tokens", f"{usage.output_tokens:,}")
    columns[2].metric("Total tokens", f"{usage.total_tokens:,}")
    columns[3].metric("Time", f"{usage.seconds:.0f} s")
    st.caption(
        f"Model: {os.getenv('LLM_MODEL', 'gpt-5-mini')}. Tokens cover research, writing and every LLM call in this run."
    )


def render_result(result: PlanResult) -> None:
    render_summary(result)
    itinerary, budget, travel, weather, usage = st.tabs(
        ["📅 Itinerary", "💰 Budget", "✈️ Flights & stay", "🌦️ Weather", "📊 Run details"]
    )
    with itinerary:
        render_itinerary(result)
    with budget:
        render_budget(result)
    with travel:
        render_travel_details(result)
    with weather:
        render_weather(result)
    with usage:
        render_usage(result)
