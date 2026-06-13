from app.utils.common import generate_cache_key, sanitize_json_string


class TestSanitizeJsonString:
    def test_normal_json(self):
        text = '{"key": "value"}'
        assert sanitize_json_string(text) == text

    def test_markdown_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        expected = '{"key": "value"}'
        assert sanitize_json_string(text) == expected

    def test_markdown_with_language(self):
        text = '```json\n{\n  "name": "test",\n  "score": 8.5\n}\n```'
        result = sanitize_json_string(text)
        assert '"name": "test"' in result
        assert '"score": 8.5' in result
        assert "```" not in result

    def test_text_before_json(self):
        text = '以下是分析结果：\n{"result": "success"}'
        assert sanitize_json_string(text) == '{"result": "success"}'

    def test_text_after_json(self):
        text = '{"result": "success"}\n以上是分析结果'
        assert sanitize_json_string(text) == '{"result": "success"}'

    def test_surrounding_text(self):
        text = '分析：{"data": "内容"}。结束。'
        assert sanitize_json_string(text) == '{"data": "内容"}'

    def test_markdown_with_text_surrounding(self):
        text = '```\n{"key": "value"}\n```\n注释'
        assert sanitize_json_string(text) == '{"key": "value"}'

    def test_no_json_found(self):
        text = "纯文本内容，没有JSON"
        assert sanitize_json_string(text) == text

    def test_empty_string(self):
        assert sanitize_json_string("") == ""

    def test_invalid_json_content(self):
        text = "```\n{invalid json}\n```"
        result = sanitize_json_string(text)
        assert result == "{invalid json}"


class TestGenerateCacheKey:
    def test_same_args_produce_same_key(self):
        k1 = generate_cache_key("analysis", "case_123")
        k2 = generate_cache_key("analysis", "case_123")
        assert k1 == k2

    def test_different_args_produce_different_key(self):
        k1 = generate_cache_key("analysis", "case_a")
        k2 = generate_cache_key("analysis", "case_b")
        assert k1 != k2

    def test_hex_string_output(self):
        key = generate_cache_key("test")
        assert all(c in "0123456789abcdef" for c in key)

    def test_consistent_length(self):
        k1 = generate_cache_key("short")
        k2 = generate_cache_key("a" * 1000)
        assert len(k1) == len(k2)

    def test_with_multiple_args(self):
        key = generate_cache_key("analysis", "case_1", "mode", "single")
        assert isinstance(key, str)
        assert len(key) > 0

    def test_with_none_args(self):
        key = generate_cache_key("analysis", None)
        assert isinstance(key, str)
        assert len(key) > 0

    def test_with_dict_args(self):
        key = generate_cache_key("test", {"complex": "object"})
        assert isinstance(key, str)
