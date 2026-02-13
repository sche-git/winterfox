"""
Base search provider protocol and manager.

Supports multiple search providers with automatic fallback.
"""

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result."""

    title: str
    url: str
    snippet: str
    score: float = 0.0
    published_date: str | None = None
    source: str | None = None  # Which provider returned this


class SearchProvider(Protocol):
    """Protocol for search providers."""

    @property
    def name(self) -> str:
        """Provider name (tavily, brave, serper, etc.)."""
        ...

    @property
    def cost_per_search(self) -> float:
        """Approximate cost in USD per search."""
        ...

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs,
    ) -> list[SearchResult]:
        """
        Execute search and return results.

        Args:
            query: Search query
            max_results: Maximum results to return
            **kwargs: Provider-specific options

        Returns:
            List of search results
        """
        ...


class SearchManager:
    """Manages multiple search providers with fallback."""

    def __init__(
        self,
        providers: list[SearchProvider],
        fallback_enabled: bool = True,
    ):
        """
        Initialize search manager.

        Args:
            providers: List of search providers (in priority order)
            fallback_enabled: Enable automatic fallback on failure
        """
        self.providers = providers
        self.fallback_enabled = fallback_enabled

    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[SearchResult]:
        """
        Search using providers with automatic fallback.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            List of search results

        Raises:
            RuntimeError: If all providers fail
        """
        last_error = None

        for provider in self.providers:
            try:
                logger.debug(f"Trying search provider: {provider.name}")
                results = await provider.search(query, max_results)

                if results:
                    logger.info(
                        f"Search via {provider.name}: {len(results)} results for '{query[:50]}...'"
                    )
                    return results

                logger.warning(f"No results from {provider.name}")

            except Exception as e:
                logger.warning(f"Search failed for {provider.name}: {e}")
                last_error = e

                if not self.fallback_enabled:
                    raise

        # All providers failed
        if last_error:
            raise RuntimeError(
                f"All search providers failed. Last error: {last_error}"
            ) from last_error

        return []
