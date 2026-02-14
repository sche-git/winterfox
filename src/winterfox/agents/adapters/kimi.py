"""
Moonshot AI Kimi 2.5 adapter.

Supports:
- Kimi 2.5 with 200k+ context window
- Bilingual (Chinese + English)
- OpenAI-compatible API
- Cost-effective alternative (~$0.20 per 1M tokens)
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

import httpx

from ..protocol import AgentOutput, Evidence, SearchRecord, ToolDefinition
from .base import AgentAuthenticationError, BaseAdapter, extract_json_from_text

logger = logging.getLogger(__name__)


class KimiAdapter(BaseAdapter):
    """Adapter for Moonshot AI's Kimi 2.5 model."""

    def __init__(
        self,
        api_key: str,
        model: str = "kimi-2.5",
        timeout: int = 300,
    ):
        """
        Initialize Kimi adapter.

        Args:
            api_key: Moonshot API key
            model: Model identifier (kimi-2.5)
            timeout: Request timeout in seconds
        """
        super().__init__(model, api_key)
        self.base_url = "https://api.moonshot.ai/v1"
        self.timeout = timeout
        self.supports_native_search = False  # Kimi doesn't have native search

    @property
    def name(self) -> str:
        """Human-readable agent name."""
        return f"kimi-{self.model}"

    async def verify(self) -> None:
        """Verify API key with a minimal request."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 1,
                    },
                )
                if response.status_code in (401, 403):
                    raise AgentAuthenticationError(
                        provider="Kimi/Moonshot", api_key_env="MOONSHOT_API_KEY"
                    )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise AgentAuthenticationError(
                    provider="Kimi/Moonshot", api_key_env="MOONSHOT_API_KEY"
                ) from e
            raise

    def _convert_tool_to_openai_schema(self, tool: ToolDefinition) -> dict[str, Any]:
        """
        Convert ToolDefinition to OpenAI tool schema.

        Args:
            tool: Tool definition

        Returns:
            OpenAI tool schema dict
        """
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    async def _execute_tool(
        self, tool_name: str, tool_input: dict[str, Any], tools: list[ToolDefinition]
    ) -> str:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            tool_input: Input parameters
            tools: Available tools

        Returns:
            Tool execution result as string
        """
        # Find tool
        tool = next((t for t in tools if t.name == tool_name), None)
        if not tool:
            return f"Error: Tool '{tool_name}' not found"

        try:
            # Execute tool — always check return value for coroutine since
            # execute may be a lambda wrapping an async function
            result = tool.execute(**tool_input)
            if asyncio.iscoroutine(result):
                result = await result

            # Convert result to string
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            return str(result)

        except Exception as e:
            logger.error(f"Tool execution error: {tool_name} - {e}")
            return f"Error executing {tool_name}: {str(e)}"

    async def run(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        max_iterations: int = 30,
    ) -> AgentOutput:
        """
        Run Kimi with tool use loop.

        Args:
            system_prompt: System instructions
            user_prompt: User research request
            tools: Available tools
            max_iterations: Maximum tool-use iterations

        Returns:
            Structured AgentOutput
        """
        start_time = time.time()

        # Convert tools to OpenAI schema
        openai_tools = [self._convert_tool_to_openai_schema(t) for t in tools]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        total_tokens = 0
        input_tokens_estimate = 0
        output_tokens_estimate = 0
        tool_calls_log = []
        iterations = 0

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for iteration in range(max_iterations):
                    iterations = iteration + 1

                    # Build request payload
                    payload: dict[str, Any] = {
                        "model": self.model,
                        "messages": messages,
                    }
                    if openai_tools:
                        payload["tools"] = openai_tools

                    # Make API call
                    response = await self._with_retry(
                        client.post,
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                    response.raise_for_status()
                    data = response.json()

                    # Track tokens (Kimi provides usage)
                    if "usage" in data:
                        usage = data["usage"]
                        input_tokens_estimate += usage.get("prompt_tokens", 0)
                        output_tokens_estimate += usage.get("completion_tokens", 0)
                        total_tokens += usage.get("total_tokens", 0)

                    choice = data["choices"][0]
                    message = choice["message"]

                    logger.debug(
                        f"Iteration {iteration + 1}/{max_iterations}: "
                        f"finish_reason={choice.get('finish_reason')}"
                    )

                    # Check if done
                    if choice["finish_reason"] == "stop":
                        # Agent finished
                        messages.append(message)
                        break

                    elif choice["finish_reason"] == "tool_calls":
                        # Execute tools
                        tool_calls = message.get("tool_calls", [])
                        messages.append(message)

                        # Execute each tool call
                        for tool_call in tool_calls:
                            function = tool_call["function"]
                            tool_name = function["name"]
                            tool_input = json.loads(function["arguments"])

                            # Execute
                            result = await self._execute_tool(tool_name, tool_input, tools)

                            tool_calls_log.append(
                                {
                                    "name": tool_name,
                                    "input": tool_input,
                                    "result": result,
                                }
                            )

                            # Add tool result to messages
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "content": result,
                                }
                            )

                    elif choice["finish_reason"] == "length":
                        logger.warning("Hit max tokens limit")
                        messages.append(message)
                        break

                    else:
                        logger.warning(f"Unexpected finish reason: {choice['finish_reason']}")
                        messages.append(message)
                        break

                # Extract final text from messages
                final_text = ""
                for msg in messages:
                    if msg["role"] == "assistant" and "content" in msg:
                        content = msg["content"]
                        if content:
                            final_text += content + "\n"

                # Calculate cost and duration
                duration = time.time() - start_time
                cost = self._calculate_cost(input_tokens_estimate, output_tokens_estimate)

                # Parse findings
                # Extract search records
                searches = self._extract_searches(tool_calls_log)

                return AgentOutput(
                    raw_text=final_text,
                    self_critique="",
                    searches_performed=searches,
                    cost_usd=cost,
                    duration_seconds=duration,
                    agent_name=self.name,
                    model=self.model,
                    total_tokens=total_tokens,
                    input_tokens=input_tokens_estimate,
                    output_tokens=output_tokens_estimate,
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise AgentAuthenticationError(
                    provider="Kimi/Moonshot", api_key_env="MOONSHOT_API_KEY"
                ) from e
            logger.error(f"Error in Kimi agent: {e}", exc_info=True)
            duration = time.time() - start_time
            cost = self._calculate_cost(input_tokens_estimate, output_tokens_estimate)

            return AgentOutput(
                raw_text=f"Agent failed after {iterations} iterations: {str(e)}",
                self_critique=f"Error: {str(e)}",
                searches_performed=[],
                cost_usd=cost,
                duration_seconds=duration,
                agent_name=self.name,
                model=self.model,
                total_tokens=total_tokens,
                input_tokens=input_tokens_estimate,
                output_tokens=output_tokens_estimate,
            )

        except Exception as e:
            logger.error(f"Error in Kimi agent: {e}", exc_info=True)
            duration = time.time() - start_time
            cost = self._calculate_cost(input_tokens_estimate, output_tokens_estimate)

            return AgentOutput(
                raw_text=f"Agent failed after {iterations} iterations: {str(e)}",
                self_critique=f"Error: {str(e)}",
                searches_performed=[],
                cost_usd=cost,
                duration_seconds=duration,
                agent_name=self.name,
                model=self.model,
                total_tokens=total_tokens,
                input_tokens=input_tokens_estimate,
                output_tokens=output_tokens_estimate,
            )

    def _extract_searches(
        self, tool_calls: list[dict[str, Any]]
    ) -> list[SearchRecord]:
        """
        Extract search records from tool calls.

        Args:
            tool_calls: Log of tool calls

        Returns:
            List of SearchRecord objects
        """
        searches = []

        for call in tool_calls:
            if "search" in call["name"].lower():
                searches.append(
                    SearchRecord(
                        query=call["input"].get("query", ""),
                        engine=call["name"],
                        timestamp=datetime.now(),
                        results_summary=call.get("result", "")[:200],
                        urls_visited=[],
                    )
                )

        return searches
