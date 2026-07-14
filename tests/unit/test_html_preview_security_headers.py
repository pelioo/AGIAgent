#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for ``GUI.security_headers.apply_html_preview_security_headers``.

The helper attaches defense-in-depth security headers to every response served
by ``/api/html-preview/<path>``. It is critical because the iframe sandbox on
the consumer side grants ``allow-same-origin`` + ``allow-scripts`` together,
which per WHATWG effectively neutralises the sandbox's origin isolation. The
server must therefore enforce CSP, frame-ancestors, MIME safety, and
no-caching for the embedded HTML so a malicious saved page cannot call the
same-origin API or leak api_key via referrer/proxy caches.
"""

import pytest
from flask import Flask, Response


def _make_blank_response() -> Response:
    """Build a minimal Flask Response we can mutate through the helper."""
    app = Flask(__name__)
    with app.test_request_context("/"):
        return Response("<html></html>", mimetype="text/html")


class TestHtmlPreviewSecurityHeaders:
    """Pin the security header contract of the /api/html-preview/ endpoint."""

    def test_sets_content_security_policy_with_frame_ancestors_self(self):
        """CSP MUST include ``frame-ancestors 'self'`` so only the AGI Agent
        GUI can embed the preview. Without this, any third-party page could
        ``<iframe src=/api/html-preview/...>`` the response and re-trigger
        the frame-busting vectors the sandbox is trying to close.
        """
        from GUI.security_headers import apply_html_preview_security_headers

        response = apply_html_preview_security_headers(_make_blank_response())
        csp = response.headers.get("Content-Security-Policy", "")
        assert csp, "Content-Security-Policy header is missing"
        assert "frame-ancestors 'self'" in csp, (
            f"CSP must include frame-ancestors 'self', got: {csp!r}"
        )

    def test_sets_x_content_type_options_nosniff(self):
        """``X-Content-Type-Options: nosniff`` MUST be set so browsers do not
        MIME-sniff the response — a saved page containing a polyglot
        text/html+javascript payload should never be re-typed by the agent.
        """
        from GUI.security_headers import apply_html_preview_security_headers

        response = apply_html_preview_security_headers(_make_blank_response())
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_sets_referrer_policy_no_referrer(self):
        """``Referrer-Policy: no-referrer`` MUST be set so resources loaded
        inside the iframe do not leak the preview URL (which contains the
        user's ``file_path`` and possibly an ``api_key`` query parameter)
        via the ``Referer`` header.
        """
        from GUI.security_headers import apply_html_preview_security_headers

        response = apply_html_preview_security_headers(_make_blank_response())
        assert response.headers.get("Referrer-Policy") == "no-referrer"

    def test_sets_cache_control_no_store(self):
        """``Cache-Control: private, no-store`` MUST be set. The preview URL
        embeds the user's ``api_key`` as a query parameter; intermediate
        proxies or shared HTTP caches MUST NOT retain this response.
        """
        from GUI.security_headers import apply_html_preview_security_headers

        response = apply_html_preview_security_headers(_make_blank_response())
        assert response.headers.get("Cache-Control") == "private, no-store"

    def test_returns_same_response_instance(self):
        """The helper MUST mutate-and-return the passed Response so that
        ``return apply_html_preview_security_headers(resp)`` works as a
        drop-in replacement for ``return resp`` in the route.
        """
        from GUI.security_headers import apply_html_preview_security_headers

        original = _make_blank_response()
        returned = apply_html_preview_security_headers(original)
        assert returned is original