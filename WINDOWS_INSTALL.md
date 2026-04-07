# AGIAgent Windows 安装指南

## 📋 概述

本指南帮助 `Windows` 用户在本地项目中设置AGIAgent开发环境。

## 🚀 快速开始

### 方法一：双击运行（推荐）

1. 确保绿色版Python在项目根目录的 `python` 文件夹中
2. 双击运行 `install.bat`
3. 按照提示完成安装

### 方法二：PowerShell运行

```powershell
.\install.ps1
```

或

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

## 📦 安装内容

脚本将自动完成以下安装：

### ✅ 自动化安装
- ✅ Python版本检查（使用本地绿色版）
- ✅ 虚拟环境创建/更新（`.venv`）
- ✅ Python依赖包安装（requirements.txt）
- ✅ Playwright Chromium浏览器安装

### ⚡ 半自动化安装
- ⚠️ Pandoc文档转换工具
  - 自动：使用winget（如果可用）
  - 手动：提供下载链接

- ⚠️ XeLaTeX/MiKTeX（PDF生成）
  - 自动：使用winget（如果可用）
  - 手动：提供下载链接

### ❌ 无需安装
- 中文字体：Windows自带
- Cairo库：cairosvg在Windows下使用备用方案

## 🔧 系统要求

- Windows 10/11
- PowerShell 5.0+
- winget（可选，用于自动安装Pandoc和MiKTeX）
- 绿色版Python 3.8+（已在项目中）

## 📁 安装后结构

```
项目根目录/
├── python/              # 绿色版Python
│   └── python.exe
├── .venv/               # 虚拟环境
│   └── Scripts/
├── requirements.txt     # 依赖列表
├── install.bat          # Windows安装脚本
└── install.ps1          # PowerShell核心脚本
```

## 💡 使用方法

### 1. 激活虚拟环境

在PowerShell中：

```powershell
.\.venv\Scripts\Activate.ps1
```

或直接使用虚拟环境中的Python：

```powershell
.\.venv\Scripts\python.exe your_script.py
```

### 2. 配置API密钥

编辑 `config\config.txt` 文件，填入你的API密钥。

### 3. 运行应用

**GUI模式：**
```bash
python GUI\app.py
```

**CLI模式：**
```bash
python agia.py "写一首诗"
```

## 🔧 常见问题

### Q1: winget未找到怎么办？

手动下载安装Pandoc和MiKTeX：
- Pandoc: https://pandoc.org/installing.html
- MiKTeX: https://miktex.org/download

### Q2: 虚拟环境创建失败？

确保Python路径正确：
```powershell
.\python\python.exe --version
```

### Q3: Playwright安装失败？

在虚拟环境中手动安装：
```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

### Q4: pip安装依赖失败？

检查requirements.txt是否存在，或手动安装：
```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

## 📚 更多信息

- 项目文档：[README.md](README.md)
- 安装指南：[md/INSTALL_zh.md](md/INSTALL_zh.md)

## 🆘 获取帮助

如果遇到问题：
1. 查看错误日志
2. 检查Python版本
3. 确认requirements.txt文件存在
4. 参考Linux/Mac安装脚本：install.sh
