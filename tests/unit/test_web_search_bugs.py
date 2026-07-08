#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for web_search_tools.py bugs.

验证发现并已修复的问题：
1. _is_quality_content 导航关键词重复 → 已去重
2. _download_webpage_with_requests HTTPError dead code → 已移除
3. _save_webpage_content 和 _from_html 中 downloaded_urls.add 重复 → 已合并
4. _fetch_webpage_content 敏感关键词检查重复 → 已移除冗余
"""

import pytest
import re
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestIsQualityContent:
    """验证 _is_quality_content 方法"""

    def test_no_duplicate_navigation_keywords(self):
        """导航关键词列表中无重复值"""
        from src.tools.web_search_tools import WebSearchTools

        source_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "src", "tools", "web_search_tools.py"
        )
        with open(source_file, 'r', encoding='utf-8') as f:
            source = f.read()

        match = re.search(
            r'NAVIGATION_KEYWORDS\s*=\s*\((.*?)\)',
            source,
            re.DOTALL
        )
        assert match, "NAVIGATION_KEYWORDS not found"
        keywords_text = match.group(1)

        keywords = re.findall(r"'([^']+)'", keywords_text)
        keywords_lower = [k.lower() for k in keywords]

        seen = set()
        duplicates = set()
        for kw in keywords_lower:
            if kw in seen:
                duplicates.add(kw)
            seen.add(kw)

        assert len(duplicates) == 0, (
            f"Found duplicate navigation keywords: {duplicates}"
        )

    def test_duplicates_removed_count(self):
        """验证去重后关键词列表数量正确（12个唯一值，无子串重叠）"""
        from src.tools.web_search_tools import WebSearchTools

        source_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "src", "tools", "web_search_tools.py"
        )
        with open(source_file, 'r', encoding='utf-8') as f:
            source = f.read()

        match = re.search(
            r'NAVIGATION_KEYWORDS\s*=\s*\((.*?)\)',
            source,
            re.DOTALL
        )
        assert match
        keywords_text = match.group(1)
        keywords = re.findall(r"'([^']+)'", keywords_text)

        assert len(keywords) == 12, (
            f"Expected 12 unique keywords (no substring overlap), got {len(keywords)}: {keywords}"
        )
        # 验证无子串重叠（如 'privacy' ⊂ 'privacy policy'）
        for kw in keywords:
            others = [k for k in keywords if k != kw]
            assert not any(kw in other for other in others), (
                f"Keyword '{kw}' is a substring of another keyword, causing double-counting"
            )


class TestDownloadWebpageHTTPError:
    """验证 _download_webpage_with_requests 无 HTTPError dead code"""

    def test_no_http_error_dead_code(self):
        """确认 HTTPError catch block 已被移除"""
        source_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "src", "tools", "web_search_tools.py"
        )
        with open(source_file, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'requests.exceptions.HTTPError' not in source, (
            "HTTPError catch block should have been removed (dead code)"
        )


class TestDownloadedUrlsNoDuplicate:
    """验证 downloaded_urls.add 不重复"""

    def test_downloaded_urls_add_once_in_save(self):
        """_save_webpage_content 中 downloaded_urls.add 仅出现1次"""
        source_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "src", "tools", "web_search_tools.py"
        )
        with open(source_file, 'r', encoding='utf-8') as f:
            source = f.read()

        add_count = source.count('self.downloaded_urls.add(normalized_url)')
        assert add_count == 2, (
            f"downloaded_urls.add(normalized_url) appears {add_count} times "
            f"(expected 2: once in _save_webpage_content, once in _save_webpage_content_from_html)"
        )

    def test_downloaded_urls_not_in_save_blocks(self):
        """确认 downloaded_urls.add 不在 HTML/TXT 保存块内部"""
        source_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "src", "tools", "web_search_tools.py"
        )
        with open(source_file, 'r', encoding='utf-8') as f:
            source = f.read()

        # 检查 HTML 保存块后没有直接跟 add
        html_save_pattern = r"f\.write\(html_content\)\s*\n\s*# 成功保存HTML后"
        assert not re.search(html_save_pattern, source), (
            "Should not have '记录URL' comment after HTML save"
        )

        # 检查 TXT 保存块后没有直接跟 add
        txt_save_pattern = r"f\.write\(formatted_content\)\s*\n\s*# 成功保存后"
        assert not re.search(txt_save_pattern, source), (
            "Should not have '记录URL' comment after TXT save"
        )


class TestFetchWebpageContentNoDuplicateFilter:
    """验证 _fetch_webpage_content 敏感词过滤器无重复"""

    def test_sensitive_keywords_not_duplicated(self):
        """敏感关键词仅以类常量方式引用，无重复本地定义"""
        source_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "src", "tools", "web_search_tools.py"
        )
        with open(source_file, 'r', encoding='utf-8') as f:
            source = f.read()

        fetch_method_pos = source.find("def _fetch_webpage_content(self")
        assert fetch_method_pos >= 0, "Could not find _fetch_webpage_content"

        method_end = source.find("\n    def ", fetch_method_pos + 30)
        if method_end < 0:
            method_end = len(source)
        fetch_section = source[fetch_method_pos:method_end]

        count = fetch_section.count("SENSITIVE_TITLE_KEYWORDS")
        assert count == 1, (
            f"SENSITIVE_TITLE_KEYWORDS appears {count} times in "
            f"_fetch_webpage_content (expected 1: usage via class constant)"
        )

        # Also verify no local list definition exists
        assert 'sensitive_keywords = [' not in fetch_section, (
            "Should not have local sensitive_keywords definition in _fetch_webpage_content"
        )


class TestHtmlWriteFailureBehavior:
    """行为化测试：验证 HTML 写入失败时 URL 不被标记为已下载"""

    def test_html_write_failure_does_not_mark_url(self, tmp_path):
        """HTML/TXT 写入失败时 downloaded_urls 应为空（C1 回归防护）"""
        import builtins
        from src.tools.web_search_tools import WebSearchTools

        tools = object.__new__(WebSearchTools)
        tools.downloaded_urls = set()
        tools.web_result_dir = str(tmp_path)
        tools.verbose = False
        tools.enable_llm_filtering = False
        tools.enable_summary = True
        tools.use_zhipu_search = False
        tools.failed_engines = set()

        original_open = builtins.open

        def _failing_open(*args, **kwargs):
            """Only fail for writes inside web_result_dir"""
            path = args[0] if args else ''
            if isinstance(path, str) and path.startswith(str(tmp_path)):
                raise OSError("No space left on device")
            return original_open(*args, **kwargs)

        with patch.multiple(tools,
            _normalize_url_for_dedup=MagicMock(return_value="https://example.com/test"),
            _detect_special_page=MagicMock(return_value=(False, "", "")),
            _ensure_result_directory=MagicMock(),
            _clean_text_for_saving=MagicMock(return_value="x" * 100),
            _clean_text_for_saving_simple=MagicMock(return_value="y" * 100)):
            with patch("builtins.open", side_effect=_failing_open):
                tools._save_webpage_content_from_html(
                    html_content="<html>test</html>",
                    url="https://example.com/test",
                    title="Test",
                    content="Some text content that is long enough to pass the 50 char threshold for txt saving.",
                )

        assert len(tools.downloaded_urls) == 0, (
            f"URL should NOT be marked as downloaded when all writes fail. "
            f"Got: {tools.downloaded_urls}"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
