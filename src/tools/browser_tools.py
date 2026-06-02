#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Browser Tools - 基于 agent-browser 的浏览器控制工具
====================================================

提供浏览器控制能力：导航、截图、表单填写、元素交互等。
底层使用 agent-browser CLI 实现高性能浏览器自动化。

设计原则：
1. 统一返回格式（所有方法返回相同的结构）
2. 状态机管理
3. next_step 提示引导 LLM
4. 错误恢复机制
"""

import json
import os
import re
import subprocess
import urllib.parse
from typing import Dict, Any, List, Optional
from enum import Enum
import time

from .print_system import print_current


class BrowserState(Enum):
    """浏览器状态"""
    IDLE = "idle"           # 未启动
    OPENED = "opened"       # 已打开页面
    BROWSING = "browsing"    # 正在交互
    CLOSED = "closed"        # 已关闭


class BrowserTools:
    """
    浏览器控制工具类
    
    统一返回格式：
    {
        "success": bool,           # 操作是否成功
        "status": str,              # 当前状态
        "action": str,              # 执行的动作
        "timestamp": float,        # 时间戳
        "next_step": str,          # 下一步建议
        "data": {...},              # 实际数据（可选）
        "error": str,               # 错误信息（可选）
    }
    """
    
    # 动作到下一个动作的映射
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
        "get_url": "Use the URL for your task",
        "keyboard_type": "Continue typing or press Enter",
        "close": "Task completed. Browser closed.",
        "fill_form": "Form filled. Click submit or close() when done.",
        "navigate_and_interact": "All actions completed. Call close() when done.",
    }
    
    def __init__(self, workspace_root: str = None):
        self.workspace_root = workspace_root
        self._agent_browser_available: Optional[bool] = None
        self._browser_cmd: Optional[str] = None
        self._session_name: Optional[str] = None
        self._state: BrowserState = BrowserState.IDLE
        self._last_url: Optional[str] = None
        self._last_title: Optional[str] = None
    
    def _is_agent_browser_available(self) -> bool:
        """检测 agent-browser 是否可用"""
        if self._agent_browser_available is not None:
            return self._agent_browser_available
        
        # 只检测 PATH 中的命令，不硬编码用户路径
        possible_paths = [
            "agent-browser",
        ]
        
        for cmd_path in possible_paths:
            try:
                result = subprocess.run(
                    [cmd_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self._agent_browser_available = True
                    self._browser_cmd = cmd_path
                    version = result.stdout.strip().split('\n')[0] if result.stdout else "unknown"
                    print_current(f"[BrowserTools] agent-browser v{version} loaded")
                    return True
            except Exception:
                continue
        
        self._agent_browser_available = False
        print_current(f"[BrowserTools] agent-browser not available")
        return False
    
    def _validate_path(self, path: str) -> bool:
        """验证路径安全性，防止 Path Traversal"""
        if not path:
            return False  # 【修复】空路径应拒绝，不允许写入根目录
        # 拒绝包含 .. 的路径（防止目录遍历）
        if ".." in path:
            return False
        # 拒绝绝对路径（无论是 Unix 还是 Windows 格式）
        if os.path.isabs(path):
            # 如果有 workspace_root，验证路径在允许目录内
            if self.workspace_root:
                try:
                    real_path = os.path.realpath(path)
                    real_root = os.path.realpath(self.workspace_root)
                    return real_path.startswith(real_root)
                except Exception:
                    return False
            return False
        # 拒绝看起来像 Unix 绝对路径的模式（以 / 开头但不是相对路径）
        if path.startswith('/') and not path.startswith('./'):
            return False
        return True
    
    def _run_browser_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """执行 agent-browser 命令"""
        cmd = [self._browser_cmd or "agent-browser"] + args + ["--json"]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                shell=False  # 【修复】显式设置 shell=False 防止命令注入
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                stdout, stderr = "", ""
                return {"success": False, "error": "Command timed out", "_raw": stdout}
            if process.returncode == 0:
                try:
                    result = json.loads(stdout)
                    # 【修复】保留 success 字段，不丢失响应状态
                    if "data" in result:
                        return {"success": result.get("success", True), **result["data"]}
                    return result
                except json.JSONDecodeError:
                    return {"success": False, "error": f"Invalid JSON response: {stdout[:200] if stdout else 'empty'}"}
            else:
                return {"success": False, "error": stderr or "Command failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    def _check_command_failure(self, result: Dict[str, Any], action: str) -> Optional[Dict[str, Any]]:
        """检查命令执行结果，如果失败则返回错误响应"""
        if not result.get("success", True):
            return self._make_response(
                action, success=False,
                error=result.get("error", "Command failed")
            )
        return None
    def _check_state(self, required_states: List[BrowserState] = None) -> bool:
        """检查状态，如果浏览器已关闭则不允许操作"""
        if self._state == BrowserState.CLOSED:
            return False
        if required_states and self._state not in required_states:
            return False
        return True
    
    def _get_common_args(self) -> List[str]:
        args = []
        if self._session_name:
            args.extend(["--session", self._session_name])
        return args
    
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
        
        Args:
            action: 执行的动作
            success: 是否成功
            data: 实际数据
            error: 错误信息
            update_state: 更新状态（可选）
        
        Returns:
            统一的响应字典
        """
        response = {
            "success": success,
            "status": self._state.value if not update_state else update_state.value,
            "action": action,
            "timestamp": time.time(),
            "next_step": self.NEXT_STEP_HINTS.get(action, "Continue your task"),
        }
        
        if data:
            response.update(data)
        
        if error:
            response["error"] = error
        
        # 更新状态
        if update_state:
            self._state = update_state
        
        return response
    
    # ==================== 浏览器控制 ====================
    
    def browser_open(self, url: str, session: str = None, headless: bool = False) -> Dict[str, Any]:
        """打开浏览器并导航到指定 URL"""
        if not self._is_agent_browser_available():
            return self._make_response(
                "open", success=False,
                error="agent-browser not available. Install: npm install -g agent-browser"
            )
        # 【修复】URL 格式验证，防止 javascript: 和 data: URL
        if not url or not url.startswith(("http://", "https://", "file://")):
            return self._make_response(
                "open", success=False,
                error=f"Invalid URL format: {url[:50] if url else 'empty'}. Only http://, https://, file:// allowed."
            )
        # 【修复】file:// 协议路径安全校验
        if url.startswith("file://"):
            # 提取文件路径（去掉 file:// 前缀）
            file_path = url[7:]  # len("file://") == 7
            # 检查路径遍历
            if ".." in file_path:
                return self._make_response(
                    "open", success=False,
                    error="Invalid file URL: path traversal not allowed."
                )
            # 如果有 workspace_root，验证路径在允许目录内
            if self.workspace_root:
                try:
                    import urllib.parse
                    decoded_path = urllib.parse.unquote(file_path)
                    real_path = os.path.realpath(decoded_path) if decoded_path else ""
                    real_root = os.path.realpath(self.workspace_root)
                    if real_path and not real_path.startswith(real_root):
                        return self._make_response(
                            "open", success=False,
                            error=f"Access denied: file outside workspace root."
                        )
                except Exception:
                    return self._make_response(
                        "open", success=False,
                        error="Invalid file path."
                    )
        # 如果浏览器已关闭，先重置状态
        if self._state == BrowserState.CLOSED:
            self._state = BrowserState.IDLE
        args = ["open", url]
        if session:
            args.extend(["--session", session])
            self._session_name = session
        if not headless:
            args.append("--headed")
        
        result = self._run_browser_command(args)
        
        # 【修复】不要强制覆盖 success，只在真正成功时处理
        if not result.get("success", True):
            return self._make_response(
                "open",
                success=False,
                error=result.get("error", "Failed to open browser"),
                update_state=BrowserState.CLOSED
            )
        
        title = result.get("title", result.get("data", {}).get("title", ""))
        current_url = result.get("url", result.get("data", {}).get("url", url))
        
        self._last_url = current_url
        self._last_title = title
        
        return self._make_response(
            "open",
            success=True,
            data={
                "title": title,
                "url": current_url,
                "message": f"Opened {url} - Title: {title}",
            },
            update_state=BrowserState.OPENED
        )
    
    def browser_snapshot(self, interactive: bool = True) -> Dict[str, Any]:
        """获取页面元素快照"""
        if not self._check_state():
            return self._make_response(
                "snapshot", success=False,
                error="Browser is closed. Call open() first."
            )
        
        if not self._is_agent_browser_available():
            return self._make_response(
                "snapshot", success=False,
                error="agent-browser not available"
            )
        
        args = ["snapshot"]
        if interactive:
            args.append("-i")
        args.extend(self._get_common_args())
        result = self._run_browser_command(args)
        # 【修复 CRIT-1】检查命令失败
        if error_resp := self._check_command_failure(result, "snapshot"):
            return error_resp
        # 解析 refs 字段转换为 elements 格式
        elements = []
        refs = result.get("refs") or {}
        for ref_id, ref_data in refs.items():
            elements.append({
                "ref": f"@{ref_id}",
                "type": ref_data.get("role", "unknown"),
                "text": ref_data.get("name", ""),
                "role": ref_data.get("role", "")
            })
        snapshot_text = result.get("snapshot", result.get("output", ""))
        return self._make_response(
            "snapshot",
            success=True,
            data={
                "elements": elements,
                "elements_count": len(elements),
                "text": snapshot_text,
            },
            update_state=BrowserState.BROWSING
        )
    
    def browser_click(self, selector: str) -> Dict[str, Any]:
        """点击页面元素"""
        if not self._check_state():
            return self._make_response(
                "click", success=False,
                error="Browser is closed. Call open() first."
            )
        
        if not self._is_agent_browser_available():
            return self._make_response(
                "click", success=False,
                error="agent-browser not available"
            )
        
        args = ["click", selector]
        args.extend(self._get_common_args())
        
        result = self._run_browser_command(args)
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "click"):
            return error_resp
        url = result.get("url", self._last_url)
        return self._make_response(
            "click",
            success=True,
            data={"url": url, "selector": selector},
            update_state=BrowserState.BROWSING
        )
    
    def browser_fill(self, selector: str, value: str) -> Dict[str, Any]:
        """填写表单字段"""
        if not self._check_state():
            return self._make_response(
                "fill", success=False,
                error="Browser is closed. Call open() first."
            )
        
        if not self._is_agent_browser_available():
            return self._make_response(
                "fill", success=False,
                error="agent-browser not available"
            )
        
        args = ["fill", selector, value]
        args.extend(self._get_common_args())
        
        result = self._run_browser_command(args)
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "fill"):
            return error_resp
        return self._make_response(
            "fill",
            success=True,
            data={"selector": selector, "value": value, "message": f"Filled {selector}"},
            update_state=BrowserState.BROWSING
        )
    
    def browser_type(self, selector: str, value: str) -> Dict[str, Any]:
        """输入文本到元素"""
        if not self._check_state():
            return self._make_response(
                "type", success=False,
                error="Browser is closed. Call open() first."
            )
        
        if not self._is_agent_browser_available():
            return self._make_response(
                "type", success=False,
                error="agent-browser not available"
            )
        
        args = ["type", selector, value]
        args.extend(self._get_common_args())
        
        result = self._run_browser_command(args)
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "type"):
            return error_resp
        return self._make_response(
            "type",
            success=True,
            data={"selector": selector, "value": value},
            update_state=BrowserState.BROWSING
        )
    
    def browser_screenshot(self, path: str = None, full: bool = False, annotate: bool = False) -> Dict[str, Any]:
        """截图"""
        if not self._check_state():
            return self._make_response(
                "screenshot", success=False,
                error="Browser is closed. Call open() first."
            )
        
        if not self._is_agent_browser_available():
            return self._make_response(
                "screenshot", success=False,
                error="agent-browser not available"
            )
        
        # 【修复】路径安全校验 - 无论 path 是否为空都需要验证
        if not self._validate_path(path):
            return self._make_response(
                "screenshot", success=False,
                error="Invalid path: path traversal not allowed" if path else "Path cannot be empty"
            )
        
        args = ["screenshot"]
        if path:
            args.append(path)
        if full:
            args.append("--full")
        if annotate:
            args.append("--annotate")
        args.extend(self._get_common_args())
        
        result = self._run_browser_command(args)
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "screenshot"):
            return error_resp
        return self._make_response(
            "screenshot",
            success=True,
            data={"path": result.get("path", path)},
            update_state=BrowserState.BROWSING
        )
    
    def browser_select(self, selector: str, value: str) -> Dict[str, Any]:
        """选择下拉选项"""
        if not self._check_state():
            return self._make_response(
                "select", success=False,
                error="Browser is closed. Call open() first."
            )
        
        if not self._is_agent_browser_available():
            return self._make_response(
                "select", success=False,
                error="agent-browser not available"
            )
        
        args = ["select", selector, value]
        args.extend(self._get_common_args())
        
        result = self._run_browser_command(args)
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "select"):
            return error_resp
        return self._make_response(
            "select",
            success=True,
            data={"selector": selector, "value": value},
            update_state=BrowserState.BROWSING
        )
    
    def browser_check(self, selector: str) -> Dict[str, Any]:
        """勾选复选框/单选框"""
        if not self._check_state():
            return self._make_response(
                "check", success=False,
                error="Browser is closed. Call open() first."
            )
        
        if not self._is_agent_browser_available():
            return self._make_response(
                "check", success=False,
                error="agent-browser not available"
            )
        
        args = ["check", selector]
        args.extend(self._get_common_args())
        
        result = self._run_browser_command(args)
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "check"):
            return error_resp
        return self._make_response(
            "check",
            success=True,
            data={"selector": selector},
            update_state=BrowserState.BROWSING
        )
    
    def browser_uncheck(self, selector: str) -> Dict[str, Any]:
        """取消勾选复选框"""
        if not self._check_state():
            return self._make_response(
                "uncheck", success=False,
                error="Browser is closed. Call open() first."
            )
        
        if not self._is_agent_browser_available():
            return self._make_response(
                "uncheck", success=False,
                error="agent-browser not available"
            )
        
        args = ["uncheck", selector]
        args.extend(self._get_common_args())
        
        result = self._run_browser_command(args)
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "uncheck"):
            return error_resp
        return self._make_response(
            "uncheck",
            success=True,
            data={"selector": selector},
            update_state=BrowserState.BROWSING
        )
    
    def browser_press(self, key: str, selector: str = None) -> Dict[str, Any]:
        """按键"""
        if not self._check_state():
            return self._make_response(
                "press", success=False,
                error="Browser is closed. Call open() first."
            )
        
        if not self._is_agent_browser_available():
            return self._make_response(
                "press", success=False,
                error="agent-browser not available"
            )
        
        args = ["press"]
        if selector:
            args.append(selector)
        args.append(key)
        args.extend(self._get_common_args())
        
        result = self._run_browser_command(args)
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "press"):
            return error_resp
        return self._make_response(
            "press",
            success=True,
            data={"key": key, "selector": selector},
            update_state=BrowserState.BROWSING
        )
    
    def browser_close(self, close_all: bool = False) -> Dict[str, Any]:
        """关闭浏览器"""
        if not self._is_agent_browser_available():
            return self._make_response(
                "close", success=False,
                error="agent-browser not available"
            )
        
        args = ["close"]
        if close_all:
            args.append("--all")
        args.extend(self._get_common_args())
        
        result = self._run_browser_command(args, timeout=5)
        # 【修复 MAJ-1】检查命令失败
        if not result.get("success", True):
            self._session_name = None
            return self._make_response(
                "close", success=False,
                error=result.get("error", "Failed to close browser")
            )
        # 重置状态
        self._session_name = None
        
        return self._make_response(
            "close",
            success=True,
            data={
                "task_completed": True,
                "message": "Browser closed. Task completed.",
                "output": "Browser automation task finished successfully."
            },
            update_state=BrowserState.CLOSED
        )
    
    def browser_back(self) -> Dict[str, Any]:
        """后退"""
        if not self._check_state():
            return self._make_response(
                "back", success=False,
                error="Browser is closed. Call open() first."
            )
        
        result = self._run_browser_command(["back"] + self._get_common_args())
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "back"):
            return error_resp
        return self._make_response(
            "back",
            success=True,
            data={"url": result.get("url", "")},
            update_state=BrowserState.BROWSING
        )
    
    def browser_forward(self) -> Dict[str, Any]:
        """前进"""
        if not self._check_state():
            return self._make_response(
                "forward", success=False,
                error="Browser is closed. Call open() first."
            )
        
        result = self._run_browser_command(["forward"] + self._get_common_args())
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "forward"):
            return error_resp
        return self._make_response(
            "forward",
            success=True,
            update_state=BrowserState.BROWSING
        )
    
    def browser_reload(self) -> Dict[str, Any]:
        """刷新页面"""
        if not self._check_state():
            return self._make_response(
                "reload", success=False,
                error="Browser is closed. Call open() first."
            )
        
        result = self._run_browser_command(["reload"] + self._get_common_args())
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "reload"):
            return error_resp
        return self._make_response(
            "reload",
            success=True,
            update_state=BrowserState.BROWSING
        )
    
    def browser_scroll(self, direction: str = "down", pixels: int = 500) -> Dict[str, Any]:
        """滚动页面"""
        if not self._check_state():
            return self._make_response(
                "scroll", success=False,
                error="Browser is closed. Call open() first."
            )
        # 【修复】验证 direction 参数
        valid_directions = {"up", "down", "left", "right"}
        if direction not in valid_directions:
            return self._make_response(
                "scroll", success=False,
                error=f"Invalid direction: {direction}. Must be one of: {', '.join(valid_directions)}"
            )
        # 【修复】验证 pixels 参数
        if pixels <= 0:
            return self._make_response(
                "scroll", success=False,
                error=f"Invalid pixels: {pixels}. Must be positive."
            )
        max_pixels = 10000
        if pixels > max_pixels:
            return self._make_response(
                "scroll", success=False,
                error=f"Invalid pixels: {pixels}. Exceeds max {max_pixels}"
            )
        result = self._run_browser_command(["scroll", direction, str(pixels)] + self._get_common_args())
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "scroll"):
            return error_resp
        return self._make_response(
            "scroll",
            success=True,
            data={"direction": direction, "pixels": pixels},
            update_state=BrowserState.BROWSING
        )
    
    def browser_wait(self, wait_for: str) -> Dict[str, Any]:
        """等待"""
        if not self._check_state():
            return self._make_response(
                "wait", success=False,
                error="Browser is closed. Call open() first."
            )
        
        result = self._run_browser_command(["wait", wait_for] + self._get_common_args())
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "wait"):
            return error_resp
        return self._make_response(
            "wait",
            success=True,
            data={"wait_for": wait_for},
            update_state=BrowserState.BROWSING
        )
    
    def browser_hover(self, selector: str) -> Dict[str, Any]:
        """悬停"""
        if not self._check_state():
            return self._make_response(
                "hover", success=False,
                error="Browser is closed. Call open() first."
            )
        
        result = self._run_browser_command(["hover", selector] + self._get_common_args())
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "hover"):
            return error_resp
        return self._make_response(
            "hover",
            success=True,
            data={"selector": selector},
            update_state=BrowserState.BROWSING
        )
    
    def browser_get_text(self, selector: str = None) -> Dict[str, Any]:
        """获取文本"""
        if not self._check_state():
            return self._make_response(
                "get_text", success=False,
                error="Browser is closed. Call open() first."
            )
        
        args = ["get"]
        if selector:
            args.extend(["text", selector])
        else:
            args.append("title")
        args.extend(self._get_common_args())
        
        result = self._run_browser_command(args)
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "get_text"):
            return error_resp
        return self._make_response(
            "get_text",
            success=True,
            data={"text": result.get("text", result.get("title", ""))},
            update_state=BrowserState.BROWSING
        )
    
    def browser_get_url(self) -> Dict[str, Any]:
        """获取当前 URL"""
        if not self._check_state():
            return self._make_response(
                "get_url", success=False,
                error="Browser is closed. Call open() first."
            )
        
        result = self._run_browser_command(["get", "url"] + self._get_common_args())
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "get_url"):
            return error_resp
        return self._make_response(
            "get_url",
            success=True,
            data={"url": result.get("url", result.get("output", ""))},
            update_state=BrowserState.BROWSING
        )
    
    def browser_keyboard_type(self, text: str) -> Dict[str, Any]:
        """键盘输入（无需选择器）"""
        if not self._check_state():
            return self._make_response(
                "keyboard_type", success=False,
                error="Browser is closed. Call open() first."
            )
        
        # 【修复】添加长度限制
        max_length = 10000
        if len(text) > max_length:
            return self._make_response(
                "keyboard_type", success=False,
                error=f"Text too long: {len(text)} chars (max: {max_length})"
            )
        
        result = self._run_browser_command(["keyboard", "type", text] + self._get_common_args())
        # 【修复】检查命令失败
        if error_resp := self._check_command_failure(result, "keyboard_type"):
            return error_resp
        return self._make_response(
            "keyboard_type",
            success=True,
            data={"text": text},
            update_state=BrowserState.BROWSING
        )
    
    # ==================== 便捷方法 ====================
    
    def browser_navigate_and_interact(self, url: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """导航并执行一系列交互操作"""
        if not self._is_agent_browser_available():
            return self._make_response(
                "navigate_and_interact", success=False,
                error="agent-browser not available"
            )
        # 【修复 CRIT-2】检查状态（CLOSED 状态不允许操作）
        if self._state == BrowserState.CLOSED:
            return self._make_response(
                "navigate_and_interact", success=False,
                error="Browser is closed. Call browser_open first."
            )
        open_result = self.browser_open(url)
        if not open_result.get("success"):
            return open_result
        
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
                elif action_type == "press":
                    result = self.browser_press(value, selector)
                elif action_type == "wait":
                    result = self.browser_wait(str(int(action.get("seconds", 1) * 1000)))
                elif action_type == "scroll":
                    result = self.browser_scroll(action.get("direction", "down"), action.get("pixels", 500))
                else:
                    continue
                
                # 【修复】如果某个 action 失败，返回错误
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
    
    def browser_fill_form(self, data: Dict[str, str], submit_selector: str = None) -> Dict[str, Any]:
        """填写表单并提交"""
        if not self._check_state():
            return self._make_response(
                "fill_form", success=False,
                error="Browser is closed. Call open() first."
            )
        
        for selector, value in data.items():
            # 【修复】只有普通 selector 才需要转换，已经有 @ 或 [ 前缀的不转换
            if not selector.startswith("@") and not selector.startswith("["):
                selector = f'[name="{selector}"]'
            result = self.browser_fill(selector, value)
            if not result.get("success"):
                return result
        
        if submit_selector:
            click_result = self.browser_click(submit_selector)
            if not click_result.get("success"):
                return click_result
        
        return self._make_response(
            "fill_form",
            success=True,
            data={"fields_filled": len(data), "submitted": submit_selector is not None},
            update_state=BrowserState.BROWSING
        )
    
    # ==================== 统一入口 ====================
    
    def browser_automation(self, action: str = None, **kwargs) -> Dict[str, Any]:
        """
        统一的浏览器自动化入口
        根据 action 参数分发到对应的方法。
        """
        # 如果没有指定 action，返回帮助信息
        if not action:
            return {
                "success": True,
                "available_actions": list(self.NEXT_STEP_HINTS.keys()),
                "usage": "browser_automation(action='action_name', **params)",
                "hint": "Required workflow: open → snapshot → interact → close"
            }
        
        # 分发到对应的方法
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
            "close": lambda: self.browser_close(
                close_all=kwargs.get("close_all", False)
            ),
            "hover": lambda: self.browser_hover(
                selector=kwargs.get("selector", "")
            ),
            "wait": lambda: self.browser_wait(
                wait_for=kwargs.get("wait_for", kwargs.get("value", ""))
            ),
            "select": lambda: self.browser_select(
                selector=kwargs.get("selector", ""),
                value=kwargs.get("value", "")
            ),
            "get_text": lambda: self.browser_get_text(
                selector=kwargs.get("selector")
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
        
        # 执行对应的 action
        if action in action_map:
            try:
                return action_map[action]()
            except Exception as e:
                return self._make_response(
                    action, success=False, error=str(e)
                )
        else:
            return self._make_response(
                action, success=False,
                error=f"Unknown action: {action}",
            )