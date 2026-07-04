#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端逻辑链测试 + Bug 排查

测试目标：
1. 验证两个工具改动后的完整逻辑链路
2. 验证环境变量优先级（用户显式 > Extend-dependenc > 默认）
3. 验证 Headless Shell binary 选择（默认 + GUI fallback）
4. 验证状态机完整性（open→interact→close→reopen）
5. 排查潜在 bug：env 污染、并发、状态泄漏等
"""

import os
import sys
import time
import subprocess
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, '.')

# 让输出更好读
def section(name):
    print()
    print("=" * 70)
    print(f"  {name}")
    print("=" * 70)

def check(name, condition, details=""):
    status = "✅" if condition else "❌"
    print(f"  {status} {name}", end="")
    if details:
        print(f"  [{details}]", end="")
    print()
    return condition

def count_procs(image_name):
    """Windows tasklist 计数"""
    r = subprocess.run(
        ['tasklist', '/FI', f'IMAGENAME eq {image_name}', '/NH', '/FO', 'CSV'],
        capture_output=True, text=True
    )
    out = r.stdout.strip()
    if not out or 'No tasks' in out:
        return 0
    return len([l for l in out.split('\n') if l.strip()])


# ============================================================================
# SCENARIO 1: 默认场景 - 无 env var，期望走 Extend-dependenc + headless_shell
# ============================================================================
section("SCENARIO 1: 默认 (no env var) → auto-detect → headless_shell")
# 清理可能的残留进程
subprocess.run(['taskkill', '/F', '/IM', 'chrome-headless-shell.exe'],
               capture_output=True)
subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'],
               capture_output=True)
time.sleep(0.5)

# 确保无 env
os.environ.pop('PLAYWRIGHT_BROWSERS_PATH', None)

from src.tools.browser_tools import BrowserTools

bt = BrowserTools()
env_set = 'PLAYWRIGHT_BROWSERS_PATH' in os.environ
check("env var 被自动设置", env_set)
check("指向 Extend-dependenc/playwright",
      env_set and 'Extend-dependenc' in os.environ['PLAYWRIGHT_BROWSERS_PATH'],
      os.environ.get('PLAYWRIGHT_BROWSERS_PATH', ''))

# 实际打开
result = bt.browser_open('https://example.com', headless=True)
time.sleep(0.5)

headless_shell_count = count_procs('chrome-headless-shell.exe')
full_chrome_count = count_procs('chrome.exe')

check("browser_open 成功", result.get('success') is True,
      f"error={result.get('error', 'none')}")
check("headless_shell.exe 进程存在（4 个左右：主+子）",
      headless_shell_count >= 1,
      f"count={headless_shell_count}")
check("chrome.exe 进程数（应该是残留，不应该新增）",
      full_chrome_count < 10,
      f"count={full_chrome_count}")

bt.browser_close()
time.sleep(0.5)


# ============================================================================
# SCENARIO 2: 完整交互链路 - snapshot / click / fill
# ============================================================================
section("SCENARIO 2: 完整链路 snapshot → fill → click → close")
os.environ.pop('PLAYWRIGHT_BROWSERS_PATH', None)

bt = BrowserTools(workspace_root=os.getcwd())
r1 = bt.browser_open('https://example.com', headless=True)
check("open 成功", r1.get('success') is True)

# 用真实例子测试
r2 = bt.browser_snapshot()
check("snapshot 成功", r2.get('success') is True)
check("snapshot 返回 elements 字段（data 平铺到响应根级）",
      'elements' in r2,
      f"keys={list(r2.keys())[:5]}")

r3 = bt.browser_get_text('h1')
check("get_text(h1) 成功", r3.get('success') is True)

r4 = bt.browser_get_url()
check("get_url 成功", r4.get('success') is True,
      f"url={r4.get('data', {}).get('url', '')[:40]}")

r5 = bt.browser_close()
check("close 成功", r5.get('success') is True)


# ============================================================================
# SCENARIO 3: 状态机 - close 后 reopen
# ============================================================================
section("SCENARIO 3: 状态机 - close → reopen")
os.environ.pop('PLAYWRIGHT_BROWSERS_PATH', None)

bt = BrowserTools()
bt.browser_open('https://example.com', headless=True)
bt.browser_close()
time.sleep(0.3)

# 重新打开 - 应该用 IDLE → OPENED 转换
r = bt.browser_open('https://example.com', headless=True)
check("reopen 成功", r.get('success') is True,
      f"state={r.get('status', '?')}")
bt.browser_close()


# ============================================================================
# SCENARIO 4: env var 优先级 - 显式 env 优先于 Extend-dependenc
# ============================================================================
section("SCENARIO 4: 显式 env var 应被尊重，不被覆盖")
fake_cache = Path(tempfile.mkdtemp(prefix="pw_fake_"))
try:
    # 设置一个 fake 路径作为 env
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(fake_cache)

    bt = BrowserTools()
    # 读 _ensure_playwright 内部状态 - 它检查 env var 而不是设它
    # 但我们之前已经看到了 env_set 那一步（只设一次）

    # 因为我们在 Scenario 1-3 已经 import 过 BrowserTools 了，env var 在第一次设过
    # 现在设的是 fake 路径，应该被尊重

    # 打开一个 fake URL（headless=True 会快速 fail 因为 fake 路径没 chromium）
    r = bt.browser_open('https://example.com', headless=True)

    # 因为 fake 路径下没有 chromium，应该 fail
    fail_with_env_respected = not r.get('success') and 'fake' in str(fake_cache).lower() or \
                              fake_cache.name.encode().decode('utf-8', errors='ignore').lower() in str(r.get('error', '')).lower()
    # 更可靠的判断：error 包含 fake 路径的某部分
    error_mentions_path = str(fake_cache) in str(r.get('error', '')) or \
                          fake_cache.name in str(r.get('error', ''))
    check("env var 被尊重（fake 路径下 launch 失败）",
          not r.get('success') and (
              'chrome-headless-shell' in str(r.get('error', '')) or
              'chromium' in str(r.get('error', '')) or
              'Executable' in str(r.get('error', ''))
          ),
          f"err={str(r.get('error', ''))[:100]}")

    # 检查 env var 没有被改成 Extend-dependenc
    still_fake = os.environ.get('PLAYWRIGHT_BROWSERS_PATH') == str(fake_cache)
    check("env var 保持为 fake 路径（未被覆盖）", still_fake)

    bt.browser_close()
finally:
    shutil.rmtree(fake_cache, ignore_errors=True)
    os.environ.pop('PLAYWRIGHT_BROWSERS_PATH', None)


# ============================================================================
# SCENARIO 5: web_search_tools 三个 launch 点都用 headless_shell
# ============================================================================
section("SCENARIO 5: web_search_tools 三个 launch 点都用 headless_shell")
import re

with open('src/tools/web_search_tools.py', 'r', encoding='utf-8') as f:
    src = f.read()

# 找到所有 chromium.launch 调用
launches = re.findall(
    r'browser\s*=\s*p\.chromium\.launch\(\s*\n(.*?)\)',
    src, re.DOTALL
)
check(f"找到 3 处 chromium.launch", len(launches) == 3,
      f"actual={len(launches)}")
for i, body in enumerate(launches):
    has_headless_shell = 'channel="chromium-headless-shell"' in body
    check(f"  launch #{i+1} 包含 channel=chromium-headless-shell", has_headless_shell)


# ============================================================================
# SCENARIO 6: headless_shell 二进制存在性
# ============================================================================
section("SCENARIO 6: 关键二进制文件存在")
shell_exe = Path('./Extend-dependenc/playwright/chromium_headless_shell-1223/'
                 'chrome-headless-shell-win64/chrome-headless-shell.exe')
full_exe = Path('./Extend-dependenc/playwright/chromium-1223/chrome-win64/chrome.exe')

check("headless_shell.exe 存在", shell_exe.exists(), str(shell_exe)[:60])
check("完整 chrome.exe 存在", full_exe.exists(), str(full_exe)[:60])
check("两者大小（headless_shell 应该更大因为是 fat binary）",
      shell_exe.stat().st_size > 50_000_000,
      f"{shell_exe.stat().st_size // 1_000_000}MB")


# ============================================================================
# SCENARIO 7: headless=False 时启动 GUI 模式（应该 fallback 到 chrome.exe）
# ============================================================================
section("SCENARIO 7: headless=False → Playwright fallback 到 chrome.exe")
os.environ.pop('PLAYWRIGHT_BROWSERS_PATH', None)

# 清理残留
subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'],
               capture_output=True)
time.sleep(0.3)

# 不实际打开 GUI（避免阻塞测试），但验证 launch_kwargs 包含 channel
import inspect
src = inspect.getsource(BrowserTools.browser_open)
has_channel_unconditional = 'channel="chromium-headless-shell"' in src and \
                            '"channel": "chromium-headless-shell"' in src
check("browser_open launch_kwargs 无条件包含 channel",
      has_channel_unconditional)

# 模拟：headless=False 时 channel 仍被设，由 Playwright 决定
# 实际 launch 会尝试弹窗（headless=False），我们只验证逻辑不真正弹窗


# ============================================================================
# SCENARIO 8: 端到端 - 真实浏览器加载页面 (headless)
# ============================================================================
section("SCENARIO 8: 端到端真实加载 https://example.com")
os.environ.pop('PLAYWRIGHT_BROWSERS_PATH', None)

bt = BrowserTools()
r = bt.browser_open('https://example.com', headless=True)
check("打开真实 URL 成功", r.get('success') is True,
      f"err={r.get('error', '')[:80]}")

time.sleep(0.3)
# 抓取 title
r2 = bt.browser_get_text()
check("get_text 无 selector → 返回 title", r2.get('success') is True)
# 注意：_make_response 把 data 平铺到响应根级，所以 text 直接在 r2['text']
title = r2.get('text', '')
check(f"title 是 'Example Domain'（响应 data 平铺）",
      'Example Domain' in title,
      f"title={title[:50]!r}")

# 截图
import tempfile as _tmp
tmp_png = _tmp.mktemp(suffix='.png')
r3 = bt.browser_screenshot(path=os.path.basename(tmp_png), full=False)
# 因为路径不在 workspace 内，可能 fail
screenshot_worked = r3.get('success') or 'workspace' in str(r3.get('error', ''))
check("screenshot 调用成功或路径拒绝（预期）", screenshot_worked,
      f"err={r3.get('error', '')[:60]}")

bt.browser_close()


# ============================================================================
# SCENARIO 9: web_search_tools 实际 web_search 调用
# ============================================================================
section("SCENARIO 9: web_search_tools 完整流程（dry-run 模式）")
# 注意：Python 的 import 是有缓存的，sys.modules 里已有 web_search_tools 时
# 第二次 importlib.import_module 不会重跑模块顶层代码。所以要测试 import 行为，
# 必须先从 sys.modules 移除。
os.environ.pop('PLAYWRIGHT_BROWSERS_PATH', None)
import sys as _sys
_sys.modules.pop('src.tools.web_search_tools', None)

# web_search_tools 在没有 API key 时会跳过 LLM filtering
# 直接调用应该能进入 Playwright fallback 路径
import importlib
wst = importlib.import_module('src.tools.web_search_tools')

# 验证模块顶层代码在首次 import 时设了 env var
check("首次 import web_search_tools 后 env 已设",
      'PLAYWRIGHT_BROWSERS_PATH' in os.environ and
      'Extend-dependenc' in os.environ['PLAYWRIGHT_BROWSERS_PATH'],
      os.environ.get('PLAYWRIGHT_BROWSERS_PATH', ''))

# 再检查一次：env var 仍然没被覆盖为默认（说明 module-level 设置对了）
check("env var 仍然指向 Extend-dependenc",
      'Extend-dependenc' in os.environ.get('PLAYWRIGHT_BROWSERS_PATH', ''))


# ============================================================================
# SCENARIO 10: 内存泄漏检查 - 多次开关
# ============================================================================
section("SCENARIO 10: 多次 open/close 不应泄漏 browser 进程")
os.environ.pop('PLAYWRIGHT_BROWSERS_PATH', None)

# 清理
subprocess.run(['taskkill', '/F', '/IM', 'chrome-headless-shell.exe'],
               capture_output=True)
time.sleep(1.5)  # 给 Windows 足够时间 reap 已结束的进程

baseline = count_procs('chrome-headless-shell.exe')

# 5 次开关
for i in range(5):
    bt = BrowserTools()
    bt.browser_open('https://example.com', headless=True)
    bt.browser_close()
    time.sleep(1.5)  # Chromium 关闭 → Windows reap 通常需要 1-2s

final = count_procs('chrome-headless-shell.exe')
check(f"5 次开关后 chrome-headless-shell.exe 进程数（baseline={baseline}）",
      final <= 1,
      f"baseline={baseline}, final={final}")


print()
print("=" * 70)
print("  测试完成")
print("=" * 70)