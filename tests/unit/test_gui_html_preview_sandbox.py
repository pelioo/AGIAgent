#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression tests for the HTML preview iframe in GUI/templates/index.html.

Bug context
-----------
Commit 0e898c8 ("GUI HTML update", 2025-11-20) changed the workspace HTML
preview from a ``<iframe srcdoc=...>`` model to ``<iframe src=/api/html-preview/...>``
so relative resources could load. The srcdoc URL (about:srcdoc) made
``self === top`` and silently neutralized frame-busting JS like
``if(top!==self) top.location = self.location`` or
``<meta http-equiv="refresh" content="0;url=https://...">``.

After the change, the iframe points to a real same-origin URL where
``top !== self``, so the same frame-busting code escapes the iframe and
navigates the parent AGI Agent GUI window — observed e.g. on Bilibili
saved pages.

These tests pin the contract: the HTML preview iframe MUST be sandboxed
in a way that blocks top-navigation and popups but keeps the page
functional (same-origin resources, scripts), AND only those tokens — any
extra sandbox permission can re-enable a previously closed attack vector.

Why text matching instead of an HTML parser
-------------------------------------------
The preview iframe is built inside a JavaScript template literal
(``previewContent.innerHTML = `...<iframe ...>...`;``), i.e. it lives
inside a ``<script>`` block. A real HTML parser skips script content,
which means we cannot reach the iframe through DOM-style parsing.
Text-level matching on the iframe tag itself is the correct level for
this contract.

Known trade-off (allow-forms / allow-modals intentionally absent)
-----------------------------------------------------------------
Removing ``allow-forms`` means saved pages with login / search forms will
not submit. Removing ``allow-modals`` blocks ``alert/confirm/prompt``.
Both regressions are deliberate: ``allow-forms`` enables CSRF-style
exfiltration of user-entered data via ``form.action``, and ``allow-modals``
enables UI-redress via spoofed dialogs. A follow-up may add them back
behind an explicit user toggle.
"""

import re
from pathlib import Path

import pytest


INDEX_HTML_RELATIVE_PATH = Path("GUI") / "templates" / "index.html"

# Match a complete <iframe ...> start tag (single OR double quotes around
# attribute values, attributes in any order, whitespace between them
# including newlines). We deliberately do NOT require `src=` to be the
# first attribute — future maintenance that reorders attributes must not
# silently break these tests.
_IFRAME_TAG_PATTERN = re.compile(
    r'<iframe\b[^>]*>', re.IGNORECASE | re.DOTALL
)
_PREVIEW_URL_NEEDLE = "${previewUrl}"


def _extract_preview_iframe_tag(source: str) -> str:
    """Return the unique ``<iframe ...>`` whose attributes include
    ``src="${previewUrl}"`` (matched as a substring, not parsed).

    Raises ``ValueError`` (not ``assert``) so behaviour is preserved
    under ``python -O`` where ``assert`` statements are stripped.
    """
    matches: list[str] = []
    for tag in _IFRAME_TAG_PATTERN.findall(source):
        if _PREVIEW_URL_NEEDLE in tag:
            matches.append(tag)
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one <iframe ...> tag whose attributes "
            f"include src=${{previewUrl}}, found {len(matches)}. The "
            f"HTML template structure has drifted from the contract "
            f"these tests pin."
        )
    return matches[0]


def _sandbox_tokens(iframe_tag: str) -> set[str]:
    """Return the sandbox permission tokens declared on the iframe tag.

    Extracts the value of the ``sandbox`` attribute and splits it on
    whitespace per the WHATWG tokenisation rules. Robust to double /
    single quotes around the attribute value.
    """
    m = re.search(
        r"""sandbox\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
        iframe_tag,
        re.IGNORECASE,
    )
    if not m:
        return set()
    raw = next(g for g in m.groups() if g is not None)
    return set(raw.split())


def _attr(iframe_tag: str, name: str) -> str | None:
    """Return the value of ``name`` on the iframe tag, or ``None``."""
    m = re.search(
        rf"""{name}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
        iframe_tag,
        re.IGNORECASE,
    )
    if not m:
        return None
    return next(g for g in m.groups() if g is not None)


@pytest.fixture
def preview_iframe_tag(project_root: Path) -> str:
    """Load ``index.html`` from the real project root and extract the
    single ``${previewUrl}`` iframe tag string.
    """
    index_path = project_root / INDEX_HTML_RELATIVE_PATH
    return _extract_preview_iframe_tag(index_path.read_text(encoding="utf-8"))


class TestHtmlPreviewIframeSandbox:
    """Pin the security contract of the HTML preview iframe's sandbox."""

    def test_iframe_has_sandbox_attribute(self, preview_iframe_tag: str):
        """The HTML preview iframe MUST declare a sandbox attribute.

        Without it, frame-busting code inside saved pages (e.g.
        ``if(top!==self) top.location=...`` or
        ``<meta http-equiv=refresh content='0;url=https://...'>``) escapes
        the iframe and navigates the parent GUI window.
        """
        assert "sandbox" in preview_iframe_tag, (
            "HTML preview iframe is missing a sandbox attribute. "
            "Frame-busting scripts in saved pages (Bilibili, etc.) can "
            "navigate the parent GUI window."
        )

    @pytest.mark.parametrize(
        "required_token",
        ["allow-same-origin", "allow-scripts"],
    )
    def test_sandbox_grants_required_token(
        self,
        preview_iframe_tag: str,
        required_token: str,
    ):
        """``allow-same-origin`` and ``allow-scripts`` MUST both be granted.

        ``allow-same-origin`` keeps the ``<base href>`` rewrite functional
        (relative resources resolve). ``allow-scripts`` keeps video
        players and dynamic content alive. Removing either renders the
        preview blank or non-interactive.
        """
        granted = _sandbox_tokens(preview_iframe_tag)
        assert required_token in granted, (
            f"sandbox must include {required_token!r}, "
            f"got tokens: {sorted(granted)}"
        )

    @pytest.mark.parametrize(
        "forbidden_token",
        [
            "allow-top-navigation",
            "allow-top-navigation-by-user-activation",
            "allow-popups",
            "allow-popups-to-escape-sandbox",
        ],
    )
    def test_sandbox_blocks_dangerous_token(
        self,
        preview_iframe_tag: str,
        forbidden_token: str,
    ):
        """Tokens that re-open closed attack vectors MUST NOT be granted.

        * ``allow-top-navigation`` — re-enables
          ``if(top!==self) top.location=...``.
        * ``allow-top-navigation-by-user-activation`` — same family, gated
          behind a click; substring match on the bare token catches both.
        * ``allow-popups`` / ``allow-popups-to-escape-sandbox`` — let
          ``window.open`` escape the sandbox.
        """
        granted = _sandbox_tokens(preview_iframe_tag)
        assert forbidden_token not in granted, (
            f"sandbox must NOT include {forbidden_token!r}, "
            f"got tokens: {sorted(granted)}"
        )

    def test_sandbox_grants_no_extra_tokens(self, preview_iframe_tag: str):
        """The sandbox MUST be the minimal whitelist: only the two tokens
        strictly required for the preview to function. Any extra token
        (e.g. ``allow-forms``, ``allow-modals``, ``allow-downloads``)
        silently re-opens a class of attacks and must fail this test.
        """
        granted = _sandbox_tokens(preview_iframe_tag)
        allowed = {"allow-same-origin", "allow-scripts"}
        leaked = granted - allowed
        assert not leaked, (
            f"sandbox contains unexpected tokens {sorted(leaked)}. "
            f"Only {sorted(allowed)} are permitted — adding others may "
            f"leak user data or re-enable frame-busting."
        )


class TestHtmlPreviewIframeSourceContract:
    """Regression guards for the iframe source URL and surrounding attributes."""

    def test_iframe_does_not_use_srcdoc(self, preview_iframe_tag: str):
        """The iframe MUST NOT use ``srcdoc``.

        ``about:srcdoc`` makes ``self === top``, silently defeating
        frame-busting by removing the very signal those scripts test
        against. Worse, it kills relative resource loading, which is
        exactly the bug 0e898c8 moved us to the endpoint model to fix.
        """
        assert "srcdoc" not in preview_iframe_tag, (
            "iframe must not use srcdoc — it breaks relative resource "
            "loading and silently bypasses frame-busting by making "
            "self === top."
        )

    def test_iframe_src_routes_through_html_preview_endpoint(
        self,
        preview_iframe_tag: str,
    ):
        """The iframe ``src`` MUST interpolate ``${previewUrl}``.

        This is the contract that 0e898c8 established: the iframe points
        at the same-origin ``/api/html-preview/`` endpoint so the base
        rewrite (``<base href>``) can resolve relative resources. Going
        back to a literal URL would silently lose that path.
        """
        src = _attr(preview_iframe_tag, "src")
        assert src and "${previewUrl}" in src, (
            f"iframe src must interpolate ${{previewUrl}}, got: {src!r}"
        )


class TestHtmlPreviewIframeTransportAttributes:
    """Pin transport-level attributes that prevent URL leak and referrer abuse."""

    def test_iframe_has_referrerpolicy_no_referrer(self, preview_iframe_tag: str):
        """The iframe MUST set ``referrerpolicy="no-referrer"``.

        The preview URL embeds the user's ``file_path`` and possibly an
        ``api_key`` query parameter. Without this attribute, any outbound
        request from inside the iframe (e.g. ``<img src=cdn>``) leaks the
        preview URL via the ``Referer`` header.
        """
        rp = _attr(preview_iframe_tag, "referrerpolicy")
        assert rp == "no-referrer", (
            f"iframe must set referrerpolicy=\"no-referrer\" to prevent "
            f"the preview URL (which carries file_path and api_key) from "
            f"leaking via Referer. Got: {rp!r}"
        )