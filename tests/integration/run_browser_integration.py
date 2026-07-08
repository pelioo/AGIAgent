#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone integration test runner for BrowserTools.

Runs each integration test in a separate subprocess to avoid Playwright
greenlet pollution across tests. The pytest wrapper just invokes this
script and checks the exit code.

Usage:
    python tests/integration/run_browser_integration.py [--single-test NAME]
"""

import argparse
import multiprocessing
import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


# Sample HTML for tests
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
  <h1 id="title">Hello, Browser!</h1>
  <form id="login-form">
    <input type="text" name="username" id="username-input" placeholder="Enter username" />
    <input type="password" name="password" placeholder="Enter password" />
    <input type="checkbox" name="remember" id="remember-me" />
    <label for="remember-me">Remember me</label>
    <select name="role" id="role-select">
      <option value="user">User</option>
      <option value="admin">Admin</option>
    </select>
    <button type="submit" id="submit-btn">Submit</button>
  </form>
  <button class="cancel-btn" onclick="document.getElementById('title').textContent='Clicked!'">Cancel</button>
  <a href="#section2" id="anchor-link">Jump to section 2</a>
  <div id="long-content">
    <p>Line 1</p><p>Line 2</p><p>Line 3</p><p>Line 4</p>
    <p>Line 5</p><p>Line 6</p><p>Line 7</p><p>Line 8</p>
    <p>Line 9</p><p>Line 10</p><p>Line 11</p><p>Line 12</p>
  </div>
  <div id="section2">Section 2 content</div>
  <div id="error-display" style="display:none">Error message</div>
</body>
</html>
"""


def _run_test_in_subprocess(test_func, *args) -> Tuple[bool, str]:
    """Run a test function in a separate process. Returns (success, message)."""
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(1) as pool:
        async_result = pool.apply_async(test_func, args)
        try:
            result = async_result.get(timeout=60)
            return (True, "OK")
        except Exception as e:
            tb = traceback.format_exc() if hasattr(e, '__traceback__') else str(e)
            return (False, f"{type(e).__name__}: {e}\n{tb}")
        finally:
            pool.terminate()


# Individual test functions - each runs in a fresh process via the runner

def test_lifecycle_open_file():
    """Test: open local HTML file."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        result = bt.browser_open(f.as_uri())
        assert result["success"] is True, f"open failed: {result}"
        assert "Test Page" in result["title"]
        bt.browser_close()
    return "OK"


def test_lifecycle_open_close():
    """Test: open then close cleanly."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        assert bt.browser_open(f.as_uri())["success"] is True
        assert bt.browser_close()["success"] is True
        assert bt._state.value == "closed"
    return "OK"


def test_lifecycle_invalid_url():
    """Test: invalid URL is rejected without launching browser."""
    from src.tools.browser_tools import BrowserTools
    bt = BrowserTools()
    result = bt.browser_open("javascript:alert(1)")
    assert result["success"] is False
    return "OK"


def test_snapshot_returns_refs():
    """Test: snapshot returns elements with sequential refs."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        bt.browser_open(f.as_uri())
        result = bt.browser_snapshot()
        assert result["success"] is True
        assert result["elements_count"] > 0
        refs = [e["ref"] for e in result["elements"]]
        assert all(r.startswith("@e") for r in refs)
        numbers = sorted(int(r[2:]) for r in refs)
        assert numbers == list(range(1, len(refs) + 1)), f"Refs not sequential: {numbers}"
        bt.browser_close()
    return "OK"


def test_snapshot_creates_mapping():
    """Test: snapshot populates _ref_to_selector."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        bt.browser_open(f.as_uri())
        bt.browser_snapshot()
        assert "e1" in bt._ref_to_selector
        selector = bt._ref_to_selector["e1"]
        assert selector.startswith(("#", "[", ".")) or selector.startswith("button")
        bt.browser_close()
    return "OK"


def test_click_button_changes_text():
    """Test: clicking button changes page text."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        bt.browser_open(f.as_uri())
        result = bt.browser_click(".cancel-btn")
        assert result["success"] is True
        # Verify via public API (not direct _page access)
        title_result = bt.browser_get_text("#title")
        assert title_result["success"] is True
        assert title_result["text"] == "Clicked!"
        bt.browser_close()
    return "OK"


def test_fill_input():
    """Test: filling input populates value."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        bt.browser_open(f.as_uri())
        result = bt.browser_fill('[name="username"]', "alice")
        assert result["success"] is True
        # Verify via public API (avoids direct _page access from test thread)
        value_result = bt.browser_get_value('[name="username"]')
        assert value_result["success"] is True
        assert value_result["value"] == "alice"
        bt.browser_close()
    return "OK"


def test_check_checkbox():
    """Test: checking checkbox sets state."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        bt.browser_open(f.as_uri())
        # Use public API
        initial = bt.browser_is_checked("#remember-me")
        assert initial["success"] is True and initial["checked"] is False
        assert bt.browser_check("#remember-me")["success"] is True
        after = bt.browser_is_checked("#remember-me")
        assert after["success"] is True and after["checked"] is True
        bt.browser_close()
    return "OK"


def test_select_option():
    """Test: selecting dropdown option."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        bt.browser_open(f.as_uri())
        assert bt.browser_select('[name="role"]', "admin")["success"] is True
        value = bt.browser_get_value('[name="role"]')
        assert value["success"] is True and value["value"] == "admin"
        bt.browser_close()
    return "OK"


def test_get_text():
    """Test: get_text returns element text."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        bt.browser_open(f.as_uri())
        result = bt.browser_get_text("#title")
        assert result["success"] is True
        assert result["text"] == "Hello, Browser!"
        bt.browser_close()
    return "OK"


def test_get_url():
    """Test: get_url returns current URL."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        bt.browser_open(f.as_uri())
        result = bt.browser_get_url()
        assert result["success"] is True
        assert "test.html" in result["url"]
        bt.browser_close()
    return "OK"


def test_screenshot_saves_file():
    """Test: screenshot saves file to workspace."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        bt.browser_open(f.as_uri())
        result = bt.browser_screenshot("test.png")
        assert result["success"] is True
        path = Path(result["path"])
        assert path.exists() and path.stat().st_size > 0
        bt.browser_close()
    return "OK"


def test_screenshot_path_traversal_rejected():
    """Test: path traversal in screenshot is rejected by path validation, not by browser state.

    T-4 修复：先确认 browser_open 真正成功，避免 open 失败导致 success=False
    的伪通过；然后断言错误消息明确指出路径校验失败。
    """
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        # 先确认 browser_open 真的成功 —— 否则该测试会因为 browser 未启动而误通过
        open_result = bt.browser_open(f.as_uri())
        assert open_result["success"] is True, f"open failed: {open_result}"
        # 再校验路径遍历被 _validate_screenshot_path 拒绝（不是被 browser 状态拒绝）
        result = bt.browser_screenshot("../evil.png")
        assert result["success"] is False
        err = result.get("error", "").lower()
        assert ("traversal" in err or "invalid path" in err), \
            f"error should mention path validation, got: {result.get('error')!r}"
        bt.browser_close()
    return "OK"


def test_scroll_down():
    """Test: scroll down works."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        bt.browser_open(f.as_uri())
        result = bt.browser_scroll("down", 100)
        assert result["success"] is True
        bt.browser_close()
    return "OK"


def test_full_workflow():
    """Test: complete LLM-style workflow."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        # 1. Open
        open_result = bt.browser_open(f.as_uri())
        assert open_result["success"] is True
        # 2. Snapshot
        snap = bt.browser_snapshot()
        assert snap["success"] is True
        # 3. Fill
        assert bt.browser_fill('[name="username"]', "bob")["success"] is True
        # 4. Check
        assert bt.browser_check("#remember-me")["success"] is True
        # 5. Verify via public API
        username_value = bt.browser_get_value('[name="username"]')
        assert username_value["success"] is True and username_value["value"] == "bob"
        remember_checked = bt.browser_is_checked("#remember-me")
        assert remember_checked["success"] is True and remember_checked["checked"] is True
        # 6. Close
        close = bt.browser_close()
        assert close["success"] is True
        # data is merged into top-level (not nested under 'data' key)
        assert close["task_completed"] is True
    return "OK"


def test_navigate_and_interact():
    """Test: navigate_and_interact executes full action sequence."""
    from src.tools.browser_tools import BrowserTools
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        f = workspace / "test.html"
        f.write_text(SAMPLE_HTML, encoding="utf-8")
        bt = BrowserTools(workspace_root=str(workspace))
        result = bt.browser_navigate_and_interact(
            url=f.as_uri(),
            actions=[
                {"type": "fill", "selector": '[name="username"]', "value": "carol"},
                {"type": "check", "selector": "#remember-me"},
            ]
        )
        assert result["success"] is True
        # Verify via public API
        value = bt.browser_get_value('[name="username"]')
        assert value["success"] is True and value["value"] == "carol"
        bt.browser_close()
    return "OK"


# All tests
ALL_TESTS: List[Tuple[str, callable]] = [
    ("test_lifecycle_open_file", test_lifecycle_open_file),
    ("test_lifecycle_open_close", test_lifecycle_open_close),
    ("test_lifecycle_invalid_url", test_lifecycle_invalid_url),
    ("test_snapshot_returns_refs", test_snapshot_returns_refs),
    ("test_snapshot_creates_mapping", test_snapshot_creates_mapping),
    ("test_click_button_changes_text", test_click_button_changes_text),
    ("test_fill_input", test_fill_input),
    ("test_check_checkbox", test_check_checkbox),
    ("test_select_option", test_select_option),
    ("test_get_text", test_get_text),
    ("test_get_url", test_get_url),
    ("test_screenshot_saves_file", test_screenshot_saves_file),
    ("test_screenshot_path_traversal_rejected", test_screenshot_path_traversal_rejected),
    ("test_scroll_down", test_scroll_down),
    ("test_full_workflow", test_full_workflow),
    ("test_navigate_and_interact", test_navigate_and_interact),
]


def main():
    parser = argparse.ArgumentParser(description="BrowserTools integration test runner")
    parser.add_argument("--single-test", help="Run only this test by name")
    parser.add_argument("--list", action="store_true", help="List all tests")
    args = parser.parse_args()

    if args.list:
        for name, _ in ALL_TESTS:
            print(name)
        return 0

    if args.single_test:
        tests = [(n, f) for n, f in ALL_TESTS if n == args.single_test]
        if not tests:
            print(f"Unknown test: {args.single_test}")
            return 1
    else:
        tests = ALL_TESTS

    passed = 0
    failed = 0
    failures = []

    for name, test_func in tests:
        sys.stdout.write(f"  {name} ... ")
        sys.stdout.flush()
        ok, msg = _run_test_in_subprocess(test_func)
        if ok:
            print("PASS")
            passed += 1
        else:
            print(f"FAIL: {msg[:200]}")
            failures.append((name, msg))
            failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed (total {len(tests)})")
    if failures:
        print()
        print("Failure details:")
        for name, msg in failures:
            print(f"\n--- {name} ---")
            print(msg[:1000])
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
