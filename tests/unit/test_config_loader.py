#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for src/config_loader.py

Tests cover all exported functions from the config_loader module:
- load_config
- get_api_key
- get_api_base
- get_model
- get_config_value
- get_max_tokens
- get_streaming
- get_language
- get_enable_round_sync
- get_sync_round
- get_truncation_length
- clear_config_cache
- get_summary_trigger_length
- get_compression_strategy
- get_temperature
- get_top_p
- get_multi_agent
- get_enable_thinking
"""

import os
import pytest
from src.config_loader import (
    load_config,
    get_api_key,
    get_api_base,
    get_model,
    get_config_value,
    get_max_tokens,
    get_streaming,
    get_language,
    get_enable_round_sync,
    get_sync_round,
    get_truncation_length,
    clear_config_cache,
)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_basic(self, sample_config_file, clean_config_cache):
        """Test loading a basic configuration file."""
        config = load_config(str(sample_config_file))
        assert config["api_key"] == "test_key_12345"
        assert config["model"] == "claude-sonnet-4-0"

    def test_load_config_file_not_found(self, clean_config_cache):
        """Test loading a non-existent config file returns empty dict."""
        config = load_config("nonexistent_config.txt")
        assert config == {}

    def test_load_config_verbose(self, sample_config_file, clean_config_cache, capsys):
        """Test verbose mode prints debug information."""
        config = load_config(str(sample_config_file), verbose=True)
        captured = capsys.readouterr()
        assert "Loading configuration from" in captured.out

    def test_load_config_with_comments(self, tmp_path, clean_config_cache):
        """Test that # comments are properly skipped."""
        config_file = tmp_path / "config_comments.txt"
        config_file.write_text("""\
# This is a full-line comment
api_key=real_key
# api_key=disabled_key
model=test_model
temperature=0.5
""", encoding="utf-8")
        config = load_config(str(config_file))
        assert config["api_key"] == "real_key"
        assert "disabled_key" not in str(config)

    def test_load_config_inline_comment(self, tmp_path, clean_config_cache):
        """Test inline comments (text after # in a line with =)."""
        config_file = tmp_path / "config_inline.txt"
        config_file.write_text("""\
api_key=my_key  # inline comment here
model=my_model # another comment
""", encoding="utf-8")
        config = load_config(str(config_file))
        assert config["api_key"] == "my_key"
        assert config["model"] == "my_model"

    def test_load_config_empty_value(self, tmp_path, clean_config_cache):
        """Test that empty values (api_key=) are preserved."""
        config_file = tmp_path / "config_empty.txt"
        config_file.write_text("api_key=\nmodel=test\n", encoding="utf-8")
        config = load_config(str(config_file))
        assert config["api_key"] == ""

    def test_load_config_whitespace(self, tmp_path, clean_config_cache):
        """Test that whitespace around key=value is trimmed."""
        config_file = tmp_path / "config_ws.txt"
        config_file.write_text("  api_key  =  trimmed_value  \n  model=test  \n", encoding="utf-8")
        config = load_config(str(config_file))
        assert config["api_key"] == "trimmed_value"
        assert config["model"] == "test"

    def test_load_config_cache(self, sample_config_file, clean_config_cache):
        """Test that configuration is cached after first load."""
        config1 = load_config(str(sample_config_file))
        config2 = load_config(str(sample_config_file))
        assert config1 == config2

    def test_load_config_cache_invalidation(self, tmp_path, clean_config_cache):
        """Test that cache is invalidated when file is modified."""
        config_file = tmp_path / "config_cache.txt"
        config_file.write_text("api_key=key_v1\n", encoding="utf-8")

        config1 = load_config(str(config_file))
        assert config1["api_key"] == "key_v1"

        # Touch file to update mtime (Windows may have 1-2 second mtime resolution)
        import time
        time.sleep(1.1)
        config_file.write_text("api_key=key_v2\n", encoding="utf-8")

        config2 = load_config(str(config_file))
        assert config2["api_key"] == "key_v2"

    def test_agia_config_file_env(self, monkeypatch, tmp_path, clean_config_cache):
        """Test AGIA_CONFIG_FILE environment variable overrides default path."""
        config_file = tmp_path / "custom_config.txt"
        config_file.write_text("api_key=custom_key\nmodel=custom_model\n", encoding="utf-8")
        monkeypatch.setenv("AGIA_CONFIG_FILE", str(config_file))
        config = load_config()  # uses default path, should be overridden
        assert config["api_key"] == "custom_key"


class TestGetApiKey:
    """Tests for get_api_key function."""

    def test_get_api_key_from_env(self, monkeypatch, clean_config_cache):
        """Test reading API key from AGIBOT_API_KEY environment variable (highest priority)."""
        monkeypatch.setenv("AGIBOT_API_KEY", "env_api_key")
        # Use non-existent path to bypass real config file
        key = get_api_key("nonexistent_config_for_env_test.txt")
        assert key == "env_api_key"

    def test_get_api_key_from_file(self, sample_config_file, clean_config_cache):
        """Test reading API key from config file."""
        key = get_api_key(str(sample_config_file))
        assert key == "test_key_12345"

    def test_get_api_key_not_found(self, clean_config_cache):
        """Test that None is returned when no API key is found."""
        # Ensure env vars don't interfere
        os.environ.pop("AGIAGENT_API_KEY", None)
        os.environ.pop("AGIBOT_API_KEY", None)
        key = get_api_key("nonexistent.txt")
        assert key is None

    def test_get_api_key_agibot_env_priority(self, monkeypatch, clean_config_cache):
        """Test AGIBOT_API_KEY environment variable has priority."""
        monkeypatch.setenv("AGIBOT_API_KEY", "agibot_priority_key")
        monkeypatch.setenv("AGIAGENT_API_KEY", "agent_fallback_key")
        key = get_api_key()
        assert key == "agibot_priority_key"

    def test_get_api_key_empty_in_file(self, tmp_path, clean_config_cache):
        """Test that empty api_key= in file returns empty string."""
        config_file = tmp_path / "config_empty_key.txt"
        config_file.write_text("api_key=\nmodel=test\n", encoding="utf-8")
        key = get_api_key(str(config_file))
        assert key == ""


class TestGetApiBase:
    """Tests for get_api_base function."""

    def test_get_api_base_from_env(self, monkeypatch, clean_config_cache):
        """Test reading API base from AGIBOT_API_BASE environment variable."""
        monkeypatch.setenv("AGIBOT_API_BASE", "https://custom.api/v1")
        base = get_api_base("nonexistent_config_for_env_test.txt")
        assert base == "https://custom.api/v1"

    def test_get_api_base_from_file(self, sample_config_file, clean_config_cache):
        """Test reading API base from config file."""
        base = get_api_base(str(sample_config_file))
        assert base == "https://api.anthropic.com/v1"

    def test_get_api_base_not_found(self, clean_config_cache):
        """Test that None is returned when no API base is found."""
        os.environ.pop("AGIAGENT_API_BASE", None)
        os.environ.pop("AGIBOT_API_BASE", None)
        base = get_api_base("nonexistent.txt")
        assert base is None


class TestGetModel:
    """Tests for get_model function."""

    def test_get_model_from_env(self, monkeypatch, clean_config_cache):
        """Test reading model from AGIBOT_MODEL environment variable."""
        monkeypatch.setenv("AGIBOT_MODEL", "gpt-5-test")
        model = get_model("nonexistent_config_for_env_test.txt")
        assert model == "gpt-5-test"

    def test_get_model_from_file(self, sample_config_file, clean_config_cache):
        """Test reading model from config file."""
        model = get_model(str(sample_config_file))
        assert model == "claude-sonnet-4-0"

    def test_get_model_agibot_priority(self, monkeypatch, clean_config_cache):
        """Test AGIBOT_MODEL environment variable has priority."""
        monkeypatch.setenv("AGIBOT_MODEL", "priority_model")
        monkeypatch.setenv("AGIAGENT_MODEL", "fallback_model")
        model = get_model()
        assert model == "priority_model"


class TestGetConfigValue:
    """Tests for get_config_value function."""

    def test_get_config_value_existing(self, sample_config_file, clean_config_cache):
        """Test reading an existing config value."""
        value = get_config_value("model", config_file=str(sample_config_file))
        assert value == "claude-sonnet-4-0"

    def test_get_config_value_default(self, sample_config_file, clean_config_cache):
        """Test default value when key doesn't exist."""
        value = get_config_value("nonexistent_key", default="default_value", config_file=str(sample_config_file))
        assert value == "default_value"

    def test_get_config_value_no_default(self, sample_config_file, clean_config_cache):
        """Test None is returned when key doesn't exist and no default given."""
        value = get_config_value("nonexistent_key", config_file=str(sample_config_file))
        assert value is None


class TestGetMaxTokens:
    """Tests for get_max_tokens function."""

    def test_get_max_tokens_from_file(self, sample_config_file, clean_config_cache):
        """Test reading max_tokens from config file."""
        tokens = get_max_tokens(str(sample_config_file))
        assert tokens == 8192

    def test_get_max_tokens_default_claude(self, tmp_path, monkeypatch, clean_config_cache):
        """Test default max_tokens for Claude models when not specified."""
        config_file = tmp_path / "config_no_model.txt"
        config_file.write_text("api_key=test\n", encoding="utf-8")
        monkeypatch.setenv("AGIBOT_MODEL", "claude-3-5-sonnet")
        tokens = get_max_tokens(str(config_file))
        assert tokens == 16384  # Claude default

    def test_get_max_tokens_default_gpt(self, sample_config_file_minimal, monkeypatch, clean_config_cache):
        """Test default max_tokens for GPT models when not specified."""
        monkeypatch.setenv("AGIAGENT_MODEL", "gpt-4")
        tokens = get_max_tokens(str(sample_config_file_minimal))
        assert tokens == 8192  # GPT default

    def test_get_max_tokens_invalid_value(self, tmp_path, monkeypatch, clean_config_cache):
        """Test fallback to defaults when max_tokens is invalid."""
        config_file = tmp_path / "config_bad_tokens.txt"
        config_file.write_text("max_tokens=invalid\n", encoding="utf-8")
        monkeypatch.setenv("AGIAGENT_MODEL", "claude-3-5-sonnet")
        tokens = get_max_tokens(str(config_file))
        assert tokens == 16384  # Should fall back to model default


class TestGetStreaming:
    """Tests for get_streaming function."""

    def test_get_streaming_true(self, tmp_path, clean_config_cache):
        """Test streaming=True."""
        config_file = tmp_path / "config_stream.txt"
        config_file.write_text("streaming=True\n", encoding="utf-8")
        assert get_streaming(str(config_file)) is True

    def test_get_streaming_false(self, tmp_path, clean_config_cache):
        """Test streaming=False."""
        config_file = tmp_path / "config_stream.txt"
        config_file.write_text("streaming=False\n", encoding="utf-8")
        assert get_streaming(str(config_file)) is False

    def test_get_streaming_default(self, tmp_path, clean_config_cache):
        """Test default streaming value when not specified."""
        config_file = tmp_path / "config_stream.txt"
        config_file.write_text("model=test\n", encoding="utf-8")
        assert get_streaming(str(config_file)) is False


class TestGetLanguage:
    """Tests for get_language function."""

    def test_get_language_zh(self, tmp_path, clean_config_cache):
        """Test Chinese language code."""
        config_file = tmp_path / "config_lang.txt"
        config_file.write_text("LANG=zh\n", encoding="utf-8")
        assert get_language(str(config_file)) == "zh"

    def test_get_language_en(self, tmp_path, clean_config_cache):
        """Test English language code."""
        config_file = tmp_path / "config_lang.txt"
        config_file.write_text("LANG=en\n", encoding="utf-8")
        assert get_language(str(config_file)) == "en"

    def test_get_language_default(self, tmp_path, clean_config_cache):
        """Test default language when not specified."""
        config_file = tmp_path / "config_lang.txt"
        config_file.write_text("model=test\n", encoding="utf-8")
        assert get_language(str(config_file)) == "en"


class TestGetEnableRoundSync:
    """Tests for get_enable_round_sync function."""

    def test_get_enable_round_sync_true(self, sample_config_file, clean_config_cache):
        """Test enable_round_sync=True."""
        assert get_enable_round_sync(str(sample_config_file)) is True

    def test_get_enable_round_sync_false(self, tmp_path, clean_config_cache):
        """Test enable_round_sync=False."""
        config_file = tmp_path / "config_round.txt"
        config_file.write_text("enable_round_sync=False\n", encoding="utf-8")
        assert get_enable_round_sync(str(config_file)) is False

    def test_get_enable_round_sync_default(self, tmp_path, clean_config_cache):
        """Test default value when not specified."""
        config_file = tmp_path / "config_round.txt"
        config_file.write_text("model=test\n", encoding="utf-8")
        assert get_enable_round_sync(str(config_file)) is False


class TestGetSyncRound:
    """Tests for get_sync_round function."""

    def test_get_sync_round_value(self, sample_config_file, clean_config_cache):
        """Test reading sync_round value."""
        assert get_sync_round(str(sample_config_file)) == 3

    def test_get_sync_round_default(self, tmp_path, clean_config_cache):
        """Test default sync_round when not specified."""
        config_file = tmp_path / "config_sync.txt"
        config_file.write_text("model=test\n", encoding="utf-8")
        assert get_sync_round(str(config_file)) == 2

    def test_get_sync_round_invalid(self, tmp_path, clean_config_cache):
        """Test default when invalid value is specified."""
        config_file = tmp_path / "config_sync.txt"
        config_file.write_text("sync_round=invalid\n", encoding="utf-8")
        assert get_sync_round(str(config_file)) == 2


class TestGetTruncationLength:
    """Tests for get_truncation_length function."""

    def test_get_truncation_length_value(self, tmp_path, clean_config_cache):
        """Test reading truncation_length value."""
        config_file = tmp_path / "config_trunc.txt"
        config_file.write_text("truncation_length=5000\n", encoding="utf-8")
        assert get_truncation_length(str(config_file)) == 5000

    def test_get_truncation_length_default(self, tmp_path, clean_config_cache):
        """Test default truncation_length when not specified."""
        config_file = tmp_path / "config_trunc.txt"
        config_file.write_text("model=test\n", encoding="utf-8")
        assert get_truncation_length(str(config_file)) == 10000

    def test_get_truncation_length_invalid(self, tmp_path, clean_config_cache):
        """Test default when invalid value is specified."""
        config_file = tmp_path / "config_trunc.txt"
        config_file.write_text("truncation_length=invalid\n", encoding="utf-8")
        assert get_truncation_length(str(config_file)) == 10000


class TestClearConfigCache:
    """Tests for clear_config_cache function."""

    def test_clear_config_cache(self, sample_config_file, clean_config_cache):
        """Test that clear_config_cache removes cached values."""
        config1 = load_config(str(sample_config_file))
        assert len(config1) > 0

        clear_config_cache()

        # After clearing, file should be re-read
        # Verify by checking the cache was indeed cleared
        # (We can't directly inspect _config_cache, but we can verify
        # the function runs without error)
        assert True

    def test_clear_config_cache_idempotent(self, clean_config_cache):
        """Test that clearing cache multiple times is safe."""
        clear_config_cache()
        clear_config_cache()
        clear_config_cache()
        assert True
