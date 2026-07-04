#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Browser Tools - 基于 Playwright Python 的浏览器自动化工具
============================================================

提供浏览器控制能力：导航、截图、表单填写、元素交互等。
底层使用 Playwright sync API 直接驱动 Chromium。

设计原则：
1. 统一返回格式（所有方法返回相同的结构）
2. 状态机管理（IDLE → OPENED → BROWSING → CLOSED）
3. next_step 提示引导 LLM
4. @ref 引用系统（@e1, @e2...）兼容 LLM 训练时的接口
5. 异步错误处理，无进程开销
"""

import os
import re
import time
import threading
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional
from enum import Enum

# 注：D-6 修复 — print_current 是死导入，已移除以保持清洁。


def _is_within(path: str, root: str) -> bool:
    """严格边界检查：判断 path 是否在 root 内部（解决 sibling directory bypass）。

    严格模式：path 必须等于 root，或是 root/xxx 子路径。
    防止 `startswith('/work')` 误判 `/work_evil`（前缀相同但不是子目录）。
    """
    if not path or not root:
        return False
    # 规范化分隔符为 os.sep，对 Windows 与 Unix 一致
    norm_path = os.path.normpath(path)
    norm_root = os.path.normpath(root)
    # 必须以 "root + os.sep" 开头，或者恰好等于 root
    return norm_path == norm_root or norm_path.startswith(norm_root + os.sep)


def _browser_op(method):
    """装饰器：将方法体放到 BrowserTools 的专用线程中执行。

    Playwright sync API 内部使用 event loop。如果当前线程已经有运行中的
    event loop（pytest-asyncio、async 代码），sync_playwright() 会拒绝启动。
    用这个装饰器统一把方法体放到专用线程，规避冲突。
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        return self._run_in_thread(method, self, *args, **kwargs)
    return wrapper


class BrowserState(Enum):
    """浏览器状态机"""
    IDLE = "idle"           # 未启动
    OPENED = "opened"       # 已打开页面
    BROWSING = "browsing"   # 正在交互
    CLOSED = "closed"       # 已关闭


class BrowserTools:
    """
    浏览器控制工具类（Playwright 实现）

    统一返回格式：
    {
        "success": bool,           # 操作是否成功
        "status": str,              # 当前状态
        "action": str,              # 执行的动作
        "timestamp": float,        # 时间戳
        "next_step": str,          # 下一步建议（LLM 引导）
        "data": {...},              # 实际数据（可选）
        "error": str,               # 错误信息（可选）
    }
    """

    # 动作到下一个动作的映射（LLM 工作流引导）
    NEXT_STEP_HINTS: Dict[str, str] = {
        "open": "Call snapshot() to get interactive elements",
        "snapshot": "Use @e1, @e2, etc. to interact. Then close() when done.",
        "click": "Continue interacting or call snapshot() for new elements",
        "fill": "Continue filling or click submit button",
        "check": "Continue or submit the form",
        "uncheck": "Continue or submit the form",
        "type": "Continue typing or press Enter to submit",
        "select": "Continue selecting or submit the form",
        "press": "Continue or take another action",
        "scroll": "Call snapshot() or continue scrolling",
        "hover": "Click or continue interacting",
        "screenshot": "Continue or close() when done",
        "back": "Continue browsing",
        "forward": "Continue browsing",
        "reload": "Call snapshot() to see updated page",
        "wait": "Continue after waiting",
        "get_text": "Use the text data for your task",
        "get_value": "Use the value data for your task",
        "is_checked": "Use the checked state for your task",
        "get_url": "Use the URL for your task",
        "keyboard_type": "Continue typing or press Enter",
        "close": "Task completed. Browser closed.",
        "fill_form": "Form filled. Click submit or close() when done.",
        "navigate_and_interact": "All actions completed. Call close() when done.",
    }

    # 注：D-3 修复 — ALLOWED_URL_SCHEMES 是死常量（仅在 docstring 中引用），
    #     实际 _validate_url 用字面值 ('http','https','file')，已删除。

    def __init__(self, workspace_root: str = None):
        self.workspace_root = workspace_root
        self._state: BrowserState = BrowserState.IDLE
        self._last_url: Optional[str] = None
        self._last_title: Optional[str] = None

        # Playwright 对象（懒加载）
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

        # 路由 handler 状态：_ensure_browser 成功注册 context.route 后置 True。
        # 防止 route 注册失败时 javascript:/vbscript: 等请求被静默放行（D-1 part 修复）。
        self._route_active: bool = False

        # 浏览器是否曾经成功 open 过任何页面（C-M1 修复）。
        # _ensure_page 在 _ever_opened 为 False 时拒绝静默启动浏览器。
        self._ever_opened: bool = False

        # @ref → selector 映射（每次 snapshot 后重建）
        self._ref_to_selector: Dict[str, str] = {}

        # 浏览器操作专用线程：单线程 ThreadPoolExecutor，所有 Playwright 操作
        # 都在这个线程里跑。设计要点：
        # 1. 即使调用方在 asyncio event loop 中（pytest-asyncio、生产 async 代码）
        #    Playwright sync API 也能用——因为 sync_playwright 检查的是当前线程
        # 2. 单线程确保所有操作顺序执行，避免并发问题
        # 3. browser_close 后会销毁 executor，下次 open 时重建，避免跨 session 的
        #    Playwright greenlet 污染
        self._executor: Optional[ThreadPoolExecutor] = None
        self._thread_lock = threading.Lock()
        self._browser_thread: Optional[threading.Thread] = None

    # data: 协议允许的图片 MIME 白名单（仅真正的图片，禁 SVG 等可执行脚本的格式）。
    # S-1 修复：data:image/svg+xml 在 iframe/embed 上下文中会执行脚本，必须拒绝。
    _ALLOWED_DATA_MIME_TYPES = frozenset({
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/gif",
        "image/webp",
    })

    # ==================== Playwright 生命周期管理 ====================

    def _ensure_playwright(self):
        """懒加载 Playwright 模块（延迟 import 加速启动）

        必须在专用线程中调用，因为 sync_playwright() 会检查当前线程的 event loop。
        """
        # 项目内可移植回退：未显式设置 PLAYWRIGHT_BROWSERS_PATH 时，自动
        # 指向 ./Extend-dependenc/playwright/（install.ps1 默认安装位置）。
        # 这样在 IDE、裸 agia.py、CI 子进程等 install 脚本未生效 env 的场景下，
        # browser_tools 也能找到 Chromium。
        # 优先级：已存在的 env > 本地项目缓存 > 默认（用户目录）。
        if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            local_cache = os.path.join(project_root, "Extend-dependenc", "playwright")
            if os.path.isdir(local_cache):
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = local_cache

        if self._playwright is None:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError as e:
                raise RuntimeError(
                    "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"
                ) from e
            self._playwright = sync_playwright().start()
        return self._playwright

    def _get_executor(self) -> ThreadPoolExecutor:
        """懒加载专用线程执行器（单线程，串行处理所有 Playwright 操作）"""
        if self._executor is None:
            with self._thread_lock:
                if self._executor is None:
                    self._executor = ThreadPoolExecutor(
                        max_workers=1,
                        thread_name_prefix="browser-tools"
                    )
        return self._executor

    def _is_in_browser_thread(self) -> bool:
        """检查当前是否已在专用浏览器线程中（避免向自己提交任务造成死锁）"""
        return (
            self._executor is not None
            and self._browser_thread is not None
            and threading.current_thread() is self._browser_thread
        )

    def _run_in_thread(self, func, *args, **kwargs):
        """在专用线程中运行 Playwright 操作。

        Playwright sync API 内部会创建 event loop。如果当前线程已经有
        正在运行的 event loop（如 pytest-asyncio、async 代码），sync_playwright()
        会拒绝启动并报错。统一在专用线程中运行可避免这种冲突。

        注：sync_playwright() 实际允许在已有 event loop 的线程中启动（它会
        检查线程级别的 greenlet 状态），所以本装饰器只需要把工作放到一个
        独立线程即可，无需关心调用方是 sync 还是 async。同步 .result() 在
        sync 路径下是必要的——async 路径由调用方用 asyncio.to_thread 包装。

        如果调用方已经在专用线程中（嵌套调用），则直接执行避免死锁。
        """
        if self._is_in_browser_thread():
            return func(*args, **kwargs)
        executor = self._get_executor()
        # 记录 worker 线程引用
        if self._browser_thread is None:
            def _capture_thread():
                self._browser_thread = threading.current_thread()
            executor.submit(_capture_thread).result()
        return executor.submit(func, *args, **kwargs).result()

    def _ensure_browser(self):
        """确保浏览器实例存在"""
        if self._browser is None:
            pw = self._ensure_playwright()
            # channel="chromium-headless-shell" 让 Playwright 选精简 headless binary；
            # 此路径仅服务于已经 headless=True 的会话（headless=False 由
            # browser_open 直接管理），不会出现 headful 冲突。
            self._browser = pw.chromium.launch(
                headless=True,
                channel="chromium-headless-shell",
            )
            self._context = self._browser.new_context()
            self._page = self._context.new_page()
            # 路由 handler 状态：注册成功置 True，注册失败置 False。
            # 后续 _check_state 会据此判定（避免 route 静默失效时放行 XSS 请求）。
            self._route_active = False

            # 拦截非允许 scheme 的请求（javascript:、data:、vbscript: 等）
            # 仅放行 http(s)、file://、about:blank 等常见 scheme
            allowed = {"http", "https", "file", "about", "chrome"}
            import re as _re
            # data: URL 解析为 "data:<mime>;...,<payload>"；从 URL 头部抽取 mime
            _data_mime_re = _re.compile(r"^data:([^;,]+)", _re.IGNORECASE)
            def _route_handler(route, request):
                try:
                    req_scheme = (route.request.url.split(":", 1)[0] or "").lower()
                    if req_scheme and req_scheme not in allowed:
                        # 拦截 javascript:/vbscript:/blob: 等危险 scheme
                        route.abort()
                        return
                    # data: 仅允许白名单内的图片 MIME（S-1 修复：明确拒 svg+xml）
                    if req_scheme == "data":
                        m = _data_mime_re.match(route.request.url)
                        mime = (m.group(1).lower() if m else "")
                        if mime not in self._ALLOWED_DATA_MIME_TYPES:
                            route.abort()
                            return
                    route.continue_()
                except Exception:
                    # 任何意外：保守放行（不影响页面加载）
                    try:
                        route.continue_()
                    except Exception:
                        pass
            try:
                self._context.route("**/*", _route_handler)
                self._route_active = True
            except Exception:
                # 注册失败：_route_active 保持 False，后续 _check_state 会阻断危险动作
                pass
        return self._page

    def _ensure_page(self):
        """确保有可用页面（用于 open 后的操作）。

        C-M1 修复：在 browser_open 成功之前不静默启动浏览器。
        IDLE 状态下若 _page 为 None，必须先调用 browser_open；CLOSED 永远不允许。
        """
        if self._state == BrowserState.CLOSED:
            return None
        if self._page is None:
            # 阻止"未 open 直接 interact"的静默启动 —— 这是 footgun
            if not self._ever_opened:
                return None
            try:
                self._ensure_browser()
            except Exception:
                return None
        return self._page

    def _shutdown(self):
        """关闭并清理 Playwright 资源（即使 close() 抛错也要清理状态）

        同时关闭 executor 线程，因为 Playwright 的 greenlet 状态与线程绑定，
        重复使用同一线程会触发 'Cannot switch to a different thread' 错误。
        下次调用时会自动创建新 executor（懒加载）。
        """
        import gc
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            finally:
                self._context = None
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            finally:
                self._browser = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            finally:
                self._playwright = None
        # 关闭 executor 线程，避免下一次 open 时 greenlet 状态污染
        if self._executor is not None:
            try:
                self._executor.shutdown(wait=True, cancel_futures=False)
            except Exception:
                pass
            finally:
                self._executor = None
                self._browser_thread = None
        # 强制 gc，清理可能持有的 greenlet 引用
        gc.collect()
        self._page = None
        self._ref_to_selector.clear()

    # ==================== 状态与响应辅助 ====================

    def _check_state(self, required_states: List[BrowserState] = None) -> bool:
        """检查状态，如果浏览器已关闭则不允许操作"""
        if self._state == BrowserState.CLOSED:
            return False
        if required_states and self._state not in required_states:
            return False
        return True

    # 由 _make_response 管理的保留字段。data 中同名键会被过滤，避免覆盖契约层。
    _RESERVED_RESPONSE_KEYS = frozenset({
        "success", "status", "action", "timestamp", "next_step", "error",
    })

    def _make_response(
        self,
        action: str,
        success: bool = True,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        update_state: Optional[BrowserState] = None
    ) -> Dict[str, Any]:
        """
        统一构建响应格式

        Reserved keys (success/status/action/timestamp/next_step/error) are
        always owned by this method — duplicates in `data` are filtered out
        to keep the response contract intact.

        Args:
            action: 执行的动作
            success: 是否成功
            data: 实际数据
            error: 错误信息
            update_state: 更新状态（可选）
        """
        response = {
            "success": success,
            "status": self._state.value if not update_state else update_state.value,
            "action": action,
            "timestamp": time.time(),
            "next_step": self.NEXT_STEP_HINTS.get(action, "Continue your task"),
        }

        if data:
            # 过滤保留键，避免 data 中的同名键覆盖契约层字段（D-2 修复）
            safe_data = {
                k: v for k, v in data.items()
                if k not in self._RESERVED_RESPONSE_KEYS
            }
            response.update(safe_data)

        if error:
            response["error"] = error

        if update_state:
            self._state = update_state

        return response

    # ==================== @ref 系统 ====================

    @staticmethod
    def _css_escape_attr_value(value: str) -> str:
        """CSS 属性选择器值转义。

        在 CSS attr 选择器用双引号包裹时，必须转义：
        - 反斜杠（CSS 字符串内的转义字符）
        - 双引号（结束 selector）
        - 换行/回车（破坏单行选择器语法）

        注：CSS 选择器字符串里 `]` 在双引号内不需要转义（仅当作为 `[attr=val]` 边界时），
        但换行必须去除。
        """
        if not value:
            return value or ""
        # 截断到 50 字符
        s = value[:50]
        # CSS 字符串转义顺序：先转 \\ 再转 "
        s = s.replace("\\", "\\\\").replace('"', '\\"')
        # 去除换行（CSS attr 选择器不允许）
        s = s.replace("\n", " ").replace("\r", " ")
        return s

    @staticmethod
    def _build_selector_for_element(elem) -> Optional[str]:
        """为元素构建稳定的 CSS 选择器（优先级：id > name > aria-label > placeholder > text）

        文本回退：当元素没有 id/name/aria-label/placeholder 时，使用 text= 前缀
        让 LLM 能通过 text 引用常见元素（如 `<button>Submit</button>`、`<a>Next</a>`）。
        text= 是 Playwright 的引擎扩展选择器，调用 _resolve_ref 时会原样传给 Playwright。
        """
        try:
            eid = elem.get_attribute("id")
            if eid and re.match(r"^[A-Za-z][A-Za-z0-9_-]*$", eid):
                return f"#{eid}"
        except Exception:
            pass
        try:
            name = elem.get_attribute("name")
            if name:
                safe = BrowserTools._css_escape_attr_value(name)
                return f'[name="{safe}"]'
        except Exception:
            pass
        try:
            aria = elem.get_attribute("aria-label")
            if aria:
                safe = BrowserTools._css_escape_attr_value(aria)
                return f'[aria-label="{safe}"]'
        except Exception:
            pass
        try:
            placeholder = elem.get_attribute("placeholder")
            if placeholder:
                safe = BrowserTools._css_escape_attr_value(placeholder)
                return f'[placeholder="{safe}"]'
        except Exception:
            pass
        # 文本回退：用元素自身的 inner_text 构造 text= 选择器
        # 仅在文本非空且较短时（≤50 字符）使用，避免歧义匹配
        try:
            text = (elem.inner_text() or "").strip()
            if text and len(text) <= 50 and "\n" not in text:
                safe = BrowserTools._css_escape_attr_value(text)
                return f'text="{safe}"'
        except Exception:
            pass
        return None

    def _resolve_ref(self, selector: str) -> str:
        """
        解析选择器：如果是 @eN 引用，转换为实际 selector。
        否则原样返回（支持 CSS selector、text=、xpath= 等）。
        """
        if not selector:
            return selector
        selector = selector.strip()
        if selector.startswith("@"):
            ref_key = selector[1:]  # e1, e2, ...
            if ref_key in self._ref_to_selector:
                return self._ref_to_selector[ref_key]
            # 找不到时抛出（由调用方捕获）
            raise ValueError(f"Unknown ref: {selector}. Call snapshot() first.")
        return selector

    def _build_snapshot(self, interactive_only: bool = True) -> Dict[str, Any]:
        """构建页面快照：交互元素 + ref 映射"""
        page = self._ensure_page()
        if page is None:
            return {"elements": [], "elements_count": 0, "text": ""}

        self._ref_to_selector.clear()

        elements: List[Dict[str, Any]] = []

        if interactive_only:
            # 收集可交互元素
            selectors = [
                ("a", "link"),
                ("button", "button"),
                ("input", "input"),
                ("textarea", "textarea"),
                ("select", "combobox"),
                ("[role='button']", "button"),
                ("[role='link']", "link"),
                ("[role='textbox']", "textbox"),
                ("[role='checkbox']", "checkbox"),
                ("[role='radio']", "radio"),
                ("[role='combobox']", "combobox"),
                ("[onclick]", "button"),
                ("[tabindex]", "generic"),
            ]
            seen_selectors = set()
            counter = 0
            for css, role in selectors:
                try:
                    handles = page.query_selector_all(css)
                except Exception:
                    continue
                for h in handles:
                    try:
                        # 跳过不可见元素
                        if not h.is_visible():
                            continue
                        selector = self._build_selector_for_element(h)
                        if not selector or selector in seen_selectors:
                            continue
                        seen_selectors.add(selector)

                        text = ""
                        try:
                            text = (h.inner_text() or "").strip()[:80]
                        except Exception:
                            try:
                                text = (h.get_attribute("value") or "").strip()[:80]
                            except Exception:
                                text = ""

                        counter += 1
                        ref_id = f"e{counter}"
                        self._ref_to_selector[ref_id] = selector
                        elements.append({
                            "ref": f"@{ref_id}",
                            "type": role,
                            "text": text,
                            "role": role,
                            "selector": selector,
                        })
                        # 限制最多 100 个元素防止 snapshot 过大
                        if counter >= 100:
                            break
                    except Exception:
                        continue
                if counter >= 100:
                    break

        # 全文快照（用于 LLM 理解页面上下文）
        try:
            body_text = page.inner_text("body", timeout=2000)
            if len(body_text) > 5000:
                body_text = body_text[:5000] + "..."
        except Exception:
            body_text = ""

        return {
            "elements": elements,
            "elements_count": len(elements),
            "text": body_text,
        }

    # ==================== 安全校验 ====================

    def _validate_url(self, url: str) -> Optional[str]:
        """验证 URL 协议和 file:// 路径安全。返回 None 表示通过，否则返回错误信息

        安全策略：
        - scheme 必须是 http/https/file 之一（D-3 修复：移除了死常量 ALLOWED_URL_SCHEMES）
        - file:// URL 要求显式提供 workspace_root，且目标路径必须在 workspace 内
          （防止默认实例读任意本地敏感文件，如 /etc/passwd、SSH key 等）
        """
        if not url:
            return "URL is empty"
        # D-7 修复：单次 urlparse，下面的 file:// 分支复用同一结果。
        from urllib.parse import urlparse, unquote
        try:
            parsed = urlparse(url)
        except Exception:
            return f"Invalid URL: {url[:50]}"
        if not parsed.scheme or parsed.scheme.lower() not in ('http', 'https', 'file'):
            return (
                f"Invalid URL scheme: '{parsed.scheme or '(empty)'}'. "
                f"Only http, https, file allowed. Got: {url[:50]}"
            )
        # http/https 直接放行；scheme 已校验，避免再次字符串比较
        if parsed.scheme.lower() in ('http', 'https'):
            return None
        # file://：硬性要求 workspace_root
        if not self.workspace_root:
            return (
                "file:// URLs require workspace_root to be set on BrowserTools. "
                "This prevents reading arbitrary local files (e.g. /etc/passwd, ~/.ssh/id_rsa) "
                "via the default-constructed BrowserTools instance."
            )
        # file:///C:/path → C:/path（规范化掉 Windows file URL 的前导斜杠）
        # urlparse 后 netloc 可能是空的（C: 在 Windows 上是 drive），path 是 /C:/path
        # 关键 bug：直接 os.path.realpath('/C:/path') 在 Windows 上会塌缩成错误路径。
        # 改用 urlparse + 去掉前导斜杠 + ntpath.normpath 处理
        try:
            # 复用上面的 parsed（D-7 修复）
            # 规范化 file path：去掉前导斜杠（file:///C:/path → C:/path）
            path_str = parsed.path or ""
            if os.name == "nt" and path_str.startswith("/") and len(path_str) > 2 and path_str[2] == ":":
                # Windows: "/C:/x" → "C:/x"（去掉开头的 /）
                path_str = path_str[1:]
            decoded = unquote(path_str)
            real_path = os.path.realpath(decoded)
            real_root = os.path.realpath(self.workspace_root)
            if ".." in path_str:
                return "Invalid file URL: path traversal not allowed."
            # 严格边界检查：real_path 必须在 real_root 内部
            # 防止 sibling directory bypass（/work 与 /work_evil）
            if not _is_within(real_path, real_root):
                return "Access denied: file outside workspace root."
        except Exception:
            return "Invalid file path."
        return None

    def _validate_screenshot_path(self, path: Optional[str]) -> Optional[str]:
        """验证截图路径安全。返回 None 表示通过，否则返回错误信息

        S-6 修复：拒绝 '.'  /  './'  /  尾斜杠等目录形式，
        必须明确是文件路径（避免误写入 workspace 根目录）。
        """
        if not path:
            return "Path cannot be empty"
        # 拒绝目录与纯点号形式
        if path in (".", "./", os.curdir) or path.endswith(("/", os.sep)):
            return "Invalid path: must be a file path, not a directory"
        if ".." in path:
            return "Invalid path: path traversal not allowed"
        if os.path.isabs(path):
            if not self.workspace_root:
                return "Absolute path not allowed without workspace_root"
            try:
                real_path = os.path.realpath(path)
                real_root = os.path.realpath(self.workspace_root)
                if not _is_within(real_path, real_root):
                    return "Access denied: path outside workspace root"
            except Exception:
                return "Invalid path"
        if path.startswith("/") and not path.startswith("./"):
            return "Invalid path: must be relative"
        return None

    # ==================== 浏览器控制 ====================

    @_browser_op
    def browser_open(self, url: str, session: str = None, headless: bool = False) -> Dict[str, Any]:
        """
        打开浏览器并导航到指定 URL

        Args:
            url: 目标 URL（仅允许 http://, https://, file://）
            session: 会话名（用于多会话隔离，未来扩展）
            headless: 是否无头模式（默认 False，可见 GUI 调试；
                     服务器/CI/容器环境可显式传 True）
        """
        # URL 校验
        err = self._validate_url(url)
        if err:
            return self._make_response("open", success=False, error=err)

        # 如果已关闭，重置状态
        if self._state == BrowserState.CLOSED:
            self._state = BrowserState.IDLE

        # 新的 URL → 旧的 @ref 已经失效（指向另一页的元素）
        # 立即清空，避免 LLM 误用旧 ref 操作新页上不存在的元素
        self._ref_to_selector.clear()

        try:
            # 启动 Playwright（首次调用会启动浏览器进程）
            pw = self._ensure_playwright()
            # 默认未触发 fallback（第二次 open 复用现有 browser 时，变量必须已定义）
            headless_fallback = False
            if self._browser is None:
                # headless=False 在无 display 环境（CI、容器、断开的 RDP）下
                # 可能挂起或失败——传 args + 友好的错误信息兜底
                # channel="chromium-headless-shell"：Playwright 按 headless 参数智能路由——
                # headless=True 用 headless_shell 二进制（启动 ~3x 快、内存省 ~60%），
                # headless=False 时自动 fallback 到完整 chromium.exe 以支持 GUI。
                launch_kwargs: Dict[str, Any] = {
                    "headless": headless,
                    "channel": "chromium-headless-shell",
                }
                if not headless:
                    # 可见模式下必备的容错开关
                    launch_kwargs["args"] = [
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ]
                try:
                    self._browser = pw.chromium.launch(**launch_kwargs)
                except Exception as launch_err:
                    # 兜底：可见模式失败时自动降级到 headless（常见于 CI/容器）
                    if not headless:
                        try:
                            self._browser = pw.chromium.launch(
                                headless=True,
                                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                            )
                            # 标记用户请求的是 headless，但实际 fallback 了
                            headless_fallback = True
                        except Exception:
                            self._shutdown()
                            raise launch_err
                    else:
                        self._shutdown()
                        raise
                self._context = self._browser.new_context()
                self._page = self._context.new_page()

            # 导航
            response = self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if response is None:
                return self._make_response(
                    "open", success=False,
                    error=f"Failed to navigate to {url}",
                    update_state=BrowserState.CLOSED,
                )

            self._last_url = self._page.url
            try:
                self._last_title = self._page.title()
            except Exception:
                self._last_title = ""

            return self._make_response(
                "open",
                success=True,
                data={
                    "title": self._last_title,
                    "url": self._last_url,
                    "headless": headless if not headless_fallback else True,
                    "headless_fallback": headless_fallback,
                    "message": f"Opened {url} - Title: {self._last_title}"
                              + (" (fallback to headless)" if headless_fallback else ""),
                },
                update_state=BrowserState.OPENED,
            )
            # 标记已成功 open 一次；close/shutdown 后由 browser_close 重置。
            # 用于 _ensure_page 拒绝静默自动启动（C-M1 修复）。
            self._ever_opened = True
        except Exception as e:
            self._shutdown()
            return self._make_response(
                "open", success=False,
                error=f"Failed to open browser: {e}",
                update_state=BrowserState.CLOSED,
            )

    @_browser_op
    def browser_snapshot(self, interactive: bool = True) -> Dict[str, Any]:
        """获取页面元素快照"""
        if not self._check_state():
            return self._make_response(
                "snapshot", success=False,
                error="Browser is closed. Call open() first."
            )

        page = self._ensure_page()
        if page is None:
            return self._make_response(
                "snapshot", success=False,
                error="Browser not available. Call open() first."
            )

        try:
            snapshot = self._build_snapshot(interactive_only=interactive)
            return self._make_response(
                "snapshot",
                success=True,
                data=snapshot,
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("snapshot", success=False, error=str(e))

    @_browser_op
    def browser_click(self, selector: str) -> Dict[str, Any]:
        """点击页面元素（支持 @ref 或 CSS selector）"""
        if not self._check_state():
            return self._make_response("click", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("click", success=False, error="Browser not available.")

        try:
            real_selector = self._resolve_ref(selector)
            page.click(real_selector, timeout=10000)
            self._last_url = page.url
            return self._make_response(
                "click", success=True,
                data={"url": self._last_url, "selector": real_selector},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("click", success=False, error=str(e))

    @_browser_op
    def browser_fill(self, selector: str, value: str) -> Dict[str, Any]:
        """填写表单字段（清空后填入）"""
        if not self._check_state():
            return self._make_response("fill", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("fill", success=False, error="Browser not available.")

        try:
            real_selector = self._resolve_ref(selector)
            page.fill(real_selector, value, timeout=10000)
            return self._make_response(
                "fill", success=True,
                data={"selector": real_selector, "value": value, "message": f"Filled {real_selector}"},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("fill", success=False, error=str(e))

    @_browser_op
    def browser_type(self, selector: str, value: str) -> Dict[str, Any]:
        """在元素上输入文本（不清空原有内容，模拟键盘输入）"""
        if not self._check_state():
            return self._make_response("type", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("type", success=False, error="Browser not available.")

        try:
            real_selector = self._resolve_ref(selector)
            page.type(real_selector, value, timeout=10000)
            return self._make_response(
                "type", success=True,
                data={"selector": real_selector, "value": value},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("type", success=False, error=str(e))

    @_browser_op
    def browser_screenshot(self, path: str = None, full: bool = False, annotate: bool = False) -> Dict[str, Any]:
        """截图并保存到指定路径

        Args:
            path: 截图保存路径（相对 workspace_root，不允许 .. 和绝对路径）
            full: 是否截取整个页面（默认仅可视区域）
            annotate: 是否在元素上标注 ref（占位实现，未来扩展）
        """
        if not self._check_state():
            return self._make_response("screenshot", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("screenshot", success=False, error="Browser not available.")

        # 路径校验
        err = self._validate_screenshot_path(path)
        if err:
            return self._make_response("screenshot", success=False, error=err)

        try:
            # 解析为绝对路径
            abs_path = path
            if self.workspace_root and not os.path.isabs(path):
                abs_path = os.path.join(self.workspace_root, path)
            os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)

            page.screenshot(path=abs_path, full_page=full)
            return self._make_response(
                "screenshot", success=True,
                data={"path": abs_path},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("screenshot", success=False, error=str(e))

    @_browser_op
    def browser_select(self, selector: str, value: str) -> Dict[str, Any]:
        """选择下拉框选项"""
        if not self._check_state():
            return self._make_response("select", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("select", success=False, error="Browser not available.")

        try:
            real_selector = self._resolve_ref(selector)
            page.select_option(real_selector, value, timeout=10000)
            return self._make_response(
                "select", success=True,
                data={"selector": real_selector, "value": value},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("select", success=False, error=str(e))

    @_browser_op
    def browser_check(self, selector: str) -> Dict[str, Any]:
        """勾选复选框/单选框"""
        if not self._check_state():
            return self._make_response("check", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("check", success=False, error="Browser not available.")

        try:
            real_selector = self._resolve_ref(selector)
            page.check(real_selector, timeout=10000)
            return self._make_response(
                "check", success=True,
                data={"selector": real_selector},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("check", success=False, error=str(e))

    @_browser_op
    def browser_uncheck(self, selector: str) -> Dict[str, Any]:
        """取消勾选复选框"""
        if not self._check_state():
            return self._make_response("uncheck", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("uncheck", success=False, error="Browser not available.")

        try:
            real_selector = self._resolve_ref(selector)
            page.uncheck(real_selector, timeout=10000)
            return self._make_response(
                "uncheck", success=True,
                data={"selector": real_selector},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("uncheck", success=False, error=str(e))

    @_browser_op
    def browser_press(self, key: str, selector: str = None) -> Dict[str, Any]:
        """按键（可指定元素或全局按键）

        Args:
            key: 按键名，如 'Enter', 'Escape', 'Tab', 'ArrowDown'
            selector: 目标元素（可选），不指定则在当前焦点元素按键
        """
        if not self._check_state():
            return self._make_response("press", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("press", success=False, error="Browser not available.")

        try:
            if selector:
                real_selector = self._resolve_ref(selector)
                page.press(real_selector, key, timeout=10000)
            else:
                page.keyboard.press(key)
            return self._make_response(
                "press", success=True,
                data={"key": key, "selector": selector},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("press", success=False, error=str(e))

    @_browser_op
    def browser_close(self) -> Dict[str, Any]:
        """关闭浏览器并清理资源。

        关闭后 BrowserTools 实例回到 IDLE 状态，可通过再次调用 browser_open() 重用。
        """
        try:
            self._shutdown()
            self._state = BrowserState.CLOSED
            # 关闭后重置 ever_opened，下一次 open 之前 interact 方法应返回 None
            self._ever_opened = False
            return self._make_response(
                "close", success=True,
                data={
                    "task_completed": True,
                    "message": "Browser closed. Task completed.",
                    "output": "Browser automation task finished successfully.",
                },
                update_state=BrowserState.CLOSED,
            )
        except Exception as e:
            # 即使关闭失败也标记为已关闭
            self._state = BrowserState.CLOSED
            return self._make_response("close", success=False, error=str(e))

    @_browser_op
    def browser_back(self) -> Dict[str, Any]:
        """后退"""
        if not self._check_state():
            return self._make_response("back", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("back", success=False, error="Browser not available.")

        try:
            page.go_back()
            self._last_url = page.url
            return self._make_response(
                "back", success=True,
                data={"url": self._last_url},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("back", success=False, error=str(e))

    @_browser_op
    def browser_forward(self) -> Dict[str, Any]:
        """前进"""
        if not self._check_state():
            return self._make_response("forward", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("forward", success=False, error="Browser not available.")

        try:
            page.go_forward()
            self._last_url = page.url
            return self._make_response(
                "forward", success=True,
                data={"url": self._last_url},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("forward", success=False, error=str(e))

    @_browser_op
    def browser_reload(self) -> Dict[str, Any]:
        """刷新页面"""
        if not self._check_state():
            return self._make_response("reload", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("reload", success=False, error="Browser not available.")

        try:
            page.reload()
            self._last_url = page.url
            return self._make_response(
                "reload", success=True,
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("reload", success=False, error=str(e))

    @_browser_op
    def browser_scroll(self, direction: str = "down", pixels: int = 500) -> Dict[str, Any]:
        """滚动页面

        Args:
            direction: 滚动方向，必须是 up/down/left/right 之一
            pixels: 滚动像素（1-10000）
        """
        if not self._check_state():
            return self._make_response("scroll", success=False, error="Browser is closed. Call open() first.")

        # 参数校验
        valid_directions = {"up", "down", "left", "right"}
        if direction not in valid_directions:
            return self._make_response(
                "scroll", success=False,
                error=f"Invalid direction: {direction}. Must be one of: {', '.join(valid_directions)}"
            )
        # 拒绝 bool（避免 True/False 被当作 1/0）；接受 int 与 float，但 float 截断为 int
        if isinstance(pixels, bool) or not isinstance(pixels, (int, float)):
            return self._make_response("scroll", success=False, error=f"Invalid pixels: {pixels}. Must be positive number.")
        if pixels <= 0:
            return self._make_response("scroll", success=False, error=f"Invalid pixels: {pixels}. Must be positive number.")
        if pixels > 10000:
            return self._make_response("scroll", success=False, error=f"Invalid pixels: {pixels}. Exceeds max 10000.")
        pixels = int(pixels)  # 统一为 int

        page = self._ensure_page()
        if page is None:
            return self._make_response("scroll", success=False, error="Browser not available.")

        try:
            delta_map = {
                "up": (0, -pixels),
                "down": (0, pixels),
                "left": (-pixels, 0),
                "right": (pixels, 0),
            }
            dx, dy = delta_map[direction]
            page.mouse.wheel(dx, dy)
            return self._make_response(
                "scroll", success=True,
                data={"direction": direction, "pixels": pixels},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("scroll", success=False, error=str(e))

    @_browser_op
    def browser_wait(self, wait_for: str) -> Dict[str, Any]:
        """等待

        Args:
            wait_for: 等待时间（毫秒，整数字符串）或 CSS selector
        """
        if not self._check_state():
            return self._make_response("wait", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("wait", success=False, error="Browser not available.")

        try:
            # 接受数字或字符串：int/float 转毫秒；其他按 selector
            if isinstance(wait_for, (int, float)) and not isinstance(wait_for, bool):
                # 直接传数字 → 直接当作毫秒
                page.wait_for_timeout(int(wait_for))
            else:
                wait_str = str(wait_for).strip() if wait_for is not None else ""
                if wait_str.isdigit():
                    page.wait_for_timeout(int(wait_str))
                else:
                    # 否则按 selector 等待元素出现
                    page.wait_for_selector(wait_str, timeout=30000)
            return self._make_response(
                "wait", success=True,
                data={"wait_for": wait_for},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("wait", success=False, error=str(e))

    @_browser_op
    def browser_hover(self, selector: str) -> Dict[str, Any]:
        """悬停"""
        if not self._check_state():
            return self._make_response("hover", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("hover", success=False, error="Browser not available.")

        try:
            real_selector = self._resolve_ref(selector)
            page.hover(real_selector, timeout=10000)
            return self._make_response(
                "hover", success=True,
                data={"selector": real_selector},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("hover", success=False, error=str(e))

    @_browser_op
    def browser_get_text(self, selector: str = None) -> Dict[str, Any]:
        """获取文本内容（不指定 selector 则获取 title）"""
        if not self._check_state():
            return self._make_response("get_text", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("get_text", success=False, error="Browser not available.")

        try:
            if selector:
                real_selector = self._resolve_ref(selector)
                text = page.inner_text(real_selector, timeout=10000)
            else:
                text = page.title()
            return self._make_response(
                "get_text", success=True,
                data={"text": text},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("get_text", success=False, error=str(e))

    @_browser_op
    def browser_get_value(self, selector: str) -> Dict[str, Any]:
        """获取输入框/下拉框的当前 value（与 browser_get_text 不同，get_value 读 input.value）"""
        if not self._check_state():
            return self._make_response("get_value", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("get_value", success=False, error="Browser not available.")

        try:
            real_selector = self._resolve_ref(selector)
            value = page.input_value(real_selector, timeout=10000)
            return self._make_response(
                "get_value", success=True,
                data={"value": value, "selector": real_selector},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("get_value", success=False, error=str(e))

    @_browser_op
    def browser_is_checked(self, selector: str) -> Dict[str, Any]:
        """获取复选框/单选框的选中状态"""
        if not self._check_state():
            return self._make_response("is_checked", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("is_checked", success=False, error="Browser not available.")

        try:
            real_selector = self._resolve_ref(selector)
            checked = page.is_checked(real_selector, timeout=10000)
            return self._make_response(
                "is_checked", success=True,
                data={"checked": checked, "selector": real_selector},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("is_checked", success=False, error=str(e))

    @_browser_op
    def browser_get_url(self) -> Dict[str, Any]:
        """获取当前 URL"""
        if not self._check_state():
            return self._make_response("get_url", success=False, error="Browser is closed. Call open() first.")

        page = self._ensure_page()
        if page is None:
            return self._make_response("get_url", success=False, error="Browser not available.")

        try:
            url = page.url
            return self._make_response(
                "get_url", success=True,
                data={"url": url},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("get_url", success=False, error=str(e))

    @_browser_op
    def browser_keyboard_type(self, text: str) -> Dict[str, Any]:
        """键盘输入（无需选择器，向当前焦点输入）

        Args:
            text: 输入文本（最大 10000 字符）
        """
        if not self._check_state():
            return self._make_response("keyboard_type", success=False, error="Browser is closed. Call open() first.")

        if len(text) > 10000:
            return self._make_response(
                "keyboard_type", success=False,
                error=f"Text too long: {len(text)} chars (max: 10000)"
            )

        page = self._ensure_page()
        if page is None:
            return self._make_response("keyboard_type", success=False, error="Browser not available.")

        try:
            page.keyboard.type(text)
            return self._make_response(
                "keyboard_type", success=True,
                data={"text": text},
                update_state=BrowserState.BROWSING,
            )
        except Exception as e:
            return self._make_response("keyboard_type", success=False, error=str(e))

    # ==================== 便捷方法 ====================

    @_browser_op
    def browser_navigate_and_interact(self, url: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """导航并执行一系列交互操作

        Args:
            url: 目标 URL
            actions: 操作序列，每项包含 type/selector/value 等
        """
        # 先打开
        if self._state == BrowserState.CLOSED:
            return self._make_response(
                "navigate_and_interact", success=False,
                error="Browser is closed. Call browser_open first."
            )

        open_result = self.browser_open(url)
        if not open_result.get("success"):
            return open_result

        # 依次执行动作
        for action in actions:
            action_type = action.get("type")
            selector = action.get("selector")
            value = action.get("value")

            try:
                if action_type == "click":
                    result = self.browser_click(selector)
                elif action_type == "fill":
                    result = self.browser_fill(selector, value)
                elif action_type == "type":
                    result = self.browser_type(selector, value)
                elif action_type == "select":
                    result = self.browser_select(selector, value)
                elif action_type == "check":
                    result = self.browser_check(selector)
                elif action_type == "uncheck":
                    result = self.browser_uncheck(selector)
                elif action_type == "press":
                    # press: value 是按键名，selector 可选
                    result = self.browser_press(str(value) if value else "", selector)
                elif action_type == "wait":
                    seconds = action.get("seconds", 1)
                    result = self.browser_wait(str(int(seconds * 1000)))
                elif action_type == "scroll":
                    result = self.browser_scroll(action.get("direction", "down"), action.get("pixels", 500))
                elif action_type == "hover":
                    result = self.browser_hover(selector)
                else:
                    continue

                if not result.get("success"):
                    return self._make_response(
                        "navigate_and_interact",
                        success=False,
                        error=f"Action '{action_type}' failed: {result.get('error', 'unknown error')}"
                    )
            except Exception as e:
                return self._make_response(
                    "navigate_and_interact",
                    success=False,
                    error=f"Action '{action_type}' exception: {str(e)}"
                )

        return self.browser_snapshot()

    @_browser_op
    def browser_fill_form(self, data: Dict[str, str], submit_selector: str = None) -> Dict[str, Any]:
        """填写表单并可选提交

        Args:
            data: {field_name: value} 或 {selector: value}
            submit_selector: 提交按钮选择器（可选）
        """
        if not self._check_state():
            return self._make_response("fill_form", success=False, error="Browser is closed. Call open() first.")

        for key, value in data.items():
            # 兼容两种 key 形式：CSS selector 或 name 属性
            if not key.startswith("@") and not key.startswith("["):
                selector = f'[name="{key}"]'
            else:
                selector = key
            result = self.browser_fill(selector, value)
            if not result.get("success"):
                return result

        if submit_selector:
            click_result = self.browser_click(submit_selector)
            if not click_result.get("success"):
                return click_result

        return self._make_response(
            "fill_form", success=True,
            data={"fields_filled": len(data), "submitted": submit_selector is not None},
            update_state=BrowserState.BROWSING,
        )

    # ==================== 统一入口 ====================

    @_browser_op
    def browser_automation(self, action: str = None, **kwargs) -> Dict[str, Any]:
        """
        统一的浏览器自动化入口（LLM 工具调用接口）
        根据 action 参数分发到对应的方法。
        """
        if not action:
            return {
                "success": True,
                "available_actions": list(self.NEXT_STEP_HINTS.keys()),
                "usage": "browser_automation(action='action_name', **params)",
                "hint": "Required workflow: open → snapshot → interact → close"
            }

        # 显式必填参数校验：分发前先报告，不依赖底层方法的远端报错
        required_params = {
            "open": ["url"],
            "click": ["selector"],
            "fill": ["selector", "value"],
            "type": ["selector", "value"],
            "check": ["selector"],
            "uncheck": ["selector"],
            "press": [],  # key 与 value 互为别名（在 action_map 中合并），不强制
            "select": ["selector", "value"],
            "hover": ["selector"],
            "scroll": [],  # 都有默认值，仅校验类型在 action_map 中
            "screenshot": ["path"],
            "wait": [],  # wait_for 与 value 互为别名
            "get_text": [],  # selector 可选
            "get_value": ["selector"],
            "is_checked": ["selector"],
            "keyboard_type": ["value"],
            "navigate_and_interact": ["url", "actions"],
            "fill_form": ["data"],
        }
        required = required_params.get(action, [])
        missing = []
        for p in required:
            if not kwargs.get(p):
                missing.append(p)
        # press: 至少需要 key 或 value 之一
        if action == "press":
            if not kwargs.get("key") and not kwargs.get("value"):
                missing.append("key (or value)")
        # wait: 至少需要 wait_for 或 value 之一
        if action == "wait":
            if not kwargs.get("wait_for") and not kwargs.get("value"):
                missing.append("wait_for (or value)")
        if missing:
            return self._make_response(
                action, success=False,
                error=f"Missing required parameter(s) for '{action}': {', '.join(missing)}"
            )

        action_map = {
            "open": lambda: self.browser_open(
                url=kwargs.get("url", ""),
                session=kwargs.get("session"),
                headless=kwargs.get("headless", False)
            ),
            "snapshot": lambda: self.browser_snapshot(
                interactive=kwargs.get("interactive", True)
            ),
            "click": lambda: self.browser_click(
                selector=kwargs.get("selector", "")
            ),
            "fill": lambda: self.browser_fill(
                selector=kwargs.get("selector", ""),
                value=kwargs.get("value", "")
            ),
            "type": lambda: self.browser_type(
                selector=kwargs.get("selector", ""),
                value=kwargs.get("value", "")
            ),
            "check": lambda: self.browser_check(
                selector=kwargs.get("selector", "")
            ),
            "uncheck": lambda: self.browser_uncheck(
                selector=kwargs.get("selector", "")
            ),
            "press": lambda: self.browser_press(
                key=kwargs.get("key", kwargs.get("value", "")),
                selector=kwargs.get("selector")
            ),
            "screenshot": lambda: self.browser_screenshot(
                path=kwargs.get("path"),
                full=kwargs.get("full", False),
                annotate=kwargs.get("annotate", False)
            ),
            "scroll": lambda: self.browser_scroll(
                direction=kwargs.get("direction", "down"),
                pixels=kwargs.get("pixels", 500)
            ),
            "back": lambda: self.browser_back(),
            "forward": lambda: self.browser_forward(),
            "reload": lambda: self.browser_reload(),
            "close": lambda: self.browser_close(),
            "hover": lambda: self.browser_hover(
                selector=kwargs.get("selector", "")
            ),
            "wait": lambda: self.browser_wait(
                wait_for=kwargs.get("wait_for", kwargs.get("value", "1000"))
            ),
            "select": lambda: self.browser_select(
                selector=kwargs.get("selector", ""),
                value=kwargs.get("value", "")
            ),
            "get_text": lambda: self.browser_get_text(
                selector=kwargs.get("selector")
            ),
            "get_value": lambda: self.browser_get_value(
                selector=kwargs.get("selector", "")
            ),
            "is_checked": lambda: self.browser_is_checked(
                selector=kwargs.get("selector", "")
            ),
            "get_url": lambda: self.browser_get_url(),
            "keyboard_type": lambda: self.browser_keyboard_type(
                text=kwargs.get("value", "")
            ),
            "navigate_and_interact": lambda: self.browser_navigate_and_interact(
                url=kwargs.get("url", ""),
                actions=kwargs.get("actions", [])
            ),
            "fill_form": lambda: self.browser_fill_form(
                data=kwargs.get("data", {}),
                submit_selector=kwargs.get("submit_selector")
            ),
        }

        if action in action_map:
            try:
                return action_map[action]()
            except Exception as e:
                return self._make_response(action, success=False, error=str(e))
        else:
            return self._make_response(
                action, success=False,
                error=f"Unknown action: {action}",
            )