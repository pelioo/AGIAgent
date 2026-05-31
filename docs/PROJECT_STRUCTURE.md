# 项目结构

## 目录概览

```
AGIAgent/
├── agia.py                 # CLI 入口
├── install.bat             # 安装脚本
├── src/                    # 核心源码
│   ├── main.py             # 库入口
│   ├── tool_executor.py    # 工具执行器
│   ├── multi_round_executor/  # 多轮任务执行器
│   ├── api_callers/        # LLM API 调用
│   ├── tools/              # 内置工具集
│   ├── experience/         # 经验系统
│   ├── mem/                # 记忆模块
│   ├── utils/              # 工具函数
│   └── voice/              # 语音模块
├── GUI/                    # Web 界面 (Flask)
│   ├── app.py              # 主应用
│   ├── auth_manager.py     # 认证管理
│   └── deployment/         # 部署配置
├── apps/                   # 应用扩展
│   ├── childedu/           # 儿童教育应用
│   ├── colordoc/           # 彩色文档应用
│   └── patent/              # 专利应用
├── docs/                   # 文档
├── prompts/                # 提示词模板
├── routine/                # 任务模板
├── routine_zh/             # 中文任务模板
├── config/                 # 配置文件
├── tests/                  # 测试
├── models/                 # 模型文件
├── dashboard/              # 仪表板
├── python/                  # 绿色版 Python
├── .venv/                  # 虚拟环境
└── requirements.txt        # 依赖
```

## 核心模块说明

### src/ - 核心源码

| 模块 | 说明 |
|------|------|
| `tool_executor.py` | 工具调用执行器，核心调度 |
| `multi_round_executor/` | 多轮对话任务执行 |
| `api_callers/` | OpenAI/Anthropic API 封装 |
| `tools/` | 内置工具集（文件、搜索、终端等） |
| `experience/` | 长期经验系统（TF-IDF） |
| `mem/` | 记忆模块（memoir + preliminary） |
| `utils/` | 通用工具函数 |

### GUI/ - Web 界面

基于 Flask + Flask-SocketIO 的实时 Web 界面。

### apps/ - 应用扩展

预配置的应用模板，支持特定领域的 Agent 行为。

### docs/ - 文档

| 文件 | 内容 |
|------|------|
| `SETUP.md` | 环境配置 |
| `ARCHITECTURE.md` | 架构详解 |
| `REFERENCE.md` | 命令参考 |
| `TOOLS.md` | 工具列表 |
| `TROUBLESHOOT.md` | 故障排查 |
| `PROJECT_STRUCTURE.md` | 本文档 |

### prompts/ - 提示词

Agent 系统提示词、工具定义、规则配置。

### routine/ - 任务模板

预定义的任务流程模板（如学术论文、专利、博客等）。

## 文件命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| Python 模块 | 蛇形命名 | `tool_executor.py` |
| 配置 | 蛇形命名 | `config.txt` |
| 文档 | 标题式/蛇形 | `PROJECT_STRUCTURE.md` |
| 应用 | 蛇形/中文 | `childedu/`, `colordoc/` |
| 测试 | `test_*.py` | `test_tools.py` |
