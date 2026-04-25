#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest configuration and fixtures for AGIAgent tests.

This conftest.py provides fixtures that match the actual class signatures
and module structure of the AGIAgent project.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Add project root to sys.path for all tests
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def setup_python_path():
    """Ensure project root is in Python path for all tests."""
    original = sys.path.copy()
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    yield
    sys.path[:] = original


@pytest.fixture
def project_root():
    """Return project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory structure.

    Matches the actual output_YYYYMMDD_HHMMSS/workspace pattern used
    by the project's MultiRoundTaskExecutor.
    """
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = tmp_path / f"output_{timestamp}"
    output_dir.mkdir(parents=True)
    workspace = output_dir / "workspace"
    workspace.mkdir()
    logs_dir = output_dir / "logs"
    logs_dir.mkdir()
    return output_dir


@pytest.fixture
def empty_workspace(tmp_path):
    """Create a simple workspace directory (no output_ structure)."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def mock_api_key_env(monkeypatch):
    """Set test API keys via environment variables."""
    monkeypatch.setenv("AGIAGENT_API_KEY", "test_key_12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")
    monkeypatch.setenv("AGIAGENT_API_BASE", "https://api.anthropic.com/v1")
    monkeypatch.setenv("AGIAGENT_MODEL", "claude-sonnet-4-0")
    return "test_key_12345"


@pytest.fixture
def sample_config_file(tmp_path):
    """Create a sample config.txt file."""
    config_file = tmp_path / "config.txt"
    config_file.write_text("""\
# AGI Agent Test Configuration
api_key=test_key_12345
api_base=https://api.anthropic.com/v1
model=claude-sonnet-4-0
max_tokens=8192
temperature=0.7
streaming=True
LANG=zh
enable_round_sync=True
sync_round=3
summary_trigger_length=100000
compression_strategy=llm_summary
multi_agent=False
enable_thinking=False
""", encoding="utf-8")
    return config_file


@pytest.fixture
def sample_config_file_minimal(tmp_path):
    """Create a minimal config file with only required fields."""
    config_file = tmp_path / "config_minimal.txt"
    config_file.write_text("""\
api_key=minimal_key
model=gpt-4
""", encoding="utf-8")
    return config_file


# ============================================================================
# Mock API Client Fixtures
# ============================================================================

@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client that mimics the actual response format."""
    with patch('anthropic.Anthropic') as mock:
        client = MagicMock()
        mock.return_value = client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="测试回复内容")]
        mock_response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0
        )
        client.messages.create.return_value = mock_response

        yield client


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    with patch('openai.OpenAI') as mock:
        client = MagicMock()
        mock.return_value = client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="OpenAI 测试回复"))]
        mock_response.usage = MagicMock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        client.chat.completions.create.return_value = mock_response

        yield client


# ============================================================================
# ToolExecutor Fixtures
# ============================================================================

@pytest.fixture
def tool_executor_instance(mock_api_key_env):
    """Create a ToolExecutor instance with mocked dependencies.

    Note: We mock at a high level to avoid importing heavy dependencies.
    """
    with patch('src.tool_executor.ToolExecutor.__init__', return_value=None):
        from src.tool_executor import ToolExecutor

        executor = ToolExecutor.__new__(ToolExecutor)
        executor.api_key = "test_key_12345"
        executor.api_base = "https://custom.endpoint/anthropic"
        executor.model = "claude-sonnet-4-0"
        executor.max_tokens = 8192
        executor.temperature = 0.7
        executor.streaming = False
        executor.enable_thinking = False
        executor.workspace_root = None
        executor.client = None
        executor._agent_id = None

        yield executor


@pytest.fixture
def tool_executor_with_workspace(mock_api_key_env, empty_workspace):
    """Create a ToolExecutor instance with a workspace directory."""
    with patch('src.tool_executor.ToolExecutor.__init__', return_value=None):
        from src.tool_executor import ToolExecutor

        executor = ToolExecutor.__new__(ToolExecutor)
        executor.api_key = "test_key_12345"
        executor.api_base = "https://custom.endpoint/anthropic"
        executor.model = "claude-sonnet-4-0"
        executor.max_tokens = 8192
        executor.temperature = 0.7
        executor.streaming = False
        executor.enable_thinking = False
        executor.workspace_root = str(empty_workspace)
        executor.workspace_dir = str(empty_workspace)
        executor.client = None
        executor._agent_id = None

        yield executor


# ============================================================================
# Tools Class Fixtures
# ============================================================================

@pytest.fixture
def base_tools_instance():
    """Create a BaseTools instance without heavy dependencies."""
    with patch('src.tools.base_tools.BaseTools._init_code_parser', return_value=None):
        with patch('src.tools.base_tools.BaseTools._init_terminal_tools', return_value=None):
            with patch('src.tools.base_tools.BaseTools._init_sensor_collector', return_value=None):
                from src.tools.base_tools import BaseTools
                tools = BaseTools(workspace_root=None, model="claude-sonnet-4-0")
                yield tools


@pytest.fixture
def base_tools_with_workspace(empty_workspace):
    """Create a BaseTools instance with a workspace directory."""
    with patch('src.tools.base_tools.BaseTools._init_code_parser', return_value=None):
        with patch('src.tools.base_tools.BaseTools._init_terminal_tools', return_value=None):
            with patch('src.tools.base_tools.BaseTools._init_sensor_collector', return_value=None):
                from src.tools.base_tools import BaseTools
                tools = BaseTools(workspace_root=str(empty_workspace), model="claude-sonnet-4-0")
                yield tools


@pytest.fixture
def tools_instance_minimal(empty_workspace):
    """Create a minimal Tools instance for testing (mocks optional dependencies).

    Tests the base Tools class without MCP_KB_TOOLS_AVAILABLE and
    PLUGIN_TOOLS_AVAILABLE dependencies.
    """
    # Mock the optional dependencies before importing Tools
    with patch.dict('sys.modules', {
        'src.tools.mcp_knowledge_base_tools': MagicMock(),
        'tools_plugin': MagicMock(),
    }):
        with patch('src.tools.base_tools.BaseTools._init_code_parser', return_value=None):
            with patch('src.tools.base_tools.BaseTools._init_terminal_tools', return_value=None):
                with patch('src.tools.base_tools.BaseTools._init_sensor_collector', return_value=None):
                    # Mock WebSearchTools init to avoid LLM client setup
                    with patch('src.tools.web_search_tools.WebSearchTools.__init__', return_value=None):
                        # Mock ImageGenerationTools init
                        with patch('src.tools.image_generation_tools.ImageGenerationTools.__init__', return_value=None):
                            from src.tools import Tools

                            # Create instance without calling __init__
                            tools = object.__new__(Tools)
                            tools.workspace_root = str(empty_workspace)
                            tools.model = "claude-sonnet-4-0"
                            tools._agent_id = None
                            tools.llm_client = None
                            tools.code_parser = None

                            yield tools


# ============================================================================
# MultiRoundTaskExecutor Fixtures
# ============================================================================

@pytest.fixture
def multi_round_executor_instance(mock_api_key_env):
    """Create a MultiRoundTaskExecutor instance with mocked dependencies."""
    with patch('src.multi_round_executor.executor.MultiRoundTaskExecutor.__init__', return_value=None):
        from src.multi_round_executor.executor import MultiRoundTaskExecutor

        executor = MultiRoundTaskExecutor.__new__(MultiRoundTaskExecutor)
        executor.subtask_loops = 10
        executor.logs_dir = "logs"
        executor.workspace_dir = None
        executor.debug_mode = False
        executor.plan_mode = False
        executor.api_key = "test_key_12345"
        executor.model = "claude-sonnet-4-0"
        executor.api_base = "https://custom.endpoint/anthropic"
        executor.detailed_summary = False
        executor.interactive_mode = False
        executor.streaming = False
        executor.MCP_config_file = None
        executor.prompts_folder = None
        executor.user_id = None
        executor.enable_thinking = False

        yield executor


@pytest.fixture
def multi_round_executor_with_workspace(mock_api_key_env, temp_workspace):
    """Create a MultiRoundTaskExecutor with a workspace directory."""
    with patch('src.multi_round_executor.executor.MultiRoundTaskExecutor.__init__', return_value=None):
        from src.multi_round_executor.executor import MultiRoundTaskExecutor

        executor = MultiRoundTaskExecutor.__new__(MultiRoundTaskExecutor)
        executor.subtask_loops = 5
        executor.logs_dir = str(temp_workspace / "logs")
        executor.workspace_dir = str(temp_workspace)
        executor.debug_mode = False
        executor.plan_mode = False
        executor.api_key = "test_key_12345"
        executor.model = "claude-sonnet-4-0"
        executor.api_base = "https://custom.endpoint/anthropic"
        executor.detailed_summary = False
        executor.interactive_mode = False
        executor.streaming = False
        executor.MCP_config_file = None
        executor.prompts_folder = None
        executor.user_id = None
        executor.enable_thinking = False

        yield executor


# ============================================================================
# API Callers Fixtures
# ============================================================================

@pytest.fixture
def api_executor_mock():
    """Create a mock executor object for API callers testing.

    This mimics the ToolExecutor interface used by api_callers functions.
    """
    mock = MagicMock()
    mock.enable_thinking = False
    mock.temperature = 0.7
    mock.model = "claude-sonnet-4-0"
    mock.workspace_root = None

    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="API Caller Test Response")]
    mock_response.usage = MagicMock(
        input_tokens=50,
        output_tokens=30,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0
    )
    mock.client = MagicMock()
    mock.client.messages.create.return_value = mock_response
    # Properly mock parse_tool_calls to return a list
    mock.parse_tool_calls = MagicMock(return_value=[])

    return mock


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture
def clean_config_cache():
    """Clear config cache before and after test."""
    from src.config_loader import clear_config_cache
    clear_config_cache()
    yield
    clear_config_cache()
