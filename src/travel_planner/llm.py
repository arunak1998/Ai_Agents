"""The one place the LLM is created. Works with OpenAI or any OpenAI-compatible gateway."""

import os

from langchain_openai import ChatOpenAI

from travel_planner.settings import DEFAULT_MODEL, require_env

REQUEST_TIMEOUT_SECONDS = 60


def create_llm(**kwargs) -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("LLM_MODEL", DEFAULT_MODEL),
        api_key=require_env("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL") or None,
        reasoning_effort=os.getenv("LLM_REASONING_EFFORT") or None,
        timeout=REQUEST_TIMEOUT_SECONDS,  # a stalled request is retried instead of hanging the UI
        **kwargs,
    )
