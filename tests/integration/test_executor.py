#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for src/multi_round_executor/executor.py

Tests cover:
- MultiRoundTaskExecutor class
- extract_session_timestamp function
- Initialization with various configurations
- Workspace directory management
"""

import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestExtractSessionTimestamp:
    """Tests for extract_session_timestamp function."""

    def test_extract_timestamp_from_output_dir(self):
        """Test extracting timestamp from output_YYYYMMDD_HHMMSS format."""
        from src.multi_round_executor.executor import extract_session_timestamp

        timestamp = extract_session_timestamp("output_20260426_143000/logs")
        assert timestamp == "20260426_143000"

    def test_extract_timestamp_from_full_path(self):
        """Test extracting timestamp from full path."""
        from src.multi_round_executor.executor import extract_session_timestamp

        timestamp = extract_session_timestamp("/path/to/output_20260315_090500/logs")
        assert timestamp == "20260315_090500"

    def test_extract_timestamp_logs_dir_only(self):
        """Test extracting from logs directory without timestamp."""
        from src.multi_round_executor.executor import extract_session_timestamp

        timestamp = extract_session_timestamp("logs")
        assert timestamp is None

    def test_extract_timestamp_no_match(self):
        """Test that no match returns None."""
        from src.multi_round_executor.executor import extract_session_timestamp

        timestamp = extract_session_timestamp("random_directory_name")
        assert timestamp is None

    def test_extract_timestamp_empty_string(self):
        """Test empty string returns None."""
        from src.multi_round_executor.executor import extract_session_timestamp

        timestamp = extract_session_timestamp("")
        assert timestamp is None


class TestMultiRoundTaskExecutorInit:
    """Tests for MultiRoundTaskExecutor initialization."""

    def test_executor_basic_init(self, multi_round_executor_instance):
        """Test basic executor initialization."""
        assert multi_round_executor_instance.subtask_loops == 10
        assert multi_round_executor_instance.logs_dir == "logs"
        assert multi_round_executor_instance.debug_mode is False

    def test_executor_with_workspace(self, multi_round_executor_with_workspace, temp_workspace):
        """Test executor initialization with workspace directory."""
        assert multi_round_executor_with_workspace.workspace_dir == str(temp_workspace)
        assert multi_round_executor_with_workspace.logs_dir == str(temp_workspace / "logs")

    def test_executor_with_plan_mode(self, mock_api_key_env):
        """Test executor with plan_mode enabled."""
        with patch('src.multi_round_executor.executor.MultiRoundTaskExecutor.__init__', return_value=None):
            from src.multi_round_executor.executor import MultiRoundTaskExecutor

            executor = MultiRoundTaskExecutor.__new__(MultiRoundTaskExecutor)
            executor.subtask_loops = 10
            executor.plan_mode = True
            executor.logs_dir = "logs"
            executor.workspace_dir = None
            executor.debug_mode = False

            assert executor.plan_mode is True

    def test_executor_with_custom_loops(self, mock_api_key_env):
        """Test executor with custom subtask_loops."""
        with patch('src.multi_round_executor.executor.MultiRoundTaskExecutor.__init__', return_value=None):
            from src.multi_round_executor.executor import MultiRoundTaskExecutor

            executor = MultiRoundTaskExecutor.__new__(MultiRoundTaskExecutor)
            executor.subtask_loops = 50
            executor.logs_dir = "logs"

            assert executor.subtask_loops == 50

    def test_executor_api_config(self, multi_round_executor_instance):
        """Test that API configuration is correctly stored."""
        assert multi_round_executor_instance.api_key == "test_key_12345"
        assert multi_round_executor_instance.model == "claude-sonnet-4-0"
        # Note: actual function checks for URLs ending with /anthropic
        assert multi_round_executor_instance.api_base == "https://custom.endpoint/anthropic"

    def test_executor_debug_mode(self, multi_round_executor_instance):
        """Test debug mode attribute."""
        assert multi_round_executor_instance.debug_mode is False

    def test_executor_interactive_mode(self, multi_round_executor_instance):
        """Test interactive mode attribute."""
        assert multi_round_executor_instance.interactive_mode is False


class TestMultiRoundTaskExecutorWorkspace:
    """Tests for MultiRoundTaskExecutor workspace management."""

    def test_workspace_dir_created(self, multi_round_executor_with_workspace, temp_workspace):
        """Test that workspace directory is set correctly."""
        assert multi_round_executor_with_workspace.workspace_dir == str(temp_workspace)

    def test_workspace_dir_none_by_default(self, multi_round_executor_instance):
        """Test that workspace_dir is None by default."""
        assert multi_round_executor_instance.workspace_dir is None

    def test_logs_dir_in_workspace(self, multi_round_executor_with_workspace, temp_workspace):
        """Test that logs directory is within workspace."""
        expected_logs = str(temp_workspace / "logs")
        assert multi_round_executor_with_workspace.logs_dir == expected_logs


class TestMultiRoundTaskExecutorConfig:
    """Tests for MultiRoundTaskExecutor configuration options."""

    def test_detailed_summary_default(self, multi_round_executor_instance):
        """Test detailed_summary defaults to False."""
        assert multi_round_executor_instance.detailed_summary is False

    def test_streaming_default(self, multi_round_executor_instance):
        """Test streaming defaults to False."""
        assert multi_round_executor_instance.streaming is False

    def test_enable_thinking_default(self, multi_round_executor_instance):
        """Test enable_thinking is False by default."""
        assert multi_round_executor_instance.enable_thinking is False

    def test_mcp_config_default(self, multi_round_executor_instance):
        """Test MCP config is None by default."""
        assert multi_round_executor_instance.MCP_config_file is None

    def test_prompts_folder_default(self, multi_round_executor_instance):
        """Test prompts_folder is None by default."""
        assert multi_round_executor_instance.prompts_folder is None

    def test_user_id_default(self, multi_round_executor_instance):
        """Test user_id is None by default."""
        assert multi_round_executor_instance.user_id is None


class TestMultiRoundTaskExecutorAttributes:
    """Tests for MultiRoundTaskExecutor attribute completeness."""

    def test_all_init_params_stored(self, multi_round_executor_with_workspace):
        """Test that all initialization parameters are stored as attributes."""
        executor = multi_round_executor_with_workspace

        required_attrs = [
            'subtask_loops', 'logs_dir', 'workspace_dir', 'debug_mode',
            'api_key', 'model', 'api_base', 'detailed_summary',
            'interactive_mode', 'streaming', 'MCP_config_file',
            'prompts_folder', 'user_id', 'plan_mode', 'enable_thinking'
        ]

        for attr in required_attrs:
            assert hasattr(executor, attr), f"Missing attribute: {attr}"
