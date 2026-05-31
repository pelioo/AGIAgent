# 架构详解指南

> **最后更新**：2026-05-31

---

## 目录

- [架构概览](#架构概览)
- [核心组件](#核心组件)
- [数据流详解](#数据流详解)
- [状态管理](#状态管理)
- [异步模式](#异步模式)

---

## 架构概览

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户输入                                  │
│                   (CLI / GUI / Python 库)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGIAgentMain (src/main.py)                   │
│                     ← 入口点，CLI 参数，交互式提示               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              MultiRoundTaskExecutor                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ DebugRecorder     ← LLM 调用日志、消息优化              │   │
│  │ TaskChecker       ← TASK_COMPLETED/INCOMPLETE 检测     │   │
│  │ RoundSyncManager  ← 轮次同步管理                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ToolExecutor (tool_executor.py)                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ API Callers (api_callers/)                              │   │
│  │   ├─ OpenAI（流式 / 非流式 / 标准）                      │   │
│  │   └─ Claude（流式 / 非流式 / 标准）                      │   │
│  │                                                        │   │
│  │ MCP 集成                                                │   │
│  │   ├─ FastMCP 封装                                       │   │
│  │   └─ CLI-MCP 封装                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Tools (src/tools/__init__.py)                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 40+ 内置工具（Mixin 多继承架构）                         │   │
│  │                                                        │   │
│  │ BaseTools          ← 基础工具                           │   │
│  │ FileSystemTools    ← 文件操作                           │   │
│  │ TerminalTools      ← 命令执行                           │   │
│  │ WebSearchTools     ← 网页搜索                           │   │
│  │ CodeSearchTools    ← 代码导航                           │   │
│  │ ImageGenerationTools ← 图像生成                        │   │
│  │ MouseTools         ← 鼠标操作                           │   │
│  │ HelpTools          ← 帮助系统                           │   │
│  │ ...                                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Experience 模块                               │
│              ← TF-IDF 向量化实现的长期记忆                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. 入口点

| 文件 | 说明 |
|------|------|
| `agia.py` | CLI 入口脚本，直接运行 |
| `src/main.py` | 主程序，含 AGIAgentClient 库接口 |
| `GUI/app.py` | Flask + SocketIO Web 应用 |

### 2. ToolExecutor

**职责**：管理工具调用和 LLM 交互

**核心属性**：
```python
class ToolExecutor:
    tool_map          # 工具名称 → 方法的映射
    tool_source_map   # 工具名称 → 来源（regular/fastmcp/cli_mcp）
    messages          # 消息历史
    api_caller        # API 调用器
```

**关键方法**：
- `execute_tool(tool_name, **kwargs)` — 执行工具
- `call_llm(messages)` — 调用 LLM
- `should_summarize()` — 判断是否需要摘要

### 3. MultiRoundTaskExecutor

**职责**：编排多轮任务循环

**核心组件**：
- `DebugRecorder` — 记录 LLM 调用日志
- `TaskChecker` — 检测任务完成标志
- `RoundSyncManager` — 管理轮次同步

### 4. Tools 系统

**架构**：Mixin 多继承

```python
class Tools(BaseTools, FileSystemTools, TerminalTools,
            WebSearchTools, CodeSearchTools, HelpTools,
            MouseTools, ImageGenerationTools,
            OptionalMCPKnowledgeBaseTools, OptionalPluginTools):
    pass
```

**工具注册流程**：
```
prompts/tool_prompt.json
       ↓
HelpTools._load_tool_definitions()
       ↓
ToolExecutor.register_tools()
       ↓
tool_map[tool_name] = tool_method
```

### 5. Experience 模块

**职责**：长期记忆管理

**核心组件**：
- `ExperienceManager` — TF-IDF 向量存储
- `TaskReflection` — 任务回顾分析

---

## 数据流详解

### ReAct 循环流程

```
┌─────────────┐
│   用户输入   │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│                   ReAct 循环                             │
│                                                          │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐           │
│   │  计划   │ →  │  执行   │ →  │  观察   │           │
│   │ (Plan)  │    │  (Act)  │    │(Observe)│           │
│   └────┬────┘    └────┬────┘    └────┬────┘           │
│        │             │             │                   │
│        └─────────────┴─────────────┘                   │
│                       │                                 │
│                       ▼                                 │
│              ┌───────────────┐                         │
│              │   判断结果     │                         │
│              └───────┬───────┘                         │
│                      │                                 │
│        ┌─────────────┼─────────────┐                   │
│        ▼             ▼             ▼                   │
│   TASK_COMPLETED  继续循环    TASK_INCOMPLETE          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 单轮执行流程

```python
def single_round():
    # 1. 构建消息
    messages = build_messages(user_input, context)
    
    # 2. 调用 LLM
    response = llm.call(messages)
    
    # 3. 解析工具调用
    tool_calls = parse_tool_calls(response)
    
    # 4. 执行工具
    for tool_call in tool_calls:
        result = execute_tool(tool_call)
    
    # 5. 检查任务状态
    if check_task_completed(result):
        return "TASK_COMPLETED"
    else:
        return "CONTINUE"
```

---

## 状态管理

### 三层状态架构

```
┌─────────────────────────────────────────────────────────┐
│                    状态管理层                           │
├──────────────┬──────────────────┬──────────────────────┤
│   短期记忆    │     长期记忆      │     GUI 状态        │
├──────────────┼──────────────────┼──────────────────────┤
│ ToolExecutor │ ExperienceManager │ ConcurrencyManager  │
│              │                  │                     │
│ - 消息历史   │ - TF-IDF 向量     │ - 任务跟踪          │
│ - 上下文     │ - 任务回顾        │ - 超时管理          │
│ - 会话数据   │ - 经验学习        │ - 连接管理          │
└──────────────┴──────────────────┴──────────────────────┘
```

### 消息历史管理

```python
class ToolExecutor:
    def __init__(self):
        self.messages = []  # 消息历史
        self.max_history = 100  # 最大历史条数
    
    def should_summarize(self):
        """判断是否需要压缩历史"""
        return len(self.messages) > self.max_history
    
    def summarize(self):
        """压缩消息历史"""
        summary = self.llm.summarize(self.messages)
        self.messages = [{"role": "system", "content": summary}]
```

### GUI 状态管理

```python
class ConcurrencyManager:
    max_tasks = 16        # 最大并发任务
    max_connections = 40  # 最大连接数
    task_timeout = 3600   # 60 分钟超时
    idle_timeout = 1800   # 30 分钟空闲超时
```

---

## 异步模式

### GUI 异步架构

```
┌─────────────────────────────────────────────────────────┐
│                  Flask-SocketIO                         │
│                       │                                 │
│         ┌─────────────┴─────────────┐                   │
│         ▼                           ▼                   │
│   ┌──────────┐              ┌──────────┐              │
│   │  gevent  │              │ threading│ ← 回退模式    │
│   │ (主模式) │              │          │              │
│   └──────────┘              └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

### API 调用异步模式

```python
# 流式调用
async def stream_call(messages):
    async for chunk in openai_stream(messages):
        yield chunk

# 非流式调用
def non_stream_call(messages):
    return openai.complete(messages)
```

### 并发控制

```python
class ConcurrencyManager:
    def __init__(self):
        self.semaphore = Semaphore(16)  # 最多 16 任务
        self.connections = 0
    
    def acquire(self):
        """获取执行权"""
        self.semaphore.acquire()
        self.connections += 1
    
    def release(self):
        """释放执行权"""
        self.semaphore.release()
        self.connections -= 1
```

---

## MCP 集成

### MCP 架构

```
┌─────────────────────────────────────────────────────────┐
│                   MCP 集成层                             │
├────────────────────────┬────────────────────────────────┤
│      FastMCP           │         CLI-MCP                │
├────────────────────────┼────────────────────────────────┤
│ Python 原生            │ 命令行封装                     │
│ 持久化客户端           │ 进程管理                       │
│ 健康监控               │ 状态检测                       │
└────────────────────────┴────────────────────────────────┘
```

### MCP 工具注册

```python
# tool_source_map 配置
tool_source_map = {
    "internal_tool": "regular",      # 内置工具
    "mcp_tool_a": "fastmcp",         # FastMCP 工具
    "mcp_tool_b": "cli_mcp",         # CLI-MCP 工具
}
```

### MCP 回退策略

```python
def execute_mcp_tool(tool_name, **kwargs):
    try:
        # 尝试 FastMCP
        return fastmcp_client.call(tool_name, **kwargs)
    except MCPConnectionError:
        # 回退到 CLI-MCP
        try:
            return cli_mcp_client.call(tool_name, **kwargs)
        except Exception:
            # 回退到内置工具
            return fallback_to_builtin(tool_name, **kwargs)
```

---

*返回 [AGENTS.md](../AGENTS.md)*