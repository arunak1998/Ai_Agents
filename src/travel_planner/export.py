"""Render a finished plan as a Markdown document."""

from travel_planner.models import PlanResult


def plan_to_markdown(result: PlanResult) -> str:
    plan, request = result.plan, result.request
    lines = [
        f"# {plan.title}",
        "",
        f"{request.origin} → {request.destination} · {request.days} days from {request.start_date:%d %b %Y} · "
        f"{request.travelers} traveler(s) · {request.style} style",
        "",
        plan.summary,
        "",
        "## Flights",
        plan.flights,
        "",
        "## Stay",
        plan.stay,
        "",
        "## Getting around",
        plan.local_transport,
        "",
        "## Itinerary",
    ]
    for day in plan.days:
        lines += ["", f"### Day {day.day}: {day.title}"]
        lines += [
            f"- **{a.time}**: {a.title}. {a.details} ({a.est_cost:,.0f} {request.currency})" for a in day.activities
        ]
        lines += [f"- **Meals**: {day.meals}", f"- **Tip**: {day.tip}"]

    lines += ["", "## Budget", "", "| Category | Amount | Notes |", "|---|---:|---|"]
    lines += [f"| {b.category} | {b.amount:,.0f} {request.currency} | {b.notes} |" for b in plan.budget]
    lines += [f"| **Total** | **{plan.total_cost:,.0f} {request.currency}** | Budget: {request.budget:,.0f} |"]

    if plan.notes:
        lines += ["", "## Notes"] + [f"- {note}" for note in plan.notes]
    lines += ["", "> AI-generated plan. Verify prices, opening hours and entry rules before booking."]
    return "\n".join(lines) + "\n"
