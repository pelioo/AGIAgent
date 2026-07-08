#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TaskChecker Unit Tests

Tests various boundary cases for task completion flag detection
"""

import sys
from pathlib import Path

import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Directly import module to avoid triggering package loading
import importlib.util
spec = importlib.util.spec_from_file_location(
    "task_checker",
    Path(__file__).parent.parent.parent / "src" / "multi_round_executor" / "task_checker.py"
)
task_checker_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(task_checker_module)
TaskChecker = task_checker_module.TaskChecker


class TestCheckTaskCompletion:
    """Tests for check_task_completion method"""

    def test_basic_task_completed(self):
        """Basic TASK_COMPLETED format"""
        assert TaskChecker.check_task_completion("TASK_COMPLETED") is True

    def test_task_completed_with_colon(self):
        """TASK_COMPLETED: format"""
        assert TaskChecker.check_task_completion("TASK_COMPLETED: done") is True

    def test_task_completed_with_message(self):
        """Task completion flag with message"""
        assert TaskChecker.check_task_completion("TASK_COMPLETED: task finished") is True

    def test_markdown_bold_format(self):
        """Markdown bold format **TASK_COMPLETED**"""
        assert TaskChecker.check_task_completion("**TASK_COMPLETED**") is True

    def test_markdown_bold_with_colon(self):
        """**TASK_COMPLETED**: message"""
        assert TaskChecker.check_task_completion("**TASK_COMPLETED**: task completed") is True

    def test_triple_star_format(self):
        """Triple star format ***TASK_COMPLETED***"""
        assert TaskChecker.check_task_completion("***TASK_COMPLETED***") is True

    def test_no_task_completed(self):
        """No completion flag"""
        assert TaskChecker.check_task_completion("Some response text") is False

    def test_task_completed_in_middle(self):
        """Completion flag in the middle"""
        result = "Some text\nTASK_COMPLETED\nMore text"
        assert TaskChecker.check_task_completion(result) is True

    def test_task_completed_with_whitespace(self):
        """With whitespace before and after"""
        assert TaskChecker.check_task_completion("   TASK_COMPLETED   ") is True

    def test_lowercase_task_completed(self):
        """Lowercase is not a valid flag"""
        assert TaskChecker.check_task_completion("task_completed: done") is False

    def test_assignment_statement(self):
        """Assignment statement should not be recognized"""
        assert TaskChecker.check_task_completion("TASK_COMPLETED = True") is False
        assert TaskChecker.check_task_completion("TASK_COMPLETED=False") is False

    def test_comment_statement(self):
        """Comment statement should not be recognized"""
        assert TaskChecker.check_task_completion("TASK_COMPLETED; comment") is False

    def test_direct_concatenation(self):
        """Direct concatenation should not match"""
        assert TaskChecker.check_task_completion("TASK_COMPLETEDsomething") is False
        assert TaskChecker.check_task_completion("**TASK_COMPLETED**done") is False

    def test_none_input(self):
        """None input should be handled safely"""
        assert TaskChecker.check_task_completion(None) is False

    def test_empty_string(self):
        """Empty string"""
        assert TaskChecker.check_task_completion("") is False

    def test_tool_execution_results_separated(self):
        """Tool execution results should be ignored"""
        content = """TASK_COMPLETED

--- Tool Execution Results ---
Some tool output here"""
        assert TaskChecker.check_task_completion(content) is True

    def test_tool_results_with_task_completed(self):
        """TASK_COMPLETED in tool execution results should not be recognized"""
        content = """Some response

--- Tool Execution Results ---
TASK_COMPLETED = True
tool output"""
        # Since TASK_COMPLETED = True is an assignment statement, it should not match
        assert TaskChecker.check_task_completion(content) is False

    def test_type_check_int(self):
        """Integer input should be handled safely without raising"""
        assert TaskChecker.check_task_completion(123) is False

    def test_type_check_list(self):
        """List input should be handled safely without raising"""
        assert TaskChecker.check_task_completion([]) is False
        assert TaskChecker.check_task_completion([1, 2, 3]) is False

    def test_type_check_dict(self):
        """Dict input should be handled safely without raising"""
        assert TaskChecker.check_task_completion({}) is False
        assert TaskChecker.check_task_completion({"key": "value"}) is False

    def test_type_check_bytes(self):
        """Bytes input should be handled safely without raising"""
        assert TaskChecker.check_task_completion(b"TEST") is False

    def test_type_check_tuple(self):
        """Tuple input should be handled safely without raising"""
        assert TaskChecker.check_task_completion((1, 2)) is False

    def test_chinese_suffix_rejected(self):
        """TASK_COMPLETED followed directly by Chinese should be rejected"""
        assert TaskChecker.check_task_completion("TASK_COMPLETED任务") is False
        assert TaskChecker.check_task_completion("TASK_COMPLETED中文") is False

    def test_double_slash_comment_rejected(self):
        """Double slash comment style should be rejected"""
        assert TaskChecker.check_task_completion("// TASK_COMPLETED: done") is False
        assert TaskChecker.check_task_completion("  // TASK_COMPLETED") is False

    def test_sql_comment_rejected(self):
        """SQL comment style should be rejected"""
        assert TaskChecker.check_task_completion("-- TASK_COMPLETED: done") is False

    def test_four_plus_stars_prefix_rejected(self):
        """4+ stars prefix format should be rejected (not supported)"""
        # 这些格式目前不支持，明确拒绝
        assert TaskChecker.check_task_completion("****TASK_COMPLETED****") is False
        assert TaskChecker.check_task_completion("*****TASK_COMPLETED*****") is False

    def test_numeric_suffix_rejected(self):
        """TASK_COMPLETED followed by digits should be rejected"""
        assert TaskChecker.check_task_completion("TASK_COMPLETED123") is False
        assert TaskChecker.check_task_completion("TASK_COMPLETED456: done") is False


class TestExtractCompletionInfo:
    """Tests for extract_completion_info method"""

    def test_extract_basic(self):
        """Basic format"""
        result = TaskChecker.extract_completion_info("TASK_COMPLETED")
        assert result == ""

    def test_extract_with_message(self):
        """Extract message content"""
        result = TaskChecker.extract_completion_info("TASK_COMPLETED: done")
        assert result == "done"

    def test_extract_markdown_format(self):
        """Markdown bold format"""
        result = TaskChecker.extract_completion_info("**TASK_COMPLETED**: completed task")
        assert result == "completed task"

    def test_extract_triple_star(self):
        """Triple star format"""
        result = TaskChecker.extract_completion_info("***TASK_COMPLETED***: done")
        assert result == "done"

    def test_extract_no_completion(self):
        """No completion flag returns None"""
        result = TaskChecker.extract_completion_info("Some response")
        assert result is None

    def test_extract_in_middle(self):
        """Extract first match when completion flag is in the middle"""
        content = "Some text\nTASK_COMPLETED: first\nMore text\nTASK_COMPLETED: second"
        result = TaskChecker.extract_completion_info(content)
        assert result == "first"

    def test_extract_with_whitespace(self):
        """Whitespace handling"""
        result = TaskChecker.extract_completion_info("   TASK_COMPLETED   ")
        assert result == ""

    def test_extract_assignment(self):
        """Assignment statement should not return message"""
        result = TaskChecker.extract_completion_info("TASK_COMPLETED = True")
        assert result is None

    def test_extract_none_input(self):
        """None input"""
        result = TaskChecker.extract_completion_info(None)
        assert result is None

    def test_extract_empty_string(self):
        """Empty string"""
        result = TaskChecker.extract_completion_info("")
        assert result is None

    def test_extract_with_colon_no_message(self):
        """Colon but no message"""
        result = TaskChecker.extract_completion_info("TASK_COMPLETED:")
        assert result == ""

    def test_extract_with_colon_and_spaces(self):
        """Colon with spaces"""
        result = TaskChecker.extract_completion_info("TASK_COMPLETED: ")
        assert result == ""


class TestIsTaskCompletedLine:
    """Tests for _is_task_completed_line method"""

    def test_basic_format(self):
        """Basic TASK_COMPLETED format"""
        result = TaskChecker._is_task_completed_line("TASK_COMPLETED")
        assert result == (True, "", 14)

    def test_with_colon(self):
        """TASK_COMPLETED: format"""
        result = TaskChecker._is_task_completed_line("TASK_COMPLETED: done")
        assert result == (True, "done", 14)

    def test_markdown_bold_complete(self):
        """**TASK_COMPLETED** complete format"""
        result = TaskChecker._is_task_completed_line("**TASK_COMPLETED**")
        assert result[0] is True
        assert result[1] == ""
        assert result[2] == 18

    def test_markdown_bold_with_message(self):
        """**TASK_COMPLETED**: message"""
        result = TaskChecker._is_task_completed_line("**TASK_COMPLETED**: task done")
        assert result[0] is True
        assert result[1] == "task done"
        assert result[2] == 18

    def test_triple_star_format(self):
        """***TASK_COMPLETED***"""
        result = TaskChecker._is_task_completed_line("***TASK_COMPLETED***")
        assert result[0] is True
        assert result[2] == 20

    def test_assignment_rejected(self):
        """Assignment statement should be rejected"""
        result = TaskChecker._is_task_completed_line("TASK_COMPLETED = True")
        assert result == (False, "", 0)

    def test_direct_concat_rejected(self):
        """Direct concatenation should be rejected"""
        result = TaskChecker._is_task_completed_line("TASK_COMPLETEDextra")
        assert result == (False, "", 0)

    def test_markdown_bold_direct_concat_rejected(self):
        """**TASK_COMPLETED** followed by content should be rejected"""
        result = TaskChecker._is_task_completed_line("**TASK_COMPLETED**done")
        assert result == (False, "", 0)

    def test_lowercase_rejected(self):
        """Lowercase should be rejected"""
        result = TaskChecker._is_task_completed_line("task_completed")
        assert result == (False, "", 0)

    def test_with_whitespace(self):
        """With whitespace"""
        result = TaskChecker._is_task_completed_line("   TASK_COMPLETED   ")
        assert result[0] is True

    def test_empty_line(self):
        """Empty line"""
        result = TaskChecker._is_task_completed_line("")
        assert result == (False, "", 0)

    def test_random_text(self):
        """Random text"""
        result = TaskChecker._is_task_completed_line("This is random text")
        assert result == (False, "", 0)

    def test_colon_only(self):
        """Colon only"""
        result = TaskChecker._is_task_completed_line("TASK_COMPLETED:")
        assert result == (True, "", 14)


class TestEdgeCases:
    """Boundary case tests"""

    def test_tool_result_marker_split(self):
        """Tool execution result splitting"""
        content = """Good response

--- Tool Execution Results ---
TASK_COMPLETED = True
Tool output here"""
        result = TaskChecker.extract_completion_info(content)
        assert result is None

    def test_only_whitespace_before_completion(self):
        """Only whitespace before completion flag"""
        content = "   \n   TASK_COMPLETED"
        assert TaskChecker.check_task_completion(content) is True

    def test_unicode_message(self):
        """Unicode message"""
        result = TaskChecker.extract_completion_info("TASK_COMPLETED: 任务完成")
        assert result == "任务完成"

    def test_multiple_lines_first_match(self):
        """Return first match for multiple lines"""
        content = "Line 1\nTASK_COMPLETED: first\nLine 3\nTASK_COMPLETED: second"
        result = TaskChecker.extract_completion_info(content)
        assert result == "first"

    def test_exception_safety(self):
        """Exception safety"""
        try:
            result = TaskChecker._is_task_completed_line(123)
            assert result == (False, "", 0)
        except Exception:
            pytest.fail("Should not raise exception")

    def test_four_stars_markdown_bold(self):
        """Four stars markdown bold format **TASK_COMPLETED****"""
        result = TaskChecker._is_task_completed_line("**TASK_COMPLETED****")
        assert result[0] is True
        assert result[1] == ""

    def test_four_stars_markdown_bold_via_check(self):
        """Test four stars format via check_task_completion"""
        assert TaskChecker.check_task_completion("**TASK_COMPLETED****") is True

    def test_five_stars_markdown_bold(self):
        """Five stars format **TASK_COMPLETED*****"""
        result = TaskChecker._is_task_completed_line("**TASK_COMPLETED*****")
        assert result[0] is True
        assert result[1] == ""

    def test_four_stars_triple_star_format(self):
        """Four stars triple star format ***TASK_COMPLETED****"""
        result = TaskChecker._is_task_completed_line("***TASK_COMPLETED****")
        assert result[0] is True

    def test_markdown_bold_with_trailing_stars_and_message(self):
        """**TASK_COMPLETED**: followed by message"""
        result = TaskChecker._is_task_completed_line("**TASK_COMPLETED**: task done")
        assert result[0] is True
        assert result[1] == "task done"

    def test_triple_star_with_trailing_stars_and_message(self):
        """***TASK_COMPLETED**: followed by message"""
        result = TaskChecker._is_task_completed_line("***TASK_COMPLETED**: task done")
        assert result[0] is True
        assert result[1] == "task done"

    def test_four_stars_triple_star_with_message(self):
        """***TASK_COMPLETED**** followed by message"""
        result = TaskChecker._is_task_completed_line("***TASK_COMPLETED****: task done")
        assert result[0] is True
        assert result[1] == "task done"

    def test_six_stars_markdown_bold(self):
        """Six stars format **TASK_COMPLETED******"""
        result = TaskChecker._is_task_completed_line("**TASK_COMPLETED******")
        assert result[0] is True
        assert result[1] == ""

    def test_tab_before_equals(self):
        """Tab before equals should not match"""
        result = TaskChecker._is_task_completed_line("TASK_COMPLETED\t=True")
        assert result == (False, "", 0)

    def test_multiple_colons(self):
        """Multiple colons should extract content after first colon"""
        result = TaskChecker._is_task_completed_line("TASK_COMPLETED: first: second")
        assert result == (True, "first: second", 14)

    def test_whitespace_only_message(self):
        """Message with only whitespace"""
        result = TaskChecker._is_task_completed_line("TASK_COMPLETED:    ")
        assert result == (True, "", 14)

    def test_newline_in_message(self):
        """Newline in message"""
        result = TaskChecker._is_task_completed_line("TASK_COMPLETED: line1\nline2")
        assert result == (True, "line1\nline2", 14)

    def test_case_sensitive_exact(self):
        """Case must match exactly"""
        assert TaskChecker._is_task_completed_line("TASK-COMPLETED") == (False, "", 0)
        assert TaskChecker._is_task_completed_line("task_completed") == (False, "", 0)
        assert TaskChecker._is_task_completed_line("TASKCOMPLETED") == (False, "", 0)

    def test_angle_brackets(self):
        """Angle bracket format should not match"""
        assert TaskChecker._is_task_completed_line("<TASK_COMPLETED>") == (False, "", 0)
        assert TaskChecker._is_task_completed_line("**TASK_COMPLETED<>") == (False, "", 0)

    def test_hash_comment_style(self):
        """Hash comment style should not match"""
        assert TaskChecker._is_task_completed_line("# TASK_COMPLETED: done") == (False, "", 0)

    def test_five_stars_triple_star_format(self):
        """Five stars triple star format ***TASK_COMPLETED*****"""
        result = TaskChecker._is_task_completed_line("***TASK_COMPLETED*****")
        assert result[0] is True
        assert result[1] == ""

    def test_six_stars_triple_star_format(self):
        """Six stars triple star format ***TASK_COMPLETED******"""
        result = TaskChecker._is_task_completed_line("***TASK_COMPLETED******")
        assert result[0] is True
        assert result[1] == ""


class TestActualUsageScenarios:
    """Actual usage scenario tests"""

    def test_llm_response_with_completion(self):
        """LLM response with completion flag"""
        response = """I'll help you with that task.

Let me analyze the requirements...

TASK_COMPLETED: File processed successfully

--- Tool Execution Results ---
Tool: read
Result: Success"""
        assert TaskChecker.check_task_completion(response) is True
        info = TaskChecker.extract_completion_info(response)
        assert info == "File processed successfully"

    def test_llm_response_without_completion(self):
        """LLM response without completion flag"""
        response = """I'll help you with that task.

Let me analyze the requirements...

The task is in progress."""
        assert TaskChecker.check_task_completion(response) is False
        assert TaskChecker.extract_completion_info(response) is None

    def test_llm_response_with_markdown_completion(self):
        """LLM response with Markdown format"""
        response = """## Task Result

The task has been completed successfully.

**TASK_COMPLETED**: All files processed"""
        assert TaskChecker.check_task_completion(response) is True

    def test_code_like_task_completed(self):
        """TASK_COMPLETED in code"""
        code = """
def check_task():
    return TASK_COMPLETED = True
"""
        assert TaskChecker.check_task_completion(code) is False

    def test_json_like_task_completed(self):
        """JSON format"""
        json_response = '{"status": "TASK_COMPLETED", "message": "done"}'
        assert TaskChecker.check_task_completion(json_response) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])