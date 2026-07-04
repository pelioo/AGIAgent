#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest wrapper for browser integration tests.

These tests verify the BrowserTools work end-to-end with a real Playwright
browser. Each test is run in a separate subprocess via
run_browser_integration.py to avoid Playwright's known greenlet pollution
issue (which causes "Cannot switch to a different thread" errors when
multiple sync_playwright() sessions run in the same process).

Run with:
    pytest tests/integration/test_browser.py -v
    # or run directly:
    python tests/integration/run_browser_integration.py
"""

import subprocess
import sys
from pathlib import Path

import pytest


INTEGRATION_RUNNER = Path(__file__).parent / "run_browser_integration.py"


def _run_integration_test(test_name: str) -> subprocess.CompletedProcess:
    """Run a single integration test in a subprocess."""
    return subprocess.run(
        [sys.executable, str(INTEGRATION_RUNNER), "--single-test", test_name],
        capture_output=True,
        text=True,
        timeout=120,
    )


# All tests that should run via subprocess
INTEGRATION_TESTS = [
    "test_lifecycle_open_file",
    "test_lifecycle_open_close",
    "test_lifecycle_invalid_url",
    "test_snapshot_returns_refs",
    "test_snapshot_creates_mapping",
    "test_click_button_changes_text",
    "test_fill_input",
    "test_check_checkbox",
    "test_select_option",
    "test_get_text",
    "test_get_url",
    "test_screenshot_saves_file",
    "test_screenshot_path_traversal_rejected",
    "test_scroll_down",
    "test_full_workflow",
    "test_navigate_and_interact",
]


@pytest.mark.parametrize("test_name", INTEGRATION_TESTS)
def test_integration_subprocess(test_name):
    """Run an integration test in a subprocess to isolate Playwright state.

    Playwright's sync API uses greenlets that are bound to OS threads.
    Running multiple sync_playwright() sessions in the same process causes
    'Cannot switch to a different thread' errors. Running each test in a
    fresh subprocess gives each test a clean greenlet state.
    """
    if not INTEGRATION_RUNNER.exists():
        pytest.skip(f"Integration runner not found: {INTEGRATION_RUNNER}")

    result = _run_integration_test(test_name)
    if result.returncode != 0:
        pytest.fail(
            f"Integration test '{test_name}' failed.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def test_runner_lists_all_tests():
    """Verify the runner script can list all available tests."""
    result = subprocess.run(
        [sys.executable, str(INTEGRATION_RUNNER), "--list"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    listed = set(result.stdout.strip().split("\n"))
    expected = set(INTEGRATION_TESTS)
    assert expected.issubset(listed), f"Missing tests: {expected - listed}"
