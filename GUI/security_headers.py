#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security headers for ``/api/html-preview/`` responses.

Why this module exists
----------------------
The GUI HTML preview iframe is sandboxed with
``allow-same-origin allow-scripts``. Per the WHATWG HTML Living Standard,
granting ``allow-same-origin`` together with ``allow-scripts`` causes the
sandbox to treat the iframe as **same-origin with the embedder** rather than
the opaque origin it would otherwise use. In practice, JavaScript inside
the embedded HTML can call the GUI's same-origin backend API, read
``localStorage``, and read/write cookies just like the GUI itself.

The sandbox thus blocks *navigation* vectors (``top.location``, popups,
``<meta refresh>`` to top) but does NOT isolate *credential / network*
access. The server must therefore supply the missing layer via response
headers:

* ``Content-Security-Policy: ... frame-ancestors 'self'`` — only the GUI
  may embed the response, and the embedded page is restricted in what it
  can fetch / execute.
* ``X-Content-Type-Options: nosniff`` — prevent MIME sniffing of polyglot
  payloads saved by a user.
* ``Referrer-Policy: no-referrer`` — the preview URL embeds the user's
  ``file_path`` and possibly an ``api_key``; never leak it via ``Referer``
  on outbound requests from the iframe.
* ``Cache-Control: private, no-store`` — the URL may contain an ``api_key``
  query parameter; intermediate caches MUST NOT retain the response.

The helper is intentionally a pure function on a Flask ``Response`` so it
can be unit-tested without spinning up the GUI runtime.
"""

from flask import Response


_HTML_PREVIEW_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "img-src 'self' data: blob:; "
    "style-src 'self' 'unsafe-inline'; "
    "frame-ancestors 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'none'"
)


def apply_html_preview_security_headers(response: Response) -> Response:
    """Attach defense-in-depth security headers to a preview response.

    Mutates and returns ``response`` so callers can write
    ``return apply_html_preview_security_headers(resp)`` as a drop-in
    replacement for ``return resp``.
    """
    response.headers["Content-Security-Policy"] = _HTML_PREVIEW_CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "private, no-store"
    return response