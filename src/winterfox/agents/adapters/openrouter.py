"""
OpenRouter adapter for winterfox.

OpenRouter provides unified access to many LLM models through a single API.
Uses OpenAI-compatible API format.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..protocol import AgentOutput, Evidence, Finding, SearchRecord, ToolDefinition

logger = logging.getLogger(__name__)


class OpenRouterAdapter:
    """
    Adapter for OpenRouter API.

    OpenRouter provides access to many models (Claude, GPT-4, Llama, etc.)
    through a unified OpenAI-compatible API.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        timeout: int = 300,
        supports_native_search: bool = False,
    ):
        """
        Initialize OpenRouter adapter.

        Args:
            model: Model identifier (e.g., "anthropic/claude-opus-4")
            api_key: OpenRouter API key
            timeout: Request timeout in seconds
            supports_native_search: Whether model supports native search
        """
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self._supports_native_search = supports_native_search
        self.base_url = "https://openrouter.ai/api/v1"

        # Pricing per 1M tokens (will be fetched from OpenRouter API if available)
        self._pricing = {"prompt": 0.0, "completion": 0.0}

    @property
    def name(self) -> str:
        """Human-readable adapter name."""
        return f"openrouter:{self.model}"

    @property
    def supports_native_search(self) -> bool:
        """Whether this model supports native search."""
        return self._supports_native_search

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
        """
        Run agent with tool-use loop.

        Args:
            system_prompt: System instructions
            user_prompt: User request
            tools: Available tools
            max_iterations: Maximum tool-use iterations

        Returns:
            AgentOutput with findings and metadata
        """
        start_time = datetime.now()
        searches_performed = []
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0

        # Convert tools to OpenAI format
        tools_schema = [self._convert_tool_to_openai_schema(t) for t in tools]
        tool_map = {t.name: t for t in tools}

        # Initialize messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for iteration in range(max_iterations):
                logger.debug(f"[{self.name}] Iteration {iteration + 1}/{max_iterations}")

                # Make API request
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "https://github.com/naomi-kynes/winterfox",
                        "X-Title": "Winterfox Research System",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "tools": tools_schema if tools_schema else None,
                        "temperature": 0.7,
                    },
                )

                if response.status_code != 200:
                    error_text = response.text
                    raise RuntimeError(
                        f"OpenRouter API error ({response.status_code}): {error_text}"
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

                # Check for tool calls
                tool_calls = message.get("tool_calls", [])

                if not tool_calls or finish_reason == "stop":
                    # No more tool calls, extract final response
                    messages.append(message)
                    break

                # Execute tools
                messages.append(message)

                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]

                    logger.info(f"[{self.name}] Calling tool: {tool_name}")

                    # Parse arguments
                    import json

                    tool_args = json.loads(tool_args_str)

                    # Execute tool
                    tool_def = tool_map.get(tool_name)
                    if not tool_def:
                        result_content = f"Error: Tool {tool_name} not found"
                    else:
                        try:
                            result = await tool_def.execute(**tool_args)

                            # Track searches
                            if tool_name == "web_search":
                                searches_performed.append(
                                    SearchRecord(
                                        query=tool_args.get("query", ""),
                                        engine="openrouter-tools",
                                        timestamp=datetime.now(),
                                        results_summary=str(result)[:200],
                                        urls_visited=[],
                                    )
                                )

                            result_content = json.dumps(result)
                        except Exception as e:
                            logger.error(f"Tool {tool_name} failed: {e}")
                            result_content = f"Error: {str(e)}"

                    # Add tool result to messages
                    tool_results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result_content,
                        }
                    )

                messages.extend(tool_results)

        # Calculate duration and cost
        duration = (datetime.now() - start_time).total_seconds()
        cost_usd = self._calculate_cost(input_tokens, output_tokens)

        # Parse findings from conversation
        findings = self._extract_findings_from_messages(messages)

        # Extract self-critique
        final_message = messages[-1] if messages else {"content": ""}
        self_critique = final_message.get("content", "No critique provided")

        return AgentOutput(
            findings=findings,
            self_critique=self_critique,
            raw_text="\n".join([m.get("content", "") for m in messages if isinstance(m.get("content"), str)]),
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
        """
        Calculate cost in USD.

        OpenRouter pricing varies by model. We use conservative estimates
        if exact pricing is not available.
        """
        input_cost = (input_tokens / 1_000_000) * self._pricing["prompt"]
        output_cost = (output_tokens / 1_000_000) * self._pricing["completion"]
        return input_cost + output_cost

    def _extract_findings_from_messages(self, messages: list[dict]) -> list[Finding]:
        """
        Extract findings from tool calls to note_finding.

        Looks for tool calls to note_finding and parses the arguments.
        """
        findings = []

        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tool_call in msg["tool_calls"]:
                    if tool_call["function"]["name"] == "note_finding":
                        import json

                        try:
                            args = json.loads(tool_call["function"]["arguments"])

                            # Parse evidence
                            evidence = []
                            for ev in args.get("evidence", []):
                                evidence.append(
                                    Evidence(
                                        text=ev.get("text", ""),
                                        source=ev.get("source", ""),
                                        date=datetime.now(),
                                        verified_by=[self.name],
                                    )
                                )

                            # Create finding
                            finding = Finding(
                                claim=args.get("claim", ""),
                                confidence=args.get("confidence", 0.5),
                                evidence=evidence,
                                suggested_parent_id=args.get("suggested_parent_id"),
                                suggested_children=args.get("suggested_children", []),
                                tags=args.get("tags", []),
                            )

                            findings.append(finding)

                        except Exception as e:
                            logger.warning(f"Failed to parse finding: {e}")

        return findings


async def fetch_openrouter_models(api_key: str) -> list[dict[str, Any]]:
    """
    Fetch available models from OpenRouter API.

    Args:
        api_key: OpenRouter API key

    Returns:
        List of model dictionaries with id, name, context_length, pricing, etc.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch OpenRouter models: {response.text}")

        data = response.json()
        return data.get("data", [])
