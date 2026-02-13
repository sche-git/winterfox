"""Serper search provider (Google results)."""

import logging

import httpx

from .base import SearchResult

logger = logging.getLogger(__name__)


class SerperSearchProvider:
    """Serper.dev search provider (Google results)."""

    def __init__(self, api_key: str):
        """
        Initialize Serper provider.

        Args:
            api_key: Serper API key
        """
        self.api_key = api_key
        self.url = "https://google.serper.dev/search"
        self._name = "serper"
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
        Execute Serper search.

        Args:
            query: Search query
            max_results: Maximum results to return
            **kwargs: Additional options

        Returns:
            List of search results
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                headers={"X-API-KEY": self.api_key},
                json={"q": query, "num": max_results},
                timeout=30.0,
            )

            response.raise_for_status()
            data = response.json()

            results = []
            for r in data.get("organic", []):
                results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("link", ""),
                        snippet=r.get("snippet", ""),
                        published_date=r.get("date"),
                        source=self.name,
                    )
                )

            return results
