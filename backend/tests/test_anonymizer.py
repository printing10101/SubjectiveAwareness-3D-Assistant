"""数据脱敏工具单元测试.

为 anonymizer.anonymize_text 的每种脱敏模式设计至少 3 个测试用例，
并包含边界情况测试（空字符串、超长文本、格式错误的数据等）。
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: pytest
import pytest

# 导入模块: from app.utils.anonymizer
from app.utils.anonymizer import (
    _anonymize_names,
    _build_party_label,
    _mask_addresses,
    _mask_bank_cards,
    _mask_id_cards,
    _mask_phones,
    anonymize_text,
)


# ---------------------------------------------------------------------------
# anonymize_text 集成测试
# ---------------------------------------------------------------------------


# 定义 TestAnonymizeText 类
class TestAnonymizeText:
    """anonymize_text 集成场景测试."""

    def test_full_pipeline_id_card(self) -> None:
        """身份证号在集成场景下被脱敏."""
        # 初始化变量 text
        text = "被告人身份证号 110101199001011234 已核实。"
        # 初始化变量 result
        result = anonymize_text(text)
        assert "110101199001011234" not in result
        assert "110101" in result
        assert "1234" in result
        assert "********" in result

    def test_full_pipeline_phone(self) -> None:
        """手机号在集成场景下被脱敏."""
        # 初始化变量 text
        text = "联系电话：13812345678"
        # 初始化变量 result
        result = anonymize_text(text)
        assert "13812345678" not in result
        assert "138" in result
        assert "5678" in result
        assert "****" in result

    def test_full_pipeline_bank_card(self) -> None:
        """银行卡号在集成场景下被脱敏."""
        # 初始化变量 text
        text = "涉案银行卡 6222021234567890123 已冻结。"
        # 初始化变量 result
        result = anonymize_text(text)
        assert "6222021234567890123" not in result
        assert "6222" in result
        assert "0123" in result
        assert "********" in result

    def test_full_pipeline_name_mapping(self) -> None:
        """姓名按出现顺序映射为 当事人A/B/C."""
        # 初始化变量 text
        text = "张某、李某、王某三人共同实施。"
        # 初始化变量 result
        result = anonymize_text(text)
        assert "当事人A" in result
        assert "当事人B" in result
        assert "当事人C" in result
        assert "张某" not in result
        assert "李某" not in result
        assert "王某" not in result

    def test_full_pipeline_address(self) -> None:
        """详细住址被精简为省级+市级."""
        # 初始化变量 text
        text = "住址：北京市朝阳区建国路88号现代城A座1501室"
        # 初始化变量 result
        result = anonymize_text(text)
        # 应保留 "北京市"，"朝阳区" 及以下被删除
        assert "北京市" in result
        assert "建国路" not in result
        assert "1501" not in result

    def test_full_pipeline_province_city(self) -> None:
        """省级+市级地址的脱敏结果仅保留省市."""
        # 初始化变量 text
        text = "户籍地：广东省深圳市南山区科技园南区T2栋"
        # 初始化变量 result
        result = anonymize_text(text)
        assert "广东省" in result
        assert "深圳市" in result
        assert "南山区" not in result
        assert "科技园" not in result

    def test_full_pipeline_complex_case(self) -> None:
        """复杂案件描述一次性脱敏多种信息."""
        # 初始化变量 text
        text = (
            "被告人张某，男，1995年出生，户籍地：广东省深圳市南山区科技园南路88号，"
            "身份证 110101199001011234，电话 13812345678，"
            "涉案银行卡 6222021234567890123。被告人李某在同案中提供帮助。"
        )
        # 初始化变量 result
        result = anonymize_text(text)
        assert "张某" not in result
        assert "李某" not in result
        assert "当事人A" in result
        assert "当事人B" in result
        assert "110101199001011234" not in result
        assert "13812345678" not in result
        assert "6222021234567890123" not in result
        assert "南山区" not in result

    def test_full_pipeline_repeated_name(self) -> None:
        """同一姓名重复出现应映射到同一标识."""
        # 初始化变量 text
        text = "张某指使张某实施犯罪，张某事后逃离。"
        # 初始化变量 result
        result = anonymize_text(text)
        # 全文应仅有一个 "当事人A"
        assert result.count("当事人A") == 3
        assert "张某" not in result

    def test_full_pipeline_preserves_other_text(self) -> None:
        """脱敏不应破坏非敏感文本."""
        # 初始化变量 text
        text = "本案涉及帮助信息网络犯罪活动罪，案发地在北京。"
        # 初始化变量 result
        result = anonymize_text(text)
        assert "帮助信息网络犯罪活动罪" in result
        assert "案发地" in result
        # 北京市作为地址被脱敏后仅保留 "北京市"
        assert "北京" in result

    def test_full_pipeline_empty(self) -> None:
        """空字符串应原样返回."""
        assert anonymize_text("") == ""

    def test_full_pipeline_none(self) -> None:
        """None 输入应原样返回."""
        assert anonymize_text(None) is None

    def test_full_pipeline_non_string(self) -> None:
        """非字符串输入应原样返回."""
        # 非字符串输入应被原样保留（函数内部已做类型守卫）
        assert anonymize_text(123) == 123
        assert anonymize_text([]) == []

    def test_full_pipeline_very_long_text(self) -> None:
        """超长文本应能正确处理且不丢失信息."""
        # 初始化变量 prefix
        prefix = "这是一段不含敏感信息的案件描述文字，用于测试长文本处理能力。"
        # 初始化变量 long_text
        long_text = prefix * 500  # 约 25KB
        result = anonymize_text(long_text)
        assert result == long_text

    def test_full_pipeline_long_with_sensitive(self) -> None:
        """超长文本中的敏感信息应被正确脱敏."""
        # 初始化变量 base
        base = "张某一案，身份证110101199001011234，电话13812345678。"
        # 初始化变量 long_text
        long_text = base * 200
        # 初始化变量 result
        result = anonymize_text(long_text)
        assert "110101199001011234" not in result
        assert "13812345678" not in result
        assert "当事人A" in result


# ---------------------------------------------------------------------------
# 姓名脱敏
# ---------------------------------------------------------------------------


# 定义 TestAnonymizeNames 类
class TestAnonymizeNames:
    """_anonymize_names 单元测试."""

    def test_single_name(self) -> None:
        """单个姓名的脱敏."""
        # 初始化变量 result
        result = _anonymize_names("张某犯帮信罪。")
        assert result == "当事人A犯帮信罪。"

    def test_multiple_names_in_order(self) -> None:
        """多个姓名按出现顺序分配 A/B/C."""
        # 初始化变量 result
        result = _anonymize_names("张某、李某、王某")
        assert result == "当事人A、当事人B、当事人C"

    def test_repeated_name_keeps_label(self) -> None:
        """重复出现的姓名复用首次分配的标识."""
        # 初始化变量 result
        result = _anonymize_names("张某指示张某行事")
        assert result == "当事人A指示当事人A行事"

    def test_name_with_title(self) -> None:
        """带称谓的姓名应保留称谓."""
        # 初始化变量 result
        result = _anonymize_names("张某先生和李某女士")
        assert "当事人A先生" in result
        assert "当事人B女士" in result

    def test_name_momo_format(self) -> None:
        """'某某' 形式也应被识别."""
        # 初始化变量 result
        result = _anonymize_names("李某某涉案")
        assert result == "当事人A涉案"

    def test_unknown_surname_preserved(self) -> None:
        """未在已知姓氏集合中的姓名保留原文."""
        # "欧阳" 是复合姓，未在白名单中
        result = _anonymize_names("欧阳某协助作案")
        assert "欧阳某" in result
        assert "当事人A" not in result

    def test_jiang_surname(self) -> None:
        """蒋姓应在白名单内并被识别."""
        # 初始化变量 result
        result = _anonymize_names("蒋某被抓获")
        assert "当事人A" in result
        assert "蒋某" not in result

    def test_label_assignment_after_26(self) -> None:
        """超过 26 个姓名时使用 AA/AB 标识."""
        # 27 个不同常见姓氏，每个后面跟"某"形成合法姓名模式
        text = (
            "张某、李某、王某、刘某、陈某、马某、赵某、黄某、周某、吴某、"
            "徐某、孙某、胡某、朱某、高某、林某、何某、郭某、罗某、梁某、"
            "宋某、郑某、谢某、韩某、唐某、冯某、于某、董某"
        )
        # 初始化变量 result
        result = _anonymize_names(text)
        # 前 26 个姓名应映射到 当事人A-Z
        assert "当事人A" in result
        assert "当事人Z" in result
        # 第 27 个姓名（董某）应映射到 当事人AA
        assert "当事人AA" in result
        assert "董某" not in result

    def test_unicode_preservation(self) -> None:
        """姓名脱敏不应破坏中文字符编码."""
        # 初始化变量 result
        result = _anonymize_names("帮信罪案件中，张某和李某共同犯罪。")
        assert isinstance(result, str)
        assert len(result) == len("帮信罪案件中，当事人A和当事人B共同犯罪。")

    def test_empty_string(self) -> None:
        """空字符串脱敏."""
        assert _anonymize_names("") == ""

    def test_no_names(self) -> None:
        """不含姓名的文本应原样返回."""
        # 初始化变量 text
        text = "本案件涉及帮助信息网络犯罪活动罪。"
        assert _anonymize_names(text) == text


# ---------------------------------------------------------------------------
# 身份证号脱敏
# ---------------------------------------------------------------------------


# 定义 TestMaskIdCards 类
class TestMaskIdCards:
    """_mask_id_cards 单元测试."""

    def test_basic_id_card(self) -> None:
        """基本 18 位身份证号脱敏."""
        # 初始化变量 text
        text = "身份证 110101199001011234"
        # 初始化变量 result
        result = _mask_id_cards(text)
        assert result == "身份证 110101********1234"

    def test_multiple_id_cards(self) -> None:
        """多个身份证号同时脱敏."""
        # 初始化变量 text
        text = "甲：110101199001011234；乙：320106198805061234"
        # 初始化变量 result
        result = _mask_id_cards(text)
        assert "110101********1234" in result
        assert "320106********1234" in result

    def test_short_number_not_masked(self) -> None:
        """过短的数字序列不应被当作身份证号处理."""
        # 初始化变量 text
        text = "编号 12345"
        # 初始化变量 result
        result = _mask_id_cards(text)
        assert result == text

    def test_too_long_number_not_masked(self) -> None:
        """过长的数字序列（>18位）不会被误判为身份证号."""
        # 20 位连续数字：因正则末位的 (?!\d) lookahead 限制，
        # 任何 18 位子串都无法在末位后保持"非数字"边界，因此不会被遮蔽
        text = "数字 12345678901234567890"
        # 初始化变量 result
        result = _mask_id_cards(text)
        # 20 位整体不是合法身份证号，应原样保留
        assert result == text

    def test_id_card_with_prefix(self) -> None:
        """身份证号前有非数字字符时也应匹配."""
        # 初始化变量 text
        text = "身份证号:110101199001011234"
        # 初始化变量 result
        result = _mask_id_cards(text)
        assert "110101********1234" in result

    def test_id_card_with_suffix(self) -> None:
        """身份证号后有非数字字符时也应匹配."""
        # 初始化变量 text
        text = "110101199001011234,310101199001011234"
        # 初始化变量 result
        result = _mask_id_cards(text)
        assert "110101********1234" in result
        assert "310101********1234" in result

    def test_empty_string(self) -> None:
        """空字符串."""
        assert _mask_id_cards("") == ""

    def test_no_id_card(self) -> None:
        """不含身份证号的文本应原样返回."""
        # 初始化变量 text
        text = "本案涉及帮信罪。"
        assert _mask_id_cards(text) == text


# ---------------------------------------------------------------------------
# 银行卡号脱敏
# ---------------------------------------------------------------------------


# 定义 TestMaskBankCards 类
class TestMaskBankCards:
    """_mask_bank_cards 单元测试."""

    def test_basic_bank_card(self) -> None:
        """基本 16 位银行卡号脱敏."""
        # 初始化变量 text
        text = "卡号 6222021234567890"
        # 初始化变量 result
        result = _mask_bank_cards(text)
        assert result == "卡号 6222********7890"

    def test_19_digit_bank_card(self) -> None:
        """19 位银行卡号脱敏."""
        # 初始化变量 text
        text = "卡号 6222021234567890123"
        # 初始化变量 result
        result = _mask_bank_cards(text)
        assert "6222********0123" in result

    def test_17_digit_bank_card(self) -> None:
        """17 位银行卡号脱敏."""
        # 初始化变量 text
        text = "卡号 62220212345678901"
        # 初始化变量 result
        result = _mask_bank_cards(text)
        assert "6222********8901" in result

    def test_short_number_not_masked(self) -> None:
        """过短的数字序列不应被当作银行卡号处理."""
        # 初始化变量 text
        text = "卡号 1234"
        # 初始化变量 result
        result = _mask_bank_cards(text)
        assert result == text

    def test_multiple_bank_cards(self) -> None:
        """多个银行卡号同时脱敏."""
        # 初始化变量 text
        text = "卡1:6222021234567890123,卡2:6222029876543210987"
        # 初始化变量 result
        result = _mask_bank_cards(text)
        assert "6222********0123" in result
        assert "6222********0987" in result

    def test_empty_string(self) -> None:
        """空字符串."""
        assert _mask_bank_cards("") == ""

    def test_no_bank_card(self) -> None:
        """不含银行卡号的文本应原样返回."""
        # 初始化变量 text
        text = "本案件涉及银行卡。"
        assert _mask_bank_cards(text) == text


# ---------------------------------------------------------------------------
# 手机号脱敏
# ---------------------------------------------------------------------------


# 定义 TestMaskPhones 类
class TestMaskPhones:
    """_mask_phones 单元测试."""

    def test_basic_phone(self) -> None:
        """基本 11 位手机号脱敏."""
        # 初始化变量 text
        text = "电话 13812345678"
        # 初始化变量 result
        result = _mask_phones(text)
        assert result == "电话 138****5678"

    def test_phone_with_199_prefix(self) -> None:
        """199 开头手机号脱敏."""
        # 初始化变量 text
        text = "电话 19912345678"
        # 初始化变量 result
        result = _mask_phones(text)
        assert "199****5678" in result

    def test_phone_with_159_prefix(self) -> None:
        """159 开头手机号脱敏."""
        # 初始化变量 text
        text = "电话 15987654321"
        # 初始化变量 result
        result = _mask_phones(text)
        assert "159****4321" in result

    def test_invalid_prefix_preserved(self) -> None:
        """非 1[3-9] 开头的 11 位数字不应被匹配."""
        # 初始化变量 text
        text = "电话 12345678901"
        # 初始化变量 result
        result = _mask_phones(text)
        assert "12345678901" in result
        assert "****" not in result

    def test_invalid_prefix_2x(self) -> None:
        """12 开头 11 位数字不应被匹配（第二位为 2）."""
        # 初始化变量 text
        text = "电话 12345678901"
        # 初始化变量 result
        result = _mask_phones(text)
        assert "12345678901" in result

    def test_multiple_phones(self) -> None:
        """多个手机号同时脱敏."""
        # 初始化变量 text
        text = "甲 13812345678 乙 15987654321"
        # 初始化变量 result
        result = _mask_phones(text)
        assert "138****5678" in result
        assert "159****4321" in result

    def test_short_number_not_masked(self) -> None:
        """过短的数字序列不应被当作手机号处理."""
        # 初始化变量 text
        text = "编号 1234"
        # 初始化变量 result
        result = _mask_phones(text)
        assert result == text

    def test_empty_string(self) -> None:
        """空字符串."""
        assert _mask_phones("") == ""

    def test_no_phone(self) -> None:
        """不含手机号的文本应原样返回."""
        # 初始化变量 text
        text = "本案件涉及帮信罪。"
        assert _mask_phones(text) == text


# ---------------------------------------------------------------------------
# 详细住址脱敏
# ---------------------------------------------------------------------------


# 定义 TestMaskAddresses 类
class TestMaskAddresses:
    """_mask_addresses 单元测试."""

    def test_province_city_only(self) -> None:
        """省级+市级地址脱敏."""
        # 初始化变量 text
        text = "住址：广东省深圳市"
        # 初始化变量 result
        result = _mask_addresses(text)
        assert "广东省" in result
        assert "深圳市" in result

    def test_strip_district(self) -> None:
        """去除区级信息."""
        # 初始化变量 text
        text = "住址：广东省深圳市南山区"
        # 初始化变量 result
        result = _mask_addresses(text)
        assert "广东省" in result
        assert "深圳市" in result
        assert "南山区" not in result

    def test_strict_road_address(self) -> None:
        """去除路及以下地址."""
        # 初始化变量 text
        text = "户籍地：广东省深圳市南山区科技园南路88号"
        # 初始化变量 result
        result = _mask_addresses(text)
        assert "广东省" in result
        assert "深圳市" in result
        assert "南山区" not in result
        assert "科技园" not in result
        assert "88号" not in result

    def test_municipality(self) -> None:
        """直辖市格式."""
        # 初始化变量 text
        text = "户籍地：北京市海淀区中关村南大街5号"
        # 初始化变量 result
        result = _mask_addresses(text)
        assert "北京市" in result
        assert "海淀区" not in result
        assert "中关村" not in result

    def test_no_address(self) -> None:
        """不含地址的文本应原样返回."""
        # 初始化变量 text
        text = "本案件涉及帮信罪。"
        assert _mask_addresses(text) == text

    def test_empty_string(self) -> None:
        """空字符串."""
        assert _mask_addresses("") == ""

    def test_province_with_district_keyword(self) -> None:
        """地址中含"区"字的处理."""
        # 初始化变量 text
        text = "住址：江苏省南京市鼓楼区北京西路74号院"
        # 初始化变量 result
        result = _mask_addresses(text)
        assert "江苏省" in result
        assert "南京市" in result
        assert "鼓楼区" not in result


# ---------------------------------------------------------------------------
# _build_party_label 单元测试
# ---------------------------------------------------------------------------


# 定义 TestBuildPartyLabel 类
class TestBuildPartyLabel:
    """_build_party_label 标识生成测试."""

    def test_first_label_is_a(self) -> None:
        """第 0 个标识为 A."""
        assert _build_party_label(0) == "当事人A"

    def test_label_b(self) -> None:
        """第 1 个标识为 B."""
        assert _build_party_label(1) == "当事人B"

    def test_label_z(self) -> None:
        """第 25 个标识为 Z."""
        assert _build_party_label(25) == "当事人Z"

    def test_label_aa_after_26(self) -> None:
        """第 26 个标识为 AA."""
        assert _build_party_label(26) == "当事人AA"

    def test_label_ab_after_27(self) -> None:
        """第 27 个标识为 AB."""
        assert _build_party_label(27) == "当事人AB"

    def test_label_az(self) -> None:
        """第 51 个标识为 AZ."""
        assert _build_party_label(51) == "当事人AZ"

    def test_label_ba(self) -> None:
        """第 52 个标识为 BA."""
        assert _build_party_label(52) == "当事人BA"

    def test_negative_index(self) -> None:
        """负数索引返回安全占位符."""
        assert _build_party_label(-1) == "当事人?"


# ---------------------------------------------------------------------------
# 边界情况与错误处理
# ---------------------------------------------------------------------------


# 定义 TestBoundaryConditions 类
class TestBoundaryConditions:
    """边界情况与错误处理测试."""

    def test_only_whitespace(self) -> None:
        """仅空白字符的文本应原样返回."""
        assert anonymize_text("   ") == "   "

    def test_special_characters(self) -> None:
        """特殊字符不应影响脱敏结果."""
        # 初始化变量 text
        text = "@#$%^&*()_+={}[]|\\:;\"'<>,.?/~`"
        assert anonymize_text(text) == text

    def test_emoji_preserved(self) -> None:
        """emoji 字符应原样保留."""
        # 初始化变量 text
        text = "案件当事人 ⚖️ 张某 😊"
        # 初始化变量 result
        result = anonymize_text(text)
        assert "⚖️" in result
        assert "😊" in result
        assert "当事人A" in result

    def test_mixed_chinese_english(self) -> None:
        """中英文混合文本中的敏感信息应被脱敏."""
        # 初始化变量 text
        text = "User 张某 with ID 110101199001011234 and email test@example.com"
        # 初始化变量 result
        result = anonymize_text(text)
        # 邮箱不在脱敏范围内
        assert "test@example.com" in result
        assert "110101199001011234" not in result
        assert "当事人A" in result

    def test_multiline_text(self) -> None:
        """多行文本中的敏感信息应被正确处理."""
        # 初始化变量 text
        text = "第一行：张某涉案\n第二行：李某协助\n第三行：王某主谋"
        # 初始化变量 result
        result = anonymize_text(text)
        assert "当事人A" in result
        assert "当事人B" in result
        assert "当事人C" in result
        assert "张某" not in result

    def test_punctuation_preserved(self) -> None:
        """标点符号应被保留."""
        # 初始化变量 text
        text = "张某、李某、王某均已到案。"
        # 初始化变量 result
        result = anonymize_text(text)
        assert result == "当事人A、当事人B、当事人C均已到案。"

    def test_consecutive_sensitive_data(self) -> None:
        """连续的敏感信息应各自独立处理."""
        # 初始化变量 text
        text = "110101199001011234 13812345678 6222021234567890"
        # 初始化变量 result
        result = anonymize_text(text)
        assert "110101********1234" in result
        assert "138****5678" in result
        assert "6222********7890" in result

    def test_id_card_inside_other_number(self) -> None:
        """身份证号嵌入在更长数字序列中不应被误匹配."""
        # 24 位数字 - 由于 (?!\d) lookahead 限制，
        # 任何 18 位子串之后都还有数字，无法满足末位"非数字"边界
        text = "订单编号 123456789012345678901234"
        # 初始化变量 result
        result = _mask_id_cards(text)
        # 整个长数字序列不应被错误识别为身份证号
        assert result == text


# ---------------------------------------------------------------------------
# 性能与稳定性测试
# ---------------------------------------------------------------------------


# 定义 TestPerformanceStability 类
class TestPerformanceStability:
    """性能与稳定性测试."""

    def test_repeated_calls_consistent(self) -> None:
        """多次调用应产生一致结果."""
        # 初始化变量 text
        text = "张某和李某实施犯罪，张某使用 13812345678 联络。"
        # 初始化变量 first
        first = anonymize_text(text)
        # 初始化变量 second
        second = anonymize_text(text)
        # 初始化变量 third
        third = anonymize_text(text)
        assert first == second == third

    def test_unicode_edge_cases(self) -> None:
        """Unicode 边界情况."""
        # 全角字符
        text = "全角：张某１２３４５６７８"
        # 初始化变量 result
        result = anonymize_text(text)
        # 全角数字不会被当作手机号匹配
        assert "１２３４５６７８" in result

    def test_zero_width_characters(self) -> None:
        """零宽字符应不影响脱敏."""
        # 初始化变量 text
        text = "张\u200b某涉案"
        # 初始化变量 result
        result = anonymize_text(text)
        # 零宽字符不会破坏匹配
        assert "当事人A" in result

    # 应用装饰器: pytest.mark.parametrize
    @pytest.mark.parametrize(
        "text",
        [
            "张某",
            "李某和王某",
            "110101199001011234",
            "13812345678",
            "6222021234567890",
            "广东省深圳市南山区",
            "多种 张某 110101199001011234 13812345678 信息",
            "",
        ],
    )
    def test_parametrized_various_inputs(self, text: str) -> None:
        """参数化测试各种输入."""
        # 初始化变量 result
        result = anonymize_text(text)
        # 任何输入都不应抛出异常；非字符串输入原样返回
        assert isinstance(result, str) or result == text
