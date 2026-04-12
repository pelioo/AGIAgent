# AGI-Agent 系统架构说明文档

## 目录

1. [项目概览](#1-项目概览)
2. [整体架构](#2-整体架构)
3. [核心模块详解](#3-核心模块详解)
4. [工具系统](#4-工具系统)
5. [记忆系统](#5-记忆系统)
6. [多智能体系统](#6-多智能体系统)
7. [API调用系统](#7-api调用系统)
8. [配置系统](#8-配置系统)
9. [应用扩展](#9-应用扩展)
10. [GUI模块架构](#10-gui模块架构)
11. [MCP集成机制](#11-mcp集成机制)
12. [Skill进化系统](#12-skill进化系统)
13. [性能优化机制](#13-性能优化机制)
14. [部署架构](#14-部署架构)

---

## 1. 项目概览

### 1.1 简介

**AGI-Agent** 是一个开源的通用智能体平台，支持 Vibe Doc、Vibe Coding 和自然语言通用任务执行，采用 Manager + 多子Agent 的协作架构。

### 1.2 核心特性

| 特性 | 描述 |
|------|------|
| **多模型支持** | OpenAI GPT、Claude、DeepSeek V3、Kimi K2、GLM、Qwen 等 |
| **多模式运行** | GUI 网页界面 / CLI 命令行 / Python 库嵌入 |
| **跨平台** | Windows / Linux / macOS / ARM 嵌入式 |
| **工具生态** | 40+ 内置工具 + MCP 扩展 |
| **本地部署** | 完全本地化，数据隐私可控 |

---

## 2. 整体架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AGI-Agent 系统架构                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    用户交互层 (Interface Layer)                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │  │
│  │  │   GUI/Web    │  │  CLI (agia.py)│  │  Python Library     │ │  │
│  │  │  dashboard/  │  │    命令行入口   │  │  API 接口          │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
│                                    ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    主程序层 (Main Layer)                           │  │
│  │  ┌─────────────────────┐     ┌─────────────────────┐           │  │
│  │  │   AGIAgentMain      │     │   AGIAgentClient    │           │  │
│  │  │   (主程序类)         │     │   (库模式客户端)     │           │  │
│  │  └─────────────────────┘     └─────────────────────┘           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
│                                    ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │              多轮执行引擎 (Multi-Round Executor)                    │  │
│  │  ┌──────────────────────────────────────────────────────────┐  │  │
│  │  │              MultiRoundTaskExecutor                        │  │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │  │
│  │  │  │ DebugRecorder│  │ TaskChecker │  │ RoundSyncManager │  │  │  │
│  │  │  │ (调试记录)   │  │ (任务检查)   │  │ (轮次同步)     │  │  │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │  │
│  │  └──────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
│                                    ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    工具执行器 (Tool Executor)                       │  │
│  │  ┌───────────────────────────────────────────────────────────┐   │  │
│  │  │                      ToolExecutor                         │   │  │
│  │  │  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐ │   │  │
│  │  │  │ MCP集成模块    │  │ API调用封装    │  │ 工具定义     │ │   │  │
│  │  │  │ FastMCP/CLI  │  │ OpenAI/Claude │  │ prompts/*.json│ │   │  │
│  │  │  └───────────────┘  └───────────────┘  └──────────────┘ │   │  │
│  │  └───────────────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
│                                    ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                      工具层 (Tools Layer)                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │  │
│  │  │  文件系统工具  │  │  代码执行工具 │  │  网络搜索工具     │     │  │
│  │  │ file_tools   │  │ terminal_tools│  │ web_search_tools  │     │  │
│  │  └──────────────┘  └──────────────┘  └────────────────────┘     │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │  │
│  │  │  图像处理工具 │  │  多智能体工具 │  │  记忆管理工具     │     │  │
│  │  │ image_tools  │  │ multiagents  │  │ long_term_memory  │     │  │
│  │  └──────────────┘  └──────────────┘  └────────────────────┘     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
│                                    ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    API 层 (API Callers)                            │  │
│  │  ┌─────────────────────┐              ┌─────────────────────┐   │  │
│  │  │  OpenAI API Caller │              │  Claude API Caller  │   │  │
│  │  │  streaming/non     │              │  streaming/non      │   │  │
│  │  └─────────────────────┘              └─────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 执行流程 (ReAct 模式)

```
┌─────────────────────────────────────────────────────┐
│          ReAct 执行循环 (Plan → Act → Observe)        │
├─────────────────────────────────────────────────────┤
│                                                      │
│    ┌───────────────────────┐                        │
│    │    1. Plan (计划)     │                        │
│    │ 需求 → 分解 → plan.md │                        │
│    └───────────┬───────────┘                        │
│                ▼                                    │
│    ┌───────────────────────┐                        │
│    │    2. Act (执行)     │                        │
│    │ LLM → 工具调用 → 执行 │                        │
│    └───────────┬───────────┘                        │
│                ▼                                    │
│    ┌───────────────────────┐                        │
│    │   3. Observe (观察)   │                        │
│    │ 结果 → 终止检查 → 反馈 │                        │
│    └───────────┬───────────┘                        │
│                ▼                                    │
│          任务完成 / 继续循环                         │
│       (默认50轮迭代)                                │
└─────────────────────────────────────────────────────┘
```

---

## 3. 核心模块详解

### 3.1 入口模块 (agia.py)

```python
main()
├── 参数解析 (argparse)
│   ├── -r/--requirement: 用户需求
│   ├── -d/--dir: 输出目录
│   ├── -l/--loops: 执行轮数 (默认100, -1无限)
│   ├── --app: 应用模式 (colordoc/patent/childedu)
│   ├── --plan: 计划模式
│   └── --continue: 继续上次任务
└── 初始化
    ├── AGIAgentMain 实例化
    └── global_cleanup() 注册
```

### 3.2 主程序模块 (src/main.py)

**AGIAgentMain 类**：

| 方法 | 功能 |
|------|------|
| `run()` | 主入口 |
| `execute_single_task()` | 单任务执行 |
| `execute_plan_mode()` | 计划模式 |
| `_handle_task_completion()` | 任务完成处理 |

### 3.3 多轮执行引擎

```
MultiRoundTaskExecutor
├── ToolExecutor 初始化
├── DebugRecorder (调试记录)
├── TaskChecker (任务检查)
└── RoundSyncManager (轮次同步)
```

### 3.4 工具执行器 (src/tool_executor.py)

```python
class ToolExecutor:
    def __init__()
    ├── _setup_llm_client()      # API客户端
    ├── _initialize_mcp_async()  # MCP初始化
    └── _add_mcp_tools_to_map()  # 添加工具
    
    def execute_subtask()         # 执行子任务
    ├── load_system_prompt()     # 加载提示
    ├── _call_llm_with_tools()   # LLM调用
    ├── parse_tool_calls()        # 解析工具
    └── execute_tool()            # 执行工具
```

---

## 4. 工具系统

### 4.1 三层工具体系

| 层级 | 说明 |
|------|------|
| **内置工具** | 40+ 文件/代码/网络/图像工具 |
| **OS工具** | 终端命令、pip/apt包管理 |
| **MCP工具** | FastMCP/CLI扩展 |

### 4.2 核心工具模块

| 模块 | 功能 |
|------|------|
| `file_system_tools.py` | 文件读写、编辑、搜索 |
| `terminal_tools.py` | 终端命令、Claude Shell |
| `web_search_tools.py` | 网页搜索、内容抓取 |
| `image_generation_tools.py` | 图像生成 |
| `svg_processor.py` | SVG处理 |
| `mermaid_processor.py` | Mermaid图生成 |
| `multiagents.py` | 多智能体协作 |
| `long_term_memory.py` | 长期记忆 |
| `history_compression_tools.py` | 历史压缩 |
| `mcp_client.py` | MCP协议集成 |

---

## 5. 记忆系统

### 5.1 双层记忆架构

```
短期记忆                    长期记忆
├── TaskHistory          ├── LongTermMemoryManager
│   └── 当前会话历史     │   └── 跨任务知识
├── 历史压缩              └── MemManagerAgent
└── 图像数据优化             └── 向量化存储
```

### 5.2 代码索引系统

```python
class CodeRepositoryParser:
    def parse_repository()     # 索引构建
    def vector_search()        # 语义搜索
    def keyword_search()       # 关键词搜索
    def hybrid_search()       # 混合搜索
    def incremental_update()  # 增量更新
```

---

## 6. 多智能体系统

### 6.1 Manager + 子Agent 架构

```
Manager (主智能体)
├── 任务分解
├── 状态监控
└── 结果汇总
       │
       ├── agent_001 (码工)
       ├── agent_002 (艺术)
       └── agent_003 (具身)
              │
         Mailbox + Router
```

### 6.2 消息系统

```python
class MessageType(Enum):
    STATUS_UPDATE = "status_update"   # 状态更新
    TASK_REQUEST = "task_request"     # 任务请求
    COLLABORATION = "collaboration"  # 协作
    BROADCAST = "broadcast"           # 广播

class MessageRouter:
    def register_agent()      # 注册
    def route_message()       # 路由
    def broadcast_message()   # 广播
```

---

## 7. API调用系统

### 7.1 API Caller 架构

```
src/api_callers/
├── openai_chat_based_streaming.py      # OpenAI流式
├── openai_chat_based_non_streaming.py  # OpenAI非流式
├── openai_standard_tools.py             # OpenAI标准工具
├── claude_chat_based_streaming.py       # Claude流式
├── claude_chat_based_non_streaming.py  # Claude非流式
└── claude_standard_tools.py            # Claude标准工具
```

---

## 8. 配置系统

### 8.1 配置加载机制

```python
# src/config_loader.py
def load_config(config_file="config/config.txt", verbose=False):
    """
    带缓存的配置加载
    - 支持文件修改时间检测
    - 自动更新缓存
    """
    # 优先级: 环境变量 > 配置文件
```

### 8.2 配置项分类

| 类别 | 配置项 |
|------|--------|
| **API配置** | `api_key`, `api_base`, `model` |
| **执行参数** | `max_rounds`, `enable_thinking` |
| **记忆配置** | `config_memory.txt` |
| **MCP配置** | `mcp_servers.json` |

---

## 9. 应用扩展

### 9.1 apps/ 目录结构

```
apps/
├── colordoc/          # 彩文文档写作平台
│   ├── config.txt     # 特定配置
│   ├── prompts/       # 特定提示词
│   ├── routine/       # 写作模板
│   └── app.json       # 应用清单
├── patent/            # 专利写作助手
└── childedu/          # 儿童教育应用
```

---

## 10. GUI模块架构

### 10.1 目录结构

```
GUI/
├── app.py                      # Flask主应用
├── run_gui.py                  # 启动脚本
├── auth_manager.py             # 认证管理
├── app_manager.py              # 应用管理
├── agent_status_visualizer.py  # 状态可视化
├── templates/                  # HTML模板
│   ├── index.html
│   ├── register.html
│   └── terminal.html
├── static/                     # 静态资源
│   ├── css/
│   ├── js/
│   └── logo.png
└── deployment/                  # 部署脚本
    └── monitor.py
```

### 10.2 核心组件

| 组件 | 功能 |
|------|------|
| `app.py` | Flask主应用，路由处理 |
| `auth_manager.py` | 用户认证、会话管理 |
| `app_manager.py` | AGIAgent实例管理 |
| `agent_status_visualizer.py` | 执行状态可视化 |

---

## 11. MCP集成机制

### 11.1 MCP客户端架构

```python
# src/tools/mcp_client.py
class MCPClient:
    """MCP客户端 - 支持多协议适配"""
    
    def __init__(config_path="config/mcp_servers.json"):
        self._init_builtin_adapters()
        # 百度搜索适配器
        # 腾讯搜索适配器
        # Elasticsearch适配器
    
    async def call_tool(tool_name, parameters):
        # 协议转换
        # SSE/HTTP调用
```

### 11.2 FastMCP包装器

```python
# src/tools/fastmcp_wrapper.py
class FastMcpWrapper:
    """FastMCP持久化服务管理"""
    
    def __init__(config_path, workspace_dir):
        self.servers = {}        # 服务实例
        self.available_tools = {} # 可用工具
    
    async def initialize():
        # 加载配置
        # 发现工具
        # 启动服务
    
    async def call_tool(tool_name, arguments):
        # 工具调用
```

### 11.3 协议适配器系统

```python
class ProtocolAdapter:
    """自定义协议适配器"""
    
    def request_transformer(tool_name, parameters):
        # 转换请求格式
    
    def response_transformer(data):
        # 转换响应格式
```

---

## 12. Experience进化系统

### 12.1 Experience管理器

```python
# src/experience/experience_manager.py
class ExperienceManager:
    """Experience整理管理器"""
    
    def merge_similar_experiences()    # 合并相似skill
    def cleanup_unused_experiences()   # 清理无用skill
    def cross_integrate()         # 跨skill整合
```

### 12.2 Experience工具

```python
# src/experience/experience_tools.py
class ExperienceTools:
    """Experience管理与经验总结"""
    
    def list_experiences()             # 列出skill
    def get_experience_details()       # 获取详情
    def evaluate_experience()         # 评价skill
    def update_experience()           # 更新skill
    
    # 中文分词 (jieba)
    # TF-IDF相似度计算
```

---

## 13. 性能优化机制

### 13.1 延迟导入优化

```python
# 重量级库延迟加载
def _ensure_lazy_imports():
    """首次使用时加载numpy、sklearn"""
    global np, TfidfVectorizer
    if not _LAZY_IMPORTS_LOADED:
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
```

### 13.2 缓存机制

```python
# 配置缓存
_config_cache: Dict[str, Dict[str, str]] = {}
_config_file_mtime: Dict[str, float] = {}

def load_config(config_file):
    # 检查文件修改时间
    # 有效则使用缓存
```

### 13.3 资源清理优化

```python
# 只清理已加载的模块
def cleanup():
    if 'src.tools.fastmcp_wrapper' in sys.modules:
        safe_cleanup_fastmcp_wrapper()
```

---

## 14. 部署架构

### 14.1 部署模式

| 模式 | 说明 |
|------|------|
| **本地CLI** | `python agia.py` |
| **Web GUI** | `python GUI/app.py` |
| **Python库** | `from agia import create_client` |
| **云端部署** | Docker + Web服务 |

### 14.2 依赖要求

```
Python 3.8+
├── anthropic          # Claude API
├── openai             # OpenAI API
├── fastmcp           # MCP支持
├── playwright         # 网页抓取
├── jieba             # 中文分词
└── scikit-learn      # TF-IDF
```

---

## 附录：技术栈总结

| 类别 | 技术 |
|------|------|
| **语言** | Python 3.8+ |
| **框架** | Flask (GUI), asyncio |
| **AI模型** | OpenAI/Claude/国产模型 |
| **协议** | MCP (Model Context Protocol) |
| **搜索** | TF-IDF + 向量化 |
| **部署** | Docker / 云端 |

---

*文档版本: 1.0*
*更新时间: 2026-04-04*
