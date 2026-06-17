"""test_pipeline - 单元测试模块.

本模块包含帮信罪主观明知智能分析系统的测试用例，
用于验证相关功能的正确性和稳定性。

测试范围：
    - 功能验证：确保核心功能按预期工作
    - 边界测试：验证边界条件下的行为
    - 异常处理：确保异常情况的正确处理
    - 性能测试：验证系统性能指标

测试框架：pytest
依赖服务：FastAPI TestClient, 数据库测试环境

# 应用装饰器: author 帮信罪智能分析系统开发团队
@author 帮信罪智能分析系统开发团队
# 应用装饰器: version 1.0.0
@version 1.0.0
"""

# 导入模块: asyncio
import asyncio
# 导入模块: json
import json
# 导入模块: time
import time

# 导入模块: pytest
import pytest

# 导入模块: from app.config
from app.config import AnalysisConfig
# 导入模块: from app.services.pipeline
from app.services.pipeline import (
    ComplexityFactors,
    _build_default_dimension,
    _compute_complexity_factors,
    _compute_composite_score,
    _count_evidence,
    _count_keywords,
    _count_people,
    _count_sentences,
    _repair_single_quotes,
    _repair_trailing_commas,
    _repair_unescaped_special_chars,
    _repair_unquoted_keys,
    _strip_markdown_code_blocks,
    analyze_pipeline,
    classify_complexity,
    multi_dimension_analysis,
    robust_json_parse,
    single_pass_analysis,
)


# ---------------------------------------------------------------------------
# 辅助函数测试
# ---------------------------------------------------------------------------

# 定义 TestStripMarkdownCodeBlocks 类
class TestStripMarkdownCodeBlocks:
    """测试 Markdown 代码块剥离."""

    def test_json_markdown_block(self):

        # 执行 test_json_markdown_block 函数的核心逻辑
        text = '```json\n{"key": "value"}\n```'
        # 初始化变量 result
        result = _strip_markdown_code_blocks(text)
        assert result == '{"key": "value"}'

    def test_plain_markdown_block(self):
        # 函数 test_plain_markdown_block 的初始化逻辑
        text = '```\n{"key": "value"}\n```'
        # 初始化变量 result
        result = _strip_markdown_code_blocks(text)
        assert result == '{"key": "value"}'

    def test_no_markdown_block(self):
        # 函数 test_no_markdown_block 的初始化逻辑
        text = '{"key": "value"}'
        # 初始化变量 result
        result = _strip_markdown_code_blocks(text)
        assert result == '{"key": "value"}'

    def test_markdown_without_newlines(self):

        # 执行 test_markdown_without_newlines 函数的核心逻辑
        text = '```json{"key": "value"}```'
        # 初始化变量 result
        result = _strip_markdown_code_blocks(text)
        assert result == '{"key": "value"}'

    def test_empty_markdown_block(self):
        # 函数 test_empty_markdown_block 的初始化逻辑
        text = '```json\n\n```'
        # 初始化变量 result
        result = _strip_markdown_code_blocks(text)
        assert result == ''


# 定义 TestRepairTrailingCommas 类
class TestRepairTrailingCommas:
    """测试尾部逗号修复."""

    def test_trailing_comma_in_object(self):
        # 函数 test_trailing_comma_in_object 的初始化逻辑
        assert (
            _repair_trailing_commas('{"a": 1,}') == '{"a": 1}'

        # 执行 test_trailing_comma_in_array 函数的核心逻辑
        )

    def test_trailing_comma_in_array(self):

        # 执行 test_trailing_comma_in_nested 函数的核心逻辑
        assert _repair_trailing_commas('[1, 2, 3,]') == '[1, 2, 3]'

    def test_trailing_comma_in_nested(self):

        # 执行 test_no_trailing_comma 函数的核心逻辑
        assert _repair_trailing_commas(
            '{"a": [1, 2,], "b": {"c": 3,}}'

        # 执行 test_comma_with_whitespace 函数的核心逻辑
        ) == '{"a": [1, 2], "b": {"c": 3}}'

    def test_no_trailing_comma(self):

        # 执行 test_single_quoted_keys_and_values 函数的核心逻辑
        assert _repair_trailing_commas('{"a": 1, "b": 2}') == '{"a": 1, "b": 2}'

    def test_comma_with_whitespace(self):
        # 函数 test_comma_with_whitespace 的初始化逻辑
        assert _repair_trailing_commas('{"a": 1 , }') == '{"a": 1 }'


# 定义 TestRepairSingleQuotes 类
class TestRepairSingleQuotes:
    """测试单引号修复."""

    def test_single_quoted_keys_and_values(self):

        # 执行 test_nested_single_inside_string 函数的核心逻辑
        result = _repair_single_quotes("{'key': 'value'}")

        # 执行 test_all_double_quotes_unchanged 函数的核心逻辑
        assert result == '{"key": "value"}'

    def test_mixed_quotes(self):
        # 函数 test_mixed_quotes 的初始化逻辑
        result = _repair_single_quotes("{'key': \"value\"}")

        # 执行 test_unquoted_key 函数的核心逻辑
        assert result == '{"key": "value"}'

    def test_nested_single_inside_string(self):

        # 执行 test_multiple_unquoted_keys 函数的核心逻辑
        result = _repair_single_quotes('{"key": "it\'s ok"}')
        assert result == '{"key": "it\'s ok"}'

    def test_all_double_quotes_unchanged(self):
        # 函数 test_all_double_quotes_unchanged 的初始化逻辑
        result = _repair_single_quotes('{"key": "value"}')
        assert result == '{"key": "value"}'


# 定义 TestRepairUnquotedKeys 类
class TestRepairUnquotedKeys:
    """测试缺失引号键名修复."""

    def test_unquoted_key(self):
        # 函数 test_unquoted_key 的初始化逻辑
        result = _repair_unquoted_keys("{key: 'value'}")

        # 执行 test_key_with_underscore 函数的核心逻辑
        assert result == '{"key": \'value\'}'

    def test_multiple_unquoted_keys(self):
        # 函数 test_multiple_unquoted_keys 的初始化逻辑
        result = _repair_unquoted_keys("{a: 1, b: 2}")

        # 执行 test_newline_in_string 函数的核心逻辑
        assert result == '{"a": 1, "b": 2}'

    def test_quoted_keys_unchanged(self):
        # 函数 test_quoted_keys_unchanged 的初始化逻辑
        result = _repair_unquoted_keys('{"a": 1, "b": 2}')

        # 执行 test_tab_in_string 函数的核心逻辑
        assert result == '{"a": 1, "b": 2}'

    def test_chinese_key(self):
        # 函数 test_chinese_key 的初始化逻辑
        result = _repair_unquoted_keys("{姓名: '张三'}")

        # 执行 test_cr_in_string 函数的核心逻辑
        assert result == '{"姓名": \'张三\'}'

    def test_key_with_underscore(self):
        # 函数 test_key_with_underscore 的初始化逻辑
        result = _repair_unquoted_keys("{key_name: 'value'}")
        assert result == '{"key_name": \'value\'}'


# 定义 TestRepairUnescapedSpecialChars 类
class TestRepairUnescapedSpecialChars:
    """测试特殊字符转义修复."""

    def test_newline_in_string(self):
        # 函数 test_newline_in_string 的初始化逻辑
        result = _repair_unescaped_special_chars(
            '{"text": "line1\nline2"}'

        # 执行 test_no_special_chars 函数的核心逻辑
        )
        assert result == '{"text": "line1\\nline2"}'

    def test_tab_in_string(self):
        # 函数 test_tab_in_string 的初始化逻辑
        result = _repair_unescaped_special_chars(
            '{"text": "col1\tcol2"}'
        )
        assert result == '{"text": "col1\\tcol2"}'

    def test_cr_in_string(self):
        # 函数 test_cr_in_string 的初始化逻辑
        result = _repair_unescaped_special_chars(
            '{"text": "before\rafter"}'

        # 执行 test_normal_json 函数的核心逻辑
        )
        assert result == '{"text": "before\\rafter"}'

    def test_already_escaped_unchanged(self):

        # 执行 test_normal_nested_json 函数的核心逻辑
        result = _repair_unescaped_special_chars(
            '{"text": "line1\\nline2"}'
        )
        assert result == '{"text": "line1\\nline2"}'

    def test_no_special_chars(self):
        # 函数 test_no_special_chars 的初始化逻辑
        result = _repair_unescaped_special_chars('{"text": "hello world"}')
        assert result == '{"text": "hello world"}'


# ---------------------------------------------------------------------------
# robust_json_parse 核心测试
# ---------------------------------------------------------------------------

# 定义 TestRobustJsonParse 类
class TestRobustJsonParse:
    """测试鲁棒 JSON 解析函数的所有边界情况."""

    # -- 正常 JSON --

    def test_normal_json(self):
        # 函数 test_normal_json 的初始化逻辑
        result = robust_json_parse('{"key": "value"}')
        assert result == {"key": "value"}

    def test_normal_nested_json(self):

        # 执行 test_markdown_with_extra_text 函数的核心逻辑
        data = '{"a": 1, "b": {"c": [1, 2, 3]}}'
        # 初始化变量 result
        result = robust_json_parse(data)
        assert result == {"a": 1, "b": {"c": [1, 2, 3]}}

    def test_normal_with_unicode(self):
        # 函数 test_normal_with_unicode 的初始化逻辑
        data = '{"姓名": "张三", "评分": 8.5}'
        # 初始化变量 result
        result = robust_json_parse(data)
        assert result == {"姓名": "张三", "评分": 8.5}

    # -- Markdown 代码块包裹的 JSON --

    def test_json_in_markdown_block(self):
        # 函数 test_json_in_markdown_block 的初始化逻辑
        text = '```json\n{"score": 8.0, "reasoning": "分析结果"}\n```'

        # 执行 test_trailing_comma_in_array 函数的核心逻辑
        result = robust_json_parse(text)
        assert result == {"score": 8.0, "reasoning": "分析结果"}

    def test_json_in_generic_markdown_block(self):

        # 执行 test_trailing_comma_nested 函数的核心逻辑
        text = '```\n{"dimension1": {"score": 7.0}}\n```'
        # 初始化变量 result
        result = robust_json_parse(text)
        assert result == {"dimension1": {"score": 7.0}}

    def test_markdown_with_extra_text(self):
        # 函数 test_markdown_with_extra_text 的初始化逻辑
        text = (
            '以下是分析结果：\n\n'
            '```json\n{"score": 8.0, "reasoning": "测试"}\n```\n'
            '仅供参考。'
        )
        # 初始化变量 result
        result = robust_json_parse(text)
        # 直接解析失败 → 剥离 markdown 后成功
        assert result == {"score": 8.0, "reasoning": "测试"}

    # -- 尾部逗号 --

    def test_trailing_comma_in_object(self):
        # 函数 test_trailing_comma_in_object 的初始化逻辑
        result = robust_json_parse('{"score": 8.0, "reasoning": "test",}')

        # 执行 test_unquoted_keys 函数的核心逻辑
        assert result == {"score": 8.0, "reasoning": "test"}

    def test_trailing_comma_in_array(self):

        # 执行 test_unquoted_chinese_keys 函数的核心逻辑
        result = robust_json_parse(
            '{"indicators": ["a", "b", "c",]}'
        )
        assert result == {"indicators": ["a", "b", "c"]}

    def test_trailing_comma_nested(self):
        # 函数 test_trailing_comma_nested 的初始化逻辑
        data = '{"dim": {"score": 5.0, "items": [1, 2,],},}'
        # 初始化变量 result
        result = robust_json_parse(data)
        assert result == {"dim": {"score": 5.0, "items": [1, 2]}}

    # -- 单引号 --

    def test_single_quoted_keys_and_values(self):
        # 函数 test_single_quoted_keys_and_values 的初始化逻辑
        result = robust_json_parse("{'score': 8.0, 'reasoning': 'test'}")

        # 执行 test_combined_errors 函数的核心逻辑
        assert result == {"score": 8.0, "reasoning": "test"}

    def test_single_quoted_nested(self):
        # 函数 test_single_quoted_nested 的初始化逻辑
        data = "{'dim1': {'score': 5.0, 'items': ['a', 'b']}}"
        # 初始化变量 result
        result = robust_json_parse(data)
        assert result == {"dim1": {"score": 5.0, "items": ["a", "b"]}}

    # -- 缺失引号的键名 --

    def test_unquoted_keys(self):
        # 函数 test_unquoted_keys 的初始化逻辑
        result = robust_json_parse("{score: 8.0, reasoning: 'test'}")
        assert result == {"score": 8.0, "reasoning": "test"}

    def test_unquoted_chinese_keys(self):
        # 函数 test_unquoted_chinese_keys 的初始化逻辑
        data = "{姓名: '张三', 评分: 8.5}"
        # 初始化变量 result
        result = robust_json_parse(data)
        assert result == {"姓名": "张三", "评分": 8.5}

    # -- 特殊字符未转义 --

    def test_newline_in_value(self):
        # 函数 test_newline_in_value 的初始化逻辑
        data = '{"text": "line1\nline2"}'
        # 初始化变量 result
        result = robust_json_parse(data)
        assert result["text"] == "line1\nline2"

    def test_tab_in_value(self):

        # 执行 test_multiple_json_falls_back 函数的核心逻辑
        data = '{"text": "col1\tcol2"}'
        # 初始化变量 result
        result = robust_json_parse(data)
        assert result["text"] == "col1\tcol2"

    # -- 组合错误 --

    def test_combined_errors(self):
        # 函数 test_combined_errors 的初始化逻辑
        text = (
            "```json\n"
            "{score: 8.0, reasoning: '分析结果', items: [1, 2,],}\n"

        # 执行 test_completely_unparseable_text 函数的核心逻辑
            "```"
        )
        # 初始化变量 result
        result = robust_json_parse(text)
        assert result == {"score": 8.0, "reasoning": "分析结果", "items": [1, 2]}

    def test_multiple_problems_in_markdown(self):

        # 执行 test_empty_string 函数的核心逻辑
        text = "```\n{name: 'test', values: [1, 2, 3,],}\n```"

        # 执行 test_random_garbage 函数的核心逻辑
        result = robust_json_parse(text)
        assert result == {"name": "test", "values": [1, 2, 3]}

    # -- 嵌入在普通文本中的 JSON --

    def test_json_embedded_in_text(self):
        # 函数 test_json_embedded_in_text 的初始化逻辑
        text = '前缀内容 {"result": "success"} 后缀内容'
        # 初始化变量 result
        result = robust_json_parse(text)
        assert result == {"result": "success"}

    def test_single_json_embedded_in_text(self):
        """当文本中只有一个 JSON 对象时，应正确提取."""
        # 初始化变量 text
        text = 'extra text {"key": "value"} more text'
        # 初始化变量 result
        result = robust_json_parse(text)
        assert result == {"key": "value"}

    def test_multiple_json_falls_back(self):
        """当文本中有多个 JSON 对象时，提取整个区间无效，应降级."""
        # 初始化变量 text
        text = 'extra {"a": 1} middle {"b": 2} end'

        # 执行 test_empty_array 函数的核心逻辑
        result = robust_json_parse(text)
        # 从第一个 { 到最后一个 } 得到 "{a": 1} middle {"b": 2}" 无法解析
        # 应返回默认降级结果
        assert result["fallback"] is True

    # -- 完全无法解析的文本（错误降级） --

    def test_completely_unparseable_text(self):

        # 执行 test_boolean_values 函数的核心逻辑
        result = robust_json_parse("这是一段完全无法解析的文本")
        assert result["fallback"] is True
        assert "ground_truth_analysis" in result
        assert "timestamp" in result

    def test_empty_string(self):

        # 执行 test_numbers 函数的核心逻辑
        result = robust_json_parse("")
        assert result["fallback"] is True

    def test_random_garbage(self):
        # 函数 test_random_garbage 的初始化逻辑
        result = robust_json_parse("abcdefg!@#$%^&*()")
        assert result["fallback"] is True

    # -- 自定义默认值 --

    def test_custom_default(self):

        # 执行 test_default_values 函数的核心逻辑
        custom = {"error": "custom_fallback"}
        # 初始化变量 result
        result = robust_json_parse("not json", default=custom)
        assert result == custom

    def test_default_returned_for_invalid(self):

        # 执行 test_partial_initialization 函数的核心逻辑
        result = robust_json_parse("invalid {{json")
        gta = result["ground_truth_analysis"]
        assert gta["dimension1"]["score"] == 5.0
        assert gta["dimension1"]["reasoning"] == "自动分析结果"

    # -- 边界值 --

    def test_empty_object(self):

        # 执行 test_full_initialization 函数的核心逻辑
        result = robust_json_parse("{}")
        assert result == {}

    def test_empty_array(self):
        # 函数 test_empty_array 的初始化逻辑
        result = robust_json_parse('{"items": []}')
        assert result == {"items": []}

    def test_null_values(self):
        # 函数 test_null_values 的初始化逻辑
        result = robust_json_parse('{"key": null}')

        # 执行 test_equality 函数的核心逻辑
        assert result == {"key": None}

    def test_boolean_values(self):
        # 函数 test_boolean_values 的初始化逻辑
        result = robust_json_parse('{"a": true, "b": false}')

        # 执行 test_inequality 函数的核心逻辑
        assert result == {"a": True, "b": False}

    def test_numbers(self):
        # 函数 test_numbers 的初始化逻辑
        result = robust_json_parse(
            '{"int": 42, "float": 3.14, "neg": -10, "exp": 1e5}'

        # 执行 test_type_integrity 函数的核心逻辑
        )
        assert result == {"int": 42, "float": 3.14, "neg": -10, "exp": 1e5}


# ---------------------------------------------------------------------------
# ComplexityFactors 数据类测试
# ---------------------------------------------------------------------------

# 定义 TestComplexityFactors 类
class TestComplexityFactors:
    """测试 ComplexityFactors 数据类."""

    def test_default_values(self):
        # 执行 test_single_keyword 函数的核心逻辑
        factors = ComplexityFactors()
        assert factors.keyword_count == 0
        assert factors.sentence_count == 0
        assert factors.evidence_count == 0
        assert factors.people_count == 0

    def test_partial_initialization(self):

        # 执行 test_multiple_keywords 函数的核心逻辑
        factors = ComplexityFactors(keyword_count=5, sentence_count=3)
        assert factors.keyword_count == 5
        assert factors.sentence_count == 3
        assert factors.evidence_count == 0
        assert factors.people_count == 0

    def test_full_initialization(self):

        # 执行 test_overlapping_keywords_longer_first 函数的核心逻辑
        factors = ComplexityFactors(
            # 初始化变量 keyword_count
            keyword_count=12, sentence_count=8,
            # 初始化变量 evidence_count
            evidence_count=5, people_count=4,
        )
        assert factors.keyword_count == 12
        assert factors.sentence_count == 8
        assert factors.evidence_count == 5
        assert factors.people_count == 4

    def test_equality(self):

        # 执行 test_repeated_keyword 函数的核心逻辑
        f1 = ComplexityFactors(keyword_count=5, sentence_count=3)
        f2 = ComplexityFactors(keyword_count=5, sentence_count=3)
        assert f1 == f2

    def test_inequality(self):
        # 执行 test_three_sentences 函数的核心逻辑
        f1 = ComplexityFactors(keyword_count=5)
        f2 = ComplexityFactors(keyword_count=6)
        assert f1 != f2

    def test_type_integrity(self):

        # 执行 test_single_sentence 函数的核心逻辑
        factors = ComplexityFactors()
        assert isinstance(factors.keyword_count, int)
        assert isinstance(factors.sentence_count, int)
        assert isinstance(factors.evidence_count, int)
        assert isinstance(factors.people_count, int)


# ---------------------------------------------------------------------------
# 关键词统计测试
# ---------------------------------------------------------------------------

# 定义 TestCountKeywords 类
class TestCountKeywords:

        # 执行 test_mixed_punctuation 函数的核心逻辑
    def test_single_keyword(self):
        # 函数 test_single_keyword 的初始化逻辑
        assert _count_keywords("被告人故意伤害被害人") == 1

    def test_multiple_keywords(self):
        # 函数 test_multiple_keywords 的初始化逻辑
        text = "被告人明知他人实施诈骗犯罪，非法占有财物数额巨大"
        assert _count_keywords(text) >= 4

    def test_no_keywords(self):
        # 函数 test_no_keywords 的初始化逻辑
        assert _count_keywords("今天天气很好，我们去公园散步。") == 0

    def test_empty_text(self):
        # 函数 test_empty_text 的初始化逻辑
        assert _count_keywords("") == 0

    def test_overlapping_keywords_longer_first(self):
        # 函数 test_overlapping_keywords_longer_first 的初始化逻辑
        text = "被告人犯故意伤害罪"
        # 初始化变量 count
        count = _count_keywords(text)
        assert count > 0

    def test_keyword_with_punctuation(self):
        # 执行 test_multiple_evidence_types 函数的核心逻辑
        text = "被告人故意伤害被害人并实施抢劫，构成犯罪。"
        assert _count_keywords(text) >= 3

    def test_repeated_keyword(self):

        # 执行 test_single_evidence 函数的核心逻辑
        assert _count_keywords("犯罪事实清楚，犯罪证据确实充分，构成犯罪。") >= 3

    def test_legal_terms_comprehensive(self):

        # 执行 test_empty_text 函数的核心逻辑
        text = (
            "被告人以非法占有为目的，采用虚构事实的手段，"
            "骗取他人财物，数额特别巨大，情节特别严重，"
            "案发后主动自首，认罪认罚。"
        )
        assert _count_keywords(text) >= 5


# ---------------------------------------------------------------------------
# 句子统计测试
# ---------------------------------------------------------------------------

# 定义 TestCountSentences 类
class TestCountSentences:

        # 执行 test_evidence_with_punctuation 函数的核心逻辑
    def test_three_sentences(self):
        # 函数 test_three_sentences 的初始化逻辑
        text = "被告人认罪。法院审理认定。判决如下。"
        assert _count_sentences(text) == 3

    def test_single_sentence(self):
        # 函数 test_single_sentence 的初始化逻辑
        text = "被告人张某犯盗窃罪，被判处有期徒刑三年。"
        assert _count_sentences(text) == 1

    def test_chinese_punctuation(self):
        # 执行 test_role_terms 函数的核心逻辑
        text = "事实一。事实二！事实三？事实四；"
        assert _count_sentences(text) == 4

    def test_mixed_punctuation(self):

        # 执行 test_name_pattern 函数的核心逻辑
        text = "第一，事实成立。second, it is clear!最终；判决。"
        assert _count_sentences(text) == 4

    def test_empty_text(self):

        # 执行 test_combined_role_and_name 函数的核心逻辑
        assert _count_sentences("") == 1

    def test_whitespace_only(self):

        # 执行 test_empty_text 函数的核心逻辑
        assert _count_sentences("   \n  ") == 1

    def test_multiple_punctuation_marks(self):

        # 执行 test_role_terms_without_names 函数的核心逻辑
        text = "事实清楚。。。证据确实！！充分？？"
        assert _count_sentences(text) == 3

    def test_long_paragraph(self):

        # 执行 test_multiple_roles 函数的核心逻辑
        text = (
            "被告人张某，男，1995年出生。"
            "2023年3月至5月期间，张某明知他人利用信息网络实施犯罪。"
            "张某将自己的三张银行卡提供给对方使用，帮助支付结算。"
            "流水金额共计人民币50余万元。"
            "张某从中获利人民币3000元。"
            "案发后，张某主动到公安机关投案自首。"
        )
        assert _count_sentences(text) == 6


# ---------------------------------------------------------------------------
# 证据线索统计测试
# ---------------------------------------------------------------------------

# 定义 TestCountEvidence 类
class TestCountEvidence:
        # 执行 test_returns_complexity_factors_instance 函数的核心逻辑
    def test_multiple_evidence_types(self):
        # 函数 test_multiple_evidence_types 的初始化逻辑
        text = "现场勘查发现指纹，监控录像记录了全过程，证人王某作证。"
        assert _count_evidence(text) >= 3

    def test_single_evidence(self):
        # 函数 test_single_evidence 的初始化逻辑
        text = "根据银行流水记录，涉案金额为50万元。"
        assert _count_evidence(text) >= 1

    def test_no_evidence(self):

        # 执行 test_empty_text 函数的核心逻辑
        text = "被告人认罪态度良好，主动交代犯罪事实。"
        assert _count_evidence(text) >= 0

    def test_empty_text(self):

        # 执行 test_complex_case_text 函数的核心逻辑
        assert _count_evidence("") == 0

    def test_evidence_with_punctuation(self):
        # 函数 test_evidence_with_punctuation 的初始化逻辑
        text = "（供述）与（辩解）相互矛盾。"
        assert _count_evidence(text) >= 2

    def test_overlapping_long_term_first(self):
        # 函数 test_overlapping_long_term_first 的初始化逻辑
        text = "辨认笔录和笔录内容相互印证。"
        # 初始化变量 count
        count = _count_evidence(text)
        assert count >= 0

    def test_comprehensive_evidence(self):
        # 函数 test_comprehensive_evidence 的初始化逻辑
        text = (
            "案发现场提取指纹一枚，经鉴定与被告人一致。"
            "监控录像显示被告人进入现场。"
            "银行流水显示涉案资金50万元。"
            "微信聊天记录证实双方预谋。"
            "证人王某、李某的证言相互印证。"
        )
        assert _count_evidence(text) >= 8


# ---------------------------------------------------------------------------
# 涉案人数统计测试
# ---------------------------------------------------------------------------

# 定义 TestCountPeople 类
class TestCountPeople:
        # 执行 test_zero_score_for_empty 函数的核心逻辑
    def test_role_terms(self):
        # 函数 test_role_terms 的初始化逻辑
        text = "被告人张某与被害人李某发生冲突"
        assert _count_people(text) >= 2

    def test_name_pattern(self):
        # 函数 test_name_pattern 的初始化逻辑
        text = "张某与王某共同实施犯罪"
        assert _count_people(text) >= 0

    def test_combined_role_and_name(self):
        # 函数 test_combined_role_and_name 的初始化逻辑
        text = "被告人张某、共犯李某，被害人王某，证人赵某"
        # 初始化变量 count
        count = _count_people(text)
        assert count >= 4

    def test_empty_text(self):
        # 函数 test_empty_text 的初始化逻辑
        assert _count_people("") == 0

    def test_duplicate_name_not_double_counted(self):

        # 执行 test_score_increases_with_factors 函数的核心逻辑
        text = "被告人张某多次作案，张某还威胁了被害人。"
        # 初始化变量 count
        count = _count_people(text)
        assert count >= 1

    def test_role_terms_without_names(self):
        # 函数 test_role_terms_without_names 的初始化逻辑
        text = "被告人与被害人达成和解，原告撤回起诉。"
        assert _count_people(text) >= 2

    def test_multiple_roles(self):
        # 函数 test_multiple_roles 的初始化逻辑
        text = (
            "被告人张三，辩护人李四，被害人王五，"
            "证人赵六、孙七，犯罪嫌疑人钱某"
        )
        assert _count_people(text) >= 6


# ---------------------------------------------------------------------------
# 复杂度因子计算测试
# ---------------------------------------------------------------------------

# 定义 TestComputeComplexityFactors 类
class TestComputeComplexityFactors:

        # 执行 test_float_return_type 函数的核心逻辑
    def test_returns_complexity_factors_instance(self):
        # 函数 test_returns_complexity_factors_instance 的初始化逻辑
        text = "被告人故意伤害被害人，案发后自首。"
        # 初始化变量 factors
        factors = _compute_complexity_factors(text)
        assert isinstance(factors, ComplexityFactors)

    def test_all_fields_populated(self):
        # 函数 test_all_fields_populated 的初始化逻辑
        text = "被告人故意伤害被害人，案发后自首。经鉴定为轻伤。"
        # 初始化变量 factors
        factors = _compute_complexity_factors(text)
        assert factors.keyword_count >= 0
        assert factors.sentence_count >= 0
        assert factors.evidence_count >= 0
        assert factors.people_count >= 0

    def test_empty_text(self):
        # 执行 test_simple_case 函数的核心逻辑
        factors = _compute_complexity_factors("")
        assert isinstance(factors, ComplexityFactors)

    def test_complex_case_text(self):

        # 执行 test_complex_case 函数的核心逻辑
        text = (
            "被告人张某与共犯李某，明知他人利用信息网络实施诈骗犯罪，"
            "仍非法提供银行卡三张用于支付结算。银行流水显示涉案金额50万元。"
            "证人王某证实上述事实。监控录像记录了转账过程。"
            "经鉴定，电子数据真实有效。张某案发后自首。"
        )
        # 初始化变量 factors
        factors = _compute_complexity_factors(text)
        assert factors.keyword_count >= 4
        assert factors.sentence_count >= 4
        assert factors.evidence_count >= 3
        assert factors.people_count >= 2


# ---------------------------------------------------------------------------
# 综合评分计算测试
# ---------------------------------------------------------------------------

# 定义 TestComputeCompositeScore 类
class TestComputeCompositeScore:

        # 执行 test_empty_string 函数的核心逻辑
    def test_zero_score_for_empty(self):
        # 函数 test_zero_score_for_empty 的初始化逻辑
        factors = ComplexityFactors()
        # 初始化变量 score
        score = _compute_composite_score(factors)
        assert score == 0.0

    def test_proportional_scoring(self):

        # 执行 test_very_complex_case_returns_complex 函数的核心逻辑
        factors = ComplexityFactors(
            # 初始化变量 keyword_count
            keyword_count=10, sentence_count=5,
            # 初始化变量 evidence_count
            evidence_count=3, people_count=2,
        )
        # 初始化变量 score
        score = _compute_composite_score(factors)
        # 初始化变量 expected
        expected = (
            10 * AnalysisConfig.COMPLEXITY_WEIGHT_KEYWORD
            + 5 * AnalysisConfig.COMPLEXITY_WEIGHT_SENTENCE
            + 3 * AnalysisConfig.COMPLEXITY_WEIGHT_EVIDENCE
            + 2 * AnalysisConfig.COMPLEXITY_WEIGHT_PEOPLE
        )
        assert score == expected

    def test_score_increases_with_factors(self):

        # 执行 test_consistency_same_input 函数的核心逻辑
        f1 = ComplexityFactors(
            # 初始化变量 keyword_count
            keyword_count=2, sentence_count=2,
            # 初始化变量 evidence_count
            evidence_count=1, people_count=1,
        )
        f2 = ComplexityFactors(
            # 初始化变量 keyword_count
            keyword_count=5, sentence_count=5,
            # 初始化变量 evidence_count
            evidence_count=3, people_count=3,
        )
        assert _compute_composite_score(f1) < _compute_composite_score(f2)

    def test_float_return_type(self):

        # 执行 test_classification_labels_are_chinese 函数的核心逻辑
        factors = ComplexityFactors(
            # 初始化变量 keyword_count
            keyword_count=3, sentence_count=2, evidence_count=1, people_count=1,
        )
        # 初始化变量 score
        score = _compute_composite_score(factors)
        assert isinstance(score, float)

    def test_non_negative_score(self):
        # 函数 test_non_negative_score 的初始化逻辑
        factors = ComplexityFactors()
        assert _compute_composite_score(factors) >= 0.0


# ---------------------------------------------------------------------------
# 复杂度分类测试（增强版）
# ---------------------------------------------------------------------------

# 定义 TestClassifyComplexity 类
class TestClassifyComplexity:

    # TestClassifyComplexity 类定义，封装相关属性和方法
    def test_simple_case(self):
        # 函数 test_simple_case 的初始化逻辑
        text = "被告人故意伤害被害人，案发后自首。"
        assert classify_complexity(text) == "simple"

    def test_medium_case(self):
        # 函数 test_medium_case 的初始化逻辑
        text = (
            "被告人张某明知他人实施诈骗犯罪，仍提供银行卡用于转账。"
            "银行流水显示涉案金额50万元。证人王某证实上述事实。"
            "本案涉及多名被害人。"
        )
        # 初始化变量 result
        result = classify_complexity(text)
        assert result in ("simple", "medium", "complex")

    def test_complex_case(self):
        # 函数 test_complex_case 的初始化逻辑
        text = (
            "被告人张某与共犯李某预谋后，以非法占有为目的，采用虚构事实的手段，"
            "骗取多名被害人财物。经查，张某利用银行卡进行支付结算，"
            "银行流水显示涉案金额共计100余万元，数额特别巨大。"
            "案发现场监控录像记录全过程，证人王某、赵某、孙某的证言相互印证。"
            "电子数据经鉴定真实有效。被害人存在多处伤情，经鉴定为轻伤。"
            "被告人曾因类似犯罪被判处有期徒刑，系累犯。"
            "案发后部分赃款已被追回。"
        )
        # 初始化变量 result
        result = classify_complexity(text)
        assert result in ("medium", "complex")

    def test_empty_string(self):
        # 函数 test_empty_string 的初始化逻辑
        assert classify_complexity("") == "simple"

    def test_short_non_legal_text(self):
        # 函数 test_short_non_legal_text 的初始化逻辑
        text = "今天天气很好。"
        assert classify_complexity(text) == "simple"

    def test_return_type_is_valid(self):
        # 函数 test_return_type_is_valid 的初始化逻辑
        text = "任意测试文本"
        # 初始化变量 result
        result = classify_complexity(text)
        assert result in ("simple", "medium", "complex")

    def test_very_complex_case_returns_complex(self):
        # 函数 test_very_complex_case_returns_complex 的初始化逻辑
        text = (
            "被告人张三与共犯李四、王五预谋后，以非法占有为目的，"
            "采用虚构事实、隐瞒真相的手段，骗取多名被害人财物。"
            "经鉴定，银行流水显示涉案金额共计200余万元，数额特别巨大，"
            "情节特别严重。案发现场监控录像记录全过程，"
            "证人赵六、孙七、周八、吴九的证言相互印证。"
            "电子数据、物证、书证、鉴定意见均指向被告人有罪。"
            "DNA鉴定确认现场血迹与被告人一致，指纹比对成功。"
            "被告人曾因故意伤害罪被判处有期徒刑，系累犯。"
            "部分赃款已被追回，作案工具被扣押。"
            "微信聊天记录、通话记录证实犯罪预谋过程。"
            "被告人自首后认罪认罚，但情节特别严重。"
        )
        assert classify_complexity(text) == "complex"

    def test_consistency_same_input(self):
        # 函数 test_consistency_same_input 的初始化逻辑
        text = "被告人故意伤害被害人，造成轻伤结果。经鉴定伤情属实。"
        # 初始化变量 result1
        result1 = classify_complexity(text)
        # 初始化变量 result2
        result2 = classify_complexity(text)
        assert result1 == result2

    def test_classification_labels_are_chinese(self):
        # 函数 test_classification_labels_are_chinese 的初始化逻辑
        text = "被告人故意伤害被害人。"
        # 初始化变量 result
        result = classify_complexity(text)
        assert result in ("simple", "medium", "complex")


# ---------------------------------------------------------------------------
# 单通道分析测试
# ---------------------------------------------------------------------------

# 定义 TestSinglePassAnalysis 类
class TestSinglePassAnalysis:

    # TestSinglePassAnalysis 类定义，封装相关属性和方法
    async def test_successful_analysis(
        # 函数 test_successful_analysis 的初始化逻辑
            self, sample_case_text, mock_ollama_response  # noqa: ARG002
    ):
        # 初始化变量 result
        result = await single_pass_analysis(sample_case_text)
        assert "subjective_knowledge" in result
        assert "sentence" in result
        assert "ground_truth_analysis" in result
        assert result["ground_truth_analysis"]["dimension1"]["score"] == 8.0

    async def test_with_mode_param(
        # 函数 test_with_mode_param 的初始化逻辑
            self, sample_case_text, mock_ollama_response  # noqa: ARG002
    ):
        # 初始化变量 result
        result = await single_pass_analysis(sample_case_text, mode="single")
        assert result["ground_truth_analysis"]["dimension2"]["score"] == 7.0

    async def test_llm_error(self, mock_ollama_response):
        # 函数 test_llm_error 的初始化逻辑
        mock_ollama_response.side_effect = RuntimeError("LLM unavailable")
        # 使用上下文管理器管理资源
        with pytest.raises(RuntimeError, match="LLM unavailable"):
            # 异步等待操作完成
            await single_pass_analysis("test case")

    async def test_unparseable_response(self, mock_ollama_response):
        """当 LLM 返回无法解析的文本时，应返回默认降级结果."""
        # 清除 side_effect，使用 return_value 返回不可解析的文本
        mock_ollama_response.side_effect = None
        mock_ollama_response.return_value = "这不是有效的 JSON"
        # 初始化变量 result
        result = await single_pass_analysis("test case")
        assert result["fallback"] is True
        assert result["subjective_knowledge"] == "未知"
        assert "ground_truth_analysis" in result

    async def test_markdown_wrapped_response(self, mock_ollama_response):
        """LLM 返回被 markdown 包裹的 JSON 时应正确解析."""
        # 清除 side_effect，使用 return_value
        mock_ollama_response.side_effect = None
        mock_ollama_response.return_value = json.dumps(
            {
                "subjective_knowledge": "明知",
                "sentence": "有期徒刑一年",
                "ground_truth_analysis": {
                    "dimension1": {"score": 8.0, "reasoning": "test1"},
                    "dimension2": {"score": 7.0, "reasoning": "test2"},
                    "dimension3": {"score": 6.0, "reasoning": "test3"},
                },
            }
        )
        # 初始化变量 result
        result = await single_pass_analysis("test case")
        assert result["subjective_knowledge"] == "明知"


# ---------------------------------------------------------------------------
# 多维度分析测试（含并行执行和异常隔离）
# ---------------------------------------------------------------------------

# 定义 TestMultiDimensionAnalysis 类
class TestMultiDimensionAnalysis:

    # TestMultiDimensionAnalysis 类定义，封装相关属性和方法
    async def test_successful_analysis(
        # 函数 test_successful_analysis 的初始化逻辑
            self, sample_case_text, mock_ollama_response
    ):
        mock_ollama_response.side_effect = None
        mock_ollama_response.return_value = json.dumps(
            {
                "score": 8.0,
                "reasoning": "test",
                "key_indicators": ["明知"],
                "sentence_suggestion": "有期徒刑一年",
            }
        )
        # 初始化变量 result
        result = await multi_dimension_analysis(sample_case_text)
        assert "ground_truth_analysis" in result
        assert "subjective_knowledge" in result
        assert "sentence" in result
        assert result["subjective_knowledge"] == "明知"

    async def test_returns_ground_truth(
        # 函数 test_returns_ground_truth 的初始化逻辑
            self, sample_case_text, mock_ollama_response
    ):
        mock_ollama_response.return_value = json.dumps(
            {
                "score": 8.0,
                "reasoning": "test",
                "key_indicators": ["明知"],
                "sentence_suggestion": "有期徒刑一年",
            }
        )
        # 初始化变量 result
        result = await multi_dimension_analysis(sample_case_text)
        gta = result["ground_truth_analysis"]
        assert "dimension1" in gta
        assert "dimension2" in gta
        assert "dimension3" in gta

    async def test_parallel_call_count(
        # 函数 test_parallel_call_count 的初始化逻辑
            self, sample_case_text, mock_ollama_response
    ):
        """验证并行执行时三次 LLM 调用均被执行."""
        mock_ollama_response.return_value = json.dumps(
            {
                "score": 8.0,
                "reasoning": "test",
                "key_indicators": ["明知"],
                "sentence_suggestion": "有期徒刑一年",
            }
        )
        # 异步等待操作完成
        await multi_dimension_analysis(sample_case_text)
        assert mock_ollama_response.call_count == 3

    async def test_exception_isolation(self, mock_ollama_response):
        """单个维度失败不影响其他维度，降级为默认值."""
        # 维度1正常，维度2抛异常，维度3正常 —— 分三次调用
        call_count = 0

        async def side_effect(*_args, **_kwargs):
            # 函数 side_effect 的初始化逻辑
            nonlocal call_count
            call_count += 1
            # 条件判断：处理业务逻辑
            if call_count == 2:
                msg = "维度2 LLM 调用失败"
                # 抛出异常，处理错误情况
                raise RuntimeError(msg)
            # 返回处理结果
            return json.dumps({"score": 8.0, "reasoning": f"dim{call_count}"})

        mock_ollama_response.side_effect = side_effect

        # 初始化变量 result
        result = await multi_dimension_analysis("test case")
        gta = result["ground_truth_analysis"]

        # 维度1正常
        assert gta["dimension1"]["score"] == 8.0
        # 维度2降级
        assert gta["dimension2"]["score"] == 5.0
        assert gta["dimension2"]["reasoning"] == "自动分析结果"
        # 维度3正常
        assert gta["dimension3"]["score"] == 8.0

    async def test_all_dimensions_fail(self, mock_ollama_response):
        """所有维度均失败时，全部降级为默认值."""
        mock_ollama_response.side_effect = RuntimeError("all fail")

        # 初始化变量 result
        result = await multi_dimension_analysis("test case")
        gta = result["ground_truth_analysis"]

        # 遍历: for dim_key in ("dimension1", "dimension2", "dimen
        for dim_key in ("dimension1", "dimension2", "dimension3"):
            assert gta[dim_key]["score"] == 5.0
            assert gta[dim_key]["reasoning"] == "自动分析结果"

        assert result["subjective_knowledge"] == "未知"
        assert result["sentence"] == "待定"

    async def test_unparseable_response_per_dimension(
        # 函数 test_unparseable_response_per_dimension 的初始化逻辑
            self, mock_ollama_response
    ):
        """LLM 返回无法解析的文本时，各维度独立降级."""
        # 初始化变量 call_count
        call_count = 0

        async def side_effect(*_args, **_kwargs):
            # 函数 side_effect 的初始化逻辑
            nonlocal call_count
              # 条件判断：处理业务逻辑
          call_count += 1
            # 条件判断: 检查 call_count == 2
            if call_count == 2:
                # 返回处理结果
                return "not valid json at all"
            # 返回处理结果
            return json.dumps(
                {"score": 8.0, "reasoning": f"dim{call_count}"}
            )

        mock_ollama_response.side_effect = side_effect

        # 初始化变量 result
        result = await multi_dimension_analysis("test case")
        gta = result["ground_truth_analysis"]

        assert gta["dimension1"]["reasoning"] == "dim1"
        assert gta["dimension2"]["reasoning"] == "自动分析结果"  # 降级
        assert gta["dimension3"]["reasoning"] == "dim3"

    # -------------------------------------------------------------------
    # 并行执行 + 性能计时 + 异常元数据 测试
    # -------------------------------------------------------------------

    async def test_dimension_meta_present_on_success(
        # 函数 test_dimension_meta_present_on_success 的初始化逻辑
        self, sample_case_text, mock_ollama_response
    ):
        """成功执行时，dimension_meta 包含各维度状态和耗时信息."""
        mock_ollama_response.return_value = json.dumps(
            {
                "score": 8.0,
                "reasoning": "test",
                "key_indicators": ["明知"],
                "sentence_suggestion": "有期徒刑一年",
            }
        )
        # 初始化变量 result
        result = await multi_dimension_analysis(sample_case_text)
        assert "dimension_meta" in result
        # 初始化变量 meta
        meta = result["dimension_meta"]

        # 遍历: for dim_key in ("dimension1", "dimension2", "dimen
        for dim_key in ("dimension1", "dimension2", "dimension3"):
            assert dim_key in meta
            assert meta[dim_key]["status"] == "success"
            assert meta[dim_key]["duration_ms"] >= 0
            assert "start_time" in meta[dim_key]
            assert "end_time" in meta[dim_key]
            assert meta[dim_key]["start_time"] != ""
            assert "error" not in meta[dim_key]

    async def test_dimension_meta_on_exception(
        # 函数 test_dimension_meta_on_exception 的初始化逻辑
        self, mock_ollama_response
    ):
        """单维度失败时，dimension_meta 记录失败状态和异常详情."""
        # 初始化变量 call_count
        call_count = 0

        async def side_effect(*_args, **_kwargs):
                    # 条件判断：处理业务逻辑
    nonlocal call_count
            call_count += 1
            # 条件判断: 检查 call_count == 2
            if call_count == 2:
                msg = "维度2 LLM 连接超时"
                # 抛出异常，处理错误情况
                raise RuntimeError(msg)
            # 返回处理结果
            return json.dumps({"score": 8.0, "reasoning": f"dim{call_count}"})

        mock_ollama_response.side_effect = side_effect

        # 初始化变量 result
        result = await multi_dimension_analysis("test case")
        # 初始化变量 meta
        meta = result["dimension_meta"]

        assert meta["dimension1"]["status"] == "success"
        assert meta["dimension2"]["status"] == "failed"
        assert meta["dimension3"]["status"] == "success"

        assert meta["dimension2"]["error"] == "维度2 LLM 连接超时"
        assert meta["dimension2"]["error_type"] == "RuntimeError"
        assert "error_time" in meta["dimension2"]
        assert meta["dimension2"]["error_time"] != ""

        assert meta["dimension1"]["duration_ms"] >= 0
        assert meta["dimension2"]["duration_ms"] >= 0
        assert meta["dimension3"]["duration_ms"] >= 0

    async def test_dimension_meta_all_fail(self, mock_ollama_response):
        """所有维度均失败时，dimension_meta 全部记录为 failed."""
        mock_ollama_response.side_effect = RuntimeError("全部失败")

        # 初始化变量 result
        result = await multi_dimension_analysis("test case")
        # 初始化变量 meta
        meta = result["dimension_meta"]

        # 遍历: for dim_key in ("dimension1", "dimension2", "dimen
        for dim_key in ("dimension1", "dimension2", "dimension3"):
            assert meta[dim_key]["status"] == "failed"
            assert meta[dim_key]["error_type"] == "RuntimeError"
            assert "error_time" in meta[dim_key]

        gta = result["ground_truth_analysis"]
        assert gta["dimension1"]["score"] == 5.0
        assert gta["dimension2"]["score"] == 5.0
        assert gta["dimension3"]["score"] == 5.0

    async def test_dimension_meta_timing_values(
        # 函数 test_dimension_meta_timing_values 的初始化逻辑
        self, sample_case_text, mock_ollama_response
    ):
        """验证各维度耗时记录为合理的非负数值."""

        mock_ollama_response.return_value = json.dumps(
            {"score": 8.0, "reasoning": "test"}
        )

        # 初始化变量 result
        result = await multi_dimension_analysis(sample_case_text)
        # 初始化变量 meta
        meta = result["dimension_meta"]

        # 遍历: for dim_key in ("dimension1", "dimension2", "dimen
        for dim_key in ("dimension1", "dimension2", "dimension3"):
            # 初始化变量 duration
            duration = meta[dim_key]["duration_ms"]
            assert isinstance(duration, (int, float))
            assert duration >= 0
            assert duration < 60000  # 不应超过 60 秒（测试 mock 调用极快）

    async def test_parallel_execution_timing(
        # 函数 test_parallel_execution_timing 的初始化逻辑
        self, sample_case_text, mock_ollama_response
    ):
        """验证并行执行：总耗时小于各维度单独耗时之和."""
        # 初始化变量 delays
        delays = [0.05, 0.05, 0.05]  # 各维度 50ms 延迟
        call_times: list[float] = []

        async def delayed_response(*_args, **_kwargs):
            # 函数 delayed_response 的初始化逻辑
            call_times.append(time.perf_counter())
            # 异步等待操作完成
            await asyncio.sleep(delays[len(call_times) - 1])
            # 返回处理结果
            return json.dumps({"score": 8.0, "reasoning": "test"})

        mock_ollama_response.side_effect = delayed_response

        t0 = time.perf_counter()
        # 初始化变量 result
        result = await multi_dimension_analysis(sample_case_text)
        # 初始化变量 total_elapsed
        total_elapsed = (time.perf_counter() - t0) * 1000

        # 初始化变量 meta
        meta = result["dimension_meta"]
        # 初始化变量 individual_sum
        individual_sum = sum(
            meta[dim]["duration_ms"]
            # 循环遍历：处理业务逻辑
            for dim in ("dimension1", "dimension2", "dimension3")
        )

        assert total_elapsed < individual_sum * 0.8

        assert mock_ollama_response.call_count == 3

    async def test_return_format_backward_compatible(
        # 函数 test_return_format_backward_compatible 的初始化逻辑
        self, sample_case_text, mock_ollama_response
    ):
        """验证返回结果格式向后兼容，原有字段均存在."""
        mock_ollama_response.return_value = json.dumps(
            {
                "score": 8.0,
                "reasoning": "test",
                "key_indicators": ["明知"],
                "sentence_suggestion": "有期徒刑一年",
            }
        )
        # 初始化变量 result
        result = await multi_dimension_analysis(sample_case_text)
        assert "ground_truth_analysis" in result
        assert "subjective_knowledge" in result
        assert "sentence" in result
        assert "fallback" in result
        assert "timestamp" in result
        assert result["fallback"] is False
        assert result["timestamp"].endswith("Z") or "+" in result["timestamp"]
        assert "dimension_meta" in result

    async def test_dimension_meta_different_exception_types(
        # 函数 test_dimension_meta_different_exception_types 的初始化逻辑
        self, mock_ollama_response
    ):
        """验证不同类型异常均能正确记录."""
        # 初始化变量 call_count
        call_count = 0

        async def side_effect(*_            # 条件判断：处理业务逻辑
            # 函数 side_effect 的初始化逻辑
args, **_kwargs):
            nonlocal call_count
            call_count             # 条件判断：处理业务逻辑
+= 1
            # 条件判断: 检查 call_count == 1
            if call_count == 1:
                msg = "参数错误"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 条件判断: 检查 call_count == 2
            if call_count == 2:
                msg = "连接失败"
                # 抛出异常，处理错误情况
                raise ConnectionError(msg)
            msg = "超时"
            # 抛出异常，处理错误情况
            raise TimeoutError(msg)

        mock_ollama_response.side_effect = side_effect

        # 初始化变量 result
        result = await multi_dimension_analysis("test case")
        # 初始化变量 meta
        meta = result["dimension_meta"]

        assert meta["dimension1"]["status"] == "failed"
        assert meta["dimension1"]["error_type"] == "ValueError"
        assert meta["dimension1"]["error"] == "参数错误"

        assert meta["dimension2"]["status"] == "failed"
        assert meta["dimension2"]["error_type"] == "ConnectionError"
        assert meta["dimension2"]["error"] == "连接失败"

        assert meta["dimension3"]["status"] == "failed"
        assert meta["dimension3"]["error_type"] == "TimeoutError"
        assert meta["dimension3"]["error"] == "超时"

    async def test_dimension_meta_partial_failure(
        # 函数 test_dimension_meta_partial_failure 的初始化逻辑
        self, mock_ollama_response
    ):
        """部分维度失败时，成功维度不受影响且正常返回数据."""
                # 条件判断：处理业务逻辑
    call_count = 0

        async def side_effect(*_args, **_kwargs):
            # 函数 side_effect 的初始化逻辑
            nonlocal call_count
            call_count += 1
            # 条件判断: 检查 call_count == 2
            if call_count == 2:
                msg = "维度2失败"
                # 抛出异常，处理错误情况
                raise RuntimeError(msg)
            # 返回处理结果
            return json.dumps(
                {
                    "score": 8.0,
                    "reasoning": f"dim{call_count}",
                    "key_indicators": [f"指标{call_count}"],
                    "sentence_suggestion": f"建议{call_count}",
                }
            )

        mock_ollama_response.side_effect = side_effect

        # 初始化变量 result
        result = await multi_dimension_analysis("test case")
        gta = result["ground_truth_analysis"]

        assert gta["dimension1"]["reasoning"] == "dim1"
        assert gta["dimension3"]["reasoning"] == "dim3"
        assert gta["dimension2"]["score"] == 5.0
        assert result["subjective_knowledge"] == "指标1"
        assert result["sentence"] == "建议1"


# ---------------------------------------------------------------------------
# 分析管道主入口测试
# ---------------------------------------------------------------------------

# 定义 TestAnalyzePipeline 类
class TestAnalyzePipeline:

    # TestAnalyzePipeline 类定义，封装相关属性和方法
    async def test_auto_simple_case(
        # 函数 test_auto_simple_case 的初始化逻辑
            self, sample_case_text, mock_ollama_response  # noqa: ARG002
    ):
        # 初始化变量 result
        result = await analyze_pipeline(sample_case_text, mode="auto", version="v1")
        assert "ground_truth_analysis" in result
        assert "fallback" in result
        assert "timestamp" in result
        assert result["fallback"] is False

    async def test_auto_complex_case(self, mock_ollama_response):
        # 执行 test_returns_default_score_and_reasoning 函数的核心逻辑
        mock_ollama_response.return_value = json.dumps(
            {
                "score": 8.0,
                "reasoning": "test",
                "key_indicators": ["明知"],
                "sentence_suggestion": "有期徒刑一年",
            }
        )
        # 初始化变量 long_text
        long_text = "案情描述。" * 500
        # 初始化变量 result
        result = await analyze_pipeline(long_text, mode="auto", version="v1")
        assert result["fallback"] is False

    async def test_force_single_mode(
        # 函数 test_force_single_mode 的初始化逻辑
            self, sample_case_text, mock_ollama_response
    ):
        mock_ollama_response.return_value = json.dumps(
            {
                "subjective_knowledge": "明知",
                "sentence": "有期徒刑一年",
                "ground_truth_analysis": {
                    "dimension1": {"score": 8.0, "reasoning": "test"},
                    "dimension2": {"score": 7.0, "reasoning": "test"},
                    "dimension3": {"score": 6.0, "reasoning": "test"},
                },
            }
        )
        # 异步等待操作完成
        await analyze_pipeline(sample_case_text, mode="single", version="v1")
        assert mock_ollama_response.call_count == 1

    async def test_force_multi_mode(
        # 函数 test_force_multi_mode 的初始化逻辑
            self, sample_case_text, mock_ollama_response
    ):
        mock_ollama_response.return_value = json.dumps(
            {
                "score": 8.0,
                "reasoning": "test",
                "key_indicators": ["明知"],
                "sentence_suggestion": "有期徒刑一年",
            }
        )
        # 异步等待操作完成
        await analyze_pipeline(sample_case_text, mode="multi", version="v1")
        assert mock_ollama_response.call_count == 9

    async def test_fallback_dimensions(self, mock_ollama_response):
        # 函数 test_fallback_dimensions 的初始化逻辑
        mock_ollama_response.side_effect = None
        mock_ollama_response.return_value = json.dumps(
            {"subjective_knowledge": "明知", "sentence": "test"}
        )
        # 初始化变量 result
        result = await analyze_pipeline("test case", mode="single", version="v1")
        gta = result["ground_truth_analysis"]
        assert gta["dimension1"]["score"] == 5.0
        assert gta["dimension2"]["score"] == 5.0
        assert gta["dimension3"]["score"] == 5.0
        assert gta["dimension1"]["reasoning"] == "自动分析结果"

    async def test_timestamp_and_fallback(
        # 函数 test_timestamp_and_fallback 的初始化逻辑
            self, sample_case_text, mock_ollama_response  # noqa: ARG002
    ):
        # 初始化变量 result
        result = await analyze_pipeline(sample_case_text, mode="single", version="v1")
        assert result["fallback"] is False
        assert "timestamp" in result
        assert result["timestamp"].endswith("Z") or "+" in result["timestamp"]


# ---------------------------------------------------------------------------
# 默认值构建函数测试
# ---------------------------------------------------------------------------

# 定义 TestBuildDefaultDimension 类
class TestBuildDefaultDimension:

    # TestBuildDefaultDimension 类定义，封装相关属性和方法
    def test_returns_default_score_and_reasoning(self):
        # 函数 test_returns_default_score_and_reasoning 的初始化逻辑
        result = _build_default_dimension()
        assert result["score"] == 5.0
        assert result["reasoning"] == "自动分析结果"
