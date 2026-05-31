# 参考资料指南

> **最后更新**：2026-05-31

---

## 目录

- [核心目录](#核心目录)
- [重要文件](#重要文件)
- [配置文件](#配置文件)
- [开发命令](#开发命令)
- [代码规范](#代码规范)

---

## 核心目录

| 目录 | 用途 |
|------|------|
| `src/` | 核心源代码 |
| `src/tools/` | 46 个 Python 工具模块（Mixin 架构） |
| `src/multi_round_executor/` | 多轮任务编排 |
| `src/experience/` | 长期记忆（TaskReflection、ExperienceManager） |
| `src/api_callers/` | API 客户端（6 模块 × 3 种调用方式） |
| `src/mem/` | 短期记忆 / 历史压缩 |
| `src/utils/` | 工具函数 |
| `src/voice/` | 语音相关工具 |
| `GUI/` | Flask + SocketIO Web 界面 |
| `GUI/templates/` | HTML 模板 |
| `GUI/deployment/` | 多应用部署监控脚本 |
| `prompts/` | 系统提示词、工具定义 |
| `config/` | 配置文件 |
| `routine/` / `routine_zh/` | 技能模板 |
| `tests/` | pytest 测试套件 |
| `docs/` | 架构文档 |

---

## 重要文件

### 入口点

| 文件 | 用途 |
|------|------|
| `agia.py` | CLI 入口脚本（推荐使用） |
| `src/main.py` | 主程序（含 Python 库接口 AGIAgentClient） |
| `GUI/app.py` | Flask + SocketIO Web 应用 |

### 核心模块

| 文件 | 用途 |
|------|------|
| `src/tool_executor.py` | 核心执行器：LLM 设置、工具执行、历史管理 |
| `src/multi_round_executor/executor.py` | 多轮编排，轮次同步屏障 |
| `src/config_loader.py` | 平面文件配置加载，带缓存 |
| `src/tools/__init__.py` | 通过多继承动态构建的 Tools 类 |
| `src/tools/base_tools.py` | 基础 Mixin：workspace_root、code_parser、terminal_tools |
| `src/tools/fastmcp_wrapper.py` | FastMCP 服务器封装，支持持久化客户端和健康监控 |
| `src/tools/web_search_tools.py` | Web 搜索，带 LLM 过滤和智谱 AI 集成 |
| `src/experience/experience_manager.py` | 长期记忆编排 |
| `src/experience/task_reflection.py` | 任务回顾分析 |

---

## 配置文件

### 主配置 (config/config.txt)

```
api_key=sk-your-api-key
model=gpt-4o
streaming=true
language=zh
debug_mode=false
```

### MCP 配置 (config/mcp_servers.json)

```json
{
  "servers": [
    {
      "name": "example",
      "command": "npx",
      "args": ["-y", "@example/mcp-server"]
    }
  ]
}
```

### 其他配置

| 文件 | 用途 |
|------|------|
| `prompts/tool_prompt.json` | LLM 函数调用的 JSON 工具定义 |
| `prompts/system_prompt.txt` | 主系统提示词 |
| `prompts/multiagent_prompt.txt` | 多 Agent 执行指令 |
| `GUI/deployment/monitor_config.json` | 应用注册表 |
| `GUI/config/authorized_keys.json` | 身份验证密钥 |

---

## 开发命令

### 测试命令

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行特定测试文件
pytest tests/unit/test_tool_executor.py -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=term-missing

# 查看覆盖率详情
pytest tests/ --cov=src --cov-report=html
# 打开 htmlcov/index.html 查看报告
```

### 监控命令

```bash
# 启动守护进程
cd GUI/deployment && ./start_monitor_daemon.sh

# 查看守护进程状态
cd GUI/deployment && ./monitor_manager.sh status

# 重启守护进程
cd GUI/deployment && ./monitor_manager.sh restart
```

### 代码质量

```bash
# 代码格式化（如果配置了 black/isort）
black src/ tests/

# 代码检查（如果配置了 flake8/pylint）
pylint src/

# 类型检查（如果配置了 mypy）
mypy src/
```

---

## 代码规范

### 工具架构（Mixin）

工具在 `src/tools/__init__.py` 中使用多继承：

```python
class Tools(BaseTools, CodeSearchTools, FileSystemTools,
            TerminalTools, WebSearchTools, HelpTools,
            MouseTools, ImageGenerationTools,
            OptionalMCPKnowledgeBaseTools, OptionalPluginTools):
    """
    通过 Mixin 多继承组合所有工具模块。
    每个 Mixin 提供一组相关工具方法。
    """
```

**Mixin 规范**：
```python
class FileSystemTools:
    """
    文件系统工具 Mixin。
    所有工具方法接收 workspace_root 参数。
    返回 Dict[str, Any] 格式。
    """
    
    def __init__(self, workspace_root: str, **kwargs):
        self.workspace_root = workspace_root
    
    def read_file(self, path: str, **kwargs) -> Dict[str, Any]:
        """读取文件内容"""
        ...
```

### 工具注册

```python
# tool_map 映射
tool_map[tool_name] = tool_method

# tool_source_map 路由
tool_source_map[tool_name] = 'regular' | 'fastmcp' | 'cli_mcp'

# 工具定义加载
HelpTools._load_tool_definitions()  # 从 prompts/tool_prompt.json 加载
```

### 错误处理模式

```python
def cleanup(self):
    # 延迟导入，避免不必要地加载重型模块
    if 'fastmcp' in sys.modules:
        del sys.modules['fastmcp']
```

### 测试模式

```python
class TestToolExecutor:
    """测试类使用 Test<ClassName> 命名"""
    
    @pytest.fixture
    def tool_executor(self, mock_api_client):
        """Fixture 依赖注入"""
        return ToolExecutor(api_client=mock_api_client)
    
    def test_execute_tool_success(self, tool_executor):
        """测试成功执行"""
        result = tool_executor.execute_tool("read_file", path="test.txt")
        assert result["success"] is True
```

---

## 技术选型

| 方面 | 选择 |
|------|------|
| 运行时 | Python 3.13.7 |
| 虚拟环境 | `.venv` |
| 绿色版 Python | `python/` 目录 |
| Web 框架 | Flask + Flask-SocketIO |
| 异步 | gevent（主）、threading（回退） |
| 测试 | pytest + `unittest.mock` |
| API 客户端 | `openai`、`anthropic` |
| Web 自动化 | `playwright` |
| MCP | FastMCP + CLI-MCP |

---

*返回 [AGENTS.md](../AGENTS.md)*