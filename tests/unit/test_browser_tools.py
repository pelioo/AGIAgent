#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for src/tools/browser_tools.py

Tests cover:
- BrowserTools initialization
- BrowserState state machine
- _make_response format and state transitions
- _validate_url (http/https/file/javascript/data injection prevention)
- _validate_screenshot_path (path traversal prevention)
- _resolve_ref (@ref → selector mapping)
- Error responses when browser is closed
- Parameter validation (scroll direction/pixels, keyboard_type length)
- browser_automation dispatch (action routing)
- browser_fill_form selector handling
- Mocked Playwright integration (without launching real browser)

Note: Full browser-driven integration tests live in tests/integration/test_browser.py
"""

import os
import re
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.tools.browser_tools import BrowserTools, BrowserState


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def browser_tools(empty_workspace):
    """Create a BrowserTools instance with a workspace."""
    from src.tools.browser_tools import BrowserTools, BrowserState
    return BrowserTools(workspace_root=str(empty_workspace))


@pytest.fixture
def browser_tools_no_workspace():
    """Create a BrowserTools instance without a workspace."""
    from src.tools.browser_tools import BrowserTools, BrowserState
    return BrowserTools()


@pytest.fixture
def mock_page():
    """Create a mock Playwright Page object."""
    page = MagicMock()
    page.url = "https://example.com/"
    page.title.return_value = "Example Domain"
    return page


@pytest.fixture
def browser_tools_with_page(browser_tools, mock_page):
    """BrowserTools instance pre-configured with a mock page."""
    browser_tools._page = mock_page
    browser_tools._state = browser_tools._state.__class__.BROWSING
    return browser_tools


# ============================================================================
# Initialization Tests
# ============================================================================

class TestBrowserToolsInit:
    """Tests for BrowserTools initialization."""

    def test_init_without_workspace(self, browser_tools_no_workspace):
        """Test initialization without workspace_root."""
        bt = browser_tools_no_workspace
        assert bt.workspace_root is None
        assert bt._state.value == "idle"
        assert bt._playwright is None
        assert bt._browser is None
        assert bt._context is None
        assert bt._page is None
        assert bt._ref_to_selector == {}

    def test_init_with_workspace(self, browser_tools, empty_workspace):
        """Test initialization with workspace_root."""
        assert browser_tools.workspace_root == str(empty_workspace)
        assert browser_tools._state.value == "idle"

    def test_next_step_hints_completeness(self):
        """NEXT_STEP_HINTS must contain entries for all public actions."""
        from src.tools.browser_tools import BrowserTools, BrowserState
        expected_actions = {
            "open", "snapshot", "click", "fill", "check", "uncheck", "type",
            "select", "press", "scroll", "screenshot", "back", "forward", "reload",
            "wait", "hover", "get_text", "get_value", "is_checked", "get_url",
            "keyboard_type", "close", "fill_form", "navigate_and_interact",
        }
        assert set(BrowserTools.NEXT_STEP_HINTS.keys()) == expected_actions

    def test_url_scheme_whitelist_behavior(self):
        """D-3 修复回归：ALLOWED_URL_SCHEMES 常量已删除；断言通过实际 _validate_url 行为验证白名单。

        约定的安全 scheme：仅 http/https/file；危险 scheme 必须被拒绝。
        """
        from src.tools.browser_tools import BrowserTools
        bt = BrowserTools()
        # 允许的 scheme
        assert bt._validate_url("http://example.com") is None
        assert bt._validate_url("https://example.com") is None
        # 危险的 scheme 必须被拒绝
        assert bt._validate_url("javascript:alert(1)") is not None
        assert bt._validate_url("vbscript:msgbox(1)") is not None
        assert bt._validate_url("data:text/html,<script>alert(1)</script>") is not None
        assert bt._validate_url("blob:http://x.com/abc") is not None


# ============================================================================
# State Machine Tests
# ============================================================================

class TestBrowserStateMachine:
    """Tests for BrowserState state machine transitions."""

    def test_initial_state_is_idle(self, browser_tools):
        """Initial state should be IDLE."""
        from src.tools.browser_tools import BrowserState
        assert browser_tools._state == BrowserState.IDLE

    def test_closed_state_blocks_actions(self, browser_tools):
        """Once CLOSED, all interactive actions should fail."""
        from src.tools.browser_tools import BrowserState
        browser_tools._state = BrowserState.CLOSED

        # All these actions should return error
        actions_to_test = [
            ("browser_click", ("@e1",)),
            ("browser_snapshot", ()),
            ("browser_fill", ("@e1", "value")),
            ("browser_type", ("@e1", "value")),
            ("browser_screenshot", ("path.png",)),
            ("browser_select", ("@e1", "value")),
            ("browser_check", ("@e1",)),
            ("browser_uncheck", ("@e1",)),
            ("browser_press", ("Enter",)),
            ("browser_back", ()),
            ("browser_forward", ()),
            ("browser_reload", ()),
            ("browser_scroll", ("down", 500)),
            ("browser_wait", ("1000",)),
            ("browser_hover", ("@e1",)),
            ("browser_get_text", (None,)),
            ("browser_get_url", ()),
            ("browser_keyboard_type", ("text",)),
        ]
        for method_name, args in actions_to_test:
            method = getattr(browser_tools, method_name)
            result = method(*args)
            assert result["success"] is False, f"{method_name} should fail when CLOSED"
            assert "closed" in result["error"].lower(), \
                f"{method_name} error should mention 'closed', got: {result['error']}"

    def test_closed_state_resets_on_open(self, browser_tools):
        """If open() is called after close, state should reset."""
        from src.tools.browser_tools import BrowserState
        browser_tools._state = BrowserState.CLOSED
        # Mock _ensure_playwright to avoid actually launching
        with patch.object(browser_tools, "_ensure_playwright") as mock_pw:
            mock_pw.return_value.chromium.launch.return_value.new_context.return_value.new_page.return_value = MagicMock()
            # Patch page.goto to succeed
            mock_page = mock_pw.return_value.chromium.launch.return_value.new_context.return_value.new_page.return_value
            mock_page.goto.return_value = MagicMock()  # non-None response
            mock_page.url = "https://example.com"
            mock_page.title.return_value = "Example"

            result = browser_tools.browser_open("https://example.com")
            # After successful open, state should be OPENED
            assert result["success"] is True
            assert browser_tools._state == BrowserState.OPENED

    def test_state_transitions_via_make_response(self, browser_tools):
        """_make_response should update state when update_state is provided."""
        from src.tools.browser_tools import BrowserState
        browser_tools._make_response("test", update_state=BrowserState.BROWSING)
        assert browser_tools._state == BrowserState.BROWSING


# ============================================================================
# Response Format Tests
# ============================================================================

class TestMakeResponse:
    """Tests for the unified _make_response format."""

    def test_success_response_basic(self, browser_tools):
        """Success response should include all required fields."""
        r = browser_tools._make_response("open", success=True)
        assert r["success"] is True
        assert r["status"] == "idle"
        assert r["action"] == "open"
        assert "timestamp" in r
        assert isinstance(r["timestamp"], float)
        assert "next_step" in r
        assert r["next_step"] == browser_tools.NEXT_STEP_HINTS["open"]

    def test_error_response(self, browser_tools):
        """Error response should include error field."""
        r = browser_tools._make_response("open", success=False, error="bad URL")
        assert r["success"] is False
        assert r["error"] == "bad URL"

    def test_data_merges_into_response(self, browser_tools):
        """data dict should be merged into the response (flat, not nested)."""
        r = browser_tools._make_response("open", success=True, data={"title": "Test", "url": "https://x"})
        assert r["title"] == "Test"
        assert r["url"] == "https://x"
        # data is merged into top level, no 'data' key
        assert "data" not in r

    def test_next_step_uses_default_for_unknown_action(self, browser_tools):
        """Unknown action should fall back to default next_step."""
        r = browser_tools._make_response("totally_unknown", success=True)
        assert r["next_step"] == "Continue your task"


# ============================================================================
# URL Validation Tests
# ============================================================================

class TestValidateUrl:
    """Tests for _validate_url security checks."""

    def test_https_url_accepted(self, browser_tools):
        """https:// URLs should be allowed."""
        assert browser_tools._validate_url("https://example.com") is None

    def test_http_url_accepted(self, browser_tools):
        """http:// URLs should be allowed."""
        assert browser_tools._validate_url("http://example.com") is None

    def test_empty_url_rejected(self, browser_tools):
        """Empty URL should be rejected."""
        err = browser_tools._validate_url("")
        assert err is not None
        assert "empty" in err.lower()

    def test_javascript_url_rejected(self, browser_tools):
        """javascript: URLs must be rejected (XSS prevention)."""
        err = browser_tools._validate_url("javascript:alert(1)")
        assert err is not None
        assert "scheme" in err.lower()

    def test_data_url_rejected(self, browser_tools):
        """data: URLs must be rejected."""
        err = browser_tools._validate_url("data:text/html,<script>alert(1)</script>")
        assert err is not None

    def test_vbscript_url_rejected(self, browser_tools):
        """vbscript: URLs must be rejected."""
        err = browser_tools._validate_url("vbscript:msgbox(1)")
        assert err is not None

    def test_file_url_with_path_traversal_rejected(self, browser_tools):
        """file:// URLs with .. should be rejected."""
        err = browser_tools._validate_url("file:///etc/../../passwd")
        assert err is not None
        assert "traversal" in err.lower() or "outside" in err.lower()

    def test_file_url_outside_workspace_rejected(self, browser_tools, empty_workspace):
        """file:// URL pointing outside workspace should be rejected."""
        # On Windows: file:///C:/Windows/system32
        # On Unix: file:///etc/passwd
        if os.name == "nt":
            url = "file:///C:/Windows/system32"
        else:
            url = "file:///etc/passwd"
        err = browser_tools._validate_url(url)
        assert err is not None


# ============================================================================
# Path Validation Tests
# ============================================================================

class TestValidateScreenshotPath:
    """Tests for _validate_screenshot_path security checks."""

    def test_empty_path_rejected(self, browser_tools):
        """Empty path must be rejected (would default to current dir)."""
        err = browser_tools._validate_screenshot_path("")
        assert err is not None

    def test_none_path_rejected(self, browser_tools):
        """None path must be rejected."""
        err = browser_tools._validate_screenshot_path(None)
        assert err is not None

    def test_path_traversal_rejected(self, browser_tools):
        """Paths containing .. must be rejected."""
        err = browser_tools._validate_screenshot_path("../etc/passwd")
        assert err is not None
        assert "traversal" in err.lower() or "invalid" in err.lower()

    def test_absolute_path_outside_workspace_rejected(self, browser_tools):
        """Absolute paths outside workspace must be rejected."""
        if os.name == "nt":
            path = "C:/Windows/System32/evil.png"
        else:
            path = "/etc/passwd"
        err = browser_tools._validate_screenshot_path(path)
        assert err is not None

    def test_absolute_path_within_workspace_accepted(self, browser_tools, empty_workspace):
        """Absolute paths within workspace should be accepted."""
        valid_path = os.path.join(str(empty_workspace), "screenshot.png")
        err = browser_tools._validate_screenshot_path(valid_path)
        assert err is None

    def test_relative_path_accepted(self, browser_tools):
        """Relative paths (without leading /) should be accepted."""
        err = browser_tools._validate_screenshot_path("screenshots/test.png")
        assert err is None


# ============================================================================
# @ref Resolution Tests
# ============================================================================

class TestRefResolution:
    """Tests for @ref → selector mapping."""

    def test_known_ref_resolves(self, browser_tools):
        """@e1 should resolve to its mapped selector."""
        browser_tools._ref_to_selector = {"e1": "#submit", "e2": '[name="email"]'}
        assert browser_tools._resolve_ref("@e1") == "#submit"
        assert browser_tools._resolve_ref("@e2") == '[name="email"]'

    def test_unknown_ref_raises(self, browser_tools):
        """Unknown @ref should raise ValueError."""
        browser_tools._ref_to_selector = {"e1": "#submit"}
        with pytest.raises(ValueError) as exc_info:
            browser_tools._resolve_ref("@e99")
        assert "@e99" in str(exc_info.value)
        assert "snapshot" in str(exc_info.value).lower()

    def test_non_ref_selector_passthrough(self, browser_tools):
        """Non-@ref selectors should pass through unchanged."""
        browser_tools._ref_to_selector = {"e1": "#submit"}
        assert browser_tools._resolve_ref("#other") == "#other"
        assert browser_tools._resolve_ref("text=Submit") == "text=Submit"
        assert browser_tools._resolve_ref("button.primary") == "button.primary"

    def test_empty_selector_passthrough(self, browser_tools):
        """Empty selector should pass through (will fail later in click)."""
        assert browser_tools._resolve_ref("") == ""

    def test_ref_with_whitespace_trimmed(self, browser_tools):
        """@ref with surrounding whitespace should still resolve."""
        browser_tools._ref_to_selector = {"e1": "#submit"}
        assert browser_tools._resolve_ref("  @e1  ") == "#submit"


# ============================================================================
# Selector Building Tests
# ============================================================================

class TestBuildSelector:
    """Tests for building CSS selectors from elements."""

    def test_id_attribute_preferred(self, browser_tools):
        """Elements with valid id should get #id selector."""
        elem = MagicMock()
        elem.get_attribute.side_effect = lambda attr: {
            "id": "submit-btn", "name": "submit", "aria-label": "Submit"
        }.get(attr)
        selector = browser_tools._build_selector_for_element(elem)
        assert selector == "#submit-btn"

    def test_invalid_id_falls_back_to_name(self, browser_tools):
        """Elements with invalid id should fall back to name."""
        elem = MagicMock()
        elem.get_attribute.side_effect = lambda attr: {
            "id": "123-invalid",  # starts with digit
            "name": "submit",
            "aria-label": "Submit"
        }.get(attr)
        selector = browser_tools._build_selector_for_element(elem)
        assert selector == '[name="submit"]'

    def test_name_attribute(self, browser_tools):
        """Elements with name should get [name=x] selector."""
        elem = MagicMock()
        elem.get_attribute.side_effect = lambda attr: {
            "id": None, "name": "email", "aria-label": None, "placeholder": None
        }.get(attr)
        selector = browser_tools._build_selector_for_element(elem)
        assert selector == '[name="email"]'

    def test_aria_label_attribute(self, browser_tools):
        """Elements with only aria-label should get [aria-label=x] selector."""
        elem = MagicMock()
        elem.get_attribute.side_effect = lambda attr: {
            "id": None, "name": None, "aria-label": "Close dialog", "placeholder": None
        }.get(attr)
        selector = browser_tools._build_selector_for_element(elem)
        assert selector == '[aria-label="Close dialog"]'

    def test_placeholder_attribute(self, browser_tools):
        """Elements with only placeholder should get [placeholder=x] selector."""
        elem = MagicMock()
        elem.get_attribute.side_effect = lambda attr: {
            "id": None, "name": None, "aria-label": None, "placeholder": "Enter text"
        }.get(attr)
        selector = browser_tools._build_selector_for_element(elem)
        assert selector == '[placeholder="Enter text"]'

    def test_quotes_in_aria_label_escaped(self, browser_tools):
        """Quotes in aria-label should be escaped."""
        elem = MagicMock()
        elem.get_attribute.side_effect = lambda attr: {
            "id": None, "name": None, "aria-label": 'Say "Hello"', "placeholder": None
        }.get(attr)
        selector = browser_tools._build_selector_for_element(elem)
        assert '\\"' in selector

    def test_no_identifying_attribute_no_text_returns_none(self, browser_tools):
        """Elements without identifying attributes AND without text should return None."""
        elem = MagicMock()
        elem.get_attribute.return_value = None
        elem.inner_text.return_value = ""  # no text either
        selector = browser_tools._build_selector_for_element(elem)
        assert selector is None

    def test_long_text_truncated(self, browser_tools):
        """Long aria-labels should be truncated to 50 chars."""
        long_label = "x" * 100
        elem = MagicMock()
        elem.get_attribute.side_effect = lambda attr: {
            "id": None, "name": None, "aria-label": long_label, "placeholder": None
        }.get(attr)
        selector = browser_tools._build_selector_for_element(elem)
        assert selector is not None
        # Inside the quoted portion should be <= 50 chars
        assert len(selector) <= len('[aria-label=""]') + 50


# ============================================================================
# Mocked Playwright Tests
# ============================================================================

class TestBrowserOpenMocked:
    """Tests for browser_open with mocked Playwright."""

    def test_open_with_invalid_url_returns_error(self, browser_tools):
        """Open with non-http URL should return error without launching browser."""
        result = browser_tools.browser_open("javascript:alert(1)")
        assert result["success"] is False
        assert browser_tools._state.value == "idle"
        assert browser_tools._browser is None

    def test_open_with_empty_url_returns_error(self, browser_tools):
        """Open with empty URL should return error."""
        result = browser_tools.browser_open("")
        assert result["success"] is False

    def test_open_success_updates_state(self, browser_tools):
        """Successful open should transition to OPENED state."""
        with patch.object(browser_tools, "_ensure_playwright") as mock_pw:
            mock_page = MagicMock()
            mock_page.goto.return_value = MagicMock()
            mock_page.url = "https://example.com"
            mock_page.title.return_value = "Example"

            mock_pw.return_value.chromium.launch.return_value.new_context.return_value.new_page.return_value = mock_page

            result = browser_tools.browser_open("https://example.com")
            assert result["success"] is True
            assert browser_tools._state.value == "opened"
            assert browser_tools._last_url == "https://example.com"
            assert browser_tools._last_title == "Example"
            mock_page.goto.assert_called_once()

    def test_open_navigation_failure_returns_error(self, browser_tools):
        """If page.goto returns None, should report failure."""
        with patch.object(browser_tools, "_ensure_playwright") as mock_pw:
            mock_page = MagicMock()
            mock_page.goto.return_value = None  # Navigation failed
            mock_pw.return_value.chromium.launch.return_value.new_context.return_value.new_page.return_value = mock_page

            result = browser_tools.browser_open("https://example.com")
            assert result["success"] is False
            assert browser_tools._state.value == "closed"


class TestBrowserSnapshotMocked:
    """Tests for browser_snapshot with mocked page."""

    def test_snapshot_returns_elements(self, browser_tools_with_page, mock_page):
        """Snapshot should return element list with refs."""
        # Setup mock elements
        mock_button = MagicMock()
        mock_button.is_visible.return_value = True
        mock_button.get_attribute.side_effect = lambda attr: {"id": "btn1", "name": None, "aria-label": None, "placeholder": None}.get(attr)
        mock_button.inner_text.return_value = "Click Me"

        mock_input = MagicMock()
        mock_input.is_visible.return_value = True
        mock_input.get_attribute.side_effect = lambda attr: {"id": None, "name": "email", "aria-label": None, "placeholder": None}.get(attr)
        mock_input.inner_text.return_value = ""

        mock_page.query_selector_all.return_value = [mock_button, mock_input]
        mock_page.inner_text.return_value = "Page body text"

        result = browser_tools_with_page.browser_snapshot()

        assert result["success"] is True
        assert result["elements_count"] == 2
        assert len(result["elements"]) == 2
        assert result["elements"][0]["ref"] == "@e1"
        assert result["elements"][1]["ref"] == "@e2"
        # Ref map should be populated
        assert "@e1" in browser_tools_with_page._ref_to_selector.values() or \
               "#btn1" in browser_tools_with_page._ref_to_selector.values()

    def test_snapshot_skips_invisible_elements(self, browser_tools_with_page, mock_page):
        """Snapshot should not include invisible elements."""
        mock_button = MagicMock()
        mock_button.is_visible.return_value = False
        mock_page.query_selector_all.return_value = [mock_button]
        mock_page.inner_text.return_value = ""

        result = browser_tools_with_page.browser_snapshot()

        assert result["success"] is True
        assert result["elements_count"] == 0

    def test_snapshot_when_closed_returns_error(self, browser_tools):
        """Snapshot on closed browser should return error."""
        from src.tools.browser_tools import BrowserState
        browser_tools._state = BrowserState.CLOSED
        result = browser_tools.browser_snapshot()
        assert result["success"] is False


class TestBrowserClickMocked:
    """Tests for browser_click with mocked page."""

    def test_click_resolves_ref(self, browser_tools_with_page, mock_page):
        """Click with @ref should resolve to underlying selector."""
        browser_tools_with_page._ref_to_selector = {"e1": "#submit"}
        result = browser_tools_with_page.browser_click("@e1")
        assert result["success"] is True
        mock_page.click.assert_called_once_with("#submit", timeout=10000)

    def test_click_passes_css_selector_through(self, browser_tools_with_page, mock_page):
        """Click with CSS selector should use it directly."""
        result = browser_tools_with_page.browser_click("#submit")
        assert result["success"] is True
        mock_page.click.assert_called_once_with("#submit", timeout=10000)

    def test_click_unknown_ref_returns_error(self, browser_tools_with_page, mock_page):
        """Click with unknown @ref should return error."""
        result = browser_tools_with_page.browser_click("@e99")
        assert result["success"] is False
        mock_page.click.assert_not_called()

    def test_click_handles_playwright_exception(self, browser_tools_with_page, mock_page):
        """Playwright exceptions should be caught and returned as error."""
        mock_page.click.side_effect = Exception("Element not found")
        result = browser_tools_with_page.browser_click("#missing")
        assert result["success"] is False
        assert "not found" in result["error"]


class TestBrowserFillMocked:
    """Tests for browser_fill with mocked page."""

    def test_fill_success(self, browser_tools_with_page, mock_page):
        """Fill should call page.fill with resolved selector."""
        browser_tools_with_page._ref_to_selector = {"e1": '[name="email"]'}
        result = browser_tools_with_page.browser_fill("@e1", "test@example.com")
        assert result["success"] is True
        mock_page.fill.assert_called_once_with('[name="email"]', "test@example.com", timeout=10000)


# ============================================================================
# T-2 修复：补齐之前零正向覆盖的 7 个公共方法的成功路径测试
# ============================================================================

class TestBrowserTypeMocked:
    """browser_type must call page.type (not page.fill) — appends, doesn't clear."""

    def test_type_resolves_ref(self, browser_tools_with_page, mock_page):
        browser_tools_with_page._ref_to_selector = {"e1": '[name="email"]'}
        result = browser_tools_with_page.browser_type("@e1", "appended")
        assert result["success"] is True
        mock_page.type.assert_called_once_with('[name="email"]', "appended", timeout=10000)
        # page.fill 不应被调用（避免与 test_fill_success 混淆）
        mock_page.fill.assert_not_called()

    def test_type_passes_css_through(self, browser_tools_with_page, mock_page):
        result = browser_tools_with_page.browser_type("#direct", "hello")
        assert result["success"] is True
        mock_page.type.assert_called_once_with("#direct", "hello", timeout=10000)

    def test_type_unknown_ref_fails(self, browser_tools_with_page, mock_page):
        result = browser_tools_with_page.browser_type("@e99", "x")
        assert result["success"] is False
        mock_page.type.assert_not_called()


class TestBrowserUncheckMocked:
    """browser_uncheck must call page.uncheck."""

    def test_uncheck_success(self, browser_tools_with_page, mock_page):
        result = browser_tools_with_page.browser_uncheck("#remember-me")
        assert result["success"] is True
        mock_page.uncheck.assert_called_once_with("#remember-me", timeout=10000)

    def test_uncheck_resolves_ref(self, browser_tools_with_page, mock_page):
        browser_tools_with_page._ref_to_selector = {"e1": "#terms"}
        result = browser_tools_with_page.browser_uncheck("@e1")
        assert result["success"] is True
        mock_page.uncheck.assert_called_once_with("#terms", timeout=10000)


class TestBrowserPressMocked:
    """browser_press must call page.press (with selector) or page.keyboard.press (without)."""

    def test_press_with_selector(self, browser_tools_with_page, mock_page):
        result = browser_tools_with_page.browser_press("Enter", "#input")
        assert result["success"] is True
        mock_page.press.assert_called_once_with("#input", "Enter", timeout=10000)

    def test_press_without_selector_uses_keyboard(self, browser_tools_with_page, mock_page):
        result = browser_tools_with_page.browser_press("Escape")
        assert result["success"] is True
        mock_page.keyboard.press.assert_called_once_with("Escape")

    def test_press_resolves_ref(self, browser_tools_with_page, mock_page):
        browser_tools_with_page._ref_to_selector = {"e1": "#submit"}
        result = browser_tools_with_page.browser_press("Enter", "@e1")
        assert result["success"] is True
        mock_page.press.assert_called_once_with("#submit", "Enter", timeout=10000)


class TestBrowserHoverMocked:
    """browser_hover must call page.hover."""

    def test_hover_success(self, browser_tools_with_page, mock_page):
        result = browser_tools_with_page.browser_hover("#menu")
        assert result["success"] is True
        mock_page.hover.assert_called_once_with("#menu", timeout=10000)

    def test_hover_resolves_ref(self, browser_tools_with_page, mock_page):
        browser_tools_with_page._ref_to_selector = {"e1": "#tooltip-target"}
        result = browser_tools_with_page.browser_hover("@e1")
        assert result["success"] is True
        mock_page.hover.assert_called_once_with("#tooltip-target", timeout=10000)


class TestBrowserBackForwardReloadMocked:
    """browser_back / browser_forward / browser_reload must call Playwright navigation."""

    def test_back_calls_go_back(self, browser_tools_with_page, mock_page):
        mock_page.url = "https://prev.com"
        result = browser_tools_with_page.browser_back()
        assert result["success"] is True
        mock_page.go_back.assert_called_once_with()
        assert result["url"] == "https://prev.com"

    def test_forward_calls_go_forward(self, browser_tools_with_page, mock_page):
        mock_page.url = "https://next.com"
        result = browser_tools_with_page.browser_forward()
        assert result["success"] is True
        mock_page.go_forward.assert_called_once_with()
        assert result["url"] == "https://next.com"

    def test_reload_calls_reload(self, browser_tools_with_page, mock_page):
        result = browser_tools_with_page.browser_reload()
        assert result["success"] is True
        mock_page.reload.assert_called_once_with()


class TestNoSilentAutoLaunch:
    """C-M1 修复回归：未 browser_open 直接 interact 应返回 None page / 失败响应。"""

    def test_scroll_without_open_returns_error(self, browser_tools):
        """未 open 直接 interact 不应静默启动浏览器。"""
        result = browser_tools.browser_scroll("down", 100)
        assert result["success"] is False
        assert "closed" in result["error"].lower() or "not available" in result["error"].lower()
        assert browser_tools._browser is None
        assert browser_tools._page is None

    def test_keyboard_type_without_open_returns_error(self, browser_tools):
        result = browser_tools.browser_keyboard_type("hello")
        assert result["success"] is False
        assert browser_tools._browser is None


class TestDataReservedKeysNotClobbered:
    """D-2 修复回归：data 中的保留键不应覆盖响应顶层字段。"""

    def test_data_with_status_does_not_clobber(self, browser_tools):
        """data={'status': 'fake'} 不应覆盖 _make_response 构造的 status 字段。"""
        r = browser_tools._make_response(
            "open", success=True, data={"status": "tampered"}
        )
        assert r["status"] != "tampered"
        assert r["status"] == browser_tools._state.value

    def test_data_with_success_does_not_clobber(self, browser_tools):
        r = browser_tools._make_response(
            "open", success=True, data={"success": False}
        )
        assert r["success"] is True, "data 中的 success 不应覆盖"

    def test_data_with_timestamp_does_not_clobber(self, browser_tools):
        r = browser_tools._make_response(
            "open", success=True, data={"timestamp": 0.0}
        )
        assert r["timestamp"] != 0.0
        assert isinstance(r["timestamp"], float)

    def test_data_with_non_reserved_keys_still_merges(self, browser_tools):
        """非保留键照常合并到顶层（向后兼容）。"""
        r = browser_tools._make_response(
            "open", success=True, data={"custom_field": 42, "title": "Test"}
        )
        assert r["custom_field"] == 42
        assert r["title"] == "Test"


class TestSvgNotAllowedAsDataUrl:
    """S-1 修复回归：data:image/svg+xml 应被路由白名单拒绝。"""

    def test_svg_data_url_not_in_image_whitelist(self, browser_tools):
        """image/svg+xml 不在 _ALLOWED_DATA_MIME_TYPES 中。"""
        # 验证常量本身已不含 svg+xml（这是一道文档测试，防止回归）。
        from src.tools.browser_tools import BrowserTools
        assert "image/svg+xml" not in BrowserTools._ALLOWED_DATA_MIME_TYPES
        assert "image/svg" not in BrowserTools._ALLOWED_DATA_MIME_TYPES
        # 而真正的图片应该被允许
        assert "image/png" in BrowserTools._ALLOWED_DATA_MIME_TYPES
        assert "image/jpeg" in BrowserTools._ALLOWED_DATA_MIME_TYPES


class TestScreenshotRejectsDotPath:
    """S-6 修复回归：'.' / './' 不应被接受为 screenshot 路径。"""

    def test_dot_path_rejected(self, browser_tools):
        err = browser_tools._validate_screenshot_path(".")
        assert err is not None

    def test_dot_slash_path_rejected(self, browser_tools):
        err = browser_tools._validate_screenshot_path("./")
        assert err is not None

    def test_trailing_slash_rejected(self, browser_tools):
        err = browser_tools._validate_screenshot_path("dir/")
        assert err is not None


class TestBrowserScrollMocked:
    """Tests for browser_scroll with mocked page."""

    def test_scroll_down(self, browser_tools_with_page, mock_page):
        """scroll down should trigger mouse.wheel with positive dy."""
        result = browser_tools_with_page.browser_scroll("down", 300)
        assert result["success"] is True
        mock_page.mouse.wheel.assert_called_once_with(0, 300)

    def test_scroll_up(self, browser_tools_with_page, mock_page):
        """scroll up should trigger mouse.wheel with negative dy."""
        result = browser_tools_with_page.browser_scroll("up", 200)
        assert result["success"] is True
        mock_page.mouse.wheel.assert_called_once_with(0, -200)

    def test_scroll_left_right(self, browser_tools_with_page, mock_page):
        """horizontal scroll should use dx."""
        browser_tools_with_page.browser_scroll("left", 100)
        mock_page.mouse.wheel.assert_called_with(-100, 0)
        browser_tools_with_page.browser_scroll("right", 100)
        mock_page.mouse.wheel.assert_called_with(100, 0)

    def test_scroll_invalid_direction(self, browser_tools_with_page, mock_page):
        """Invalid direction should be rejected without calling playwright."""
        result = browser_tools_with_page.browser_scroll("diagonal", 100)
        assert result["success"] is False
        mock_page.mouse.wheel.assert_not_called()

    def test_scroll_negative_pixels(self, browser_tools_with_page, mock_page):
        """Negative pixels should be rejected."""
        result = browser_tools_with_page.browser_scroll("down", -100)
        assert result["success"] is False

    def test_scroll_excessive_pixels(self, browser_tools_with_page, mock_page):
        """Pixels > 10000 should be rejected."""
        result = browser_tools_with_page.browser_scroll("down", 100000)
        assert result["success"] is False


class TestBrowserScreenshotMocked:
    """Tests for browser_screenshot with mocked page."""

    def test_screenshot_with_invalid_path(self, browser_tools_with_page, mock_page):
        """Screenshot with traversal path should fail."""
        result = browser_tools_with_page.browser_screenshot("../etc/passwd.png")
        assert result["success"] is False
        mock_page.screenshot.assert_not_called()

    def test_screenshot_with_empty_path(self, browser_tools_with_page, mock_page):
        """Screenshot with empty path should fail."""
        result = browser_tools_with_page.browser_screenshot("")
        assert result["success"] is False

    def test_screenshot_success(self, browser_tools_with_page, mock_page, empty_workspace):
        """Valid screenshot should save and return path."""
        result = browser_tools_with_page.browser_screenshot("test.png")
        assert result["success"] is True
        assert "path" in result
        mock_page.screenshot.assert_called_once()


class TestBrowserClose:
    """Tests for browser_close lifecycle."""

    def test_close_shuts_down_resources(self, browser_tools):
        """Close should call _shutdown and set state to CLOSED."""
        browser_tools._browser = MagicMock()
        browser_tools._context = MagicMock()
        browser_tools._playwright = MagicMock()

        result = browser_tools.browser_close()
        assert result["success"] is True
        assert browser_tools._state.value == "closed"
        assert browser_tools._page is None
        assert browser_tools._browser is None

    def test_close_when_already_closed(self, browser_tools):
        """Close when already closed should still succeed."""
        from src.tools.browser_tools import BrowserState
        browser_tools._state = BrowserState.CLOSED
        result = browser_tools.browser_close()
        assert result["success"] is True
        assert browser_tools._state.value == "closed"


# ============================================================================
# browser_automation Dispatch Tests
# ============================================================================

class TestBrowserAutomationDispatch:
    """Tests for browser_automation action routing."""

    def test_no_action_returns_help(self, browser_tools):
        """No action should return help with available actions."""
        result = browser_tools.browser_automation()
        assert result["success"] is True
        assert "available_actions" in result
        assert "open" in result["available_actions"]
        assert "close" in result["available_actions"]

    def test_unknown_action_returns_error(self, browser_tools):
        """Unknown action should return error with action name."""
        result = browser_tools.browser_automation("nonexistent")
        assert result["success"] is False
        assert "nonexistent" in result["error"]

    def test_action_exception_caught(self, browser_tools):
        """Exception in action handler should be caught."""
        with patch.object(browser_tools, "browser_close", side_effect=Exception("boom")):
            result = browser_tools.browser_automation("close")
            assert result["success"] is False
            assert "boom" in result["error"]

    def test_dispatches_to_correct_method(self, browser_tools):
        """Action map should call the right method."""
        with patch.object(browser_tools, "browser_get_url") as mock_method:
            mock_method.return_value = {"success": True, "url": "https://x"}
            browser_tools.browser_automation("get_url")
            mock_method.assert_called_once()

    def test_scroll_action_passes_params(self, browser_tools):
        """Scroll action should pass direction and pixels to method."""
        with patch.object(browser_tools, "browser_scroll") as mock_method:
            mock_method.return_value = {"success": True}
            browser_tools.browser_automation("scroll", direction="up", pixels=200)
            mock_method.assert_called_once_with(direction="up", pixels=200)

    def test_press_action_falls_back_to_value_for_key(self, browser_tools):
        """Press should accept 'key' or fall back to 'value'."""
        with patch.object(browser_tools, "browser_press") as mock_method:
            mock_method.return_value = {"success": True}
            browser_tools.browser_automation("press", key="Enter", selector="@e1")
            mock_method.assert_called_once_with(key="Enter", selector="@e1")

            mock_method.reset_mock()
            browser_tools.browser_automation("press", value="Escape")
            mock_method.assert_called_once_with(key="Escape", selector=None)

    def test_missing_required_param_returns_structured_error(self, browser_tools):
        """M3 regression: missing required kwargs should return structured error, not call method."""
        # get_value without selector → should fail before dispatching
        result = browser_tools.browser_automation("get_value")
        assert result["success"] is False
        assert "Missing required parameter" in result["error"]
        assert "selector" in result["error"]

    def test_missing_selector_for_is_checked(self, browser_tools):
        """is_checked without selector should report missing param."""
        result = browser_tools.browser_automation("is_checked")
        assert result["success"] is False
        assert "selector" in result["error"]

    def test_missing_url_for_open(self, browser_tools):
        """open without url should report missing param."""
        result = browser_tools.browser_automation("open")
        assert result["success"] is False
        assert "url" in result["error"]

    def test_missing_data_for_fill_form(self, browser_tools):
        """fill_form without data should report missing param."""
        result = browser_tools.browser_automation("fill_form")
        assert result["success"] is False
        assert "data" in result["error"]

    def test_press_accepts_either_key_or_value(self, browser_tools):
        """press should accept key or value (no missing-params error)."""
        with patch.object(browser_tools, "browser_press") as mock_method:
            mock_method.return_value = {"success": True}
            # Either of these should work, neither should report missing param
            result1 = browser_tools.browser_automation("press", key="Enter")
            assert "Missing required parameter" not in result1.get("error", "")
            result2 = browser_tools.browser_automation("press", value="Escape")
            assert "Missing required parameter" not in result2.get("error", "")

    def test_press_without_any_key_fails(self, browser_tools):
        """press with neither key nor value should report missing param."""
        result = browser_tools.browser_automation("press", selector="@e1")
        assert result["success"] is False
        assert "key" in result["error"].lower() or "value" in result["error"].lower()

    def test_screenshot_with_valid_params_dispatches(self, browser_tools):
        """screenshot with explicit path should not be blocked by validation."""
        # Just make sure validation isn't blocking
        # We don't actually take a screenshot since browser is closed
        from src.tools.browser_tools import BrowserState
        browser_tools._state = BrowserState.CLOSED
        result = browser_tools.browser_automation("screenshot", path="test.png")
        # Should fail with browser-closed, not with "missing path"
        assert result["success"] is False
        assert "Missing required parameter" not in result.get("error", "")


# ============================================================================
# H1 regression Tests: browser launch error handling
# ============================================================================

class TestBrowserLaunchFallback:
    """H1 regression: visible-mode failure should fall back to headless."""

    def test_headless_mode_no_args(self):
        """headless=True should not include extra chromium args."""
        from src.tools.browser_tools import BrowserTools, BrowserState
        bt = BrowserTools()
        with patch.object(bt, "_ensure_playwright") as mock_pw:
            mock_page = MagicMock()
            mock_page.goto.return_value = MagicMock()
            mock_page.url = "https://example.com"
            mock_page.title.return_value = "Example"
            mock_browser = MagicMock()
            mock_pw.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value.new_page.return_value = mock_page

            bt.browser_open("https://example.com", headless=True)

            # Should call launch with headless=True and NO extra args
            call_kwargs = mock_pw.return_value.chromium.launch.call_args.kwargs
            assert call_kwargs.get("headless") is True
            assert "args" not in call_kwargs

    def test_visible_mode_includes_args(self):
        """headless=False should include --no-sandbox args for resilience."""
        from src.tools.browser_tools import BrowserTools, BrowserState
        bt = BrowserTools()
        with patch.object(bt, "_ensure_playwright") as mock_pw:
            mock_page = MagicMock()
            mock_page.goto.return_value = MagicMock()
            mock_page.url = "https://example.com"
            mock_page.title.return_value = "Example"
            mock_browser = MagicMock()
            mock_pw.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value.new_page.return_value = mock_page

            bt.browser_open("https://example.com", headless=False)

            call_kwargs = mock_pw.return_value.chromium.launch.call_args.kwargs
            assert call_kwargs.get("headless") is False
            assert "args" in call_kwargs
            assert "--no-sandbox" in call_kwargs["args"]

    def test_visible_mode_failure_falls_back_to_headless(self):
        """H1: When headless=False launch fails, should fall back to headless=True."""
        from src.tools.browser_tools import BrowserTools, BrowserState
        bt = BrowserTools()
        with patch.object(bt, "_ensure_playwright") as mock_pw:
            mock_page = MagicMock()
            mock_page.goto.return_value = MagicMock()
            mock_page.url = "https://example.com"
            mock_page.title.return_value = "Example"
            mock_browser = MagicMock()
            # First call (visible) raises; second call (headless) succeeds
            mock_pw.return_value.chromium.launch.side_effect = [
                Exception("Missing X server"),
                mock_browser,
            ]
            mock_browser.new_context.return_value.new_page.return_value = mock_page

            result = bt.browser_open("https://example.com", headless=False)

            assert result["success"] is True
            # Fallback should be flagged
            assert result["headless_fallback"] is True
            assert result["headless"] is True  # Actual mode used
            assert "fallback to headless" in result["message"]
            # launch should be called twice (visible fails, headless succeeds)
            assert mock_pw.return_value.chromium.launch.call_count == 2

    def test_visible_mode_failure_then_headless_also_fails(self):
        """If both visible AND fallback headless fail, original error should propagate."""
        from src.tools.browser_tools import BrowserTools, BrowserState
        bt = BrowserTools()
        with patch.object(bt, "_ensure_playwright") as mock_pw:
            original_err = Exception("Browser binary missing")
            mock_pw.return_value.chromium.launch.side_effect = [
                original_err,
                Exception("Also headless fails"),
            ]

            result = bt.browser_open("https://example.com", headless=False)

            assert result["success"] is False
            # Error message includes the original visible-mode error
            assert "Browser binary missing" in result["error"]

    def test_headless_failure_does_not_fallback(self):
        """If headless launch fails (user explicitly asked for headless), should NOT try second time."""
        from src.tools.browser_tools import BrowserTools, BrowserState
        bt = BrowserTools()
        with patch.object(bt, "_ensure_playwright") as mock_pw:
            mock_pw.return_value.chromium.launch.side_effect = Exception("Headless failed")

            result = bt.browser_open("https://example.com", headless=True)

            assert result["success"] is False
            # Only ONE launch attempt — no fallback
            assert mock_pw.return_value.chromium.launch.call_count == 1


# ============================================================================
# HIGH-2 Regression Tests: Sibling Directory Bypass
# ============================================================================

class TestSiblingBypassFix:
    """HIGH-2 regression: path validation must reject sibling directories with shared prefix."""

    @staticmethod
    def _bt():
        from src.tools.browser_tools import BrowserTools, BrowserState
        return BrowserTools

    def test_sibling_directory_blocked_in_screenshot_path(self, tmp_path):
        """Workspace = /root/work, attacker writes to /root/work_evil — must reject."""
        BrowserTools = self._bt()
        work = tmp_path / "work"
        work.mkdir()
        evil = tmp_path / "work_evil"
        evil.mkdir()
        (evil / "secret.png").write_text("evil")
        bt = BrowserTools(workspace_root=str(work))
        # Try to access the sibling directory's file
        err = bt._validate_screenshot_path(str(evil / "secret.png"))
        assert err is not None, f"Sibling bypass succeeded: {err}"
        assert "outside" in err.lower() or "access denied" in err.lower()

    def test_real_workspace_file_accepted(self, tmp_path):
        """Genuine workspace files must still pass."""
        work = tmp_path / "work"
        work.mkdir()
        (work / "screenshot.png").write_text("ok")
        bt = BrowserTools(workspace_root=str(work))
        assert bt._validate_screenshot_path(str(work / "screenshot.png")) is None

    def test_sibling_directory_blocked_in_url(self, tmp_path):
        """file:// URL to sibling directory must be rejected."""
        work = tmp_path / "work"
        work.mkdir()
        evil = tmp_path / "work_evil"
        evil.mkdir()
        (evil / "secret.txt").write_text("evil")
        bt = BrowserTools(workspace_root=str(work))
        if os.name == "nt":
            file_url = f"file:///{str(evil / 'secret.txt').replace(chr(92), '/')}"
        else:
            file_url = f"file://{evil / 'secret.txt'}"
        err = bt._validate_url(file_url)
        assert err is not None, f"Sibling bypass via file:// succeeded: {err}"


# ============================================================================
# CRIT-1 Regression Tests: file:// requires workspace_root
# ============================================================================

class TestFileUrlRequiresWorkspace:
    """CRIT-1 regression: file:// must require workspace_root to prevent SSRF by default."""

    def test_file_url_without_workspace_rejected(self):
        """BrowserTools() with no workspace must reject file:// URLs."""
        bt = BrowserTools()
        err = bt._validate_url("file:///etc/passwd")
        assert err is not None
        assert "workspace_root" in err or "outside" in err.lower()

    def test_file_url_with_workspace_allowed(self, tmp_path):
        """file:// to a file inside workspace must succeed."""
        work = tmp_path / "work"
        work.mkdir()
        test_html = work / "page.html"
        test_html.write_text("<html><body>Hello</body></html>")
        bt = BrowserTools(workspace_root=str(work))
        if os.name == "nt":
            url = f"file:///{str(test_html).replace(chr(92), '/')}"
        else:
            url = f"file://{test_html}"
        assert bt._validate_url(url) is None

    def test_file_url_outside_workspace_rejected(self, tmp_path):
        """file:// outside workspace must fail even when workspace is set."""
        work = tmp_path / "work"
        work.mkdir()
        bt = BrowserTools(workspace_root=str(work))
        if os.name == "nt":
            sensitive = "file:///C:/Windows/system32"
        else:
            sensitive = "file:///etc/passwd"
        err = bt._validate_url(sensitive)
        assert err is not None


# ============================================================================
# HIGH-1 Regression Tests: URL scheme case normalization
# ============================================================================

class TestUrlSchemeNormalization:
    """HIGH-1 regression: URL scheme comparison should be case-insensitive."""

    def test_uppercase_https_accepted(self):
        """HTTPS://example.com should be accepted (RFC says scheme is case-insensitive)."""
        bt = BrowserTools()
        err = bt._validate_url("HTTPS://example.com")
        assert err is None

    def test_mixed_case_https_accepted(self):
        """Https://example.com should also work."""
        bt = BrowserTools()
        assert bt._validate_url("Https://example.com") is None


# ============================================================================
# MEDIUM-1 Regression Tests: CSS selector escape
# ============================================================================

class TestCssEscape:
    """MEDIUM-1 regression: selector values must escape special chars."""

    def test_escape_handles_double_quote(self):
        bt = BrowserTools()
        out = bt._css_escape_attr_value('Say "Hi"')
        # After escape: Say \"Hi\" (with 2 backslash-quote escape sequences)
        assert '\\"' in out
        assert out.count('\\"') == 2  # both embedded quotes escaped

    def test_escape_handles_backslash(self):
        bt = BrowserTools()
        out = bt._css_escape_attr_value("back\\slash")
        assert "\\\\" in out

    def test_escape_handles_newlines(self):
        bt = BrowserTools()
        out = bt._css_escape_attr_value("line\nbreak\rmore")
        assert "\n" not in out
        assert "\r" not in out

    def test_escape_truncates_long_values(self):
        bt = BrowserTools()
        out = bt._css_escape_attr_value("a" * 100)
        assert len(out) == 50

    def test_escape_empty_value(self):
        bt = BrowserTools()
        assert bt._css_escape_attr_value("") == ""
        assert bt._css_escape_attr_value(None) == ""

    def test_build_selector_uses_escape(self):
        """_build_selector_for_element with quote-in-value must produce escaped selector."""
        from unittest.mock import MagicMock
        elem = MagicMock()
        elem.get_attribute.side_effect = lambda attr: {
            "id": None, "name": None,
            "aria-label": 'evil"break',
            "placeholder": None
        }.get(attr)
        bt = BrowserTools()
        sel = bt._build_selector_for_element(elem)
        # The selector value has the quote escaped
        assert sel is not None
        assert '\\"' in sel


# ============================================================================
# MEDIUM-2 Regression Tests: close_all param removed
# ============================================================================

class TestCloseAllRemoved:
    """MEDIUM-2 regression: browser_close no longer accepts close_all."""

    def test_browser_close_no_kwargs(self, browser_tools):
        """browser_close() should work without arguments."""
        import inspect
        sig = inspect.signature(browser_tools.browser_close)
        params = list(sig.parameters.keys())
        assert "close_all" not in params
        # Just check it can be called
        result = browser_tools.browser_close()
        assert result["success"] is True

    def test_dispatch_close_does_not_pass_close_all(self):
        """browser_automation('close') must still work after dead param removal."""
        bt = BrowserTools()
        with patch.object(bt, "browser_close") as mock_method:
            mock_method.return_value = {"success": True, "task_completed": True}
            result = bt.browser_automation("close")  # close_all no longer expected
            mock_method.assert_called_once_with()  # Called with no args
            assert result["success"] is True


# ============================================================================
# LOW-4 Regression Tests: headless=False default (GUI mode)
# ============================================================================

class TestHeadlessDefault:
    """LOW-4 regression: browser_open default headless must be False (GUI mode)."""

    def test_default_headless_is_false(self):
        """The signature default must be False (GUI mode for browser automation)."""
        import inspect
        sig = inspect.signature(BrowserTools.browser_open)
        headless_param = sig.parameters.get("headless")
        assert headless_param is not None
        assert headless_param.default is False, \
            f"headless default should be False, got {headless_param.default}"

    def test_explicit_headless_true_uses_no_extra_args(self):
        """headless=True should not include --no-sandbox args (unnecessary overhead)."""
        from src.tools.browser_tools import BrowserTools, BrowserState
        bt = BrowserTools()
        with patch.object(bt, "_ensure_playwright") as mock_pw:
            mock_page = MagicMock()
            mock_page.goto.return_value = MagicMock()
            mock_page.url = "https://example.com"
            mock_page.title.return_value = "Example"
            mock_browser = MagicMock()
            mock_pw.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value.new_page.return_value = mock_page

            bt.browser_open("https://example.com", headless=True)

            call_kwargs = mock_pw.return_value.chromium.launch.call_args.kwargs
            assert call_kwargs.get("headless") is True
            assert "args" not in call_kwargs


# ============================================================================
# browser_fill_form Tests
# ============================================================================

class TestBrowserFillForm:
    """Tests for browser_fill_form."""

    def test_fill_form_with_name_keys(self, browser_tools_with_page, mock_page):
        """Form filling with name keys should auto-convert to [name=x]."""
        result = browser_tools_with_page.browser_fill_form(
            data={"username": "alice", "password": "secret"},
            submit_selector="#login"
        )
        assert result["success"] is True
        # Verify fill was called with name selectors
        calls = mock_page.fill.call_args_list
        assert any('[name="username"]' in str(c) and "alice" in str(c) for c in calls)
        assert any('[name="password"]' in str(c) and "secret" in str(c) for c in calls)
        # Verify submit was clicked
        mock_page.click.assert_called_with("#login", timeout=10000)

    def test_fill_form_preserves_explicit_selectors(self, browser_tools_with_page, mock_page):
        """Form filling should preserve @ref and [name=] selectors."""
        # Register the @e1 ref so the test doesn't depend on snapshot()
        browser_tools_with_page._ref_to_selector = {"e1": "#ref-target"}
        result = browser_tools_with_page.browser_fill_form(
            data={"@e1": "value1", "#explicit": "value2"}
        )
        assert result["success"] is True
        # Verify both selectors were passed through unchanged
        calls = mock_page.fill.call_args_list
        assert any("#ref-target" in str(c) for c in calls)
        assert any("#explicit" in str(c) for c in calls)

    def test_fill_form_without_submit(self, browser_tools_with_page, mock_page):
        """Form filling without submit_selector should not click anything."""
        result = browser_tools_with_page.browser_fill_form(
            data={"field": "value"}
        )
        assert result["success"] is True
        assert result["submitted"] is False
        mock_page.click.assert_not_called()

    def test_fill_form_aborts_on_field_error(self, browser_tools_with_page, mock_page):
        """If a field fill fails, should return error and not submit."""
        mock_page.fill.side_effect = Exception("Field not found")
        result = browser_tools_with_page.browser_fill_form(
            data={"field": "value"},
            submit_selector="#submit"
        )
        assert result["success"] is False
        mock_page.click.assert_not_called()


# ============================================================================
# Helper Methods Tests
# ============================================================================

class TestEnsurePlaywright:
    """Tests for Playwright lazy loading."""

    def test_first_call_imports_playwright(self, browser_tools):
        """First call should lazy-import and start Playwright."""
        with patch("playwright.sync_api.sync_playwright") as mock_sp:
            mock_sp.return_value.start.return_value = MagicMock()
            browser_tools._ensure_playwright()
            mock_sp.assert_called_once()

    def test_subsequent_calls_reuse_instance(self, browser_tools):
        """After init, _ensure_playwright should reuse the instance."""
        with patch("playwright.sync_api.sync_playwright") as mock_sp:
            mock_sp.return_value.start.return_value = MagicMock()
            browser_tools._ensure_playwright()
            browser_tools._ensure_playwright()
            # Should only start Playwright once
            mock_sp.assert_called_once()

    def test_missing_playwright_raises(self, browser_tools):
        """If Playwright is not installed, should raise with install hint."""
        import sys
        # Save original
        original_playwright = sys.modules.get("playwright")
        original_sync_api = sys.modules.get("playwright.sync_api")
        try:
            # Remove from sys.modules to force ImportError
            sys.modules["playwright"] = None  # Causes ImportError
            sys.modules["playwright.sync_api"] = None
            with pytest.raises(RuntimeError) as exc_info:
                browser_tools._ensure_playwright()
            assert "Playwright" in str(exc_info.value)
            assert "pip install" in str(exc_info.value)
        finally:
            # Restore
            if original_playwright is not None:
                sys.modules["playwright"] = original_playwright
            else:
                sys.modules.pop("playwright", None)
            if original_sync_api is not None:
                sys.modules["playwright.sync_api"] = original_sync_api
            else:
                sys.modules.pop("playwright.sync_api", None)


class TestShutdown:
    """Tests for _shutdown cleanup."""

    def test_shutdown_clears_all_resources(self, browser_tools):
        """_shutdown should close all Playwright resources."""
        browser_tools._browser = MagicMock()
        browser_tools._context = MagicMock()
        browser_tools._playwright = MagicMock()
        browser_tools._page = MagicMock()
        browser_tools._ref_to_selector = {"e1": "#x"}

        browser_tools._shutdown()

        assert browser_tools._browser is None
        assert browser_tools._context is None
        assert browser_tools._playwright is None
        assert browser_tools._page is None
        assert browser_tools._ref_to_selector == {}

    def test_shutdown_tolerates_exceptions(self, browser_tools):
        """_shutdown should not raise even if close() fails."""
        browser_tools._browser = MagicMock()
        browser_tools._browser.close.side_effect = Exception("close failed")
        browser_tools._context = MagicMock()
        browser_tools._context.close.side_effect = Exception("close failed")
        browser_tools._playwright = MagicMock()
        browser_tools._playwright.stop.side_effect = Exception("stop failed")

        # Should not raise
        browser_tools._shutdown()

        # All should still be reset
        assert browser_tools._browser is None
        assert browser_tools._context is None
        assert browser_tools._playwright is None


# ============================================================================
# Keyboard & Misc Action Tests
# ============================================================================

class TestKeyboardType:
    """Tests for browser_keyboard_type validation."""

    def test_normal_text_accepted(self, browser_tools_with_page, mock_page):
        """Normal-length text should be accepted."""
        result = browser_tools_with_page.browser_keyboard_type("Hello, World!")
        assert result["success"] is True
        mock_page.keyboard.type.assert_called_once_with("Hello, World!")

    def test_text_too_long_rejected(self, browser_tools_with_page, mock_page):
        """Text > 10000 chars should be rejected without calling keyboard."""
        long_text = "x" * 10001
        result = browser_tools_with_page.browser_keyboard_type(long_text)
        assert result["success"] is False
        assert "too long" in result["error"].lower()
        mock_page.keyboard.type.assert_not_called()

    def test_text_at_limit_accepted(self, browser_tools_with_page, mock_page):
        """Text at exactly 10000 chars should be accepted."""
        text = "x" * 10000
        result = browser_tools_with_page.browser_keyboard_type(text)
        assert result["success"] is True


class TestBrowserWait:
    """Tests for browser_wait."""

    def test_wait_with_numeric_string(self, browser_tools_with_page, mock_page):
        """Numeric wait_for should call wait_for_timeout."""
        result = browser_tools_with_page.browser_wait("1500")
        assert result["success"] is True
        mock_page.wait_for_timeout.assert_called_once_with(1500)

    def test_wait_with_selector(self, browser_tools_with_page, mock_page):
        """Non-numeric wait_for should be treated as selector."""
        result = browser_tools_with_page.browser_wait("#my-element")
        assert result["success"] is True
        mock_page.wait_for_selector.assert_called_once_with("#my-element", timeout=30000)


class TestBrowserGetTextUrl:
    """Tests for browser_get_text and browser_get_url."""

    def test_get_text_with_selector(self, browser_tools_with_page, mock_page):
        """get_text with selector should call inner_text."""
        mock_page.inner_text.return_value = "Hello"
        result = browser_tools_with_page.browser_get_text("#greeting")
        assert result["success"] is True
        assert result["text"] == "Hello"

    def test_get_text_without_selector_returns_title(self, browser_tools_with_page, mock_page):
        """get_text without selector should return page title."""
        mock_page.title.return_value = "My Page"
        result = browser_tools_with_page.browser_get_text()
        assert result["success"] is True
        assert result["text"] == "My Page"

    def test_get_url_returns_current_url(self, browser_tools_with_page, mock_page):
        """get_url should return page.url."""
        mock_page.url = "https://example.com/path"
        result = browser_tools_with_page.browser_get_url()
        assert result["success"] is True
        assert result["url"] == "https://example.com/path"


class TestBrowserGetValueIsChecked:
    """Tests for browser_get_value and browser_is_checked (added for testability)."""

    def test_get_value_returns_input_value(self, browser_tools_with_page, mock_page):
        """browser_get_value should return input.value attribute."""
        mock_page.input_value.return_value = "alice"
        result = browser_tools_with_page.browser_get_value('[name="username"]')
        assert result["success"] is True
        assert result["value"] == "alice"
        mock_page.input_value.assert_called_once_with('[name="username"]', timeout=10000)

    def test_get_value_resolves_ref(self, browser_tools_with_page, mock_page):
        """browser_get_value should resolve @ref to selector."""
        browser_tools_with_page._ref_to_selector = {"e1": '[name="email"]'}
        mock_page.input_value.return_value = "bob@x.com"
        result = browser_tools_with_page.browser_get_value("@e1")
        assert result["success"] is True
        assert result["value"] == "bob@x.com"
        mock_page.input_value.assert_called_once_with('[name="email"]', timeout=10000)

    def test_get_value_with_unknown_ref_fails(self, browser_tools_with_page, mock_page):
        """browser_get_value with unknown @ref should return error."""
        result = browser_tools_with_page.browser_get_value("@e99")
        assert result["success"] is False
        mock_page.input_value.assert_not_called()

    def test_get_value_when_closed_fails(self, browser_tools):
        """browser_get_value when closed should return error."""
        from src.tools.browser_tools import BrowserState
        browser_tools._state = BrowserState.CLOSED
        result = browser_tools.browser_get_value("#x")
        assert result["success"] is False

    def test_is_checked_returns_true(self, browser_tools_with_page, mock_page):
        """browser_is_checked should return checked state."""
        mock_page.is_checked.return_value = True
        result = browser_tools_with_page.browser_is_checked("#remember-me")
        assert result["success"] is True
        assert result["checked"] is True

    def test_is_checked_returns_false(self, browser_tools_with_page, mock_page):
        """browser_is_checked should return False for unchecked box."""
        mock_page.is_checked.return_value = False
        result = browser_tools_with_page.browser_is_checked("#remember-me")
        assert result["success"] is True
        assert result["checked"] is False

    def test_is_checked_when_closed_fails(self, browser_tools):
        """browser_is_checked when closed should return error."""
        from src.tools.browser_tools import BrowserState
        browser_tools._state = BrowserState.CLOSED
        result = browser_tools.browser_is_checked("#x")
        assert result["success"] is False


# ============================================================================
# Navigate and Interact Tests
# ============================================================================

class TestNavigateAndInteract:
    """Tests for browser_navigate_and_interact."""

    def test_aborts_when_browser_closed(self, browser_tools):
        """If browser is closed, should return error without opening."""
        from src.tools.browser_tools import BrowserState
        browser_tools._state = BrowserState.CLOSED
        result = browser_tools.browser_navigate_and_interact(
            url="https://example.com",
            actions=[]
        )
        assert result["success"] is False

    def test_executes_actions_in_sequence(self, browser_tools):
        """Should execute all actions sequentially."""
        with patch.object(browser_tools, "browser_open") as mock_open, \
             patch.object(browser_tools, "browser_click") as mock_click, \
             patch.object(browser_tools, "browser_snapshot") as mock_snapshot:
            mock_open.return_value = {"success": True}
            mock_click.return_value = {"success": True}
            mock_snapshot.return_value = {"success": True, "elements": []}

            result = browser_tools.browser_navigate_and_interact(
                url="https://example.com",
                actions=[
                    {"type": "click", "selector": "@e1"},
                    {"type": "click", "selector": "@e2"},
                ]
            )
            assert result["success"] is True
            assert mock_click.call_count == 2

    def test_action_failure_aborts_sequence(self, browser_tools):
        """If an action fails, should return error and stop."""
        with patch.object(browser_tools, "browser_open") as mock_open, \
             patch.object(browser_tools, "browser_click") as mock_click:
            mock_open.return_value = {"success": True}
            mock_click.return_value = {"success": False, "error": "element not found"}

            result = browser_tools.browser_navigate_and_interact(
                url="https://example.com",
                actions=[
                    {"type": "click", "selector": "@e1"},
                    {"type": "click", "selector": "@e2"},  # Should not be executed
                ]
            )
            assert result["success"] is False
            assert "click" in result["error"]
            assert mock_click.call_count == 1

    def test_unsupported_action_is_skipped(self, browser_tools):
        """Unsupported action types should be skipped silently."""
        with patch.object(browser_tools, "browser_open") as mock_open, \
             patch.object(browser_tools, "browser_snapshot") as mock_snapshot:
            mock_open.return_value = {"success": True}
            mock_snapshot.return_value = {"success": True}

            result = browser_tools.browser_navigate_and_interact(
                url="https://example.com",
                actions=[
                    {"type": "unknown_action"},
                    {"type": "another_unknown"},
                ]
            )
            # Should not fail - unknown actions are just skipped
            assert result["success"] is True


class TestHeadlessFallbackReuse:
    """Regression: 第二次 browser_open 复用现有 browser 时，headless_fallback 必须已定义。"""

    def test_second_open_does_not_raise_unbound(self, browser_tools, monkeypatch):
        """第二次 open 必须返回成功而非 UnboundLocalError。"""
        # 第一次 open：模拟成功
        browser_tools._browser = MagicMock()
        browser_tools._context = MagicMock()
        page = MagicMock()
        page.goto.return_value = MagicMock(status=200)
        page.url = "https://a.com"
        page.title.return_value = "A"
        browser_tools._context.new_page.return_value = page
        browser_tools._state = BrowserState.OPENED

        # 第二次 open：触发 headless_fallback 引用
        browser_tools._page = page
        result = browser_tools.browser_open("https://b.com")
        assert result["success"] is True
        # data 被合并到 response 顶层（非 result["data"]）
        assert "headless" in result
        assert "headless_fallback" in result
        assert result["headless_fallback"] is False


class TestWaitForIntCoercion:
    """Regression: wait_for 接受 int/float/str，不抛 AttributeError。"""

    def test_wait_for_int(self, browser_tools):
        browser_tools._state = BrowserState.OPENED
        page = MagicMock()
        browser_tools._page = page
        result = browser_tools.browser_wait(wait_for=3000)
        assert result["success"] is True
        page.wait_for_timeout.assert_called_once_with(3000)

    def test_wait_for_float(self, browser_tools):
        browser_tools._state = BrowserState.OPENED
        page = MagicMock()
        browser_tools._page = page
        result = browser_tools.browser_wait(wait_for=500.5)
        assert result["success"] is True
        page.wait_for_timeout.assert_called_once_with(500)

    def test_wait_for_str_digits(self, browser_tools):
        browser_tools._state = BrowserState.OPENED
        page = MagicMock()
        browser_tools._page = page
        result = browser_tools.browser_wait(wait_for="1500")
        assert result["success"] is True
        page.wait_for_timeout.assert_called_once_with(1500)


class TestScrollPixelsType:
    """Regression: scroll pixels 接受 int/float，拒绝 bool。"""

    def test_scroll_int(self, browser_tools):
        browser_tools._state = BrowserState.OPENED
        page = MagicMock()
        browser_tools._page = page
        result = browser_tools.browser_scroll("down", 500)
        assert result["success"] is True

    def test_scroll_float_truncated(self, browser_tools):
        browser_tools._state = BrowserState.OPENED
        page = MagicMock()
        browser_tools._page = page
        result = browser_tools.browser_scroll("down", 500.7)
        assert result["success"] is True

    def test_scroll_bool_rejected(self, browser_tools):
        browser_tools._state = BrowserState.OPENED
        page = MagicMock()
        browser_tools._page = page
        result = browser_tools.browser_scroll("down", True)
        assert result["success"] is False
        assert "positive number" in result["error"]


class TestRefClearedOnOpen:
    """Regression: browser_open 重新导航时必须清空旧 @ref，避免误操作新页元素。"""

    def test_open_clears_stale_refs(self, browser_tools):
        browser_tools._ref_to_selector = {"e1": "#old-button"}
        browser_tools._browser = MagicMock()
        browser_tools._context = MagicMock()
        page = MagicMock()
        page.goto.return_value = MagicMock(status=200)
        page.url = "https://new.com"
        page.title.return_value = "New"
        browser_tools._context.new_page.return_value = page
        browser_tools._state = BrowserState.OPENED
        browser_tools._page = page

        browser_tools.browser_open("https://new.com")
        assert browser_tools._ref_to_selector == {}


class TestTextOnlySelectorFallback:
    """Regression: 没有 id/name/aria/placeholder 的元素用 text= 选择器。"""

    def test_button_with_only_text(self):
        # 构造一个 mock 元素：没有 id/name/aria/placeholder，有 inner_text
        elem = MagicMock()
        elem.get_attribute.side_effect = lambda attr: None
        elem.inner_text.return_value = "Submit"

        selector = BrowserTools._build_selector_for_element(elem)
        assert selector == 'text="Submit"'

    def test_button_with_empty_text_returns_none(self):
        elem = MagicMock()
        elem.get_attribute.side_effect = lambda attr: None
        elem.inner_text.return_value = ""

        selector = BrowserTools._build_selector_for_element(elem)
        assert selector is None

    def test_id_still_takes_priority(self):
        elem = MagicMock()
        elem.get_attribute.side_effect = lambda attr: "myid" if attr == "id" else None
        elem.inner_text.return_value = "Should not be used"

        selector = BrowserTools._build_selector_for_element(elem)
        assert selector == "#myid"


class TestSchemeRouteHandler:
    """Regression: 浏览器启动时注册 context.route 拦截 javascript:/data: 等。"""

    def test_ensure_browser_registers_route(self, browser_tools, monkeypatch):
        """_ensure_browser 必须在 new_context 之后注册 route handler。"""
        mock_context = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = MagicMock()

        mock_pw = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        monkeypatch.setattr(browser_tools, "_ensure_playwright", lambda: mock_pw)

        browser_tools._ensure_browser()
        # 验证调用了 context.route
        assert mock_context.route.called
        args, _ = mock_context.route.call_args
        assert args[0] == "**/*"


class TestToolPromptSchema:
    """Regression: tool_prompt.json 必须包含所有 dispatch 需要的参数。"""

    def test_schema_includes_required_params(self):
        import json
        from pathlib import Path
        path = Path(__file__).parent.parent.parent / "prompts" / "tool_prompt.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        params = schema["browser_automation"]["parameters"]["properties"]
        # 至少需要这些 key
        for key in ["action", "url", "selector", "value", "key", "headless",
                    "path", "direction", "pixels", "wait_for", "data", "actions"]:
            assert key in params, f"Missing param: {key}"

    def test_headless_default_is_true(self):
        import json
        from pathlib import Path
        path = Path(__file__).parent.parent.parent / "prompts" / "tool_prompt.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        headless = schema["browser_automation"]["parameters"]["properties"]["headless"]
        assert headless.get("default") is True, f"Expected default=true, got {headless.get('default')}"