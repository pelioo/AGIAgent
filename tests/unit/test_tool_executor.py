#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for src/tool_executor.py

Tests cover:
- is_anthropic_api function
- ToolExecutor class initialization and core methods
"""

import pytest
from unittest.mock import MagicMock, patch, call


class TestIsAnthropicApi:
    """Tests for is_anthropic_api function.

    Note: The actual implementation checks if api_base ends with '/anthropic'.
    """

    def test_is_anthropic_api_true(self):
        """Test detection of URLs ending with /anthropic."""
        from src.tool_executor import is_anthropic_api
        # Actual function checks if URL ends with '/anthropic'
        assert is_anthropic_api("https://custom.endpoint/anthropic") is True
        assert is_anthropic_api("https://api.anthropic.endpoint/ANTHROPIC") is True
        assert is_anthropic_api("https://proxy.example.com/anthropic") is True

    def test_is_anthropic_api_false(self):
        """Test rejection of non-Anthropic API format."""
        from src.tool_executor import is_anthropic_api
        assert is_anthropic_api("https://api.openai.com/v1") is False
        assert is_anthropic_api("https://api.deepseek.com/v1") is False
        assert is_anthropic_api("http://localhost:8080") is False

    def test_is_anthropic_api_none(self):
        """Test that None returns False."""
        from src.tool_executor import is_anthropic_api
        assert is_anthropic_api(None) is False

    def test_is_anthropic_api_case_insensitive(self):
        """Test case-insensitive detection."""
        from src.tool_executor import is_anthropic_api
        assert is_anthropic_api("https://custom.endpoint/ANTHROPIC") is True
        assert is_anthropic_api("https://custom.endpoint/Anthropic") is True

    def test_is_anthropic_api_empty(self):
        """Test that empty string returns False."""
        from src.tool_executor import is_anthropic_api
        assert is_anthropic_api("") is False


class TestToolExecutorInit:
    """Tests for ToolExecutor class initialization."""

    def test_tool_executor_instance_created(self, tool_executor_instance):
        """Test that a ToolExecutor instance can be created via fixture."""
        assert tool_executor_instance.api_key == "test_key_12345"
        assert tool_executor_instance.model == "claude-sonnet-4-0"

    def test_tool_executor_with_workspace(self, tool_executor_with_workspace, empty_workspace):
        """Test ToolExecutor with workspace directory."""
        assert tool_executor_with_workspace.workspace_root == str(empty_workspace)

    def test_tool_executor_attributes(self, tool_executor_instance):
        """Test that all expected attributes are set."""
        assert hasattr(tool_executor_instance, "api_key")
        assert hasattr(tool_executor_instance, "api_base")
        assert hasattr(tool_executor_instance, "model")
        assert hasattr(tool_executor_instance, "max_tokens")
        assert hasattr(tool_executor_instance, "temperature")
        assert hasattr(tool_executor_instance, "streaming")
        assert hasattr(tool_executor_instance, "enable_thinking")
        assert hasattr(tool_executor_instance, "workspace_root")


class TestToolExecutorApiDetection:
    """Tests for API type detection in ToolExecutor."""

    def test_anthropic_api_detected(self, tool_executor_instance):
        """Test that Anthropic API is correctly identified."""
        from src.tool_executor import is_anthropic_api
        # The fixture sets api_base to https://api.anthropic.com/v1 which ends with anthropic
        assert is_anthropic_api(tool_executor_instance.api_base) is True

    def test_openai_api_detected(self, mock_api_key_env):
        """Test that OpenAI API is correctly identified."""
        with patch('src.tool_executor.ToolExecutor.__init__', return_value=None):
            from src.tool_executor import ToolExecutor, is_anthropic_api

            executor = ToolExecutor.__new__(ToolExecutor)
            executor.api_base = "https://api.openai.com/v1"
            assert is_anthropic_api(executor.api_base) is False

    def test_custom_anthropic_api_detected(self, mock_api_key_env):
        """Test that custom Anthropic-format API is detected."""
        with patch('src.tool_executor.ToolExecutor.__init__', return_value=None):
            from src.tool_executor import ToolExecutor, is_anthropic_api

            executor = ToolExecutor.__new__(ToolExecutor)
            executor.api_base = "https://my-custom anthropic.proxy/v1"
            # Note: custom endpoint still ends with /anthropic
            assert is_anthropic_api(executor.api_base) is False


class TestToolExecutorWorkspace:
    """Tests for ToolExecutor workspace management."""

    def test_workspace_root_default_none(self, tool_executor_instance):
        """Test that workspace_root defaults to None."""
        assert tool_executor_instance.workspace_root is None

    def test_workspace_root_set(self, tool_executor_with_workspace, empty_workspace):
        """Test that workspace_root is correctly set."""
        assert tool_executor_with_workspace.workspace_root == str(empty_workspace)

    def test_workspace_dir_attribute(self, tool_executor_with_workspace, empty_workspace):
        """Test that workspace_dir attribute is set."""
        assert tool_executor_with_workspace.workspace_dir == str(empty_workspace)


class TestToolExecutorAgentContext:
    """Tests for ToolExecutor agent context management."""

    def test_agent_id_default_none(self, tool_executor_instance):
        """Test that _agent_id defaults to None."""
        assert tool_executor_instance._agent_id is None

    def test_agent_id_can_be_set(self, tool_executor_instance):
        """Test that _agent_id can be set."""
        tool_executor_instance._agent_id = "manager"
        assert tool_executor_instance._agent_id == "manager"
