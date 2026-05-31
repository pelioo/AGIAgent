#!/usr/bin/env python3
"""
工具列表自动生成脚本
用于从 src/tools/ 目录自动提取工具定义并生成 docs/TOOLS.md

用法：
    python scripts/generate_tools_md.py
"""

import os
import re
from pathlib import Path
from typing import Dict, List

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
SRC_TOOLS_DIR = PROJECT_ROOT / "src" / "tools"
OUTPUT_FILE = PROJECT_ROOT / "docs" / "TOOLS.md"


def extract_tools_from_file(file_path: Path) -> List[Dict[str, str]]:
    """从工具文件中提取工具定义"""
    tools = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 匹配工具方法（以 def tool_ 或 def _tool_ 开头）
    pattern = r'def (_?\w+)\(self[,\s]*([^)]*)\):'
    matches = re.findall(pattern, content)
    
    for name, params in matches:
        # 过滤掉私有方法
        if name.startswith('_') and not name.startswith('_tool'):
            continue
        
        # 提取文档字符串
        doc_start = content.find(f'def {name}(')
        if doc_start == -1:
            continue
        
        doc_section = content[doc_start:doc_start + 500]
        doc_match = re.search(r'"""(.*?)"""', doc_section, re.DOTALL)
        
        description = ""
        if doc_match:
            description = doc_match.group(1).strip().split('\n')[0]
        
        tools.append({
            'name': name,
            'params': params.strip(),
            'description': description,
            'source': file_path.stem
        })
    
    return tools


def extract_mcp_tools() -> List[Dict[str, str]]:
    """从 MCP 配置中提取工具"""
    mcp_config = PROJECT_ROOT / "config" / "mcp_servers.json"
    
    if not mcp_config.exists():
        return []
    
    # 如果有 MCP 配置，添加占位符
    return [{
        'name': 'mcp_server_tools',
        'params': '...',
        'description': '动态加载的 MCP 服务器工具',
        'source': 'mcp_servers.json'
    }]


def generate_tools_md() -> str:
    """生成工具文档内容"""
    all_tools = []
    
    # 从 src/tools/ 目录提取工具
    if SRC_TOOLS_DIR.exists():
        for py_file in SRC_TOOLS_DIR.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            tools = extract_tools_from_file(py_file)
            all_tools.extend(tools)
    
    # 添加 MCP 工具
    all_tools.extend(extract_mcp_tools())
    
    # 按来源分组
    tools_by_source: Dict[str, List] = {}
    for tool in all_tools:
        source = tool.pop('source')
        if source not in tools_by_source:
            tools_by_source[source] = []
        tools_by_source[source].append(tool)
    
    # 生成 Markdown
    md_content = f"""# 工具列表

> **自动生成**：由 `scripts/generate_tools_md.py` 生成
> **生成时间**：最后更新

---

## 目录

"""
    
    for source in sorted(tools_by_source.keys()):
        anchor = source.replace('_', '-').lower()
        md_content += f"- [{source}](#{anchor})\n"
    
    md_content += "\n---\n\n"
    
    for source in sorted(tools_by_source.keys()):
        md_content += f"## {source}\n\n"
        md_content += "| 工具名称 | 参数 | 说明 |\n"
        md_content += "|----------|------|------|\n"
        
        for tool in tools_by_source[source]:
            name = f"`{tool['name']}`"
            params = f"`{tool['params']}`" if tool['params'] else "—"
            desc = tool['description'] or "—"
            md_content += f"| {name} | {params} | {desc} |\n"
        
        md_content += "\n"
    
    md_content += """---

## 使用说明

### 工具调用格式

```python
result = tool_executor.execute_tool("tool_name", param1="value1", param2="value2")
```

### 返回值格式

所有工具返回 `Dict[str, Any]`，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `result` | Any | 工具执行结果 |
| `error` | str | 错误信息（如有） |

### 工具来源

| 来源 | 说明 |
|------|------|
| `base_tools` | 基础工具（workspace_root、code_parser 等） |
| `file_system_tools` | 文件操作工具 |
| `terminal_tools` | 终端命令工具 |
| `web_search_tools` | 网页搜索工具 |
| `code_search_tools` | 代码导航工具 |
| `image_generation_tools` | 图像生成工具 |
| `mouse_tools` | 鼠标操作工具 |
| `help_tools` | 帮助系统 |
| `mcp_*` | MCP 服务器工具 |

---

*如需更新此文档，请运行 `python scripts/generate_tools_md.py`*  
*返回 [AGENTS.md](../AGENTS.md)*
"""
    
    return md_content


def main():
    """主函数"""
    print("正在生成工具列表文档...")
    
    # 生成内容
    content = generate_tools_md()
    
    # 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    
    # 统计
    tool_count = content.count('| `')
    file_count = content.count('## ')
    
    print(f"✅ 已生成 {OUTPUT_FILE}")
    print(f"   - 工具数量：{tool_count}")
    print(f"   - 来源文件：{file_count - 1}")  # 减去标题


if __name__ == "__main__":
    main()