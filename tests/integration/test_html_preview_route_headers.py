#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for the ``/api/html-preview/<path>`` Flask route.

These tests stand up the real Flask app from ``GUI.app`` via ``test_client``
and assert the security-header contract is observable through the public
HTTP interface — i.e. a regression in the route cannot hide behind a unit
test that only exercises the helper in isolation.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# The GUI package is imported as a flat module ("from app import app") inside
# GUI/app.py because that file lives in D:\Project\AGIAgent\GUI\ and adds
# itself to sys.path. Mirror that contract here so the import resolves.
_GUI_DIR = Path(__file__).resolve().parents[2] / "GUI"
if str(_GUI_DIR) not in sys.path:
    sys.path.insert(0, str(_GUI_DIR))


@pytest.fixture
def html_preview_app():
    """Yield the Flask app with GUI internals patched out, plus a writeable
    workspace directory containing a sample HTML file.

    The patches stub out everything the route needs *beyond* the Flask layer
    itself: GUI session lookup, app-switch routing, and the per-request base
    data dir. The actual response-building code runs untouched so the test
    exercises the real ``serve_html_preview`` body.
    """
    from app import app  # noqa: WPS433 (deliberate import-time path setup)

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "output_test" / "workspace"
        workspace.mkdir(parents=True)
        sample = workspace / "sample.html"
        sample.write_text(
            "<!DOCTYPE html><html><head><title>test</title></head>"
            "<body><p>hello</p></body></html>",
            encoding="utf-8",
        )

        fake_gui = MagicMock()
        fake_session = MagicMock()
        fake_session.get_user_directory.return_value = str(workspace)
        fake_gui.get_user_session.return_value = fake_session
        fake_gui.get_base_data_dir_for_request.return_value = str(workspace.parent)

        with patch("app.gui_instance", fake_gui), \
             patch("app.create_temp_session_id", return_value="sess-test"):
            app.config["TESTING"] = True
            yield app, fake_gui, sample


class TestHtmlPreviewRouteSecurityHeaders:
    """End-to-end pin: the live route MUST emit the security headers."""

    def test_route_sets_content_security_policy(self, html_preview_app):
        app, _, sample = html_preview_app
        client = app.test_client()

        resp = client.get(f"/api/html-preview/{sample.name}")

        assert resp.status_code == 200, (
            f"Expected 200 OK from preview route, got {resp.status_code}: "
            f"{resp.get_data(as_text=True)[:200]!r}"
        )
        csp = resp.headers.get("Content-Security-Policy", "")
        assert csp, "Response missing Content-Security-Policy header"
        assert "frame-ancestors 'self'" in csp, (
            f"CSP must include frame-ancestors 'self', got: {csp!r}"
        )

    def test_route_sets_x_content_type_options(self, html_preview_app):
        app, _, sample = html_preview_app
        resp = app.test_client().get(f"/api/html-preview/{sample.name}")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_route_sets_referrer_policy(self, html_preview_app):
        app, _, sample = html_preview_app
        resp = app.test_client().get(f"/api/html-preview/{sample.name}")
        assert resp.headers.get("Referrer-Policy") == "no-referrer"

    def test_route_sets_cache_control_no_store(self, html_preview_app):
        app, _, sample = html_preview_app
        resp = app.test_client().get(f"/api/html-preview/{sample.name}")
        assert resp.headers.get("Cache-Control") == "private, no-store"