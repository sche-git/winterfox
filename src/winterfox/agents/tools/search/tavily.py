"""Tavily search provider."""

import logging

from tavily import TavilyClient

from .base import SearchResult

logger = logging.getLogger(__name__)


class TavilySearchProvider:
    """Tavily search provider (best for research)."""

    def __init__(self, api_key: str):
        """
        Initialize Tavily provider.

        Args:
            api_key: Tavily API key
        """
        self.client = TavilyClient(api_key=api_key)
        self._name = "tavily"
        self._cost_per_search = 0.001  # ~$1 per 1000 searches

    @property
    def name(self) -> str:
        return self._name

    @property
    def cost_per_search(self) -> float:
        return self._cost_per_search

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs,
    ) -> list[SearchResult]:
        """
        Execute Tavily search.

        Args:
            query: Search query
            max_results: Maximum results to return
            **kwargs: Additional options (search_depth, include_answer, etc.)

        Returns:
            List of search results
        """
        search_depth = kwargs.get("search_depth", "advanced")
        include_answer = kwargs.get("include_answer", True)

        # Tavily search is synchronous
        response = self.client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=include_answer,
        )

        results = []
        for r in response.get("results", []):
            results.append(
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", ""),
                    score=r.get("score", 0.0),
                    published_date=r.get("published_date"),
                    source=self.name,
                )
            )

        return results
