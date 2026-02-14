"""
Tests for OpenRouter tool call normalization.

Covers all known format variations across model providers:
- Standard OpenAI format (GPT-4, etc.)
- Missing function name (Qwen3 thinking models)
- Arguments as dict instead of string (Anthropic/Gemini leak-through)
- Empty/null arguments
- Tool calls embedded in content (Hermes/Qwen, Mistral)
- Missing tool call IDs
"""

import json

import pytest

from winterfox.agents.adapters.openrouter import (
    NormalizedToolCall,
    _extract_tool_calls_from_content,
    _parse_arguments,
    normalize_tool_calls,
)


class TestParseArguments:
    """Test _parse_arguments handles all known argument formats."""

    def test_json_string(self) -> None:
        result = _parse_arguments('{"query": "quantum computing"}')
        assert result == {"query": "quantum computing"}

    def test_dict_passthrough(self) -> None:
        result = _parse_arguments({"query": "quantum computing"})
        assert result == {"query": "quantum computing"}

    def test_empty_string(self) -> None:
        assert _parse_arguments("") == {}

    def test_none(self) -> None:
        assert _parse_arguments(None) == {}

    def test_whitespace_only(self) -> None:
        assert _parse_arguments("   ") == {}

    def test_empty_object_string(self) -> None:
        assert _parse_arguments("{}") == {}

    def test_malformed_json_trailing_comma(self) -> None:
        result = _parse_arguments('{"query": "test",}')
        # Should handle trailing comma gracefully
        assert result == {} or result == {"query": "test"}

    def test_non_dict_json(self) -> None:
        """JSON arrays or primitives should return empty dict."""
        assert _parse_arguments("[1, 2, 3]") == {}
        assert _parse_arguments('"just a string"') == {}

    def test_nested_arguments(self) -> None:
        raw = json.dumps({"query": "test", "options": {"max_results": 10}})
        result = _parse_arguments(raw)
        assert result == {"query": "test", "options": {"max_results": 10}}


class TestNormalizeToolCalls:
    """Test normalize_tool_calls handles all model response formats."""

    def test_standard_openai_format(self) -> None:
        """GPT-4, standard OpenAI-compatible responses."""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "arguments": '{"query": "quantum ML"}',
                    },
                }
            ],
        }
        results = normalize_tool_calls(message)
        assert len(results) == 1
        assert results[0].name == "web_search"
        assert results[0].arguments == {"query": "quantum ML"}
        assert results[0].id == "call_abc123"

    def test_missing_function_name(self) -> None:
        """Qwen3 thinking models sometimes return tool calls without name."""
        message = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_xyz",
                    "function": {
                        "arguments": '{"query": "test"}',
                    },
                }
            ],
        }
        results = normalize_tool_calls(message)
        assert len(results) == 0  # Skipped, not crashed

    def test_arguments_as_dict(self) -> None:
        """Anthropic/Gemini via OpenRouter may leak dict arguments."""
        message = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_123",
                    "function": {
                        "name": "web_search",
                        "arguments": {"query": "test"},  # Dict, not string
                    },
                }
            ],
        }
        results = normalize_tool_calls(message)
        assert len(results) == 1
        assert results[0].arguments == {"query": "test"}

    def test_empty_arguments(self) -> None:
        """Anthropic returns empty string for no-arg tools."""
        message = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_123",
                    "function": {
                        "name": "get_status",
                        "arguments": "",
                    },
                }
            ],
        }
        results = normalize_tool_calls(message)
        assert len(results) == 1
        assert results[0].arguments == {}

    def test_missing_tool_call_id(self) -> None:
        """Some models don't provide tool call IDs."""
        message = {
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {
                        "name": "web_search",
                        "arguments": '{"query": "test"}',
                    },
                }
            ],
        }
        results = normalize_tool_calls(message)
        assert len(results) == 1
        assert results[0].id.startswith("call_")  # Synthetic ID

    def test_multiple_tool_calls(self) -> None:
        message = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "web_search",
                        "arguments": '{"query": "topic A"}',
                    },
                },
                {
                    "id": "call_2",
                    "function": {
                        "name": "web_fetch",
                        "arguments": '{"url": "https://example.com"}',
                    },
                },
            ],
        }
        results = normalize_tool_calls(message)
        assert len(results) == 2
        assert results[0].name == "web_search"
        assert results[1].name == "web_fetch"

    def test_mixed_valid_and_invalid(self) -> None:
        """Valid tool calls should be kept even when others are malformed."""
        message = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "web_search",
                        "arguments": '{"query": "test"}',
                    },
                },
                {
                    "id": "call_2",
                    "function": {
                        "arguments": '{"bad": true}',
                        # Missing name
                    },
                },
            ],
        }
        results = normalize_tool_calls(message)
        assert len(results) == 1
        assert results[0].name == "web_search"

    def test_no_tool_calls_no_content(self) -> None:
        """Plain text response with no tools."""
        message = {
            "role": "assistant",
            "content": "Here is my analysis...",
        }
        results = normalize_tool_calls(message)
        assert len(results) == 0

    def test_null_tool_calls(self) -> None:
        """Some models return tool_calls: null instead of omitting it."""
        message = {
            "role": "assistant",
            "content": "Done.",
            "tool_calls": None,
        }
        results = normalize_tool_calls(message)
        assert len(results) == 0

    def test_missing_function_key(self) -> None:
        """tool_call entry with no 'function' key at all."""
        message = {
            "role": "assistant",
            "tool_calls": [
                {"id": "call_1", "type": "function"},
            ],
        }
        results = normalize_tool_calls(message)
        assert len(results) == 0


class TestExtractToolCallsFromContent:
    """Test fallback parsing for tool calls embedded in content text."""

    def test_hermes_qwen_format(self) -> None:
        """Qwen 2.5/3 Hermes format."""
        content = """Let me search for that.

<tool_call>
{"name": "web_search", "arguments": {"query": "quantum computing startups"}}
</tool_call>"""

        results = _extract_tool_calls_from_content(content)
        assert len(results) == 1
        assert results[0].name == "web_search"
        assert results[0].arguments == {"query": "quantum computing startups"}

    def test_hermes_multiple_calls(self) -> None:
        content = """<tool_call>
{"name": "web_search", "arguments": {"query": "topic A"}}
</tool_call>

<tool_call>
{"name": "web_search", "arguments": {"query": "topic B"}}
</tool_call>"""

        results = _extract_tool_calls_from_content(content)
        assert len(results) == 2

    def test_mistral_format(self) -> None:
        """Mistral [TOOL_CALLS] format."""
        content = '[TOOL_CALLS] [{"name": "web_search", "arguments": {"query": "test"}}]'

        results = _extract_tool_calls_from_content(content)
        assert len(results) == 1
        assert results[0].name == "web_search"

    def test_no_tool_calls_in_content(self) -> None:
        """Regular text should return no tool calls."""
        content = "Here is my analysis of quantum computing trends."
        results = _extract_tool_calls_from_content(content)
        assert len(results) == 0

    def test_content_fallback_only_when_no_standard_calls(self) -> None:
        """Content parsing should only run when standard tool_calls are absent."""
        message = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "web_search",
                        "arguments": '{"query": "standard"}',
                    },
                }
            ],
            "content": '<tool_call>\n{"name": "web_search", "arguments": {"query": "fallback"}}\n</tool_call>',
        }
        results = normalize_tool_calls(message)
        # Should use standard path, not content fallback
        assert len(results) == 1
        assert results[0].arguments["query"] == "standard"
