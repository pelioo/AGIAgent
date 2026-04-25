#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for src/api_callers/ module.

Tests cover the API caller functions:
- call_claude_with_chat_based_tools_non_streaming
- call_claude_with_chat_based_tools_streaming
- call_openai_with_chat_based_tools_non_streaming
- call_openai_with_chat_based_tools_streaming
- call_claude_with_standard_tools
- call_openai_with_standard_tools
"""

import pytest
from unittest.mock import MagicMock, patch, call
from src.api_callers import (
    call_claude_with_chat_based_tools_non_streaming,
    call_claude_with_chat_based_tools_streaming,
    call_openai_with_chat_based_tools_non_streaming,
    call_openai_with_chat_based_tools_streaming,
    call_claude_with_standard_tools,
    call_openai_with_standard_tools,
)


class TestClaudeNonStreaming:
    """Tests for call_claude_with_chat_based_tools_non_streaming."""

    def test_call_claude_non_streaming_basic(self, api_executor_mock, mock_anthropic_client):
        """Test basic non-streaming Claude API call."""
        api_executor_mock.client = mock_anthropic_client

        messages = [{"role": "user", "content": "你好"}]
        system = "你是助手"

        content, tool_calls = call_claude_with_chat_based_tools_non_streaming(
            api_executor_mock, messages, system
        )

        # Verify the API was called
        api_executor_mock.client.messages.create.assert_called_once()

    def test_call_claude_non_streaming_response_format(self, api_executor_mock, mock_anthropic_client):
        """Test that response is properly formatted."""
        api_executor_mock.client = mock_anthropic_client

        messages = [{"role": "user", "content": "test"}]
        system = "system"

        content, tool_calls = call_claude_with_chat_based_tools_non_streaming(
            api_executor_mock, messages, system
        )

        assert isinstance(content, str)
        assert isinstance(tool_calls, list)

    def test_call_claude_non_streaming_thinking_mode(self, mock_anthropic_client):
        """Test Claude API call with thinking mode enabled."""
        mock_executor = MagicMock()
        mock_executor.enable_thinking = True
        mock_executor.temperature = 0.7
        mock_executor.model = "claude-sonnet-4-0"
        mock_executor._get_max_tokens_for_model = MagicMock(return_value=16384)
        mock_executor.workspace_root = None

        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="thinking response")]
        mock_response.usage = MagicMock(
            input_tokens=100, output_tokens=50,
            cache_creation_input_tokens=0, cache_read_input_tokens=0
        )
        mock_executor.client = MagicMock()
        mock_executor.client.messages.create.return_value = mock_response

        messages = [{"role": "user", "content": "test"}]
        system = "system"

        content, tool_calls = call_claude_with_chat_based_tools_non_streaming(
            mock_executor, messages, system
        )

        # Verify the call was made
        mock_executor.client.messages.create.assert_called_once()


class TestClaudeStreaming:
    """Tests for call_claude_with_chat_based_tools_streaming."""

    def test_call_claude_streaming_basic(self):
        """Test basic streaming Claude API call structure."""
        mock_executor = MagicMock()
        mock_executor.enable_thinking = False
        mock_executor.temperature = 0.7
        mock_executor.model = "claude-sonnet-4-0"
        mock_executor.workspace_root = None
        mock_executor.client = MagicMock()

        messages = [{"role": "user", "content": "hello"}]
        system = "You are a helpful assistant"

        # Function should be callable
        assert callable(call_claude_with_chat_based_tools_streaming)

    def test_call_claude_streaming_function_signature(self):
        """Test that streaming function has expected parameters."""
        import inspect
        sig = inspect.signature(call_claude_with_chat_based_tools_streaming)
        params = list(sig.parameters.keys())
        assert "executor" in params
        assert "messages" in params
        assert "system_message" in params


class TestOpenAINonStreaming:
    """Tests for call_openai_with_chat_based_tools_non_streaming."""

    def test_call_openai_non_streaming_basic(self, api_executor_mock, mock_openai_client):
        """Test basic OpenAI non-streaming call."""
        api_executor_mock.client = mock_openai_client

        messages = [{"role": "user", "content": "你好"}]
        system = "你是助手"

        content, tool_calls = call_openai_with_chat_based_tools_non_streaming(
            api_executor_mock, messages, system
        )

        assert isinstance(content, str)
        assert isinstance(tool_calls, list)

    def test_call_openai_non_streaming_response(self, api_executor_mock, mock_openai_client):
        """Test OpenAI response is correctly extracted."""
        api_executor_mock.client = mock_openai_client

        messages = [{"role": "user", "content": "test"}]
        system = "system"

        content, tool_calls = call_openai_with_chat_based_tools_non_streaming(
            api_executor_mock, messages, system
        )

        assert "OpenAI" in content or "test" in content.lower()


class TestOpenAIStreaming:
    """Tests for call_openai_with_chat_based_tools_streaming."""

    def test_call_openai_streaming_basic(self):
        """Test basic streaming OpenAI call structure."""
        mock_executor = MagicMock()
        mock_executor.workspace_root = None

        messages = [{"role": "user", "content": "hello"}]
        system = "You are helpful"

        assert callable(call_openai_with_chat_based_tools_streaming)


class TestStandardTools:
    """Tests for standard tools API callers."""

    def test_call_claude_standard_tools_exists(self):
        """Test that call_claude_with_standard_tools is importable."""
        assert callable(call_claude_with_standard_tools)

    def test_call_openai_standard_tools_exists(self):
        """Test that call_openai_with_standard_tools is importable."""
        assert callable(call_openai_with_standard_tools)

    def test_standard_tools_function_signatures(self):
        """Test that standard tools functions have expected parameters."""
        import inspect

        sig_claude = inspect.signature(call_claude_with_standard_tools)
        params_claude = list(sig_claude.parameters.keys())
        assert "executor" in params_claude
        assert "messages" in params_claude
        assert "system_message" in params_claude

        sig_openai = inspect.signature(call_openai_with_standard_tools)
        params_openai = list(sig_openai.parameters.keys())
        assert "executor" in params_openai
        assert "messages" in params_openai


class TestAPICallersExports:
    """Tests for api_callers module exports."""

    def test_all_expected_functions_exported(self):
        """Test that all expected functions are exported from __init__."""
        from src.api_callers import __all__

        expected = [
            'call_claude_with_chat_based_tools_streaming',
            'call_openai_with_chat_based_tools_streaming',
            'call_claude_with_chat_based_tools_non_streaming',
            'call_openai_with_chat_based_tools_non_streaming',
            'call_openai_with_standard_tools',
            'call_claude_with_standard_tools',
        ]

        for func_name in expected:
            assert func_name in __all__, f"{func_name} not in __all__"

    def test_functions_are_callable(self):
        """Test that all exported functions are callable."""
        from src.api_callers import __all__
        import src.api_callers as api_callers

        for func_name in __all__:
            func = getattr(api_callers, func_name)
            assert callable(func), f"{func_name} is not callable"
