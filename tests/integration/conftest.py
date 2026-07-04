#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests configuration.

Playwright's sync API cannot run inside an asyncio event loop, and pytest's
asyncio/anyio plugins may leave event loops running between tests. This conftest
adds a fixture that explicitly cleans up any asyncio state after each test,
allowing Playwright's sync API to work in subsequent tests.
"""

import asyncio
import gc
import pytest


@pytest.fixture(autouse=True)
def cleanup_event_loops():
    """Cleanup any asyncio event loops that may have been created during the test.

    This is needed because pytest-asyncio and pytest-anyio can leave event loops
    running between tests, which breaks Playwright's sync API.
    """
    yield
    # After each test, try to clean up any lingering event loops
    try:
        # Try to get and stop the current event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.stop()
            if not loop.is_closed():
                loop.close()
        except RuntimeError:
            # No event loop in current thread - that's fine
            pass
    except Exception:
        pass
    finally:
        # Force garbage collection to clean up any lingering resources
        gc.collect()
