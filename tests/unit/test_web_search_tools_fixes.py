#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for web_search_tools.py fixes.

验证内容：
1. 性能参数集中管理为类常量
2. 错误消息正确反映超时值
3. 并行下载线程数使用类常量
4. 等待时间使用类常量
"""

import pytest
import re
import sys
import os
from unittest.mock import MagicMock, patch

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestPerformanceConstants:
    """验证性能参数常量定义"""

    def test_class_constants_defined(self):
        """验证类常量已正确定义"""
        from src.tools.web_search_tools import WebSearchTools

        # 验证常量存在
        assert hasattr(WebSearchTools, 'BAIDU_WAIT_TIME_MS'), "缺少 BAIDU_WAIT_TIME_MS 常量"
        assert hasattr(WebSearchTools, 'DEFAULT_WAIT_TIME_MS'), "缺少 DEFAULT_WAIT_TIME_MS 常量"
        assert hasattr(WebSearchTools, 'DOWNLOAD_TIMEOUT_SEC'), "缺少 DOWNLOAD_TIMEOUT_SEC 常量"
        assert hasattr(WebSearchTools, 'MAX_PARALLEL_WORKERS'), "缺少 MAX_PARALLEL_WORKERS 常量"

        # 验证常量值正确
        assert WebSearchTools.BAIDU_WAIT_TIME_MS == 2000, f"百度等待时间应为 2000ms，实际为 {WebSearchTools.BAIDU_WAIT_TIME_MS}"
        assert WebSearchTools.DEFAULT_WAIT_TIME_MS == 1500, f"其他引擎等待时间应为 1500ms，实际为 {WebSearchTools.DEFAULT_WAIT_TIME_MS}"
        assert WebSearchTools.DOWNLOAD_TIMEOUT_SEC == 15.0, f"下载超时应为 15.0s，实际为 {WebSearchTools.DOWNLOAD_TIMEOUT_SEC}"
        assert WebSearchTools.MAX_PARALLEL_WORKERS == 8, f"最大并发应为 8，实际为 {WebSearchTools.MAX_PARALLEL_WORKERS}"


class TestDownloadTimeoutFix:
    """验证超时参数和错误消息修复"""

    def test_error_message_uses_dynamic_timeout(self):
        """验证错误消息使用动态 timeout 值，而非硬编码"""
        from src.tools.web_search_tools import WebSearchTools

        source_file = WebSearchTools.__module__
        # 动态导入获取源码
        import src.tools.web_search_tools as wst
        source_file = wst.__file__

        with open(source_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        # 检查不应有硬编码的 "timeout 30s"
        hardcoded_30s = re.search(r'timeout 30s', source_code)
        assert hardcoded_30s is None, "错误消息中不应有硬编码的 'timeout 30s'"
        # 错误消息应使用动态值
        dynamic_timeout_pattern = re.search(r'timeout \{int\([^)]+\)\}s\)', source_code)
        assert dynamic_timeout_pattern, "错误消息应使用动态 timeout 值"

    def test_timeout_value_uses_class_constant(self):
        """验证超时值使用类常量"""
        import src.tools.web_search_tools as wst

        with open(wst.__file__, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # download_timeout 应使用类常量
        assert 'download_timeout = self.DOWNLOAD_TIMEOUT_SEC' in source_code, \
            "download_timeout 应使用类常量 self.DOWNLOAD_TIMEOUT_SEC"

    def test_download_function_uses_timeout_parameter(self):
        """验证下载函数使用 timeout 参数"""
        import src.tools.web_search_tools as wst

        with open(wst.__file__, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # _download_webpage_with_requests 应使用 download_timeout 参数
        assert 'timeout=download_timeout' in source_code, \
            "_download_webpage_with_requests 应使用 download_timeout 参数"


class TestParallelDownloadConfig:
    """验证并行下载配置"""

    def test_max_workers_uses_class_constant(self):
        """验证 max_workers 使用类常量"""
        import src.tools.web_search_tools as wst

        with open(wst.__file__, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # max_workers 应使用类常量
        assert 'max_workers = min(self.MAX_PARALLEL_WORKERS' in source_code, \
            "max_workers 应使用类常量 self.MAX_PARALLEL_WORKERS"


class TestWaitTimeConfig:
    """验证页面等待时间配置"""

    def test_baidu_wait_time_uses_class_constant(self):
        """验证百度等待时间使用类常量"""
        import src.tools.web_search_tools as wst

        with open(wst.__file__, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # wait_time 应使用类常量
        assert 'wait_time = self.BAIDU_WAIT_TIME_MS if engine' in source_code, \
            "百度等待时间应使用类常量 self.BAIDU_WAIT_TIME_MS"

    def test_other_engine_wait_time_uses_class_constant(self):
        """验证其他引擎等待时间使用类常量"""
        import src.tools.web_search_tools as wst

        with open(wst.__file__, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # wait_time else 分支应使用类常量
        assert 'self.DEFAULT_WAIT_TIME_MS' in source_code, \
            "其他引擎等待时间应使用类常量 self.DEFAULT_WAIT_TIME_MS"


class TestErrorMessageIntegration:
    """集成测试：验证错误消息与超时参数一致"""

    def test_timeout_consistency_in_source(self):
        """验证源码中错误消息与超时参数一致"""
        import src.tools.web_search_tools as wst

        with open(wst.__file__, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # 查找错误消息中的超时值引用
        error_message_pattern = re.search(r'f"Failed to download webpage \(timeout \{int\(([^)]+)\)[^}]*\}s\)"', source_code)

        assert error_message_pattern, "找不到错误消息模式"
        timeout_var = error_message_pattern.group(1)

        # 错误消息中的变量应与 download_timeout 相关
        assert 'download_timeout' in timeout_var or 'DOWNLOAD_TIMEOUT_SEC' in timeout_var, \
            "错误消息应使用动态值而非硬编码"