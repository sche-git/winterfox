"""Multi-provider search tools."""

from .base import SearchProvider, SearchResult, SearchManager
from .tavily import TavilySearchProvider
from .brave import BraveSearchProvider
from .serper import SerperSearchProvider

# Global search manager instance (will be configured at runtime)
_search_manager: SearchManager | None = None


def configure_search(providers: list[SearchProvider], fallback_enabled: bool = True):
    """
    Configure global search manager.

    Args:
        providers: List of search providers
        fallback_enabled: Enable automatic fallback
    """
    global _search_manager
    _search_manager = SearchManager(providers, fallback_enabled)


def get_search_manager() -> SearchManager:
    """Get configured search manager."""
    if _search_manager is None:
        raise RuntimeError(
            "Search not configured. Call configure_search() first."
        )
    return _search_manager


async def web_search(query: str, max_results: int = 10) -> list[dict]:
    """
    Perform web search using configured providers.

    This is the main search function that agents will use.

    Args:
        query: Search query
        max_results: Maximum results to return

    Returns:
        List of search results
    """
    manager = get_search_manager()
    results = await manager.search(query, max_results)

    # Convert to dict format for tool use
    return [
        {
            "title": r.title,
            "url": r.url,
            "snippet": r.snippet,
            "score": r.score,
            "published_date": r.published_date,
            "source": r.source,
        }
        for r in results
    ]


__all__ = [
    "SearchProvider",
    "SearchResult",
    "SearchManager",
    "TavilySearchProvider",
    "BraveSearchProvider",
    "SerperSearchProvider",
    "configure_search",
    "get_search_manager",
    "web_search",
]
