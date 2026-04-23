# AGIAgent 项目 Pandoc 安装与使用指南

基于项目代码分析，以下是完整的 Pandoc 相关文档。

---

## 一、Pandoc 在项目中的用途

根据 `src/tools/file_system_tools.py` 中的代码，Pandoc 用于以下功能：

### 1. 文档转 Markdown（`convert_document_to_markdown` 方法）

支持的格式：

| 输入格式 | 输出格式 | 说明 |
|----------|----------|------|
| `.docx` | Markdown | Word 文档 |
| `.xlsx` | Markdown | Excel 表格 |
| `.html` | Markdown | 网页内容 |
| `.latex` | Markdown | LaTeX 文档 |
| `.rst` | Markdown | reStructuredText |
| `.pptx` | Markdown | PowerPoint |

### 2. Markdown 转 Word

使用 pandocfilters 过滤器处理后转换为 docx 格式。

### 3. Markdown 转 PDF/LaTeX

在 `src/utils/trans_md_to_pdf.py` 中配合 XeLaTeX 生成高质量 PDF。

### 4. SVG 中文处理

`src/utils/svg_chinese_filter.py` 使用 pandocfilters 进行 SVG 过滤。

---

## 二、安装方法

### 方法 1：winget 安装（推荐）

在 PowerShell 中运行：

```powershell
winget install --id JohnMacFarlane.Pandoc -e
```

### 方法 2：MSI 安装包

1. 访问 https://pandoc.org/installing.html
2. 下载 Windows MSI 安装包
3. 双击运行安装程序
4. 安装后自动添加到 PATH

### 方法 3：Portable 版本（项目本地）

1. 从 https://pandoc.org/installing.html 下载 portable 版本
2. 将可执行文件放入 `Extend-dependenc\pandoc\`
3. 将该路径添加到系统 PATH 环境变量

### 方法 4：本地 MSI（自动安装）

将 `pandoc.msi` 文件放入 `Extend-dependenc\` 目录，运行 install.ps1 时会自动检测并安装。

---

## 三、验证安装

安装后运行以下命令验证：

```powershell
pandoc --version
```

输出应显示 Pandoc 版本号，例如：

```
pandoc 3.1.12.3
User-agent: https://pandoc.org/MILESTONE
```

如果显示"命令未找到"，请重新启动终端或检查 PATH 环境变量。

---

## 四、项目集成方式

### 核心调用代码

项目通过 subprocess 调用 pandoc 命令：

```python
# src/tools/file_system_tools.py 中的调用方式
cmd = [
    'pandoc',
    input_file,
    '-o', output_file,
    '-f', format_type,  # docx, latex, html 等
    '-t', 'gfm'         # 输出为 GitHub Flavored Markdown
]
result = subprocess.run(cmd, ...)
```

### PDF 转换（配合 XeLaTeX）

```python
# src/utils/trans_md_to_pdf.py
cmd = [
    'pandoc',
    input_file,
    '-o', output_file,
    '-pdf-engine=xelatex',
    '--pdf-engine-opts=-shell-escape'
]
```

---

## 五、依赖关系

| 依赖项 | 说明 | 状态 |
|--------|------|------|
| `pandoc>=2.0.0` | 声明在 requirements.txt 中 | 必须安装 |
| `pandocfilters` | Python 过滤器库，配合 pandoc 使用 | pip 安装 |
| `markitdown` | 备选文档转换方案 | 部分替代 |

---

## 六、常见问题

### Q: Pandoc 未找到怎么办？

**A:** 检查以下三点：
1. 确认 pandoc 已安装且添加到 PATH
2. 重启终端或 IDE 使环境变量生效
3. 使用完整路径调用：`C:\Program Files\Pandoc\pandoc.exe`

### Q: 能否完全移除 Pandoc 依赖？

**A:** 可以使用 `markitdown` 作为部分替代，但它对 LaTeX 和 Word 的支持较弱。完全移除需要重构以下功能：

- Markdown → Word 转换（用 python-docx 替代）
- LaTeX → PDF 转换（用其他 PDF 库替代）
- 文档解析（用 markitdown 替代部分场景）

重构成本较高，不建议在当前阶段进行。

### Q: 如何获取最新版本？

**A:** 访问 https://pandoc.org/installing.html 下载最新版本。

### Q: 安装后仍提示找不到 Pandoc？

**A:** 项目中 pandoc 会被 `Test-Pandoc` 函数检测。如果安装后仍有问题：

1. 检查 pandoc 是否在 PATH 中：
   ```powershell
   where.exe pandoc
   ```

2. 或者直接在代码中使用完整路径

---

## 七、相关文件列表

| 文件路径 | 用途 |
|----------|------|
| `src/tools/file_system_tools.py` | 文档转换核心逻辑 |
| `src/utils/trans_md_to_pdf.py` | Markdown 转 PDF |
| `src/utils/svg_chinese_filter.py` | SVG 中文过滤器 |
| `install.ps1` | 安装脚本中的 Pandoc 安装逻辑 |
| `requirements.txt` | pandoc 和 pandocfilters 依赖 |

---

## 八、与其他工具的配合

Pandoc 在项目中的工作流程：

```
用户文档 (docx/xlsx/html/latex/pptx)
         ↓
    Pandoc 转换
         ↓
Markdown 文件
    ↓          ↓
Word 文档    PDF/LaTeX
         ↓
   XeLaTeX → 最终 PDF
```

Pandoc 负责"中间转换"角色，连接各种文档格式与项目的工作流程。

---

*文档更新时间：2026-04-24*