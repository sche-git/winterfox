"""
Base adapter utilities shared across all LLM adapters.

Provides:
- Retry logic with exponential backoff
- Cost calculation
- Token counting
"""

import asyncio
import logging
from typing import Any, Callable, TypeVar

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AgentAuthenticationError(Exception):
    """Raised when an agent fails due to invalid or missing API key."""

    def __init__(self, provider: str, api_key_env: str):
        self.provider = provider
        self.api_key_env = api_key_env
        super().__init__(
            f"{provider} authentication failed. "
            f"Check that {api_key_env} is set to a valid API key."
        )


class BaseAdapter:
    """Base class with shared adapter utilities."""

    # Model pricing (per 1M tokens)
    PRICING = {
        # Anthropic
        "claude-opus-4-20251120": {"input": 15.0, "output": 75.0},
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        # Moonshot (Kimi)
        "kimi-2.5": {"input": 0.2, "output": 0.2},
        # OpenAI
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        # Default fallback
        "default": {"input": 1.0, "output": 3.0},
    }

    def __init__(self, model: str, api_key: str | None = None):
        """
        Initialize base adapter.

        Args:
            model: Model identifier
            api_key: API key for authentication
        """
        self.model = model
        self.api_key = api_key

    async def _with_retry(
        self,
        func: Callable[..., T],
        *args: Any,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> T:
        """
        Execute function with exponential backoff retry.

        Args:
            func: Async function to execute
            max_retries: Maximum retry attempts
            *args, **kwargs: Arguments for func

        Returns:
            Result from func

        Raises:
            Last exception if all retries fail
        """
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        ):
            with attempt:
                logger.debug(f"Attempt {attempt.retry_state.attempt_number}/{max_retries}")
                return await func(*args, **kwargs)

        # This should never be reached due to reraise=True, but satisfies type checker
        raise RuntimeError("Retry logic failed unexpectedly")

    def _calculate_cost(
        self, input_tokens: int, output_tokens: int, model: str | None = None
    ) -> float:
        """
        Calculate API cost based on token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name (defaults to self.model)

        Returns:
            Cost in USD
        """
        model_name = model or self.model
        pricing = self.PRICING.get(model_name, self.PRICING["default"])

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        total_cost = input_cost + output_cost
        logger.debug(
            f"Cost calculation: {input_tokens:,} input + {output_tokens:,} output = ${total_cost:.6f}"
        )

        return total_cost

    def _count_tokens_estimate(self, text: str) -> int:
        """
        Rough token count estimate (4 chars ≈ 1 token).

        For accurate counting, use tiktoken for OpenAI models or
        model-specific tokenizers.

        Args:
            text: Text to count

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def _parse_tool_results(self, tool_calls: list[dict[str, Any]]) -> str:
        """
        Format tool call results for display.

        Args:
            tool_calls: List of tool call records

        Returns:
            Formatted string representation
        """
        if not tool_calls:
            return "No tools used."

        lines = ["Tool Calls:"]
        for i, call in enumerate(tool_calls, 1):
            lines.append(f"{i}. {call.get('name', 'unknown')}()")
            if "result" in call:
                result = str(call["result"])
                if len(result) > 200:
                    result = result[:200] + "..."
                lines.append(f"   → {result}")

        return "\n".join(lines)


def extract_json_from_text(text: str) -> dict[str, Any] | None:
    """
    Extract JSON object from text (handles markdown code blocks).

    Args:
        text: Text potentially containing JSON

    Returns:
        Parsed JSON dict or None if not found
    """
    import json
    import re

    # Try to find JSON in markdown code block
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None
