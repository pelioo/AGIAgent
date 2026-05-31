# 环境配置指南

> **最后更新**：2026-05-31

---

## 目录

- [安装方式](#安装方式)
- [依赖说明](#依赖说明)
- [虚拟环境](#虚拟环境)
- [配置初始化](#配置初始化)
- [常见问题](#常见问题)

---

## 安装方式

### 方式一：双击运行（推荐）

```powershell
install.bat
```

### 方式二：PowerShell 运行

```powershell
.\install.ps1
```

安装脚本会自动：
- 创建/更新 `.venv` 虚拟环境
- 安装 `requirements.txt` 依赖
- 安装 Playwright Chromium 浏览器

---

## 依赖说明

### 主要依赖

| 类别 | 依赖 | 版本要求 |
|------|------|----------|
| API 客户端 | `openai` | ≥1.0 |
| API 客户端 | `anthropic` | ≥0.20 |
| Web 框架 | `flask` | 最新稳定版 |
| Web 框架 | `flask-socketio` | 最新稳定版 |
| 异步 | `gevent` | 最新稳定版 |
| Web 自动化 | `playwright` | 最新稳定版 |
| 测试 | `pytest` | 最新稳定版 |
| 测试 | `pytest-cov` | 最新稳定版 |

### 完整依赖列表

参见项目根目录 `requirements.txt`。

### 安装依赖（手动）

```powershell
# 激活虚拟环境后
pip install -r requirements.txt

# 安装 Playwright 浏览器（如果 install.ps1 未自动执行）
playwright install chromium
```

---

## 虚拟环境

### 目录结构

```
项目根目录/
├── .venv/              # 虚拟环境目录
├── python/             # 绿色版 Python（可选）
├── requirements.txt    # 依赖列表
└── ...
```

### 激活虚拟环境

```powershell
# PowerShell
.\.venv\Scripts\Activate.ps1

# CMD
.\.venv\Scripts\activate.bat

# Git Bash / WSL
source .venv/Scripts/activate
```

### 直接使用虚拟环境 Python

```powershell
.\.venv\Scripts\python.exe your_script.py
```

### 验证虚拟环境

```powershell
# 检查 Python 路径
where python

# 检查已安装的包
pip list | grep -E "openai|flask|pytest"
```

---

## 配置初始化

### 配置文件位置

```
config/
└── config.txt    # 主配置文件
```

### 配置文件格式

`config.txt` 使用 `key=value` 格式：

```bash
# 必需配置
api_key=sk-your-api-key-here
model=gpt-4o

# 可选配置
streaming=true
language=zh
debug_mode=false
```

### 配置项说明

| 配置项 | 必需 | 说明 | 默认值 |
|--------|------|------|--------|
| `api_key` | ✅ | LLM API 密钥 | — |
| `model` | ✅ | 默认模型 | gpt-4o |
| `streaming` | ❌ | 是否启用流式输出 | true |
| `language` | ❌ | 界面语言 | zh |
| `debug_mode` | ❌ | 调试模式 | false |

### MCP 服务器配置

MCP 服务器配置文件位于 `config/mcp_servers.json`：

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

---

## 常见问题

### Q1: 安装失败 - ModuleNotFoundError

**原因**：依赖未正确安装

**解决**：
```powershell
# 重新安装依赖
pip install -r requirements.txt

# 或使用 pip install 单独安装
pip install openai anthropic flask flask-socketio gevent
```

### Q2: Playwright 浏览器安装失败

**原因**：网络问题或权限不足

**解决**：
```powershell
# 使用管理员权限 PowerShell
# 安装 Chromium
playwright install chromium

# 如仍失败，尝试跳过浏览器安装
# 在代码中设置 headless 模式
```

### Q3: 虚拟环境激活失败

**原因**：PowerShell 执行策略限制

**解决**：
```powershell
# 查看当前执行策略
Get-ExecutionPolicy

# 临时允许本地脚本（当前会话）
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 或使用 CMD 运行
cmd /c ".\.venv\Scripts\activate.bat"
```

### Q4: 配置文件加载失败

**原因**：配置文件格式错误或路径不对

**解决**：
```python
# 检查配置文件路径
import os
config_path = "config/config.txt"
print(os.path.exists(config_path))

# 检查文件格式
with open(config_path, "r") as f:
    for line in f:
        print(line.strip())
```

### Q5: API Key 无效

**原因**：API Key 格式错误或已过期

**解决**：
1. 检查 `config/config.txt` 中的 `api_key=` 配置
2. 确保格式正确：`api_key=sk-xxx...`（无引号）
3. 验证 API Key 在对应平台有效

---

## 验证安装

### 快速验证脚本

```python
# check_setup.py
import sys

def check_setup():
    errors = []
    
    # 检查 Python 版本
    if sys.version_info < (3, 10):
        errors.append(f"Python 版本过低: {sys.version_info.major}.{sys.version_info.minor}")
    
    # 检查关键依赖
    required = ["openai", "anthropic", "flask", "pytest"]
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            errors.append(f"缺少依赖: {pkg}")
    
    # 检查配置文件
    import os
    if not os.path.exists("config/config.txt"):
        errors.append("配置文件不存在: config/config.txt")
    
    # 报告结果
    if errors:
        print("❌ 安装检查失败:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("✅ 安装检查通过")
        return True

if __name__ == "__main__":
    check_setup()
```

运行：
```powershell
python check_setup.py
```

---

*返回 [AGENTS.md](../AGENTS.md)*