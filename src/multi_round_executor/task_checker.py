#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 AGI Agent Research Group.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
Task completion checker for detecting task completion flags
"""

from typing import Optional

from tools.print_system import print_debug


class TaskChecker:
    """Task completion checker for analyzing LLM responses"""
    
    @staticmethod
    def check_task_completion(result) -> bool:
        """
        Check if the large model response contains task completion flag
        Only triggers when a line starts with TASK_COMPLETED or **TASK_COMPLETED
        Only checks LLM's original response content, ignoring tool execution results
        (e.g., terminal output) to avoid false positives from sub-agents.
        
        Args:
            result: Large model response text (may include tool execution results)
            
        Returns:
            Whether task completion flag is detected in LLM's original response
        """
        # 【修复】处理 None 和非字符串类型输入
        if not isinstance(result, str):
            return False
        
        completion_info = TaskChecker.extract_completion_info(result)
        return completion_info is not None
    
    @staticmethod
    def _is_task_completed_line(line: str) -> tuple:
        """
        检查一行是否是任务完成标志
        
        Args:
            line: 原始行内容
            
        Returns:
            (is_completed, completion_msg, prefix_len)
            - is_completed: 是否是完成标志
            - completion_msg: 提取的完成消息（空字符串如果没有）
            - prefix_len: 匹配的前缀长度（用于后续处理）
        """
        try:
            if not isinstance(line, str):
                return (False, "", 0)
            
            stripped_line = line.strip()
            
            # 检查基本格式 TASK_COMPLETED
            if stripped_line.startswith("TASK_COMPLETED"):
                after_prefix = stripped_line[len("TASK_COMPLETED"):]
                
                # 如果后面是空的，是完成标志
                if not after_prefix:
                    return (True, "", len("TASK_COMPLETED"))
                
                # 如果后面是冒号开头，是完成标志
                if after_prefix.startswith(":"):
                    return (True, after_prefix[1:].strip(), len("TASK_COMPLETED"))
                
                # 如果后面是空白开头，是完成标志（但需要排除 = 开头的情况）
                if after_prefix.startswith(" "):
                    next_char = after_prefix[1:] if len(after_prefix) > 1 else ""
                    # 检查空白后的第一个非空白字符是否是 =
                    if next_char and next_char[0] == "=":
                        return (False, "", 0)  # 赋值语句，不匹配
                    return (True, after_prefix.strip(), len("TASK_COMPLETED"))
                
                # 后面是其他字符（如 = 直接跟上来，没有空格），不是标志
                return (False, "", 0)
            if stripped_line.startswith("**TASK_COMPLETED"):
                after_prefix = stripped_line[len("**TASK_COMPLETED"):]
                # 处理 **TASK_COMPLETED** (结尾也有 **)
                if after_prefix.startswith("**"):
                    after_stars = after_prefix[2:]
                    # 检查基本 ** 后的内容（可能是空）
                    if not after_stars:
                        return (True, "", len("**TASK_COMPLETED**"))
                    # 循环处理多余的尾部星号（如 ****、*****）
                    while after_stars and after_stars[0] == '*':
                        if len(after_stars) == 1:
                            # 只有一个星号，返回完成
                            return (True, "", len("**TASK_COMPLETED**"))
                        if after_stars[1] in ' \t:':
                            # 星号后是空白或冒号
                            msg = after_stars[2:].strip() if after_stars[1] == ':' else after_stars[1:].strip()
                            return (True, msg, len("**TASK_COMPLETED**"))
                        # 继续循环，去掉下一个星号
                        after_stars = after_stars[1:]
                    # 如果 after_stars 不再以 * 开头，检查内容
                    if after_stars and after_stars[0] in ' \t:':
                        msg = after_stars[1:].strip() if after_stars[0] == ':' else after_stars.strip()
                        return (True, msg, len("**TASK_COMPLETED**"))
                    return (False, "", 0)
                # 处理 **TASK_COMPLETED: (冒号在后面直接跟描述)
                if after_prefix.startswith(":"):
                    return (True, after_prefix[1:].strip(), len("**TASK_COMPLETED"))
                # 处理 **TASK_COMPLETED 空格后跟描述
                if not after_prefix or after_prefix.startswith(" "):
                    return (True, after_prefix.strip(), len("**TASK_COMPLETED"))
            # 检查三星格式 ***TASK_COMPLETED*** (支持更粗的粗体)
            if stripped_line.startswith("***TASK_COMPLETED"):
                after_prefix = stripped_line[len("***TASK_COMPLETED"):]
                if after_prefix.startswith("***"):
                    after_stars = after_prefix[3:]
                    # 检查基本 *** 后的内容（可能是空）
                    if not after_stars:
                        return (True, "", len("***TASK_COMPLETED***"))
                    # 循环处理多余的尾部星号
                    while after_stars and after_stars[0] == '*':
                        if len(after_stars) == 1:
                            return (True, "", len("***TASK_COMPLETED***"))
                        if after_stars[1] in ' \t:':
                            msg = after_stars[2:].strip() if after_stars[1] == ':' else after_stars[1:].strip()
                            return (True, msg, len("***TASK_COMPLETED***"))
                        # 继续循环，去掉下一个星号
                        after_stars = after_stars[1:]
                    if after_stars and after_stars[0] in ' \t:':
                        msg = after_stars[1:].strip() if after_stars[0] == ':' else after_stars.strip()
                        return (True, msg, len("***TASK_COMPLETED***"))
                    return (False, "", 0)
                # 处理 ***TASK_COMPLETED:
                if after_prefix.startswith(":"):
                    return (True, after_prefix[1:].strip(), len("***TASK_COMPLETED"))
                # 处理 ***TASK_COMPLETED** (只配对两个星号，尾部还有一个星号)
                if after_prefix.startswith("**"):
                    after_two_stars = after_prefix[2:]
                    # 检查两个星号后的内容
                    if not after_two_stars:
                        return (True, "", len("***TASK_COMPLETED**"))
                    if after_two_stars[0] in ' \t:':
                        msg = after_two_stars[1:].strip() if after_two_stars[0] == ':' else after_two_stars.strip()
                        return (True, msg, len("***TASK_COMPLETED**"))
                    if after_two_stars[0] == '*':
                        # 处理 **** 格式 ***TASK_COMPLETED***
                        remaining = after_two_stars[1:]
                        if not remaining:
                            return (True, "", len("***TASK_COMPLETED**"))
                        if remaining[0] in ' \t:':
                            msg = remaining[1:].strip() if remaining[0] == ':' else remaining.strip()
                            return (True, msg, len("***TASK_COMPLETED**"))
                    return (False, "", 0)
                # 处理 ***TASK_COMPLETED 空格
                if not after_prefix or after_prefix.startswith(" "):
                    return (True, after_prefix.strip(), len("***TASK_COMPLETED"))
            
            return (False, "", 0)
        except Exception:
            return (False, "", 0)

    @staticmethod
    def extract_completion_info(result) -> Optional[str]:
        """
        Extract task completion message from LLM response
        
        Args:
            result: Large model response text (may include tool execution results)
            
        Returns:
            Completion message if found, None otherwise
        """
        # 【修复】处理 None 和非字符串类型输入
        if not isinstance(result, str):
            return None
        
        # Extract only LLM's original response content, ignoring tool execution results
        # Tool execution results are separated by "--- Tool Execution Results ---"
        # We should only check content before this marker
        tool_results_marker = "--- Tool Execution Results ---"
        if tool_results_marker in result:
            # Only check content before tool execution results
            llm_content = result.split(tool_results_marker)[0]
        else:
            # No tool execution results, check entire result
            llm_content = result
        
        # Split LLM content into lines for line-by-line checking
        lines = llm_content.split('\n')
        
        for line in lines:
            # 【修复】使用新的检测方法
            is_completed, completion_msg, _ = TaskChecker._is_task_completed_line(line)
            if is_completed:
                return completion_msg
        
        return None