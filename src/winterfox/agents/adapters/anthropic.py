"""
Anthropic Claude adapter with extended thinking support.

Supports:
- Claude Opus 4.6 (primary research agent)
- Extended thinking with native web search
- Dual authentication (API key or subscription)
- Tool use with max 30 iterations
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

import anthropic

from ..protocol import AgentOutput, Evidence, Finding, SearchRecord, ToolDefinition
from .base import BaseAdapter, extract_json_from_text

logger = logging.getLogger(__name__)


class AnthropicAdapter(BaseAdapter):
    """Adapter for Anthropic Claude models."""

    def __init__(
        self,
        model: str = "claude-opus-4-20251120",
        api_key: str | None = None,
        use_subscription: bool = False,
        timeout: int = 300,
    ):
        """
        Initialize Anthropic adapter.

        Args:
            model: Model identifier
            api_key: API key (if not using subscription)
            use_subscription: Use subscription auth instead of API key
            timeout: Request timeout in seconds
        """
        super().__init__(model, api_key)

        if use_subscription:
            # Subscription via Anthropic Console (workbench auth)
            # Note: This may require different configuration
            self.client = anthropic.AsyncAnthropic()
        else:
            if not api_key:
                raise ValueError("api_key required when not using subscription")
            self.client = anthropic.AsyncAnthropic(api_key=api_key)

        self.timeout = timeout
        self.supports_native_search = "opus-4" in model.lower()

    @property
    def name(self) -> str:
        """Human-readable agent name."""
        return f"claude-{self.model}"

    def _convert_tool_to_anthropic_schema(self, tool: ToolDefinition) -> dict[str, Any]:
        """
        Convert ToolDefinition to Anthropic tool schema.

        Args:
            tool: Tool definition

        Returns:
            Anthropic tool schema dict
        """
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": {
                "type": "object",
                "properties": tool.parameters,
                "required": list(tool.parameters.keys()),
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
            # Execute tool
            if asyncio.iscoroutinefunction(tool.execute):
                result = await tool.execute(**tool_input)
            else:
                result = tool.execute(**tool_input)

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
        Run Claude with tool use loop.

        Args:
            system_prompt: System instructions
            user_prompt: User research request
            tools: Available tools
            max_iterations: Maximum tool-use iterations

        Returns:
            Structured AgentOutput
        """
        start_time = time.time()

        # Convert tools to Anthropic schema
        anthropic_tools = [self._convert_tool_to_anthropic_schema(t) for t in tools]

        # Enhance system prompt if model supports native search
        if self.supports_native_search:
            system_prompt += """

You have access to extended thinking with web search capabilities.
When researching, you can use your native search alongside the provided tools.
Prefer your native search for complex research questions, and use the web_search
tool for simple factual lookups or when you need structured results.
"""

        messages = [{"role": "user", "content": user_prompt}]

        total_input_tokens = 0
        total_output_tokens = 0
        tool_calls_log = []
        iterations = 0

        try:
            for iteration in range(max_iterations):
                iterations = iteration + 1

                # Make API call
                response = await self._with_retry(
                    self.client.messages.create,
                    model=self.model,
                    system=system_prompt,
                    messages=messages,
                    tools=anthropic_tools,
                    max_tokens=4096,
                    timeout=self.timeout,
                )

                # Track tokens
                total_input_tokens += response.usage.input_tokens
                total_output_tokens += response.usage.output_tokens

                logger.debug(
                    f"Iteration {iteration + 1}/{max_iterations}: "
                    f"{response.stop_reason}, "
                    f"{response.usage.input_tokens} in / {response.usage.output_tokens} out"
                )

                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Agent finished, extract final response
                    final_text = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_text += block.text

                    messages.append({"role": "assistant", "content": response.content})
                    break

                elif response.stop_reason == "tool_use":
                    # Execute tools
                    tool_results = []
                    assistant_content = []

                    for block in response.content:
                        if block.type == "text":
                            assistant_content.append(block)
                        elif block.type == "tool_use":
                            assistant_content.append(block)

                            # Execute tool
                            tool_result = await self._execute_tool(
                                block.name, block.input, tools
                            )

                            tool_calls_log.append(
                                {
                                    "name": block.name,
                                    "input": block.input,
                                    "result": tool_result,
                                }
                            )

                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": tool_result,
                                }
                            )

                    # Append assistant message and tool results
                    messages.append({"role": "assistant", "content": assistant_content})
                    messages.append({"role": "user", "content": tool_results})

                elif response.stop_reason == "max_tokens":
                    logger.warning("Hit max tokens limit, stopping")
                    # Get whatever text we have
                    final_text = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_text += block.text
                    messages.append({"role": "assistant", "content": response.content})
                    break

                else:
                    logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                    break

            # Extract final text from messages
            final_text = ""
            for msg in messages:
                if msg["role"] == "assistant":
                    for block in msg["content"]:
                        if isinstance(block, dict) and block.get("type") == "text":
                            final_text += block.get("text", "")
                        elif hasattr(block, "text"):
                            final_text += block.text

            # Parse findings from final text
            findings = self._parse_findings(final_text, tool_calls_log)

            # Calculate metrics
            duration = time.time() - start_time
            cost = self._calculate_cost(total_input_tokens, total_output_tokens)

            # Extract search records
            searches = self._extract_searches(tool_calls_log)

            return AgentOutput(
                findings=findings,
                self_critique="",  # Could parse from final text if agent provides it
                raw_text=final_text,
                searches_performed=searches,
                cost_usd=cost,
                duration_seconds=duration,
                agent_name=self.name,
                model=self.model,
                total_tokens=total_input_tokens + total_output_tokens,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
            )

        except Exception as e:
            logger.error(f"Error in Claude agent: {e}", exc_info=True)
            duration = time.time() - start_time
            cost = self._calculate_cost(total_input_tokens, total_output_tokens)

            return AgentOutput(
                findings=[],
                self_critique=f"Error: {str(e)}",
                raw_text=f"Agent failed after {iterations} iterations: {str(e)}",
                searches_performed=[],
                cost_usd=cost,
                duration_seconds=duration,
                agent_name=self.name,
                model=self.model,
                total_tokens=total_input_tokens + total_output_tokens,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
            )

    def _parse_findings(
        self, text: str, tool_calls: list[dict[str, Any]]
    ) -> list[Finding]:
        """
        Parse findings from agent's response.

        Looks for structured findings or attempts to extract from text.

        Args:
            text: Agent's final response text
            tool_calls: Log of tool calls made

        Returns:
            List of Finding objects
        """
        findings = []

        # Try to find JSON structured findings
        json_data = extract_json_from_text(text)
        if json_data and "findings" in json_data:
            for f in json_data["findings"]:
                findings.append(
                    Finding(
                        claim=f.get("claim", ""),
                        confidence=float(f.get("confidence", 0.5)),
                        evidence=[
                            Evidence(
                                text=e.get("text", ""),
                                source=e.get("source", ""),
                                date=datetime.fromisoformat(e["date"])
                                if "date" in e
                                else datetime.now(),
                            )
                            for e in f.get("evidence", [])
                        ],
                        suggested_parent_id=f.get("suggested_parent_id"),
                        suggested_children=f.get("suggested_children", []),
                        tags=f.get("tags", []),
                    )
                )

        # If no structured findings, look for note_finding tool calls
        for call in tool_calls:
            if call["name"] == "note_finding":
                inp = call["input"]
                findings.append(
                    Finding(
                        claim=inp.get("claim", ""),
                        confidence=float(inp.get("confidence", 0.5)),
                        evidence=[
                            Evidence(
                                text=e.get("text", ""),
                                source=e.get("source", ""),
                            )
                            for e in inp.get("evidence", [])
                        ],
                    )
                )

        return findings

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
                        urls_visited=[],  # Could extract from result
                    )
                )

        return searches


