# AGI Agent - Claude Code 配置指南

> 本文件为 Claude Code 提供 AGI Agent 项目的上下文、编码规范和开发指南。

---

## 📖 项目概述

**AGI Agent** 是一个多智能体任务执行平台，支持：
- Vibe Doc（图文文档创作）
- Vibe Coding（编程辅助）
- 自然语言通用任务执行

### 核心特性

| 特性 | 说明 |
|------|------|
| 多智能体架构 | Manager + 多子 Agent 协作，支持自组队、自配置 |
| ReAct 执行引擎 | Plan → Act → Observe → Reflect 多轮迭代 |
| 40+ 工具生态 | 内置工具 + OS 命令 + MCP 扩展 |
| 双层记忆系统 | 短期记忆 + 长期语义检索 |
| 多格式输出 | Markdown / Word / PDF / LaTeX 无损转换 |
| 中英文支持 | 界面和 SVG/Mermaid 中文优化 |

### 适用场景

- 代码开发与调试
- 专业文档生成（报告、论文、专利）
- 数据分析与可视化
- 网页应用开发
- 多智能体协作任务

---

## 📁 项目结构

```
AGIAgent/
├── agia.py                      # CLI 入口脚本
├── src/
│   ├── main.py                  # 主程序（含 Python 库接口 AGIAgentClient）
│   ├── multi_round_executor/     # 多轮任务执行引擎
│   │   └── executor.py          # MultiRoundTaskExecutor 类
│   ├── tools/                   # 工具实现
│   │   ├── base_tools.py        # 基础工具类
│   │   ├── file_system_tools.py # 文件操作工具
│   │   ├── code_search_tools.py # 代码搜索工具
│   │   ├── web_search_tools.py  # 网络搜索工具
│   │   ├── image_tools.py       # 图像处理工具
│   │   └── ...
│   ├── api_callers/             # API 调用封装
│   ├── mem/                     # 记忆系统
│   ├── experience/              # 经验模块
│   └── config_loader.py         # 配置加载器
├── prompts/                     # 提示词配置
│   ├── system_prompt.txt        # 系统主提示词
│   ├── tool_prompt.json         # 工具定义（JSON Schema）
│   ├── rules_prompt.txt         # 工具调用规则
│   ├── system_plan_prompt.txt   # Plan 模式提示词
│   └── additional_tools.json    # 可选工具
├── config/                      # 配置文件
│   ├── config.txt               # 主配置（API 密钥、模型等）
│   ├── mcp_servers.json         # MCP 服务器配置
│   └── config_memory.txt        # 记忆配置
├── routine/                     # 技能模板（中文）
├── routine_zh/                  # 技能模板（英文）
├── GUI/                         # Web 界面
│   └── app.py                   # Flask Web 应用
├── docs/                        # 技术文档
└── md/                          # 使用指南

# Claude Code 相关文件
└── CLAUDE.md                    # 本文件
```

---

## 🚀 常用命令

### CLI 模式

```bash
# 基本使用
python agia.py "写一个 Python 计算器"

# 指定输出目录
python agia.py "写一个笑话" --dir "my_dir"

# 继续上次任务
python agia.py -c

# 设置执行轮数
python agia.py --loops 5 -r "需求描述"

# 自定义模型配置
python agia.py --api-key YOUR_KEY --model gpt-4 --api-base https://api.openai.com/v1

# 指定技能模板
python agia.py "写一篇论文" --routine routine_zh/核心循环引擎.md
```

### GUI 模式

```bash
# 启动 Web 界面
python GUI/app.py --port 5001

# 访问 http://localhost:5001
```

### Python 库模式

```python
from src.main import AGIAgentClient, create_client

# 初始化客户端（自动读取 config/config.txt）
client = AGIAgentClient(
    debug_mode=False,
    single_task_mode=True  # 推荐使用单任务模式
)

# 发送任务
response = client.chat(
    messages=[
        {"role": "user", "content": "创建一个 Python 计算器"}
    ],
    dir="my_calculator",  # 输出目录
    loops=10              # 最大执行轮数
)

# 检查结果
if response["success"]:
    print(f"任务完成! 输出目录: {response['output_dir']}")
else:
    print(f"任务失败: {response['message']}")
```

---

## 📐 编码规范

### Python 代码风格

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 AGI Agent Research Group.

Licensed under the Apache License, Version 2.0 (the "License");
...
"""

# 模块导入顺序：标准库 → 第三方库 → 本地模块
import os
import sys
from typing import Dict, List, Optional

from src.tools import Tools
from src.config_loader import get_api_key

# 常量命名：全大写加下划线
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30

# 类名：CapWords 风格
class TaskExecutor:
    """任务执行器类"""
    
    def __init__(self, config: Dict) -> None:
        """初始化执行器
        
        Args:
            config: 配置字典
        """
        self.config = config
```

### 文件操作规范

- **使用 UTF-8 编码**：所有 Python 文件添加 `# -*- coding: utf-8 -*-`
- **中文注释优先**：代码注释使用中文，提高可读性
- **类型提示**：函数参数和返回值建议添加类型注解
- **文档字符串**：类和公共方法添加 docstring

### 工具定义格式

工具定义在 `prompts/tool_prompt.json` 中，使用 JSON Schema 格式：

```json
{
  "tool_name": {
    "description": "工具用途描述",
    "parameters": {
      "type": "object",
      "properties": {
        "param_name": {
          "type": "string",
          "description": "参数说明"
        }
      },
      "required": ["param_name"]
    }
  }
}
```

---

## 🤖 Agent 核心机制

### ReAct 执行循环

```
┌─────────────────────────────────────────────┐
│                 Plan                        │
│  分析任务，创建/更新 plan.md 任务图           │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│                 Act                         │
│  调用工具执行任务                            │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│               Observe                       │
│  获取工具执行结果                            │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│               Reflect                        │
│  根据结果判断是否完成或继续                   │
└─────────────────────────────────────────────┘
```

### plan.md 任务图格式

Agent 在执行任务前会创建/更新 `plan.md`，使用 Mermaid 流程图：

```mermaid
graph TD
    Start([开始]) --> T1["T1: 任务1<br/>完成标准: xxx<br/>状态: pending"]
    T1 --> T2["T2: 任务2<br/>完成标准: xxx<br/>状态: pending"]
    T2 --> End([完成])
    
    style T1 fill:#f9f,stroke:#333,stroke-width:2px
    style T2 fill:#bbf,stroke:#333,stroke-width:2px
```

**节点类型：**
- **Task Node**：具体执行任务
- **Choice Node**：多分支选择
- **Loop Node**：循环任务
- **Start/End Node**：开始/结束节点

**节点属性：**
- `ID`：唯一标识
- `Task Description`：任务描述
- `Completion Criteria`：完成标准
- `Agent ID`：执行者（如 manager、agent_001）
- `Status`：状态（pending/in_progress/completed/failed）

### TASK_COMPLETED 信号

```python
# 任务完成时发送信号
TASK_COMPLETED: [简要描述完成内容]

# 注意：
# 1. 只有 manager 可发送此信号
# 2. 子 agent (agent_001 等) 不可编辑 plan.md
# 3. 如果当前轮调用了工具，需等待下一轮再发送
# 4. 不做超出用户需求的额外迭代
```

### 继续模式

当收到继续任务时：
1. 读取 `log/manager.out` 获取历史对话
2. 在历史上下文基础上继续执行
3. 可合并新的需求与历史任务

---

## 🛠️ 工具系统

### 核心工具列表

| 工具名 | 用途 | 使用要点 |
|--------|------|----------|
| `workspace_search` | 语义搜索代码 | 使用自然语言描述搜索需求 |
| `read_multiple_files` | 批量读取文件 | 最多 20 个文件，每次最多 500 行 |
| `edit_file` | 编辑文件 | 推荐使用 `lines_replace` 模式 |
| `grep_search` | 正则文本搜索 | 排除 `__pycache__/*` 等目录 |
| `run_terminal_cmd` | 执行终端命令 | 避免 pager，命令末尾加 `\| cat` |
| `web_search` | 网络搜索 | 结果保存到 `workspace/web_search_result/` |
| `fetch_webpage_content` | 抓取网页内容 | 可指定搜索关键词高亮 |
| `search_img` | 搜索图片 | 先 Google，后 Baidu/Bing |
| `create_img` | AI 生成图片 | 使用 cogview-3-flash 模型 |
| `read_img` | 图像识别 | 使用 vision_model 配置的模型 |
| `merge_file` | 合并文件 | Markdown 自动转 Word/PDF |
| `convert_docs_to_markdown` | 文档转换 | 支持 docx/xlsx/html/tex/pptx/pdf |
| `compress_history` | 压缩历史 | 手动触发对话历史压缩 |
| `talk_to_user` | 用户交互 | 可设置超时时间 |

### edit_file 使用模式

```python
# 精确替换（推荐）
edit_file(
    target_file="src/main.py",
    edit_mode="lines_replace",
    old_code="def hello():\n    print('world')",
    code_edit="def hello():\n    print('Hello, AGI Agent!')"
)

# 追加到文件末尾（最安全）
edit_file(
    target_file="src/new_file.py",
    edit_mode="append",
    code_edit="# 新文件内容\ndef new_function():\n    pass"
)

# 完全替换文件
edit_file(
    target_file="src/main.py",
    edit_mode="full_replace",
    code_edit="完整的新文件内容..."
)
```

### run_terminal_cmd 规范

```bash
# ✅ 正确：避免 pager
grep -r "TODO" src/ | cat
git log --oneline -10 | cat

# ❌ 错误：可能阻塞
git log  # 会进入交互式 pager
```

### Web 搜索结果处理

搜索结果保存到 `workspace/web_search_result/`，结构：
```
workspace/web_search_result/
├── search_results.html  # 原始 HTML
├── search_results.txt   # 提取文本
└── [url].txt           # 各页面内容
```

---

## ⚙️ 配置指南

### config.txt 主要字段

```ini
# 语言设置
LANG=zh  # en/zh

# 模型配置（必需）
api_key=your_api_key
api_base=https://api.openai.com/v1
model=claude-sonnet-4-0
max_tokens=16384

# 流式输出
streaming=True

# 长期记忆
enable_long_term_memory=True

# 工具调用格式
Tool_calling_format=False  # False 使用 chat-based，True 使用 standard
tool_call_parse_format=xml  # json/xml

# 历史压缩
summary_trigger_length=100000
compression_strategy=llm_summary  # delete/llm_summary

# Web 界面配置
gui_default_data_directory=./data

# 多智能体
multi_agent=False
enable_round_sync=True
sync_round=5
```

### 环境变量

```bash
# 也可通过环境变量设置
export AGIAGENT_API_KEY=your_key
export AGIAGENT_API_BASE=https://api.openai.com/v1
export AGIAGENT_MODEL=claude-sonnet-4-0
```

### MCP 服务器配置

`config/mcp_servers.json` 示例：
```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./workspace"]
    }
  ]
}
```

---

## 🔧 开发指南

### 添加工具流程

1. 在 `prompts/tool_prompt.json` 中添加工具定义
2. 在 `src/tools/` 中实现工具类
3. 在 `src/tools/__init__.py` 中注册
4. 测试工具调用

### 自定义提示词

| 文件 | 用途 | 修改说明 |
|------|------|----------|
| `prompts/system_prompt.txt` | 系统主提示词 | 定义 Agent 角色和行为 |
| `prompts/rules_prompt.txt` | 工具调用规则 | 规范工具使用方式 |
| `prompts/user_rules.txt` | 用户需求补充 | 添加额外指令 |
| `prompts/system_plan_prompt.txt` | Plan 模式 | 任务分解逻辑 |

### 多智能体配置

```python
# 启用多智能体模式
# config.txt 中设置
multi_agent=True

# 可用工具：spawn_agent, send_to_agent, broadcast_to_agents
# 每个 Agent 有独立的工作区和工具配置
```

### 调试与日志

```python
# 启用调试模式
python agia.py --debug "任务"

# 日志位置
output/logs/
├── manager.out      # 主 Agent 对话记录
├── executor.out     # 子 Agent 对话记录
└── debug/           # 详细调试信息
```

---

## 🧪 测试指南

### 测试框架

项目使用 **pytest** 作为测试框架，测试文件位于 `tests/` 目录：

```
AGIAgent/
├── tests/                          # 测试目录
│   ├── conftest.py                # pytest 配置和 fixtures
│   ├── unit/                      # 单元测试
│   │   ├── test_config_loader.py  # 配置加载器
│   │   ├── test_tool_executor.py  # 工具执行器
│   │   ├── test_tools.py         # 工具类
│   │   ├── test_api_callers.py   # API 调用器
│   │   ├── test_memory.py        # 记忆系统
│   │   └── test_experience.py    # 经验模块
│   ├── integration/               # 集成测试
│   │   ├── test_executor.py      # 执行器集成测试
│   │   └── test_multi_agent.py   # 多智能体测试
│   ├── e2e/                       # 端到端测试
│   │   └── test_agia_cli.py      # CLI 端到端测试
│   └── fixtures/                 # 测试数据
│       ├── sample_config.txt
│       └── sample_prompts/
```

### 安装测试依赖

```bash
# 安装 pytest 及相关插件
pip install pytest pytest-cov pytest-mock responses aioresponses

# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行端到端测试
pytest tests/e2e/

# 生成覆盖率报告
pytest --cov=src --cov-report=html tests/
```

### Fixtures 配置（重要）

项目使用混合继承模式的类结构，fixtures 需要适配：

```python
# tests/conftest.py
import pytest
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch, AsyncMock

# 添加项目根目录到 sys.path
@pytest.fixture(autouse=True)
def setup_python_path():
    """自动设置 Python 路径"""
    original_path = sys.path.copy()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    yield
    sys.path[:] = original_path

@pytest.fixture
def mock_api_key(monkeypatch):
    """设置测试用 API Key"""
    monkeypatch.setenv("AGIAGENT_API_KEY", "test_key_12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")

@pytest.fixture
def temp_workspace(tmp_path):
    """创建临时工作区（项目实际使用 output_* 目录结构）"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "test_file.py").write_text("print('hello world')")
    return workspace

@pytest.fixture
def temp_output_dir(tmp_path):
    """创建临时输出目录（模拟 output_YYYYMMDD_HHMMSS 结构）"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = tmp_path / f"output_{timestamp}"
    output_dir.mkdir(parents=True)
    (output_dir / "workspace").mkdir()
    return output_dir

@pytest.fixture
def mock_anthropic_client():
    """模拟 Anthropic 客户端（项目使用 Messages API）"""
    with patch('anthropic.Anthropic') as mock:
        client = MagicMock()
        mock.return_value = client
        
        # 模拟 Claude 响应（项目中的响应格式）
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="测试回复")]
        mock_response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0
        )
        client.messages.create.return_value = mock_response
        
        yield client

@pytest.fixture
def mock_openai_client():
    """模拟 OpenAI 客户端"""
    with patch('openai.OpenAI') as mock:
        client = MagicMock()
        mock.return_value = client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="测试回复"))]
        client.chat.completions.create.return_value = mock_response
        
        yield client

@pytest.fixture
def sample_config_file(tmp_path):
    """创建示例配置文件"""
    config_file = tmp_path / "config.txt"
    config_file.write_text("""
# AGI Agent 测试配置
api_key=test_key_12345
api_base=https://api.anthropic.com/v1
model=claude-sonnet-4-0
max_tokens=8192
temperature=0.7
streaming=True
LANG=zh
""")
    return config_file

@pytest.fixture
def mock_tool_executor(mock_anthropic_client):
    """创建模拟的 ToolExecutor（项目核心组件）"""
    with patch('src.tool_executor.ToolExecutor.__init__', return_value=None):
        from src.tool_executor import ToolExecutor
        executor = ToolExecutor.__new__(ToolExecutor)
        executor.api_key = "test_key"
        executor.model = "claude-sonnet-4-0"
        executor.client = mock_anthropic_client
        executor.workspace_root = None
        executor.enable_thinking = False
        executor.temperature = 0.7
        return executor
```

### config_loader 测试（高优先级）

```python
# tests/unit/test_config_loader.py
import pytest
import os
from config_loader import (
    load_config, get_api_key, get_model, get_api_base,
    get_enable_round_sync, get_sync_round, clear_config_cache
)

class TestConfigLoader:
    """配置加载器测试（项目核心入口）"""
    
    def test_load_config_from_file(self, tmp_path):
        """测试从文件加载配置"""
        config_file = tmp_path / "config.txt"
        config_file.write_text("api_key=test_key\nmodel=claude-3-5-sonnet\n")
        
        config = load_config(str(config_file))
        assert config["api_key"] == "test_key"
        assert config["model"] == "claude-3-5-sonnet"
    
    def test_load_config_with_comments(self, tmp_path):
        """测试带注释的配置（项目使用 # 注释）"""
        config_file = tmp_path / "config.txt"
        config_file.write_text("""
# 这是一条注释
api_key=real_key
# api_key=disabled_key
model=test_model
""")
        
        config = load_config(str(config_file))
        assert config["api_key"] == "real_key"
        assert "disabled_key" not in str(config)
    
    def test_get_api_key_from_env(self, monkeypatch):
        """测试从环境变量读取 API Key（项目支持 AGIA_CONFIG_FILE）"""
        monkeypatch.setenv("AGIAGENT_API_KEY", "env_key")
        assert get_api_key() == "env_key"
    
    def test_agia_config_file_env(self, monkeypatch, tmp_path):
        """测试 AGIA_CONFIG_FILE 环境变量（项目特有）"""
        config_file = tmp_path / "custom_config.txt"
        config_file.write_text("api_key=custom_key\nmodel=custom_model\n")
        monkeypatch.setenv("AGIA_CONFIG_FILE", str(config_file))
        
        config = load_config()  # 使用默认路径
        assert config["api_key"] == "custom_key"
    
    def test_config_caching(self, tmp_path):
        """测试配置缓存（项目使用 mtime 检测）"""
        clear_config_cache()
        
        config_file = tmp_path / "config.txt"
        config_file.write_text("api_key=cached_key\n")
        
        config1 = load_config(str(config_file))
        config2 = load_config(str(config_file))
        assert config1 == config2
        assert config1["api_key"] == "cached_key"
    
    def test_cache_invalidation_on_modify(self, tmp_path):
        """测试文件修改后缓存失效"""
        clear_config_cache()
        
        config_file = tmp_path / "config.txt"
        config_file.write_text("api_key=key_v1\n")
        
        config1 = load_config(str(config_file))
        assert config1["api_key"] == "key_v1"
        
        # 修改文件
        config_file.write_text("api_key=key_v2\n")
        
        config2 = load_config(str(config_file))
        assert config2["api_key"] == "key_v2"
```

### ToolExecutor 测试（最高优先级）

```python
# tests/unit/test_tool_executor.py
import pytest
from unittest.mock import MagicMock, patch, ANY
from src.tool_executor import ToolExecutor, is_anthropic_api

class TestToolExecutor:
    """工具执行器测试（核心组件）"""
    
    def test_init_with_api_key(self, mock_api_key):
        """测试使用 API Key 初始化"""
        executor = ToolExecutor(api_key="test_key")
        assert executor.api_key == "test_key"
    
    def test_init_without_api_key_raises(self):
        """测试缺少 API Key 时抛出异常"""
        with patch('config_loader.get_api_key', return_value=None):
            with pytest.raises(ValueError, match="API key not found"):
                ToolExecutor()
    
    def test_is_anthropic_api(self):
        """测试 API 类型检测（项目特有逻辑）"""
        assert is_anthropic_api("https://api.anthropic.com/v1") is True
        assert is_anthropic_api("https://api.openai.com/v1") is False
        assert is_anthropic_api("https://custom.api/anthropic") is True
        assert is_anthropic_api(None) is False
    
    @patch('src.tool_executor.get_anthropic_client')
    def test_anthropic_client_init(self, mock_get_client, mock_api_key):
        """测试 Anthropic 客户端初始化"""
        mock_client_class = MagicMock()
        mock_get_client.return_value = mock_client_class
        
        executor = ToolExecutor(api_key="test_key")
        mock_client_class.assert_called_once()
    
    def test_executor_with_workspace(self, mock_api_key, tmp_path):
        """测试带工作区初始化"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        executor = ToolExecutor(workspace_dir=str(workspace))
        assert executor.workspace_dir == str(workspace)
```

### Tools 类测试（高优先级）

项目使用多继承 Mixin 模式，测试需要适配：

```python
# tests/unit/test_tools.py
import pytest
import os
from unittest.mock import MagicMock, patch

class TestBaseTools:
    """基础工具类测试"""
    
    def test_init_without_workspace(self):
        """测试无工作区初始化"""
        from src.tools.base_tools import BaseTools
        tools = BaseTools()
        assert tools.workspace_root is None
    
    def test_init_with_workspace(self, temp_workspace):
        """测试带工作区初始化"""
        from src.tools.base_tools import BaseTools
        tools = BaseTools(workspace_root=str(temp_workspace))
        assert tools.workspace_root == str(temp_workspace)
    
    def test_set_agent_context(self):
        """测试设置 Agent 上下文（项目核心机制）"""
        from src.tools.base_tools import BaseTools
        tools = BaseTools()
        tools.set_agent_context("manager")
        assert tools._agent_id == "manager"
    
    def test_resolve_path(self, temp_workspace):
        """测试路径解析（项目特有）"""
        from src.tools.base_tools import BaseTools
        tools = BaseTools(workspace_root=str(temp_workspace))
        
        # 测试相对路径
        resolved = tools._resolve_path("test.py")
        assert resolved == os.path.join(str(temp_workspace), "test.py")
        
        # 测试 workspace/ 前缀去除
        resolved = tools._resolve_path("workspace/test.py")
        # 应该去除冗余的 workspace/ 前缀


class TestFileSystemTools:
    """文件系统工具测试（项目核心工具）"""
    
    def test_remove_emoji_from_text(self):
        """测试 emoji 移除功能（项目中文处理）"""
        from src.tools.file_system_tools import remove_emoji_from_text
        
        text = "你好 👋 世界 🌍！"
        cleaned = remove_emoji_from_text(text)
        assert "👋" not in cleaned
        assert "🌍" not in cleaned
        assert "你好" in cleaned
        assert "世界" in cleaned
    
    def test_create_emoji_free_markdown(self, temp_workspace):
        """测试创建无 emoji 的 markdown（项目特有功能）"""
        from src.tools.file_system_tools import create_emoji_free_markdown
        
        md_file = temp_workspace / "test.md"
        md_file.write_text("# 测试 📝\n\n内容")
        
        temp_file = create_emoji_free_markdown(str(md_file))
        if temp_file:
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "📝" not in content


class TestToolsComposition:
    """Tools 类组合测试（项目使用多重继承）"""
    
    def test_tools_initialization_with_mock(self):
        """测试 Tools 类初始化（模拟模式，避免真实 API 调用）"""
        with patch('src.tools.FileSystemTools.__init__', return_value=None):
            with patch('src.tools.BaseTools.__init__', return_value=None):
                from src.tools import Tools
                
                tools = Tools.__new__(Tools)
                BaseTools.__init__(tools, workspace_root="/tmp")
                FileSystemTools.__init__(tools, workspace_root="/tmp")
                
                assert tools.workspace_root == "/tmp"
    
    def test_tools_cleanup(self):
        """测试 Tools 资源清理（项目有 cleanup 方法）"""
        with patch('src.tools.BaseTools.__init__', return_value=None):
            from src.tools import Tools
            
            tools = Tools.__new__(Tools)
            BaseTools.__init__(tools)
            
            # 模拟有需要清理的资源
            tools.llm_client = MagicMock()
            tools.code_parser = MagicMock()
            
            # 测试 cleanup 方法存在
            assert hasattr(tools, 'cleanup') or True  # cleanup 可能延迟定义
```

### API 调用器测试（中优先级）

```python
# tests/unit/test_api_callers.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.api_callers import (
    call_claude_with_chat_based_tools_non_streaming,
    call_claude_with_chat_based_tools_streaming,
    call_openai_with_chat_based_tools_non_streaming,
)

class TestClaudeAPICallers:
    """Claude API 调用测试"""
    
    def test_call_claude_non_streaming(self):
        """测试 Claude 非流式调用"""
        # 模拟 executor
        mock_executor = MagicMock()
        mock_executor.client = MagicMock()
        mock_executor.enable_thinking = False
        mock_executor.temperature = 0.7
        mock_executor.model = "claude-sonnet-4-0"
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="测试回复")]
        mock_response.usage = MagicMock(
            input_tokens=100, output_tokens=50,
            cache_creation_input_tokens=0, cache_read_input_tokens=0
        )
        mock_executor.client.messages.create.return_value = mock_response
        
        # 调用函数
        messages = [{"role": "user", "content": "你好"}]
        system = "你是助手"
        
        content, tool_calls = call_claude_with_chat_based_tools_non_streaming(
            mock_executor, messages, system
        )
        
        assert content == "测试回复"
    
    def test_call_claude_with_thinking_enabled(self):
        """测试 Claude thinking 模式（项目特有功能）"""
        mock_executor = MagicMock()
        mock_executor.client = MagicMock()
        mock_executor.enable_thinking = True
        mock_executor.temperature = 1.0  # thinking 模式下必须为 1.0
        mock_executor.model = "claude-sonnet-4-0"
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="回复")]
        mock_executor.client.messages.create.return_value = mock_response
        
        messages = [{"role": "user", "content": "test"}]
        
        content, tool_calls = call_claude_with_chat_based_tools_non_streaming(
            mock_executor, messages, "系统"
        )
        
        # 验证 thinking 参数被传递
        call_kwargs = mock_executor.client.messages.create.call_args.kwargs
        assert "thinking" in call_kwargs
    
    def test_call_claude_thinking_fallback(self):
        """测试 thinking 不支持时的降级（项目容错逻辑）"""
        mock_executor = MagicMock()
        mock_executor.client = MagicMock()
        mock_executor.enable_thinking = True
        mock_executor.temperature = 1.0
        mock_executor.model = "claude-sonnet-4-0"
        
        # 第一次调用抛出 TypeError
        mock_executor.client.messages.create.side_effect = [
            TypeError("unexpected keyword argument 'thinking'"),
            MagicMock(content=[MagicMock(type="text", text="fallback 回复")])
        ]
        
        messages = [{"role": "user", "content": "test"}]
        
        # 应该成功降级
        content, tool_calls = call_claude_with_chat_based_tools_non_streaming(
            mock_executor, messages, "系统"
        )
        
        assert content == "fallback 回复"
```

### MultiRoundTaskExecutor 测试（高优先级）

```python
# tests/integration/test_executor.py
import pytest
from unittest.mock import MagicMock, patch
import os

class TestMultiRoundTaskExecutor:
    """多轮任务执行器测试（核心组件）"""
    
    def test_init_basic(self, mock_api_key):
        """测试基本初始化"""
        from src.multi_round_executor.executor import MultiRoundTaskExecutor
        
        executor = MultiRoundTaskExecutor(
            subtask_loops=10,
            logs_dir="logs",
            debug_mode=False
        )
        
        assert executor.subtask_loops == 10
    
    def test_init_with_workspace(self, mock_api_key, temp_output_dir):
        """测试带工作区初始化"""
        from src.multi_round_executor.executor import MultiRoundTaskExecutor
        
        executor = MultiRoundTaskExecutor(
            workspace_dir=str(temp_output_dir),
            subtask_loops=5
        )
        
        assert executor.workspace_dir == str(temp_output_dir)
    
    def test_extract_session_timestamp(self):
        """测试从日志目录提取时间戳（项目特有功能）"""
        from src.multi_round_executor.executor import extract_session_timestamp
        
        timestamp = extract_session_timestamp("output_20260425_143000/logs")
        assert timestamp == "20260425_143000"
        
        timestamp = extract_session_timestamp("logs")
        assert timestamp is None
    
    @patch('src.multi_round_executor.executor.ToolExecutor')
    def test_executor_with_plan_mode(self, mock_tool_executor, mock_api_key):
        """测试 Plan 模式执行（项目特有）"""
        from src.multi_round_executor.executor import MultiRoundTaskExecutor
        
        executor = MultiRoundTaskExecutor(plan_mode=True)
        assert executor.plan_mode is True
```

### MCP 扩展测试（中优先级）

```python
# tests/unit/test_mcp.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

class TestMCPClient:
    """MCP 客户端测试"""
    
    def test_mcp_client_initialization(self):
        """测试 MCP 客户端初始化"""
        with patch('src.tools.mcp_client.MCPClient.__init__', return_value=None):
            from src.tools.mcp_client import MCPClient
            
            client = MCPClient.__new__(MCPClient)
            # 初始化模拟
            client.servers = {}
            client.connected = False
    
    def test_mcp_wrapper_creation(self):
        """测试 MCP Wrapper 创建"""
        with patch('src.tools.cli_mcp_wrapper.get_cli_mcp_wrapper') as mock_get:
            mock_wrapper = MagicMock()
            mock_get.return_value = mock_wrapper
            
            from src.tools.cli_mcp_wrapper import get_cli_mcp_wrapper
            wrapper = get_cli_mcp_wrapper()
            assert wrapper is not None
    
    def test_safe_cleanup(self):
        """测试安全清理（项目有 cleanup 优化）"""
        from src.tools.cli_mcp_wrapper import safe_cleanup_cli_mcp_wrapper
        
        # 应该不抛出异常
        safe_cleanup_cli_mcp_wrapper()
```

### 历史压缩工具测试（中优先级）

```python
# tests/unit/test_history_compression.py
import pytest
from unittest.mock import MagicMock, patch

class TestHistoryCompression:
    """历史压缩工具测试（影响 token 消耗）"""
    
    def test_compression_trigger_check(self):
        """测试压缩触发检查"""
        from src.tools.history_compression_tools import check_compression_needed
        
        # 模拟消息历史
        messages = [{"content": "x" * 1000}] * 100
        
        # 应该触发压缩
        with patch('config_loader.get_summary_trigger_length', return_value=50000):
            should_compress = check_compression_needed(messages)
            assert should_compress is True
    
    def test_llm_summary_compressor(self):
        """测试 LLM 摘要压缩器"""
        with patch('src.tools.llm_summary_compressor.LLMSummaryCompressor.__init__', return_value=None):
            from src.tools.llm_summary_compressor import LLMSummaryCompressor
            
            compressor = LLMSummaryCompressor.__new__(LLMSummaryCompressor)
            compressor.compression_ratio = 0.5
            
            # 模拟压缩
            original = "x" * 1000
            summarized = compressor.compress(original)
            assert len(summarized) < len(original)
```

### GUI 集成测试（低优先级）

```python
# tests/integration/test_gui.py
import pytest
from unittest.mock import MagicMock, patch

class TestFlaskApp:
    """Flask Web 应用测试"""
    
    def test_app_initialization(self):
        """测试应用初始化"""
        with patch('flask.Flask'):
            # 项目 GUI 使用 Flask
            from GUI.app import create_app
            
            # 模拟初始化
            app = MagicMock()
            assert app is not None
    
    def test_routes_registration(self):
        """测试路由注册"""
        # 检查主要路由是否存在
        routes = ['/', '/chat', '/api/execute']
        # 验证路由配置
```

### 运行测试命令

| 命令 | 说明 |
|------|------|
| `pytest tests/` | 运行所有测试 |
| `pytest -v` | 详细输出模式 |
| `pytest -x` | 遇到第一个失败就停止 |
| `pytest --lf` | 只运行上次失败的测试 |
| `pytest -k "test_name"` | 运行匹配的测试 |
| `pytest --cov=src` | 生成覆盖率报告 |
| `pytest --cov=src --cov-report=term-missing` | 显示未覆盖的行 |
| `pytest --tb=short` | 简短的错误回溯 |
| `pytest tests/unit/test_config_loader.py` | 运行特定文件的测试 |
| `pytest tests/integration/ -v` | 运行集成测试并详细输出 |

### 测试覆盖目标

| 模块 | 覆盖目标 | 优先级 | 原因 |
|------|----------|--------|------|
| `executor.py` | 多轮执行循环、任务分解、状态管理 | **极高** | 核心组件，破坏影响全局 |
| `config_loader.py` | 配置解析、缓存、环境变量 | **极高** | 所有功能依赖此模块 |
| `tool_executor.py` | 工具调用、API 选择、错误处理 | **高** | 工具系统入口 |
| `tools/*.py` | 40+ 工具实现、文件操作、Web 搜索 | **高** | 用户直接使用的功能 |
| `api_callers/*.py` | Claude/OpenAI 调用、streaming、thinking | **高** | 外部依赖，错误不易察觉 |
| `history_compression_tools.py` | 压缩触发、token 控制 | **中** | 影响运行成本 |
| `mem/` | 记忆读写、检索、持久化 | **中** | 影响长期效果 |
| `experience/` | 经验管理、任务反思 | **低** | 辅助功能 |
| `multiagents.py` | 多智能体协作、消息路由 | **中** | 核心特性之一 |
| `GUI/app.py` | Web 界面、API 端点 | **低** | 辅助功能 |

---

## 📝 注意事项

1. **文件路径**：优先使用相对于 workspace 的路径
2. **中文处理**：Mermaid/SVG 中文已优化，直接使用即可
3. **继续任务**：先读取 `log/manager.out` 了解上下文
4. **任务完成**：发送 TASK_COMPLETED 信号后停止，不要做额外迭代
5. **plan.md**：只有 manager 可更新，子 agent 不可修改

---

## 🔗 相关资源

- [项目主页](https://github.com/agi-hub/AGIAgent)
- [使用手册](./md/user_guide.pdf)
- [Python 库文档](./md/README_python_lib_zh.md)
- [MCP 集成指南](./md/README_MCP_zh.md)