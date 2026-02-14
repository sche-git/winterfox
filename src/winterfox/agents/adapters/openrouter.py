"""
OpenRouter adapter for winterfox.

OpenRouter provides unified access to many LLM models through a single API.
Uses OpenAI-compatible API format.

Because OpenRouter proxies many different model providers, tool call response
formats vary significantly. This adapter normalizes all known variations into
a canonical format before processing.
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..protocol import AgentOutput, Evidence, SearchRecord, ToolDefinition
from .base import AgentAuthenticationError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool call normalization
# ---------------------------------------------------------------------------

@dataclass
class NormalizedToolCall:
    """Canonical representation of a tool call, regardless of source model."""

    id: str
    name: str
    arguments: dict[str, Any]


def _generate_tool_call_id() -> str:
    """Generate a synthetic tool call ID when the model doesn't provide one."""
    return f"call_{uuid.uuid4().hex[:24]}"


def _parse_arguments(raw: Any) -> dict[str, Any]:
    """
    Parse tool call arguments from any format models might return.

    Handles:
    - JSON string (OpenAI standard): '{"query": "test"}'
    - Dict (Anthropic/Gemini leak-through): {"query": "test"}
    - Empty string: ""
    - None / missing
    - Malformed JSON with trailing commas, etc.
    """
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return {}
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
            return {}
        except json.JSONDecodeError:
            # Some models produce trailing commas or single quotes — try
            # cleaning common mistakes before giving up.
            cleaned = stripped.rstrip(",").rstrip()
            try:
                parsed = json.loads(cleaned)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                logger.warning(f"Unparseable tool arguments: {stripped[:200]}")
                return {}
    return {}


def normalize_tool_calls(message: dict[str, Any]) -> list[NormalizedToolCall]:
    """
    Extract tool calls from an assistant message, handling all known formats.

    1. Standard OpenAI tool_calls array
    2. Tool calls embedded in content text (Hermes/Qwen <tool_call>, Mistral
       [TOOL_CALLS], Llama <|python_tag|>)
    """
    results: list[NormalizedToolCall] = []

    # --- Path 1: Standard tool_calls array ---
    raw_tool_calls = message.get("tool_calls") or []
    for tc in raw_tool_calls:
        func = tc.get("function") or {}
        name = func.get("name")
        if not name:
            # Some models put name at top level
            name = tc.get("name")
        if not name:
            logger.warning(f"Skipping tool call with no function name: {tc}")
            continue

        results.append(
            NormalizedToolCall(
                id=tc.get("id") or _generate_tool_call_id(),
                name=name,
                arguments=_parse_arguments(func.get("arguments")),
            )
        )

    # --- Path 2: Tool calls embedded in content (provider parser failures) ---
    if not results:
        content = message.get("content") or ""
        if isinstance(content, str):
            results.extend(_extract_tool_calls_from_content(content))

    return results


def _extract_tool_calls_from_content(content: str) -> list[NormalizedToolCall]:
    """
    Fallback parser for tool calls dumped as raw text in the content field.

    This happens when the upstream provider's tool parser fails, especially
    with open-source models in streaming mode.
    """
    results: list[NormalizedToolCall] = []

    # --- Hermes / Qwen format: <tool_call>{"name": "...", "arguments": {...}}</tool_call> ---
    hermes_pattern = r"<tool_call>\s*(\{.*?\})\s*</tool_call>"
    for match in re.finditer(hermes_pattern, content, re.DOTALL):
        try:
            tc = json.loads(match.group(1))
            name = tc.get("name")
            if name:
                results.append(
                    NormalizedToolCall(
                        id=_generate_tool_call_id(),
                        name=name,
                        arguments=_parse_arguments(tc.get("arguments")),
                    )
                )
        except json.JSONDecodeError:
            logger.debug(f"Failed to parse Hermes tool_call: {match.group(1)[:200]}")

    if results:
        return results

    # --- Mistral format: [TOOL_CALLS] [{"name": "...", "arguments": {...}}] ---
    if "[TOOL_CALLS]" in content:
        tc_match = re.search(r"\[TOOL_CALLS\]\s*(\[.*\])", content, re.DOTALL)
        if tc_match:
            try:
                calls = json.loads(tc_match.group(1))
                for tc in calls:
                    name = tc.get("name")
                    if name:
                        results.append(
                            NormalizedToolCall(
                                id=_generate_tool_call_id(),
                                name=name,
                                arguments=_parse_arguments(tc.get("arguments")),
                            )
                        )
            except json.JSONDecodeError:
                logger.debug(f"Failed to parse Mistral tool calls: {tc_match.group(1)[:200]}")

    return results


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class OpenRouterAdapter:
    """
    Adapter for OpenRouter API.

    OpenRouter provides access to many models (Claude, GPT-4, Llama, Qwen, etc.)
    through a unified OpenAI-compatible API. Because responses come from many
    different providers and model families, this adapter normalizes tool call
    formats before processing.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        timeout: int = 300,
        supports_native_search: bool = False,
    ):
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self._supports_native_search = supports_native_search
        self.base_url = "https://openrouter.ai/api/v1"
        self._pricing = {"prompt": 0.0, "completion": 0.0}

    @property
    def name(self) -> str:
        return f"openrouter:{self.model}"

    @property
    def supports_native_search(self) -> bool:
        return self._supports_native_search

    async def verify(self) -> None:
        """Verify API key with a minimal request."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 1,
                    },
                )
                if response.status_code in (401, 403):
                    raise AgentAuthenticationError(
                        provider="OpenRouter", api_key_env="OPENROUTER_API_KEY"
                    )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise AgentAuthenticationError(
                    provider="OpenRouter", api_key_env="OPENROUTER_API_KEY"
                ) from e
            raise

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/naomi-kynes/winterfox",
            "X-Title": "Winterfox Research System",
        }

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def run(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        max_iterations: int = 30,
    ) -> AgentOutput:
        start_time = datetime.now()
        searches_performed: list[SearchRecord] = []
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0

        tools_schema = [self._convert_tool_to_openai_schema(t) for t in tools]
        tool_map = {t.name: t for t in tools}

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for iteration in range(max_iterations):
                logger.debug(f"[{self.name}] Iteration {iteration + 1}/{max_iterations}")

                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "messages": messages,
                        "tools": tools_schema if tools_schema else None,
                        "temperature": 0.7,
                    },
                )

                if response.status_code in (401, 403):
                    raise AgentAuthenticationError(
                        provider="OpenRouter", api_key_env="OPENROUTER_API_KEY"
                    )
                if response.status_code != 200:
                    raise RuntimeError(
                        f"OpenRouter API error ({response.status_code}): {response.text}"
                    )

                result = response.json()

                # Track usage
                usage = result.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                input_tokens += prompt_tokens
                output_tokens += completion_tokens
                total_tokens += prompt_tokens + completion_tokens

                # Get assistant message
                message = result["choices"][0]["message"]
                finish_reason = result["choices"][0].get("finish_reason")

                # Normalize tool calls from whatever format the model returned
                normalized_calls = normalize_tool_calls(message)

                if not normalized_calls or finish_reason == "stop":
                    messages.append(message)
                    break

                # Append assistant message (preserve original for conversation)
                messages.append(message)

                # Execute each tool call
                tool_results = []
                for tc in normalized_calls:
                    logger.info(f" Calling tool: {tc.name}")

                    tool_def = tool_map.get(tc.name)
                    if not tool_def:
                        result_content = f"Error: Tool '{tc.name}' not found. Available tools: {', '.join(tool_map.keys())}"
                    else:
                        try:
                            exec_result = await tool_def.execute(**tc.arguments)

                            if tc.name == "web_search":
                                searches_performed.append(
                                    SearchRecord(
                                        query=tc.arguments.get("query", ""),
                                        engine="openrouter-tools",
                                        timestamp=datetime.now(),
                                        results_summary=str(exec_result)[:200],
                                        urls_visited=[],
                                    )
                                )

                            result_content = json.dumps(exec_result)
                        except Exception as e:
                            logger.error(f"Tool {tc.name} failed: {e}")
                            result_content = f"Error executing {tc.name}: {e}"

                    tool_results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result_content,
                        }
                    )

                messages.extend(tool_results)

        duration = (datetime.now() - start_time).total_seconds()
        cost_usd = self._calculate_cost(input_tokens, output_tokens)

        final_message = messages[-1] if messages else {}
        self_critique = ""
        if isinstance(final_message.get("content"), str):
            self_critique = final_message["content"]
        if not self_critique:
            self_critique = "No critique provided"

        return AgentOutput(
            raw_text="\n".join(
                m.get("content", "")
                for m in messages
                if isinstance(m.get("content"), str)
            ),
            self_critique=self_critique,
            searches_performed=searches_performed,
            cost_usd=cost_usd,
            duration_seconds=duration,
            agent_name=self.name,
            model=self.model,
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _convert_tool_to_openai_schema(self, tool: ToolDefinition) -> dict[str, Any]:
        """Convert ToolDefinition to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1_000_000) * self._pricing["prompt"]
        output_cost = (output_tokens / 1_000_000) * self._pricing["completion"]
        return input_cost + output_cost


async def fetch_openrouter_models(api_key: str | None = None) -> list[dict[str, Any]]:
    """
    Fetch available models from OpenRouter API.

    Args:
        api_key: Optional OpenRouter API key (not required for model discovery)

    Returns:
        List of model dictionaries with id, name, context_length, pricing, etc.
    """
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers=headers,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch OpenRouter models: {response.text}")

        data = response.json()
        return data.get("data", [])
