# AGIAgent 测试指南

> 本文件提供 AGIAgent 项目的测试框架、运行方法和最佳实践。

---

## 📁 测试目录结构

```
tests/
├── conftest.py                     # pytest 配置和 12 个 fixtures
├── TESTING.md                      # 本文件 - 测试指南
├── unit/                           # 单元测试
│   ├── test_config_loader.py       # 配置加载器（43 个测试）
│   ├── test_tool_executor.py       # 工具执行器（15 个测试）
│   ├── test_tools.py               # 工具类（19 个测试）
│   └── test_api_callers.py         # API 调用器（13 个测试）
├── integration/                     # 集成测试
│   └── test_executor.py            # 执行器集成测试（23 个测试）
└── fixtures/                       # 测试数据
    ├── sample_config.txt
    └── sample_config_minimal.txt
```

---

## 🚀 快速开始

### 安装测试依赖

```bash
# 使用项目虚拟环境
.venv\Scripts\pip install pytest pytest-cov pytest-mock

# 或安装 dev 依赖
.venv\Scripts\pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=src --cov-report=html tests/

# 详细输出
pytest tests/ -v

# 简短的错误回溯
pytest --tb=short

# 运行特定文件
pytest tests/unit/test_config_loader.py

# 只运行上次失败的测试
pytest --lf

# 遇到第一个失败就停止
pytest -x
```

---

## 🔧 Fixtures 说明

`conftest.py` 提供了与实际类签名匹配的 fixtures：

| Fixture | 用途 |
|---------|------|
| `setup_python_path` | 自动将项目根目录加入 sys.path |
| `mock_api_key_env` | 设置测试环境变量（AGIAGENT_API_KEY 等） |
| `sample_config_file` | 创建完整配置测试文件 |
| `sample_config_file_minimal` | 创建最小化配置测试文件 |
| `temp_workspace` | 创建 output_YYYYMMDD_HHMMSS/workspace 结构 |
| `empty_workspace` | 创建简单 workspace 目录 |
| `tool_executor_instance` | ToolExecutor 实例（无 workspace） |
| `tool_executor_with_workspace` | ToolExecutor 实例（带 workspace） |
| `base_tools_instance` | BaseTools 实例 |
| `base_tools_with_workspace` | BaseTools 实例（带 workspace） |
| `tools_instance_minimal` | 最小化 Tools 实例（mock 可选依赖） |
| `multi_round_executor_instance` | MultiRoundTaskExecutor 实例 |
| `multi_round_executor_with_workspace` | MultiRoundTaskExecutor（带 workspace） |
| `api_executor_mock` | API 调用器测试用的模拟 executor |
| `mock_anthropic_client` | 模拟 Anthropic 客户端 |
| `mock_openai_client` | 模拟 OpenAI 客户端 |
| `clean_config_cache` | 清理配置缓存（测试隔离用） |

---

## 📚 测试覆盖目标

### 已完成 ✅

| 模块 | 覆盖目标 |
|------|----------|
| `config_loader.py` | 配置解析、缓存、环境变量、API 优先级 |
| `tool_executor.py` | API 检测、workspace 管理 |
| `tools/*.py` | BaseTools、Tools 初始化、agent context |
| `api_callers/*.py` | Claude/OpenAI 调用、streaming/非 streaming |
| `executor.py` | 多轮执行、session timestamp 提取 |

### 待补充

| 模块 | 说明 |
|------|------|
| `tools_plugin.py` | 插件工具 |
| `mcp_client.py` | MCP 客户端 |
| `history_compression_tools.py` | 历史压缩 |
| `mem/` | 记忆系统 |

---

## ⚠️ 测试注意事项

### 1. 类签名与实际代码匹配

- `Tools` 类使用**条件多重继承**（取决于 `MCP_KB_TOOLS_AVAILABLE` 和 `PLUGIN_TOOLS_AVAILABLE`），fixtures 会 mock 可选依赖
- 使用 `object.__new__(Tools)` 和手动设置属性来创建最小化实例

### 2. API 检测逻辑

- `is_anthropic_api()` 函数检查 URL 是否以 `/anthropic` 结尾
- 示例：`"https://custom.endpoint/anthropic"` 返回 `True`

### 3. 环境变量优先级

`get_api_key()` 优先级：
1. `AGIBOT_API_KEY`（最高）
2. config 文件中的 `api_key`
3. `AGIAGENT_API_KEY`（最低）

### 4. 测试隔离

- 每个测试函数使用 `clean_config_cache` fixture 确保配置缓存被清理
- 涉及环境变量的测试使用 `monkeypatch` 和不存在的 config 文件路径避免读取真实配置

### 5. Windows mtime 精度

- Windows 文件系统 mtime 精度为 1 秒
- 缓存失效测试使用 `time.sleep(1.1)` 确保 mtime 变化

---

## 📝 测试规范

### 测试命名

```python
class TestConfigLoader:       # 模块名
    def test_load_config_basic(self, ...):  # 功能描述
        ...

class TestIsAnthropicApi:   # 函数/类名
    def test_is_anthropic_api_true(self, ...):  # 场景描述
        ...
```

### Fixture 依赖

```python
@pytest.fixture
def my_fixture():
    """描述 fixture 的用途"""
    ...
```

### Mock 策略

- 使用 `@patch` 装饰器或 `with patch()` 上下文管理器
- 优先 mock 外部依赖（API 客户端、文件系统）
- 不要 mock 被测试的核心逻辑

---

## 🔗 相关资源

- [pytest 文档](https://docs.pytest.org/)
- [pytest-mock 文档](https://pytest-mock.readthedocs.io/)
- [CLAUDE.md](../CLAUDE.md) - 项目主文档
