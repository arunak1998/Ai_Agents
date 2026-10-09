"""Keyless web search (DuckDuckGo) used by the research tools."""

import logging

from ddgs import DDGS

logger = logging.getLogger(__name__)

MAX_RESULTS = 5
# Individual search backends fail intermittently and on different queries, so try several in order.
BACKENDS = ("bing", "yahoo", "yandex", "auto")
MAX_CHARS = 1500  # keeps tool output (and therefore token use) bounded


def format_results(results: list[dict]) -> str:
    lines = [f"- {r.get('title', '').strip()}: {r.get('body', '').strip()} ({r.get('href', '')})" for r in results]
    return "\n".join(lines)[:MAX_CHARS]


def search_backends(query: str) -> list[dict]:
    """Return results from the first backend that has any; empty when all of them fail."""
    for backend in BACKENDS:
        try:
            results = DDGS().text(query, max_results=MAX_RESULTS, backend=backend)
        except Exception as error:
            logger.info("Backend %s found nothing for %r: %s", backend, query, error)
            continue
        if results:
            return results
    return []


def web_search(query: str) -> str:
    """Return a compact text summary of the top results, or a short notice if every backend fails."""
    results = search_backends(query)
    if not results:
        logger.warning("No search results for %r", query)
        return f"Search unavailable for '{query}'. Use your general knowledge and say prices are estimates."
    return format_results(results)
