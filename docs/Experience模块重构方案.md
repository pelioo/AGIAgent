# Experience 模块重构方案

> 文档版本：v3.1  
> 创建日期：2026-04-11  
> 更新日期：2026-04-11  
> 更新说明：v3.1 补充 tool_executor.py 变量名（_skill_disabled_error, skill_query_section）、打印消息（"Skill tools registered" 等）、详细行号定位等遗漏项

> **目标**：将 `skill_evolve` 模块重构为 `experience` 模块，释放 `skills` 概念，为未来实现规范的 Skills 模块让位

---

## 一、重构背景

### 1.1 问题描述

当前项目存在两套概念重叠的系统：

```
skill_evolve/          ← 当前模块名称
├── skill_tools.py      # 工具类
├── task_reflection.py  # 反思生成
└── skill_manager.py    # 整理管理
```

**问题**：`skill_evolve` 模块虽然功能上是"经验管理"，但命名上占用了 `skill` 概念，导致：
- 与真正的 Skills 模块（可执行技能包）概念混淆
- 阻碍未来扩展规范的 Skills 模块
- 代码审查和文档中概念不清

### 1.2 当前问题统计

| 文件 | "skill" 引用数量 | 说明 |
|------|-----------------|------|
| `skill_tools.py` | 135+ 处 | 包含类名、方法名、变量名、注释、错误消息 |
| `skill_manager.py` | 21+ 处 | 同上 |
| `task_reflection.py` | 21+ 处 | 同上 |

### 1.3 重构目标

1. **正名**：`skill_evolve` → `experience`（经验模块）
2. **解耦**：释放 `skill` 相关概念，为未来 Skills 模块让位
3. **彻底**：不仅改类名/方法名，还需改注释、错误消息、匹配逻辑
4. **安全**：有备份和回滚方案

---

## 二、重构策略

### 2.1 方案选择：彻底方案

| 方案 | 改动范围 | 优缺点 |
|------|----------|--------|
| 保守方案 | 只改类名、方法名、变量名 | 快速，但注释仍含 skill，容易混淆 |
| **彻底方案** | 类名 + 方法名 + 注释 + 错误消息 + 匹配逻辑 | 干净彻底，改动大但风险可控 |

**选择理由**：
- 重构目的就是"释放 skills 概念"，不彻底就白改
- 注释/错误消息仍含 skill，会让后来者困惑
- 匹配逻辑必须改，否则改名后的文件无法被检索

### 2.2 彻底方案范围

```
✅ 目录重命名：skill_evolve → experience
✅ 文件重命名：skill_tools.py → experience_tools.py 等
✅ 类名改动：SkillTools → ExperienceTools
✅ 方法名改动：query_skill → query_experience
✅ 变量名改动：self.skill_tools → self.experience_tools
✅ 注释改动：全部 "skill" 相关注释 → "experience"
✅ Docstring 改动：模块/类/方法文档
✅ 错误消息改动：print_error / return message
✅ 文件匹配逻辑：skill_*.md → experience_*.md 【关键！】
✅ 变量名：skills → experiences, skill_files → experience_files
✅ prompts 工具定义文件改动
✅ tool_executor 帮助注释改动
✅ 返回字典字段名改动
```

---

## 三、重构范围

### 3.1 涉及文件

| 序号 | 当前路径 | 重命名后路径 | 改动类型 |
|------|----------|--------------|----------|
| 1 | `src/skill_evolve/` | `src/experience/` | 目录重命名 |
| 2 | `src/skill_evolve/__init__.py` | `src/experience/__init__.py` | 内容更新 |
| 3 | `src/skill_evolve/skill_tools.py` | `src/experience/experience_tools.py` | 文件重命名 + 彻底改内容 |
| 4 | `src/skill_evolve/skill_manager.py` | `src/experience/experience_manager.py` | 文件重命名 + 彻底改内容 |
| 5 | `src/skill_evolve/task_reflection.py` | `src/experience/task_reflection.py` | 改引用，不改名 |
| 6 | `src/tool_executor.py` | - | import 路径 + 方法名更新 + 注释更新 |
| 7 | `prompts/memory_tools.json` | - | 工具定义更新 + 描述文本更新 |
| 8 | `data/*/general/experience/skill_*.md` | `experience_*.md` | 数据文件重命名 + 内容更新 |

### 3.2 不涉及的文件

| 文件 | 原因 |
|------|------|
| `src/mem/` | 独立的记忆模块，不涉及 skills 概念 |
| `src/tools/long_term_memory.py` | 包装器，复用 mem 模块 |
| `src/skill_evolve/task_reflection.py` | 文件名中性，不含 skill 关键词 |

---

## 四、详细改动清单

### 4.1 文件重命名操作

```bash
# 1. 重命名目录
mv src/skill_evolve/ src/experience/

# 2. 重命名文件
cd src/experience/
mv skill_tools.py experience_tools.py
mv skill_manager.py experience_manager.py
# task_reflection.py 不改名
```

### 4.2 类名改动

| 当前类名 | 重命名后 | 所在文件 |
|----------|----------|----------|
| `SkillTools` | `ExperienceTools` | `experience_tools.py` |
| `SkillManager` | `ExperienceManager` | `experience_manager.py` |

### 4.3 工具方法名改动

| 当前方法名 | 重命名后 | 说明 |
|------------|----------|------|
| `query_skill()` | `query_experience()` | 查询经验 |
| `rate_skill()` | `rate_experience()` | 评价经验 |
| `edit_skill()` | `edit_experience()` | 编辑经验 |
| `delete_skill()` | `delete_experience()` | 删除经验 |
| `copy_skill_files()` | `copy_experience_files()` | 复制经验文件 |

### 4.4 内部方法名改动

| 当前方法名 | 重命名后 | 说明 |
|------------|----------|------|
| `_load_skill_file()` | `_load_experience_file()` | 加载经验文件 |
| `_save_skill_file()` | `_save_experience_file()` | 保存经验文件 |
| `_get_skill_file_path()` | `_get_experience_file_path()` | 获取经验文件路径 |

### 4.5 属性名改动

| 当前属性名 | 重命名后 | 说明 |
|------------|----------|------|
| `self.skill_tools` | `self.experience_tools` | 工具实例 |
| `self.skill_manager` | `self.experience_manager` | 管理器实例 |

### 4.6 变量名改动

| 当前变量名 | 重命名后 | 说明 |
|------------|----------|------|
| `skills` | `experiences` | 经验列表 |
| `skill_files` | `experience_files` | 经验文件列表 |
| `skill_ids` | `experience_ids` | 经验ID列表 |
| `skill_data` | `experience_data` | 经验数据 |
| `skill_result` | `experience_result` | 经验结果 |
| `skill_info` | `experience_info` | 经验信息 |

### 4.7 新文件生成逻辑改动【关键 BUG 修复！】

> ⚠️ **原方案遗漏此处改动，会导致新生成的文件无法被检索！**

新生成经验文件时，必须使用正确的前缀 `experience_` 而非 `skill_`：

| 文件 | 行号 | 改动前 | 改动后 |
|------|------|--------|--------|
| `experience_manager.py` | ~637 | `skill_filename = f"skill_{safe_title}.md"` | `experience_filename = f"experience_{safe_title}.md"` |
| `experience_manager.py` | ~639-641 | `skill_filename`, `skill_file_path` | `experience_filename`, `experience_file_path` |
| `task_reflection.py` | ~614 | `skill_filename = f"skill_{safe_title}.md"` | `experience_filename = f"experience_{safe_title}.md"` |
| `task_reflection.py` | ~616-618 | `skill_filename`, `skill_file_path` | `experience_filename`, `experience_file_path` |

**原因**：如果不改，新生成的文件将是 `skill_*.md`，而查询时使用 `experience_*.md` 匹配，导致新文件无法被检索。

### 4.8 `_sanitize_filename()` 默认值改动

| 文件 | 行号 | 改动前 | 改动后 |
|------|------|--------|--------|
| `experience_tools.py` | ~293 | `return safe_title if safe_title else "skill"` | `return safe_title if safe_title else "experience"` |

**原因**：当标题为空或全为特殊字符时，默认文件名应使用 `experience` 而非 `skill`。

---

## 五、关键逻辑改动（Bug 预防）

### 5.1 文件名匹配逻辑【关键！】

```python
# 改动前（skill_tools.py 第 278 行）
if filename.startswith('skill_') and filename.endswith('.md'):
    skill_data = self._load_skill_file(file_path)

# 改动后
if filename.startswith('experience_') and filename.endswith('.md'):
    experience_data = self._load_experience_file(file_path)
```

**原因**：如果不改，重命名后的 `experience_*.md` 文件将无法被检索！

### 5.2 需要修改的匹配逻辑位置

| 文件 | 行号 | 代码 |
|------|------|------|
| `skill_tools.py` | ~278 | `filename.startswith('skill_')` |
| `skill_tools.py` | ~331 | `filename.startswith('skill_')` |
| `skill_manager.py` | ~182 | `filename.startswith('skill_')` |

### 5.3 新文件生成前缀【关键！】

| 文件 | 行号 | 改动 |
|------|------|------|
| `experience_manager.py` | ~637 | `f"skill_{safe_title}.md"` → `f"experience_{safe_title}.md"` |
| `task_reflection.py` | ~614 | `f"skill_{safe_title}.md"` → `f"experience_{safe_title}.md"` |

---

## 六、Docstring 和注释改动

### 6.1 模块级 Docstring

```python
# 改动前
"""
Skill管理与经验总结工具集
提供skill查询、评价、编辑、删除和文件备份功能
"""

# 改动后
"""
Experience管理与经验总结工具集
提供experience查询、评价、编辑、删除和文件备份功能
"""
```

### 6.2 类级 Docstring

```python
# 改动前
class SkillTools:
    """
    Skill管理与经验总结工具类
    """

# 改动后
class ExperienceTools:
    """
    Experience管理与经验总结工具类
    """
```

### 6.3 方法 Docstring 示例

```python
# 改动前
def query_skill(self, query: str) -> Dict[str, Any]:
    """
    查询相关skill
    """

# 改动后
def query_experience(self, query: str) -> Dict[str, Any]:
    """
    查询相关experience
    """
```

---

## 七、错误消息改动

### 7.1 需要修改的错误消息

| 文件 | 改动前 | 改动后 |
|------|--------|--------|
| `experience_tools.py` | `Error loading skill file` | `Error loading experience file` |
| `experience_tools.py` | `Error saving skill file` | `Error saving experience file` |
| `experience_tools.py` | `No skills found` | `No experiences found` |
| `experience_tools.py` | `Skill with ID` not found | `Experience with ID` not found |
| `experience_tools.py` | `Failed to load skill file` | `Failed to load experience file` |
| `experience_tools.py` | `Skill {skill_id} quality index` | `Experience {experience_id} quality index` |
| `experience_tools.py` | `Skill {skill_id} updated` | `Experience {experience_id} updated` |
| `experience_tools.py` | `Skill {skill_id} moved to legacy` | `Experience {experience_id} moved to legacy` |
| `experience_tools.py` | `Copied {n} files to skill backup` | `Copied {n} files to experience backup` |

### 7.2 日志消息改动

| 文件 | 行号 | 改动前 | 改动后 |
|------|------|--------|--------|
| `experience_manager.py` | ~542 | `Cleaned unused skill: {skill_id}` | `Cleaned unused experience: {experience_id}` |
| `experience_manager.py` | ~146 | `logging.getLogger('skill_manager')` | `logging.getLogger('experience_manager')` |

### 7.3 LLM Prompt 中的 skill 引用改动

| 文件 | 行号 | 改动前 | 改动后 |
|------|------|--------|--------|
| `experience_manager.py` | ~436-444 | `skill_descriptions` 中的 `Skill {i}:` | `Experience {i}:` |
| `experience_manager.py` | ~436-444 | `- ID: {front_matter.get('skill_id')}` | `- ID: {front_matter.get('experience_id')}` |
| `experience_manager.py` | ~444 | `请分析以下{len(skill_group)}个相关的skill` | `请分析以下{len(experience_group)}个相关的experience` |

### 7.4 返回字典中的字段名【新增！】

> ⚠️ **返回字典中的 `skill_id`, `skills_count`, `skills` 等字段名也需要修改！**

#### 7.4.1 `query_experience()` 返回字段

```python
# 改动前
{
    "status": "success",
    "message": "No skills found",
    "skills_count": 0,
    "skills": []
}

# 改动后
{
    "status": "success",
    "message": "No experiences found",
    "experiences_count": 0,
    "experiences": []
}
```

#### 7.4.2 `rate_experience()` 返回字段

```python
# 改动前
{
    "status": "success",
    "message": f"Skill {skill_id} quality index updated...",
    "skill_id": skill_id,
    ...
}

# 改动后
{
    "status": "success",
    "message": f"Experience {experience_id} quality index updated...",
    "experience_id": experience_id,
    ...
}
```

#### 7.4.3 `edit_experience()` 返回字段

```python
# 改动前
{
    "status": "success",
    "message": f"Skill {skill_id} updated successfully",
    "skill_id": skill_id,
    ...
}

# 改动后
{
    "status": "success",
    "message": f"Experience {experience_id} updated successfully",
    "experience_id": experience_id,
    ...
}
```

#### 7.4.4 `delete_experience()` 返回字段

```python
# 改动前
{
    "status": "success",
    "message": f"Skill {skill_id} moved to legacy directory",
    "skill_id": skill_id,
    "legacy_path": legacy_path
}

# 改动后
{
    "status": "success",
    "message": f"Experience {experience_id} moved to legacy directory",
    "experience_id": experience_id,
    "legacy_path": legacy_path
}
```

#### 7.4.5 `copy_experience_files()` 返回字段

```python
# 改动前
{
    "status": "success",
    "message": f"Copied {n} files to skill backup directory",
    "skill_id": skill_id,
    ...
}

# 改动后
{
    "status": "success",
    "message": f"Copied {n} files to experience backup directory",
    "experience_id": experience_id,
    ...
}
```

#### 7.4.6 `query_experience()` 结果中的 experience 列表项

```python
# 改动前
{
    "skill_id": "123",
    "title": "...",
    ...
}

# 改动后
{
    "experience_id": "123",
    "title": "...",
    ...
}
```

---

## 八、具体文件改动详情

### 8.1 `src/experience/__init__.py`

```python
# 改动前
from .skill_tools import SkillTools
__all__ = ['SkillTools']

# 改动后
from .experience_tools import ExperienceTools
__all__ = ['ExperienceTools']
```

### 8.2 `src/experience/experience_tools.py`

| 改动项 | 改动前 | 改动后 |
|--------|--------|--------|
| 模块 docstring | `Skill管理与经验总结工具集` | `Experience管理与经验总结工具集` |
| 类名 | `class SkillTools:` | `class ExperienceTools:` |
| 类 docstring | `Skill管理与经验总结工具类` | `Experience管理与经验总结工具类` |
| 方法名 | `query_skill()` | `query_experience()` |
| 方法名 | `rate_skill()` | `rate_experience()` |
| 方法名 | `edit_skill()` | `edit_experience()` |
| 方法名 | `delete_skill()` | `delete_experience()` |
| 方法名 | `copy_skill_files()` | `copy_experience_files()` |
| 内部方法 | `_load_skill_file()` | `_load_experience_file()` |
| 内部方法 | `_save_skill_file()` | `_save_experience_file()` |
| 内部方法 | `_get_skill_file_path()` | `_get_experience_file_path()` |
| **默认文件名** | `return safe_title if safe_title else "skill"` | `return safe_title if safe_title else "experience"` |
| 匹配逻辑 | `filename.startswith('skill_')` | `filename.startswith('experience_')` |
| 变量名 | `skill_files`, `skills` | `experience_files`, `experiences` |
| 错误消息 | 全部更新 | 见第七节 |
| **返回字段** | `skill_id`, `skills_count`, `skills` | `experience_id`, `experiences_count`, `experiences` |

### 8.3 `src/experience/experience_manager.py`

| 改动项 | 改动前 | 改动后 |
|--------|--------|--------|
| 模块 docstring | `Skill整理脚本` | `Experience整理脚本` |
| 类名 | `class SkillManager:` | `class ExperienceManager:` |
| import | `from .skill_tools import SkillTools` | `from .experience_tools import ExperienceTools` |
| 实例化 | `self.skill_tools = SkillTools(...)` | `self.experience_tools = ExperienceTools(...)` |
| 属性引用 | `self.skill_tools.experience_dir` | `self.experience_tools.experience_dir` |
| 日志名 | `skill_manager_{date}.log` | `experience_manager_{date}.log` |
| 日志器名 | `logging.getLogger('skill_manager')` | `logging.getLogger('experience_manager')` |
| 日志消息 | `Cleaned unused skill: {skill_id}` | `Cleaned unused experience: {experience_id}` |
| 方法名 | `_load_all_skills()` | `_load_all_experiences()` |
| 方法名 | `_merge_similar_skills()` | `_merge_similar_experiences()` |
| 方法名 | `_clean_unused_skills()` | `_clean_unused_experiences()` |
| 变量名 | `skills`, `skill_data` | `experiences`, `experience_data` |
| 变量名 | `skill_ids` | `experience_ids` |
| 变量名 | `main_skill`, `other_skill` | `main_experience`, `other_experience` |
| 匹配逻辑 | `filename.startswith('skill_')` | `filename.startswith('experience_')` |
| **新文件生成** | `skill_filename = f"skill_{safe_title}.md"` | `experience_filename = f"experience_{safe_title}.md"` |
| **新文件生成** | `skill_file_path` | `experience_file_path` |
| **front matter** | `'skill_id': skill_id` | `'experience_id': experience_id` |
| **LLM prompt** | `skill_descriptions` | `experience_descriptions` |
| **LLM prompt** | `skill_id` | `experience_id` |
| **LLM prompt** | `请分析以下...个相关的skill` | `请分析以下...个相关的experience` |

### 8.4 `src/experience/task_reflection.py`

| 改动项 | 改动前 | 改动后 |
|--------|--------|--------|
| import | `from .skill_tools import SkillTools` | `from .experience_tools import ExperienceTools` |
| 实例化 | `self.skill_tools = SkillTools(...)` | `self.experience_tools = ExperienceTools(...)` |
| 属性引用 | `self.skill_tools.experience_dir` | `self.experience_tools.experience_dir` |
| 方法调用 | `self.skill_tools.copy_skill_files()` | `self.experience_tools.copy_experience_files()` |
| 方法调用 | `self.skill_tools._save_skill_file()` | `self.experience_tools._save_experience_file()` |
| 方法名 | `_generate_skill()` | `_generate_experience()` |
| 变量名 | `skill_file` | `experience_file` |
| 变量名 | `skill_id` | `experience_id` |
| 变量名 | `skill_group` | `experience_group` |
| **新文件生成** | `skill_filename = f"skill_{safe_title}.md"` | `experience_filename = f"experience_{safe_title}.md"` |
| **新文件生成** | `skill_file_path` | `experience_file_path` |
| **front matter** | `'skill_id': skill_id` | `'experience_id': experience_id` |

### 8.5 `src/tool_executor.py`

```python
# 改动前
from src.skill_evolve.skill_tools import SkillTools
self.skill_tools = SkillTools(...)
"query_skill": self.skill_tools.query_skill,
"rate_skill": self.skill_tools.rate_skill,
"edit_skill": self.skill_tools.edit_skill,
"delete_skill": self.skill_tools.delete_skill,
"copy_skill_files": self.skill_tools.copy_skill_files,

# 改动后
from src.experience.experience_tools import ExperienceTools
self.experience_tools = ExperienceTools(...)
"query_experience": self.experience_tools.query_experience,
"rate_experience": self.experience_tools.rate_experience,
"edit_experience": self.experience_tools.edit_experience,
"delete_experience": self.experience_tools.delete_experience,
"copy_experience_files": self.experience_tools.copy_experience_files,
```

### 8.6 `src/tool_executor.py` 注释和变量改动【增强！】

> ⚠️ **第 1151-1169 行的注释和变量名也需要更新！**

#### 8.6.1 变量名改动

| 行号 | 改动前 | 改动后 |
|------|--------|--------|
| ~446 | `def _skill_disabled_error(...)` | `def _experience_disabled_error(...)` |
| ~1153 | `skill_query_section = """` | `experience_query_section = """` |
| ~1167 | `skill_query_section` | `experience_query_section` |
| ~1169 | `skill_query_section` | `experience_query_section` |

#### 8.6.2 打印消息改动

| 行号 | 改动前 | 改动后 |
|------|--------|--------|
| ~436 | `print_system("🎯 Skill tools registered")` | `print_system("🎯 Experience tools registered")` |
| ~438 | `print_current("⚠️ Skill tools module import failed: {e}")` | `print_current("⚠️ Experience tools module import failed: {e}")` |
| ~441 | `print_current("⚠️ Skill tools initialization failed: {e}")` | `print_current("⚠️ Experience tools initialization failed: {e}")` |
| ~447 | `"Skill tools are only available when..."` | `"Experience tools are only available when..."` |

#### 8.6.3 注释改动

| 行号 | 改动前 | 改动后 |
|------|--------|--------|
| ~1151 | `# Add skill query feature if long-term memory is enabled` | `# Add experience query feature if long-term memory is enabled` |
| ~1154 | `## Skill Query Feature` | `## Experience Query Feature` |

#### 8.6.4 帮助文本改动

| 行号 | 改动前 | 改动后 |
|------|--------|--------|
| ~1155 | `"For complex tasks, you can use the `query_skill` tool to..."` | `"For complex tasks, you can use the `query_experience` tool to..."` |
| ~1157 | `"When you use skills from `query_skill`, make sure to..."` | `"When you use experiences from `query_experience`, make sure to..."` |
| ~1160 | `"After task completion, use `rate_skill` to update..."` | `"After task completion, use `rate_experience` to update..."` |
| ~1162 | `"The skill system helps you learn..."` | `"The experience system helps you learn..."` |
| ~1164 | `"Use it proactively for complex tasks!"` | `"Use it proactively for complex tasks!"` |

**具体改动位置**（在 `_get_system_prompt` 或类似方法中）：

```python
# 改动前
"""
For complex tasks, you can use the `query_skill` tool to search for relevant 
historical experiences and skills that might help you complete the task more 
efficiently. This is especially useful when you encounter similar problems or 
need to follow established patterns.

When you use skills from `query_skill`, make sure to:
1. Understand the skill's usage conditions
2. Adapt the skill to your specific context
3. After task completion, use `rate_skill` to update the quality index of skills you used
"""

# 改动后
"""
For complex tasks, you can use the `query_experience` tool to search for relevant 
historical experiences that might help you complete the task more efficiently. 
This is especially useful when you encounter similar problems or need to follow 
established patterns.

When you use experiences from `query_experience`, make sure to:
1. Understand the experience's usage conditions
2. Adapt the experience to your specific context
3. After task completion, use `rate_experience` to update the quality index of experiences you used
"""
```

### 8.7 `prompts/memory_tools.json` 完整改动【新增！】

> ⚠️ **此文件的改动非常关键！如果不更新，LLM 将无法正确调用重构后的工具。**

#### 8.7.1 JSON 字段名改动

| 改动项 | 改动前 | 改动后 |
|--------|--------|--------|
| 工具名 | `"query_skill"` | `"query_experience"` |
| 工具名 | `"rate_skill"` | `"rate_experience"` |
| 工具名 | `"edit_skill"` | `"edit_experience"` |
| 工具名 | `"delete_skill"` | `"delete_experience"` |
| 工具名 | `"copy_skill_files"` | `"copy_experience_files"` |

#### 8.7.2 参数名改动

| 改动项 | 改动前 | 改动后 |
|--------|--------|--------|
| 参数名 | `"skill_id"` | `"experience_id"` |
| 参数描述 | `"The ID of the skill to rate"` | `"The ID of the experience to rate"` |
| 参数描述 | `"The ID of the skill to edit"` | `"The ID of the experience to edit"` |
| 参数描述 | `"The ID of the skill to delete"` | `"The ID of the experience to delete"` |
| 参数描述 | `"The ID of the skill to associate files with"` | `"The ID of the experience to associate files with"` |

#### 8.7.3 描述文本改动

| 工具名 | 改动前描述关键词 | 改动后描述关键词 |
|--------|-----------------|-----------------|
| `query_experience` | `skills from the skill library` | `experiences from the experience library` |
| `rate_experience` | `skill's quality index` | `experience's quality index` |
| `rate_experience` | `how useful the skill was` | `how useful the experience was` |
| `edit_experience` | `skill file` | `experience file` |
| `edit_experience` | `skill content` | `experience content` |
| `delete_skill` | `skill file` | `experience file` |
| `copy_experience_files` | `skill's code backup directory` | `experience's code backup directory` |
| `copy_experience_files` | `files related to a skill` | `files related to an experience` |

#### 8.7.4 完整改动示例

```json
// 改动前
{
  "query_skill": {
    "description": "Search and retrieve relevant skills from the skill library...",
    "parameters": {
      "properties": {
        "query": {
          "description": "The query to search for relevant skills..."
        }
      }
    }
  },
  "rate_skill": {
    "description": "Rate the quality of a skill after using it...",
    "parameters": {
      "properties": {
        "skill_id": {
          "description": "The ID of the skill to rate (obtained from query_skill results)"
        }
      }
    }
  }
}

// 改动后
{
  "query_experience": {
    "description": "Search and retrieve relevant experiences from the experience library...",
    "parameters": {
      "properties": {
        "query": {
          "description": "The query to search for relevant experiences..."
        }
      }
    }
  },
  "rate_experience": {
    "description": "Rate the quality of an experience after using it...",
    "parameters": {
      "properties": {
        "experience_id": {
          "description": "The ID of the experience to rate (obtained from query_experience results)"
        }
      }
    }
  }
}
```

---

## 九、数据文件改动

### 9.1 需重命名的经验文件

路径：`data/*/general/experience/`

| 原文件名 | 新文件名 |
|----------|----------|
| `skill_test_debug.md` | `experience_test_debug.md` |
| `skill_test_fileops.md` | `experience_test_fileops.md` |
| `skill_test_python.md` | `experience_test_python.md` |
| `skill_think.md` | `experience_think.md` |
| `skill_think_*.md` | `experience_think_*.md` |

**总计**：约 20 个文件需要重命名

### 9.2 数据文件内部改动

#### 9.2.1 Front Matter 字段改动

```yaml
# skill_think.md front matter
# 改动前
---
skill_id: '1775664336'
---

# 改动后
---
experience_id: '1775664336'
---
```

**注意**：数据文件中的 front matter `skill_id` 字段也需要改为 `experience_id`

#### 9.2.2 数据文件内容中的工具名引用【必须修改！】

> ⚠️ **数据文件内容中包含对 `query_skill`、`rate_skill` 等工具名的引用，这些引用必须一并修改！**

**示例文件** `data/default/general/experience/skill_think_1775665327.md`：
```markdown
usage_conditions: 当用户询问AI能力范围...应先使用`query_skill`工具检索相关Skills...
...
我很少主动使用`query_skill`、`recall_memories`等工具...
```

**需要修改的工具名引用**：

| 原工具名 | 新工具名 |
|----------|----------|
| `query_skill` | `query_experience` |
| `rate_skill` | `rate_experience` |
| `edit_skill` | `edit_experience` |
| `delete_skill` | `delete_experience` |
| `copy_skill_files` | `copy_experience_files` |

### 9.3 批量重命名脚本

```bash
# 进入经验目录
cd data/default/general/experience/

# 批量重命名文件
for f in skill_*.md; do
    mv "$f" "${f/skill_/experience/}"
done

# 批量修改 front matter 中的 skill_id 字段
sed -i 's/^skill_id:/experience_id:/g' experience_*.md

# 批量修改数据文件内容中的工具名引用
sed -i 's/query_skill/query_experience/g' experience_*.md
sed -i 's/rate_skill/rate_experience/g' experience_*.md
sed -i 's/edit_skill/edit_experience/g' experience_*.md
sed -i 's/delete_skill/delete_experience/g' experience_*.md
sed -i 's/copy_skill_files/copy_experience_files/g' experience_*.md

# 验证修改（应该返回 0）
grep -c "skill_id\|query_skill\|rate_skill\|edit_skill\|delete_skill" experience_*.md | grep -v ":0$" || echo "All references updated successfully"
```

---

## 十、目录结构对比

### 10.1 重构前

```
src/
├── skill_evolve/
│   ├── __init__.py
│   ├── skill_tools.py          # SkillTools 类
│   ├── skill_manager.py        # SkillManager 类
│   └── task_reflection.py      # TaskReflection 类
├── tool_executor.py            # 引用 skill_evolve
└── ...

prompts/
└── memory_tools.json           # 包含 query_skill 等工具定义

data/
└── {user}/
    └── general/
        └── experience/
            ├── skill_*.md       # 经验文件
            │   └── skill_id: xxx
            ├── legacy/          # 归档
            ├── codes/           # 代码备份
            └── logs/            # 日志
```

### 10.2 重构后

```
src/
├── experience/
│   ├── __init__.py
│   ├── experience_tools.py     # ExperienceTools 类
│   ├── experience_manager.py   # ExperienceManager 类
│   └── task_reflection.py      # TaskReflection 类
├── tool_executor.py            # 引用 experience
└── ...

prompts/
└── memory_tools.json           # 包含 query_experience 等工具定义

data/
└── {user}/
    └── general/
        └── experience/
            ├── experience_*.md  # 经验文件
            │   └── experience_id: xxx
            ├── legacy/           # 归档
            ├── codes/            # 代码备份
            └── logs/             # 日志
```

---

## 十一、实施步骤

### Phase 1：备份

| 步骤 | 操作 | 命令 |
|------|------|------|
| 1.1 | 备份代码目录 | `cp -r src/skill_evolve/ src/skill_evolve.bak/` |
| 1.2 | 备份数据目录 | `cp -r data/ data.bak/` |
| 1.3 | 备份 prompts | `cp prompts/memory_tools.json prompts/memory_tools.json.bak` |

### Phase 2：代码文件重构

| 步骤 | 操作 | 命令/操作 |
|------|------|-----------|
| 2.1 | 重命名目录 | `mv src/skill_evolve/ src/experience/` |
| 2.2 | 重命名文件 | `cd src/experience/ && mv skill_tools.py experience_tools.py` |
| 2.3 | 重命名文件 | `cd src/experience/ && mv skill_manager.py experience_manager.py` |
| 2.4 | 更新 `__init__.py` | 修改 import 和导出 |
| 2.5 | 更新 `experience_tools.py` | 彻底改类名、方法名、注释、错误消息、匹配逻辑、返回字段 |
| 2.6 | 更新 `experience_manager.py` | 彻底改类名、方法名、注释、变量名、front matter 字段 |
| 2.7 | 更新 `task_reflection.py` | 修改 import 和方法调用 |
| 2.8 | 更新 `tool_executor.py` | 修改 import、工具注册 |
| 2.9 | **更新 `tool_executor.py` 变量名** | 修改 `_skill_disabled_error` → `_experience_disabled_error`，`skill_query_section` → `experience_query_section` |
| 2.10 | **更新 `tool_executor.py` 打印消息** | 修改 "Skill tools" → "Experience tools" |
| 2.11 | **更新 `tool_executor.py` 注释** | 修改第 1151-1169 行的注释和帮助文本 |

### Phase 3：prompts 文件重构【新增 Phase】

| 步骤 | 操作 | 命令 |
|------|------|------|
| 3.1 | 备份 prompts | `cp prompts/memory_tools.json prompts/memory_tools.json.bak` |
| 3.2 | 更新工具名 | 替换 `query_skill` → `query_experience` 等 |
| 3.3 | 更新参数名 | 替换 `skill_id` → `experience_id` |
| 3.4 | 更新描述文本 | 替换所有包含 "skill" 的描述文本 |
| 3.5 | 验证更新 | `grep -n "skill" prompts/memory_tools.json` 确认无 skill 引用 |

### Phase 4：数据文件重构

| 步骤 | 操作 | 命令 |
|------|------|------|
| 4.1 | 批量重命名文件 | `cd data/*/general/experience/ && rename 's/skill_/experience_/' skill_*.md` |
| 4.2 | 修改 front matter | `sed -i 's/^skill_id:/experience_id:/g' experience_*.md` |
| 4.3 | 验证重命名 | `ls experience_*.md \| wc -l` |

### Phase 4.5：数据文件内容修正【增强！】

| 步骤 | 操作 | 命令 |
|------|------|------|
| 4.5.1 | 修改工具名引用 | `sed -i 's/query_skill/query_experience/g' experience_*.md` |
| 4.5.2 | 修改工具名引用 | `sed -i 's/rate_skill/rate_experience/g' experience_*.md` |
| 4.5.3 | 修改工具名引用 | `sed -i 's/edit_skill/edit_experience/g' experience_*.md` |
| 4.5.4 | 修改工具名引用 | `sed -i 's/delete_skill/delete_experience/g' experience_*.md` |
| 4.5.5 | 修改工具名引用 | `sed -i 's/copy_skill_files/copy_experience_files/g' experience_*.md` |
| 4.5.6 | 验证修改 | `grep -c "skill_id\|query_skill" experience_*.md` 应返回 0 |

### Phase 5：测试验证

| 步骤 | 操作 | 验证内容 | 期望结果 |
|------|------|----------|----------|
| 5.1 | 语法检查 | `python -m py_compile src/experience/*.py` | 无错误 |
| 5.2 | 导入测试 | `python -c "from src.experience import ExperienceTools"` | 无错误 |
| 5.3 | **新文件生成测试** | 调用 `query_experience` 生成新经验 | 文件名以 `experience_` 开头 |
| 5.4 | **检索兼容性测试** | 调用 `query_experience` 检索 | 新文件能被检索到 |
| 5.5 | **端到端工具链测试** | `query_experience` → `rate_experience` → `edit_experience` → `delete_experience` | 全流程正常 |
| 5.6 | **prompts 验证** | `grep -n "query_skill\|skill_id" prompts/memory_tools.json` | 返回空或 0 结果 |
| 5.7 | **tool_executor 注释验证** | `grep -n "query_skill" src/tool_executor.py` | 返回空或 0 结果 |
| 5.8 | **日志检查** | `ls data/*/general/experience/logs/` | 日志名为 `experience_manager_*.log` |

### Phase 6：文档更新【新增 Phase！】

| 步骤 | 操作 | 说明 |
|------|------|------|
| 6.1 | 检查文档引用 | `grep -rn "skill_evolve\|skill_tools\|SkillTools" docs/` |
| 6.2 | 更新 ARCHITECTURE.md | 如有引用，更新为 experience |
| 6.3 | 检查其他文档 | `grep -rn "query_skill\|rate_skill" . --include="*.md"` |
| 6.4 | 更新相关文档 | 按需更新 |

### Phase 7：清理

| 步骤 | 操作 | 说明 |
|------|------|------|
| 7.1 | 删除代码备份 | `rm -rf src/skill_evolve.bak/` |
| 7.2 | 删除数据备份 | `rm -rf data.bak/` |
| 7.3 | 删除 prompts 备份 | `rm prompts/memory_tools.json.bak` |
| 7.4 | 全局搜索确认 | `grep -r "skill_tools\|SkillTools\|query_skill" src/` 确认无遗漏 |

---

## 十二、风险与回滚

### 12.1 潜在风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| import 路径遗漏 | 运行失败 | Phase 5.1 语法检查 |
| 方法名遗漏 | 功能失效 | 全局搜索确认 |
| 匹配逻辑遗漏 | 文件无法检索 | 重点检查文件名匹配 |
| 数据文件遗漏 | 经验丢失 | 先备份再操作 |
| **新文件生成逻辑遗漏** | 新文件无法被检索 | 重点检查第 4.7 节 |
| **_sanitize_filename 默认值遗漏** | 空标题生成错误文件名 | 重点检查第 4.8 节 |
| **prompts 工具名未更新** | LLM 无法调用正确工具 | Phase 3 验证 |
| **prompts 描述文本未更新** | LLM 理解错误 | Phase 3.4 验证 |
| **tool_executor 变量名未更新** | 代码一致性差 | Phase 2.9 验证 |
| **tool_executor 打印消息未更新** | 日志信息不一致 | Phase 2.10 验证 |
| **tool_executor 注释未更新** | 用户帮助信息不一致 | Phase 2.11 验证 |
| **返回字典字段名未更新** | API 调用方兼容性问题 | 重点检查第 7.4 节 |
| **数据文件内容引用未更新** | 用户体验不一致 | Phase 4.5 验证 |

### 12.2 回滚方案

```bash
# 如需回滚，执行以下命令

# 1. 回滚代码文件
rm -rf src/experience/
mv src/skill_evolve.bak/ src/skill_evolve/

# 2. 回滚 prompts 文件
cp prompts/memory_tools.json.bak prompts/memory_tools.json

# 3. 回滚数据文件
cd data/*/general/experience/
rename 's/experience_/skill_/' experience_*.md
sed -i 's/^experience_id:/skill_id:/g' skill_*.md
sed -i 's/query_experience/query_skill/g' skill_*.md
sed -i 's/rate_experience/rate_skill/g' skill_*.md
sed -i 's/edit_experience/edit_skill/g' skill_*.md
sed -i 's/delete_experience/delete_skill/g' skill_*.md
sed -i 's/copy_experience_files/copy_skill_files/g' skill_*.md

# 4. 清理备份
rm prompts/memory_tools.json.bak
```

---

## 十三、未来扩展

### 13.1 三层架构展望

```
┌─────────────────────────────────────────────────────────────────┐
│                      SKILLS 层（未来）                            │
│  • 流程 + 方法 + 可执行工作流                                     │
│  • 人工设计或从 Experience 提炼                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↑ 提炼
┌─────────────────────────────────────────────────────────────────┐
│                      EXPERIENCE 层（本次重构）                     │
│  • 经历 + 反思 + 最佳实践                                         │
│  • 从任务日志 LLM 反思生成                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↑ 依赖
┌─────────────────────────────────────────────────────────────────┐
│                      MEMORY 层（mem 模块）                        │
│  • 底层存储 + 检索引擎                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 13.2 Skills 模块规划

本次重构释放了 `skill` 概念后，未来可以实现规范的 Skills 模块：

```
skills/
├── SKILL.md                   # 规范模板
└── {skill_name}/
    ├── SKILL.md              # 技能定义
    ├── scripts/              # 执行脚本
    └── prompts/              # 提示模板
```

---

## 十四、检查清单

### 代码改动

- [ ] 目录 `src/skill_evolve/` 已重命名为 `src/experience/`
- [ ] 文件 `skill_tools.py` 已重命名为 `experience_tools.py`
- [ ] 文件 `skill_manager.py` 已重命名为 `experience_manager.py`
- [ ] 类名 `SkillTools` 已改为 `ExperienceTools`
- [ ] 类名 `SkillManager` 已改为 `ExperienceManager`
- [ ] 方法名 `query_skill` 已改为 `query_experience`
- [ ] 方法名 `rate_skill` 已改为 `rate_experience`
- [ ] 方法名 `edit_skill` 已改为 `edit_experience`
- [ ] 方法名 `delete_skill` 已改为 `delete_experience`
- [ ] 方法名 `copy_skill_files` 已改为 `copy_experience_files`
- [ ] 内部方法名已全部更新（_load_skill_file 等）
- [ ] 文件名匹配逻辑已更新（skill_*.md → experience_*.md）
- [ ] **新文件生成逻辑已更新**（experience_*.md 前缀）
- [ ] **_sanitize_filename() 默认值已更新**（"experience"）
- [ ] Docstring 已全部更新
- [ ] 注释已全部更新
- [ ] 错误消息已全部更新
- [ ] 日志消息已全部更新（logging.getLogger、logger.info 等）
- [ ] LLM prompt 中的 skill 引用已更新
- [ ] 变量名已全部更新
- [ ] **返回字典字段名已全部更新**（skill_id → experience_id 等）
- [ ] `tool_executor.py` 变量名 `_skill_disabled_error` → `_experience_disabled_error`
- [ ] `tool_executor.py` 变量名 `skill_query_section` → `experience_query_section`
- [ ] `tool_executor.py` 打印消息 "Skill tools" → "Experience tools"
- [ ] `tool_executor.py` 注释 "Skill Query Feature" → "Experience Query Feature"

### import 更新

- [ ] `src/tool_executor.py` 的 import 已更新
- [ ] `src/tool_executor.py` 的工具注册名已更新（query_skill → query_experience 等）
- [ ] `src/tool_executor.py` 的帮助注释已更新（第 1152-1160 行）
- [ ] `src/experience/__init__.py` 的导出已更新
- [ ] `src/experience/experience_manager.py` 的 import 已更新
- [ ] `src/experience/task_reflection.py` 的 import 已更新

### prompts 目录【新增！】

- [ ] `prompts/memory_tools.json` 工具名已更新（query_skill → query_experience 等）
- [ ] `prompts/memory_tools.json` 参数名已更新（skill_id → experience_id）
- [ ] `prompts/memory_tools.json` 描述文本已更新
- [ ] prompts 目录验证通过（无旧工具名）

### 数据文件

- [ ] 数据文件已重命名为 `experience_*.md`
- [ ] front matter `skill_id` 已改为 `experience_id`
- [ ] 数据文件内容中的工具名引用已更新（query_skill → query_experience 等）

### 测试验证

- [ ] 语法检查通过
- [ ] 导入测试通过
- [ ] **新文件生成测试通过**（新文件使用 experience_ 前缀）
- [ ] **检索兼容性测试通过**（新文件可被 query_experience 检索）
- [ ] 端到端工具链测试通过
- [ ] 日志名正确
- [ ] prompts 一致性验证通过
- [ ] tool_executor 注释一致性验证通过

### 文档更新【新增！】

- [ ] `docs/ARCHITECTURE.md` 已检查并更新（如有引用）
- [ ] 其他文档已检查并更新

---

## 附录 A：改动统计

| 类型 | 数量 |
|------|------|
| 目录重命名 | 1 |
| 文件重命名 | 3 |
| 类名改动 | 2 |
| 工具方法名改动 | 5 |
| 内部方法名改动 | 3 |
| 属性名改动 | 2+ |
| 变量名改动 | 6+ |
| 匹配逻辑改动 | 3+ |
| Docstring 改动 | 10+ |
| 错误消息改动 | 10+ |
| 返回字典字段改动 | 5+ |
| prompts 工具定义改动 | 5 |
| prompts 描述文本改动 | 10+ |
| 数据文件重命名 | ~20 |
| 数据字段改动 | ~20 |

## 附录 B：关键词替换映射

### B.1 类名与方法名

| 类别 | 原关键词 | 新关键词 |
|------|----------|----------|
| 模块名 | skill_evolve | experience |
| 类名 | SkillTools | ExperienceTools |
| 类名 | SkillManager | ExperienceManager |
| 方法名 | query_skill | query_experience |
| 方法名 | rate_skill | rate_experience |
| 方法名 | edit_skill | edit_experience |
| 方法名 | delete_skill | delete_experience |
| 方法名 | copy_skill_files | copy_experience_files |
| 方法名 | _load_skill_file | _load_experience_file |
| 方法名 | _save_skill_file | _save_experience_file |
| 方法名 | _get_skill_file_path | _get_experience_file_path |
| 方法名 | _generate_skill | _generate_experience |
| 方法名 | _load_all_skills | _load_all_experiences |
| 方法名 | _merge_similar_skills | _merge_similar_experiences |
| 方法名 | _clean_unused_skills | _clean_unused_experiences |

### B.2 变量名

| 类别 | 原关键词 | 新关键词 |
|------|----------|----------|
| 变量名 | skills | experiences |
| 变量名 | skill_files | experience_files |
| 变量名 | skill_ids | experience_ids |
| 变量名 | skill_data | experience_data |
| 变量名 | skill_id | experience_id |
| 变量名 | skill_result | experience_result |
| 变量名 | skill_info | experience_info |
| 变量名 | skill_file | experience_file |
| 变量名 | skill_group | experience_group |
| 变量名 | main_skill | main_experience |
| 变量名 | other_skill | other_experience |
| 变量名 | self.skill_tools | self.experience_tools |
| 变量名 | self.skill_manager | self.experience_manager |
| 变量名 | skill_descriptions | experience_descriptions |
| 变量名 | skill_filename | experience_filename |
| 变量名 | skill_file_path | experience_file_path |

### B.3 JSON 字段名（prompts/memory_tools.json）【新增！】

| 类别 | 原关键词 | 新关键词 |
|------|----------|----------|
| JSON 工具键 | "query_skill" | "query_experience" |
| JSON 工具键 | "rate_skill" | "rate_experience" |
| JSON 工具键 | "edit_skill" | "edit_experience" |
| JSON 工具键 | "delete_skill" | "delete_experience" |
| JSON 工具键 | "copy_skill_files" | "copy_experience_files" |
| JSON 参数键 | "skill_id" | "experience_id" |

### B.4 文件名与匹配逻辑

| 类别 | 原关键词 | 新关键词 |
|------|----------|----------|
| 文件名 | skill_*.md | experience_*.md |
| front matter | skill_id | experience_id |
| 日志文件名 | skill_manager_*.log | experience_manager_*.log |
| 日志器名 | 'skill_manager' | 'experience_manager' |
| 默认文件名 | "skill" (在 _sanitize_filename 中) | "experience" |

### B.5 人类语言描述

| 类别 | 原关键词 | 新关键词 |
|------|----------|----------|
| 模块 docstring | Skill管理与经验总结工具集 | Experience管理与经验总结工具集 |
| 类 docstring | Skill管理与经验总结工具类 | Experience管理与经验总结工具类 |
| 错误消息 | Error loading skill file | Error loading experience file |
| 错误消息 | Skill with ID not found | Experience with ID not found |
| 错误消息 | No skills found | No experiences found |
| 错误消息 | Skill {skill_id} updated | Experience {experience_id} updated |
| 日志消息 | Cleaned unused skill | Cleaned unused experience |
| LLM prompt | 请分析以下...个相关的skill | 请分析以下...个相关的experience |
| LLM prompt | Skill {i}: | Experience {i}: |
| 帮助文本 | use the `query_skill` tool | use the `query_experience` tool |
| 帮助文本 | When you use skills from `query_skill` | When you use experiences from `query_experience` |
| 帮助文本 | use `rate_skill` to update the quality index of skills | use `rate_experience` to update the quality index of experiences |
| 打印消息 | Skill tools registered | Experience tools registered |
| 打印消息 | Skill tools module import failed | Experience tools module import failed |
| 打印消息 | Skill tools initialization failed | Experience tools initialization failed |
| 错误消息 | Skill tools are only available | Experience tools are only available |
| 变量名 | _skill_disabled_error | _experience_disabled_error |
| 变量名 | skill_query_section | experience_query_section |
| 注释 | Add skill query feature | Add experience query feature |
| 注释 | ## Skill Query Feature | ## Experience Query Feature |

### B.6 prompts 描述文本替换规则【新增！】

| 原描述关键词 | 新描述关键词 |
|-------------|-------------|
| `skills from the skill library` | `experiences from the experience library` |
| `relevant skills` | `relevant experiences` |
| `skill's quality index` | `experience's quality index` |
| `how useful the skill was` | `how useful the experience was` |
| `skill file` | `experience file` |
| `skill content` | `experience content` |
| `skill's code backup directory` | `experience's code backup directory` |
| `files related to a skill` | `files related to an experience` |

---

## 附录 C：数据迁移验证命令【新增！】

```bash
# === Phase 5: 测试验证命令 ===

# 1. 语法检查
python -m py_compile src/experience/experience_tools.py
python -m py_compile src/experience/experience_manager.py
python -m py_compile src/experience/task_reflection.py
echo "✅ Syntax check passed"

# 2. 导入测试
cd D:/AI-APP/AGI-Agent
python -c "from src.experience import ExperienceTools; print('✅ Import test passed')"

# 3. prompts 一致性验证
echo "=== Checking prompts/memory_tools.json ==="
grep -n "query_skill\|rate_skill\|edit_skill\|delete_skill\|skill_id" prompts/memory_tools.json || echo "✅ No old tool names found in prompts"

# 4. tool_executor 注释验证
echo "=== Checking tool_executor.py ==="
grep -n "query_skill\|rate_skill" src/tool_executor.py | grep -v "# " || echo "✅ No old tool names found in tool_executor.py comments"

# 5. 数据文件验证
echo "=== Checking data files ==="
echo "New files count: $(ls data/*/general/experience/experience_*.md 2>/dev/null | wc -l)"
echo "Old files remaining: $(ls data/*/general/experience/skill_*.md 2>/dev/null | wc -l)"

# 6. front matter 验证
echo "=== Checking front matter ==="
grep -l "^skill_id:" data/*/general/experience/*.md 2>/dev/null || echo "✅ All skill_id fields updated"

# 7. 工具名引用验证
echo "=== Checking tool name references in data files ==="
grep -l "query_skill\|rate_skill\|edit_skill\|delete_skill\|copy_skill_files" data/*/general/experience/*.md 2>/dev/null || echo "✅ All tool references updated"

# 8. 代码引用验证
echo "=== Checking code references ==="
grep -rn "skill_tools\|SkillTools\|query_skill\|rate_skill" src/experience/ 2>/dev/null | grep -v "__pycache__" || echo "✅ All code references updated"
```

---

*文档结束*
