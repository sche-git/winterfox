"""Brave search provider."""

import logging

import httpx

from .base import SearchResult

logger = logging.getLogger(__name__)


class BraveSearchProvider:
    """Brave search provider (privacy-focused)."""

    def __init__(self, api_key: str):
        """
        Initialize Brave provider.

        Args:
            api_key: Brave API key
        """
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self._name = "brave"
        self._cost_per_search = 0.001  # Approximate

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
        Execute Brave search.

        Args:
            query: Search query
            max_results: Maximum results to return
            **kwargs: Additional options

        Returns:
            List of search results
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                headers={"X-Subscription-Token": self.api_key},
                params={"q": query, "count": max_results},
                timeout=30.0,
            )

            response.raise_for_status()
            data = response.json()

            results = []
            for r in data.get("web", {}).get("results", []):
                results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("description", ""),
                        source=self.name,
                    )
                )

            return results
