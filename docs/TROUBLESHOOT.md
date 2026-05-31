# 故障排查指南

> **最后更新**：2026-05-31

---

## 目录

- [常见错误](#常见错误)
- [环境问题](#环境问题)
- [运行时问题](#运行时问题)
- [调试方法](#调试方法)

---

## 常见错误

### 错误 1: API Key Not Found

**症状**：
```
Error: API key not found in config
```

**原因**：`config/config.txt` 中未配置 `api_key`

**解决**：
1. 编辑 `config/config.txt`
2. 添加 `api_key=sk-your-api-key-here`
3. 确保格式正确（无引号）

```bash
# 验证配置
cat config/config.txt | grep api_key
```

---

### 错误 2: Port Already In Use

**症状**：
```
Error: Cannot start server: Port 5001 is already in use
```

**原因**：5001 端口被其他进程占用

**解决**：
```powershell
# 方法 1：使用其他端口
python GUI/app.py --port 5002

# 方法 2：查找并关闭占用进程
netstat -ano | findstr :5001
# 找到 PID 后
taskkill /PID <PID> /F
```

---

### 错误 3: Module Not Found

**症状**：
```
ModuleNotFoundError: No module named 'openai'
```

**原因**：依赖未安装

**解决**：
```powershell
# 重新安装依赖
pip install -r requirements.txt

# 或单独安装缺失的包
pip install openai anthropic flask flask-socketio
```

---

### 错误 4: Permission Denied

**症状**：
```
PermissionError: [Errno 13] Permission denied: '.venv'
```

**原因**：虚拟环境目录权限不足

**解决**：
```powershell
# 方法 1：使用管理员权限运行 PowerShell
# 右键 → 以管理员身份运行

# 方法 2：修复虚拟环境权限
icacls .venv /reset
icacls .venv /grant:r "%USERNAME%:(OI)(CI)F"

# 方法 3：删除后重建虚拟环境
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

### 错误 5: MCP Connection Failed

**症状**：
```
Error: MCP server connection failed
```

**原因**：MCP 服务器未启动或配置错误

**解决**：
1. 检查 `config/mcp_servers.json` 配置
2. 确认 MCP 服务器已安装
3. 验证服务器可执行

```bash
# 测试 MCP 服务器
npx -y @example/mcp-server --help
```

---

### 错误 6: Playwright Browser Error

**症状**：
```
Error: Executable doesn't exist at ...
```

**原因**：Playwright 浏览器未安装

**解决**：
```powershell
# 安装 Chromium
playwright install chromium

# 或安装所有浏览器
playwright install
```

---

## 环境问题

### 问题 1: Python 版本不兼容

**症状**：
```
SyntaxError: invalid syntax
```

**原因**：Python 版本低于 3.10

**解决**：
```powershell
# 检查 Python 版本
python --version

# 如需升级 Python
# 下载并安装 Python 3.13.7+
```

---

### 问题 2: 虚拟环境激活失败

**症状**：
```
Cannot activate virtual environment
```

**原因**：执行策略限制或路径问题

**解决**：
```powershell
# 临时允许脚本执行
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 或使用 CMD
cmd /c ".\.venv\Scripts\activate.bat"

# 或直接使用 Python 路径
.\.venv\Scripts\python.exe your_script.py
```

---

### 问题 3: 依赖安装缓慢

**症状**：pip install 超时或下载慢

**解决**：
```powershell
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或设置默认镜像
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 运行时问题

### 问题 1: LLM API 超时

**症状**：
```
TimeoutError: API request timeout
```

**解决**：
1. 检查网络连接
2. 增加超时配置
3. 使用重试机制

```python
# 在代码中增加超时
from openai import OpenAI

client = OpenAI(timeout=60.0)  # 60 秒超时
```

---

### 问题 2: 消息历史过长

**症状**：响应变慢或内存占用过高

**解决**：
- 系统会自动压缩过长的消息历史
- 可手动配置 `max_history` 限制

```python
# 在 ToolExecutor 中配置
tool_executor.max_history = 50  # 最大 50 条消息
```

---

### 问题 3: GUI 连接数超限

**症状**：
```
Error: Connection limit reached (40)
```

**原因**：同时连接数超过 40

**解决**：
1. 等待空闲连接释放
2. 重启 GUI 服务
3. 增加 `max_connections` 配置

---

## 调试方法

### 方法 1: 启用调试模式

```bash
# 在 config/config.txt 中设置
debug_mode=true
```

或启动时设置：
```powershell
python agia.py "任务" --debug
```

### 方法 2: 查看日志

```python
# 在代码中添加日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 或使用 DebugRecorder
debug_recorder = DebugRecorder()
debug_recorder.log("step", "description", data)
```

### 方法 3: 使用测试验证

```bash
# 运行单个测试
pytest tests/unit/test_tool_executor.py -v

# 运行带详细输出
pytest tests/ -v -s

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

### 方法 4: 逐步验证

```python
# 1. 验证配置加载
from src.config_loader import ConfigLoader
config = ConfigLoader()
print(config.get_api_key())

# 2. 验证工具注册
from src.tools import Tools
tools = Tools(workspace_root=".")
print(tools.tool_map.keys())

# 3. 验证 API 连接
from src.api_callers import OpenAICaller
caller = OpenAICaller()
print(caller.health_check())
```

---

## 诊断清单

### 快速诊断流程

```
❓ 问题发生
  │
  ├─ 是否安装问题？
  │   ├─ 检查 Python 版本 → python --version
  │   ├─ 检查依赖安装 → pip list
  │   └─ 检查虚拟环境 → which python
  │
  ├─ 是否配置问题？
  │   ├─ 检查 config.txt → cat config/config.txt
  │   ├─ 检查 API Key → echo $API_KEY
  │   └─ 检查 MCP 配置 → cat config/mcp_servers.json
  │
  ├─ 是否运行时问题？
  │   ├─ 检查端口占用 → netstat -ano | findstr :5001
  │   ├─ 检查进程状态 → ps aux | grep python
  │   └─ 检查日志输出 → 查看终端输出
  │
  └─ 是否网络问题？
      ├─ 检查网络连接 → ping api.openai.com
      └─ 检查代理设置 → echo $HTTP_PROXY
```

---

## 获取帮助

### 自助资源

1. **检查文档**：
   - [AGENTS.md](../AGENTS.md) — 主指南
   - [SETUP.md](SETUP.md) — 安装配置
   - [ARCHITECTURE.md](ARCHITECTURE.md) — 架构详解

2. **运行诊断**：
   ```bash
   python check_setup.py  # 来自 SETUP.md 的验证脚本
   ```

3. **查看日志**：
   - 启用 `debug_mode=true`
   - 观察终端输出

### 报告问题

报告问题时请包含：
- Python 版本：`python --version`
- 操作系统：Windows/Linux/macOS
- 完整错误信息
- 复现步骤
- 已尝试的解决方法

---

*返回 [AGENTS.md](../AGENTS.md)*