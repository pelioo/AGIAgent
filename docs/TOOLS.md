# 工具列表

> **自动生成**：由 `scripts/generate_tools_md.py` 生成
> **更新时间**：2026-05-31

---

## 目录

- [文件操作工具](#文件操作工具)
- [终端工具](#终端工具)
- [代码搜索工具](#代码搜索工具)
- [Web 搜索工具](#web-搜索工具)
- [图像工具](#图像工具)
- [鼠标工具](#鼠标工具)
- [MCP 工具](#mcp-工具)
- [帮助工具](#帮助工具)
- [历史与记忆](#历史与记忆)
- [多 Agent 工具](#多-agent-工具)

---

## 文件操作工具

| 模块 | 工具名称 | 说明 |
|------|----------|------|
| `file_system_tools` | `read_file` | 读取文件内容 |
| `file_system_tools` | `edit_file` | 编辑文件（精确替换） |
| `file_system_tools` | `write_file` | 写入或创建文件 |
| `file_system_tools` | `list_dir` | 列出目录内容 |
| `file_system_tools` | `create_directory` | 创建目录 |
| `file_system_tools` | `delete_file` | 删除文件 |

## 终端工具

| 模块 | 工具名称 | 说明 |
|------|----------|------|
| `terminal_tools` | `run_terminal_cmd` | 执行终端命令 |
| `terminal_tools` | `powershell` | 执行 PowerShell 命令 |

## 代码搜索工具

| 模块 | 工具名称 | 说明 |
|------|----------|------|
| `code_search_tools` | `grep_search` | 搜索代码内容 |
| `code_search_tools` | `code_navigation` | 代码导航 |

## Web 搜索工具

| 模块 | 工具名称 | 说明 |
|------|----------|------|
| `web_search_tools` | `web_search` | 网页搜索（带 LLM 过滤） |
| `web_search_tools_z` | `web_search_z` | 智谱 AI 搜索集成 |

## 图像工具

| 模块 | 工具名称 | 说明 |
|------|----------|------|
| `image_generation_tools` | `create_img` | 生成图像 |
| `image_tools` | `image_process` | 图像处理 |
| `read_img` | `read_image` | 读取图像内容 |
| `svg_processor` | `process_svg` | SVG 处理 |
| `svg_to_png` | `svg_to_png` | SVG 转 PNG |

## 鼠标工具

| 模块 | 工具名称 | 说明 |
|------|----------|------|
| `mouse_tools` | `mouse_click` | 鼠标点击 |
| `mouse_tools` | `mouse_move` | 鼠标移动 |
| `mouse_tools` | `mouse_drag` | 鼠标拖拽 |

## MCP 工具

| 模块 | 工具名称 | 说明 |
|------|----------|------|
| `fastmcp_wrapper` | MCP 服务器工具 | FastMCP 封装工具 |
| `cli_mcp_wrapper` | CLI-MCP 工具 | 命令行 MCP 封装 |
| `mcp_client` | MCP 客户端 | MCP 连接管理 |

## 帮助工具

| 模块 | 工具名称 | 说明 |
|------|----------|------|
| `help_tools` | `help` | 显示帮助信息 |

## 历史与记忆

| 模块 | 工具名称 | 说明 |
|------|----------|------|
| `history_compression_tools` | `compress_history` | 压缩历史记录 |
| `long_term_memory` | `store_memory` | 存储长期记忆 |
| `long_term_memory` | `retrieve_memory` | 检索长期记忆 |
| `enhanced_history_compressor` | `enhanced_compress` | 增强历史压缩 |

## 多 Agent 工具

| 模块 | 工具名称 | 说明 |
|------|----------|------|
| `multiagents` | `create_subagent` | 创建子 Agent |
| `multiagents` | `delegate_task` | 委托任务 |
| `planning_tools` | `create_plan` | 创建计划 |
| `priority_scheduler` | `schedule_task` | 任务调度 |

---

## 使用说明

### 工具调用格式

```python
result = tool_executor.execute_tool("tool_name", param1="value1", param2="value2")
```

### 返回值格式

所有工具返回 `Dict[str, Any]`，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `result` | Any | 工具执行结果 |
| `error` | str | 错误信息（如有） |

### 工具来源

| 来源 | 说明 |
|------|------|
| `regular` | 内置工具（直接调用） |
| `fastmcp` | FastMCP 服务器工具 |
| `cli_mcp` | CLI-MCP 命令行工具 |

---

*如需更新此文档，请运行 `python scripts/generate_tools_md.py`*  
*返回 [AGENTS.md](../AGENTS.md)*