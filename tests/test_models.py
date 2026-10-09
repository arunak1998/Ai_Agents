import pytest
from pydantic import ValidationError

from tests.conftest import make_plan, make_request
from travel_planner.models import Usage


def test_request_prompt_lists_every_input():
    prompt = make_request(notes="vegetarian").to_prompt()
    assert "Chennai -> London" in prompt
    assert "2 days, 1 nights" in prompt
    assert "100,000 INR" in prompt
    assert "Interests: History" in prompt
    assert "vegetarian" in prompt


def test_request_rejects_invalid_values():
    with pytest.raises(ValidationError):
        make_request(budget=0)
    with pytest.raises(ValidationError):
        make_request(days=0)


def test_plan_total_is_the_sum_of_budget_lines_not_a_model_claim():
    assert make_plan(total=90000).total_cost == pytest.approx(90000)


def test_usage_total_tokens():
    assert Usage(input_tokens=10, output_tokens=5).total_tokens == 15
