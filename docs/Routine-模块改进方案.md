# Routine 模块改进方案

> **核心目标**：参考标准 Skills 规范改进 Routine 模块，支持多文件引用和脚本执行。

---

## 一、现有代码分析

### 1.1 调用链验证

**main.py (行 837-838)**：
```python
if self.routine_file:
    enhanced_requirement = append_routine_to_requirement(user_requirement, self.routine_file)
```

**结论**：main.py 无需改动，只传递 `routine_file` 字符串给 `routine_utils.py`

**routine_utils.py**：
```python
def append_routine_to_requirement(user_requirement: str, routine_file: str) -> str:
    routine_content = read_routine_content(routine_file)
```

### 1.2 现有文件格式

| 文件 | 格式 |
|------|------|
| `routine_zh/彩文：图文博客+公众号+小红书.txt` | `.txt` 纯文本 |
| `routine_zh/多智能体辩论.md` | `.md` 无 front_matter |

---

## 二、改进目标

1. ✅ **格式升级**：`.txt` → `.md` + front_matter
2. ✅ **多文件引用**：`{{include: xxx.md}}` 模块化组织
3. ✅ **脚本执行**：`{{script: scripts/xxx.py}}` AI 可执行脚本
4. ✅ **灵活命名**：保持现有文件名称
5. ✅ **可选扩展**：同名文件夹（当需要脚本时）

---

## 三、标准文件结构

### 3.1 基础结构（单文件）

```
routine_zh/
├── 彩文.md                    # 主文件，名称保持现有
├── 多智能体辩论.md             # 主文件
├── 编程：写个小游戏或软件.txt   # .txt → .md
└── ...
```

### 3.2 扩展结构（需要脚本时）

```
routine_zh/
├── 彩文.md                    # 主文件
└── 彩文/                      # 可选同名文件夹
    ├── scripts/
    │   └── generate_title.py
    ├── chapters/
    │   ├── intro.md
    │   └── summary.md
    └── templates/
        └── template.html
```

---

## 四、文件格式规范

### 4.1 主文件格式（.md + front_matter）

```yaml
---
title: 彩文写作
description: 适用于公众号、网络平台图文博客文章
routine_category: content
author: system
version: 1.0
created_at: '2026-01-01'
updated_at: '2026-04-10'
---

# 图文博客写作技巧

{{include: chapters/intro.md}}

## 标题生成

使用脚本生成吸引人的标题：

{{script: scripts/generate_title.py --style "clickbait"}}

{{include: chapters/examples.md}}

## 内容结构

1. 吸睛开头
2. 实用内容
3. 有力结尾

{{include: chapters/summary.md}}
```

### 4.2 front_matter 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `title` | 是 | Routine 标题 |
| `description` | 否 | Routine 描述 |
| `routine_category` | 否 | Routine 分类 |
| `author` | 否 | 作者 |
| `version` | 否 | 版本号 |
| `created_at` | 否 | 创建时间 |
| `updated_at` | 否 | 更新时间 |

---

## 五、核心语法

### 5.1 {{include:}} 多文件引用

引用同名文件夹下的其他文件：

```
{{include: chapters/intro.md}}
{{include: scripts/utils.py}}
```

**读取逻辑**：
- 相对于主文件所在目录解析路径
- 支持嵌套引用（递归处理）

### 5.2 {{script:}} 脚本执行

执行同名文件夹下的脚本：

```
{{script: scripts/generate_title.py --style "clickbait"}}
{{script: scripts/analyze.py --input "data.json"}}
```

**执行逻辑**：
- 相对于主文件所在目录解析路径
- 超时时间：30秒
- 输出结果以代码块形式返回

---

## 六、改进方案

### 6.1 Routine 工具模块（仅修改此文件）

**文件**：`src/routine_utils.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routine 工具模块
支持多文件引用、脚本执行、front_matter 解析
"""

import os
import re
import subprocess
import yaml
from typing import Optional


def read_routine_content(routine_path: str) -> Optional[str]:
    """
    读取 Routine 内容，支持单文件和文件夹扩展
    
    Args:
        routine_path: Routine 文件路径（.md 或 .txt）
    
    Returns:
        处理后的 Routine 内容
    """
    routine_path = routine_path.strip()
    
    if not routine_path or not os.path.exists(routine_path):
        return None
    
    # 获取基础目录
    base_dir = os.path.dirname(os.path.abspath(routine_path))
    
    # 读取主文件内容
    content = _read_file(routine_path)
    if not content:
        return None
    
    # 获取主文件名（不含扩展名）
    main_filename = os.path.splitext(os.path.basename(routine_path))[0]
    
    # 查找同名文件夹
    sibling_folder = os.path.join(base_dir, main_filename)
    
    # 处理 includes 和 scripts
    content = _process_includes(content, base_dir, main_filename)
    content = _process_scripts(content, base_dir, main_filename)
    
    return content


def _read_file(file_path: str) -> str:
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def _get_sibling_folder(base_dir: str, main_filename: str) -> Optional[str]:
    """获取同名文件夹"""
    sibling = os.path.join(base_dir, main_filename)
    if os.path.isdir(sibling):
        return sibling
    return None


def _process_includes(content: str, base_dir: str, main_filename: str) -> str:
    """处理 {{include: path}} 引用"""
    include_pattern = r'\{\{include:\s*([^}]+)\}'
    sibling_folder = _get_sibling_folder(base_dir, main_filename)
    
    def replace_include(match):
        include_path = match.group(1).strip()
        
        # 优先从同名文件夹查找
        if sibling_folder:
            full_path = os.path.join(sibling_folder, include_path)
            if os.path.exists(full_path):
                included_content = _read_file(full_path)
                # 递归处理嵌套 includes
                return _process_includes(included_content, base_dir, main_filename)
        
        # 回退到基础目录
        full_path = os.path.join(base_dir, include_path)
        if os.path.exists(full_path):
            included_content = _read_file(full_path)
            return _process_includes(included_content, base_dir, main_filename)
        
        return f"[Include not found: {include_path}]"
    
    return re.sub(include_pattern, replace_include, content)


def _process_scripts(content: str, base_dir: str, main_filename: str) -> str:
    """处理 {{script: path [args]}} 脚本执行"""
    script_pattern = r'\{\{script:\s*([^}]+)\}'
    sibling_folder = _get_sibling_folder(base_dir, main_filename)
    
    def replace_script(match):
        script_cmd = match.group(1).strip()
        parts = script_cmd.split(None, 1)
        script_path = parts[0]
        script_args = parts[1] if len(parts) > 1 else ""
        
        # 优先从同名文件夹查找
        full_path = None
        if sibling_folder:
            candidate = os.path.join(sibling_folder, script_path)
            if os.path.exists(candidate):
                full_path = candidate
        
        # 回退到基础目录
        if not full_path:
            full_path = os.path.join(base_dir, script_path)
            if not os.path.exists(full_path):
                return f"[Script not found: {script_path}]"
        
        # 执行脚本
        try:
            cmd = [full_path]
            if script_args:
                cmd.extend(script_args.split())
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.dirname(full_path)
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                return f"\n```script_output\n{output}\n```\n"
            else:
                return f"\n[Script error: {result.stderr}]\n"
        
        except subprocess.TimeoutExpired:
            return "\n[Script timeout]\n"
        except Exception as e:
            return f"\n[Script error: {str(e)}]\n"
    
    return re.sub(script_pattern, replace_script, content)


def _parse_front_matter(content: str) -> dict:
    """解析 front_matter"""
    if not content.startswith('---'):
        return {}
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}
    
    try:
        return yaml.safe_load(parts[1]) or {}
    except:
        return {}


def format_routine_for_single_task(routine_content: str) -> str:
    """格式化 Routine 内容"""
    if not routine_content:
        return ""
    
    return f"""

This is the recommended routine you should follow for this task:

{routine_content}"""


def append_routine_to_requirement(user_requirement: str, routine_file: str) -> str:
    """
    追加 Routine 内容到用户需求
    
    Args:
        user_requirement: 用户原始需求
        routine_file: Routine 文件路径
    
    Returns:
        增强后的需求
    """
    if not routine_file:
        return user_requirement
    
    routine_content = read_routine_content(routine_file)
    if not routine_content:
        return user_requirement
    
    formatted_routine = format_routine_for_single_task(routine_content)
    enhanced_requirement = user_requirement + formatted_routine
    
    return enhanced_requirement
```

---

## 七、使用示例

### 7.1 命令行

```bash
# 单个 Routine
python agia.py --routine "routine_zh/彩文.md"

# 多选组合（逗号分隔）
python agia.py --routine "routine_zh/彩文.md,routine_zh/多智能体辩论.md"
```

### 7.2 GUI

用户通过界面多选 Routines，路径逗号分隔传入。

---

## 八、与标准 Skills 规范对比

| 标准 Skills 规范 | Routine 改进方案 | 符合度 |
|-----------------|-----------------|--------|
| **front_matter** | ✅ 支持 | ✅ |
| **`{{include:}}` 语法** | ✅ 支持 | ✅ |
| **`{{script:}}` 语法** | ✅ 支持 | ✅ |
| **脚本执行** | ✅ 支持 | ✅ |
| **模块化组织** | ✅ 支持 | ✅ |
| **主文件命名** | 任意名称（保持现有） | ⚠️ 差异 |
| **必须同名文件夹** | 可选 | ⚠️ 差异 |

---

## 九、迁移策略

### 9.1 批量迁移脚本

```python
#!/usr/bin/env python3
"""迁移 .txt 文件为 .md 格式"""

import os
import yaml
from datetime import datetime

def migrate_txt_to_md(txt_path, target_path):
    """将 .txt 迁移为 .md 格式"""
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filename = os.path.basename(txt_path).replace('.txt', '')
    front_matter = {
        'title': filename,
        'description': '',
        'routine_category': 'general',
        'author': 'system',
        'version': '1.0',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
    }
    
    yaml_content = yaml.dump(front_matter, allow_unicode=True)
    
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(f"---\n{yaml_content}---\n\n{content}")
    
    print(f"Migrated: {txt_path} -> {target_path}")


# 批量迁移 routine_zh 目录
for txt_file in os.listdir('routine_zh'):
    if txt_file.endswith('.txt'):
        txt_path = os.path.join('routine_zh', txt_file)
        md_filename = txt_file.replace('.txt', '.md')
        target_path = os.path.join('routine_zh', md_filename)
        migrate_txt_to_md(txt_path, target_path)
```

### 9.2 迁移示例

| 原文件 | 新文件 |
|--------|--------|
| `routine_zh/彩文.txt` | `routine_zh/彩文.md` |
| `routine_zh/多智能体辩论.md` | `routine_zh/多智能体辩论.md`（已升级格式） |

---

## 十、文件改动清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/routine_utils.py` | **修改** | **仅此一个文件** |

---

## 十一、预估工作量

| 任务 | 时间 | 说明 |
|------|------|------|
| routine_utils.py | 1-2周 | 核心实现 |
| 迁移脚本 | 0.5天 | .txt → .md 格式 |
| 测试 | 1-2天 | 功能测试 |
| **总计** | **2-3周** | |

---

*文档版本: 7.0*
*更新时间: 2026-04-10*
