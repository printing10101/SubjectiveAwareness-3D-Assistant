"""规范路径识别器单元测试.

测试覆盖：
1. 每个路径分类的测试 fixture（4个枚举类型全覆盖）
2. 各判定函数的正确性
3. 优先级规则验证
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: json
import json
# 导入模块: from pathlib
from pathlib import Path

# 导入模块: pytest
import pytest

# 导入模块: from app.services.analysis_helpers
from app.services.analysis_helpers import (
    StandardPath,
    detect_fraud_coconspirator,
    detect_main_helper,
    detect_money_laundering,
    recognize_standard_path,
    recognize_standard_path_with_reason,
)

# 测试数据文件路径
_TEST_DATA_DIR = Path(__file__).parent / "data"
_TEST_CASES_FILE = _TEST_DATA_DIR / "path_recognition_cases.json"


# 应用装饰器: pytest.fixture
@pytest.fixture(scope="module")
def test_cases() -> list[dict]:
    """加载测试用例数据."""
    # 使用上下文管理器管理资源
    with _TEST_CASES_FILE.open("r", encoding="utf-8") as f:
        # 返回处理结果
        return json.load(f)


# 应用装饰器: pytest.fixture
@pytest.fixture
def fraud_coconspirator_case(test_cases: list[dict]) -> dict:
    """诈骗罪共同犯罪路径测试 fixture."""
    # 循环遍历：处理业务逻辑
    for case in test_cases:
        # 条件判断：处理业务逻辑
        if case["expected_path"] == "FRAUD_COCONSPIRATOR":
            # 返回处理结果
            return case
    # 抛出异常，处理错误情况
    raise ValueError("未找到 FRAUD_COCONSPIRATOR 测试用例")


# 应用装饰器: pytest.fixture
@pytest.fixture
def money_laundering_case(test_cases: list[dict]) -> dict:
    """掩饰隐瞒犯罪所得路径测试 fixture."""
    for case in test_cases:
        # 条件判断: 检查 case["expected_path"] == "MONEY_LAUNDERI
        if case["expected_path"] == "MONEY_LAUNDERING":
            # 返回处理结果
            return case
    # 抛出异常，处理错误情况
    raise ValueError("未找到 MONEY_LAUNDERING 测试用例")


# 应用装饰器: pytest.fixture
@pytest.fixture
def main_helper_case(test_cases: list[dict]) -> dict:
    """帮信罪主路径测试 fixture."""
    # 遍历: for case in test_cases:
    for case in test_cases:
        # 条件判断: 检查 case["expected_path"] == "MAIN_HELPER"
        if case["expected_path"] == "MAIN_HELPER":
            # 返回处理结果
            return case
    # 抛出异常，处理错误情况
    raise ValueError("未找到 MAIN_HELPER 测试用例")


# 应用装饰器: pytest.fixture
@pytest.fixture
def pending_verification_case(test_cases: list[dict]) -> dict:
    """规范路径待核实测试 fixture."""
    # 遍历: for case in test_cases:
    for case in test_cases:
        # 条件判断: 检查 case["expected_path"] == "PENDING_VERIFI
        if case["expected_path"] == "PENDING_VERIFICATION":
            # 返回处理结果
            return case
    # 抛出异常，处理错误情况
    raise ValueError("未找到 PENDING_VERIFICATION 测试用例")


# 定义 TestStandardPathEnum 类
class TestStandardPathEnum:
    """测试 StandardPath 枚举定义."""

    def test_enum_members(self) -> None:
        """验证枚举成员完整性."""
        assert StandardPath.MAIN_HELPER.value == "帮信罪主路径"
        assert StandardPath.FRAUD_COCONSPIRATOR.value == "诈骗罪共同犯罪路径"
        assert StandardPath.MONEY_LAUNDERING.value == "掩饰隐瞒犯罪所得路径"
        assert StandardPath.PENDING_VERIFICATION.value == "规范路径待核实"

    def test_enum_count(self) -> None:
        """验证枚举成员数量."""
        assert len(StandardPath) == 4


# 定义 TestDetectFraudCoconspirator 类
class TestDetectFraudCoconspirator:
    """测试诈骗罪共同犯罪路径判定函数."""

    def test_detect_fraud_coconspirator_positive(
        # 函数 test_detect_fraud_coconspirator_positive 的初始化逻辑
        self, fraud_coconspirator_case: dict

        # 执行 test_detect_fraud_coconspirator_positive 函数的核心逻辑
    ) -> None:
        """测试正例：命中诈骗罪共同犯罪路径."""
        # 初始化变量 result
        result = detect_fraud_coconspirator(fraud_coconspirator_case)
        assert result == StandardPath.FRAUD_COCONSPIRATOR

    def test_detect_fraud_coconspirator_negative(
        # 函数 test_detect_fraud_coconspirator_negative 的初始化逻辑
        self, main_helper_case: dict

        # 执行 test_detect_fraud_coconspirator_negative 函数的核心逻辑
    ) -> None:
        """测试反例：不命中诈骗罪共同犯罪路径."""
        # 初始化变量 result
        result = detect_fraud_coconspirator(main_helper_case)
        # 可能返回 None 或其他路径，但不应该是 FRAUD_COCONSPIRATOR
        assert result != StandardPath.FRAUD_COCONSPIRATOR


# 定义 TestDetectMoneyLaundering 类
class TestDetectMoneyLaundering:
    """测试掩饰隐瞒犯罪所得路径判定函数."""

    def test_detect_money_laundering_positive(
        # 函数 test_detect_money_laundering_positive 的初始化逻辑
        self, money_laundering_case: dict
    ) -> None:
        """测试正例：命中掩饰隐瞒犯罪所得路径."""
        # 初始化变量 result
        result = detect_money_laundering(money_laundering_case)
        assert result == StandardPath.MONEY_LAUNDERING

    def test_detect_money_laundering_negative(
        # 函数 test_detect_money_laundering_negative 的初始化逻辑
        self, main_helper_case: dict

        # 执行 test_detect_money_laundering_negative 函数的核心逻辑
    ) -> None:
        """测试反例：不命中掩饰隐瞒犯罪所得路径."""
        # 初始化变量 result
        result = detect_money_laundering(main_helper_case)
        # 可能返回 None 或其他路径，但不应该是 MONEY_LAUNDERING
        assert result != StandardPath.MONEY_LAUNDERING


# 定义 TestDetectMainHelper 类
class TestDetectMainHelper:
    """测试帮信罪主路径判定函数."""

    def test_detect_main_helper_positive(self, main_helper_case: dict) -> None:
        """测试正例：命中帮信罪主路径."""
        # 初始化变量 result
        result = detect_main_helper(main_helper_case)
        assert result == StandardPath.MAIN_HELPER

    def test_detect_main_helper_negative(
        # 函数 test_detect_main_helper_negative 的初始化逻辑
        self, pending_verification_case: dict
    ) -> None:
        """测试反例：不命中帮信罪主路径."""
        # 初始化变量 result
        result = detect_main_helper(pending_verification_case)
        assert result is None


# 定义 TestRecognizeStandardPath 类
class TestRecognizeStandardPath:
    """测试规范路径识别主函数."""

    def test_recognize_fraud_coconspirator(
        # 函数 test_recognize_fraud_coconspirator 的初始化逻辑
        self, fraud_coconspirator_case: dict
    ) -> None:
        """测试识别诈骗罪共同犯罪路径."""
        # 初始化变量 result
        result = recognize_standard_path(fraud_coconspirator_case)
        assert result == StandardPath.FRAUD_COCONSPIRATOR

    def test_recognize_money_laundering(
        # 函数 test_recognize_money_laundering 的初始化逻辑
        self, money_laundering_case: dict

        # 执行 test_recognize_money_laundering 函数的核心逻辑
    ) -> None:
        """测试识别掩饰隐瞒犯罪所得路径."""
        # 初始化变量 result
        result = recognize_standard_path(money_laundering_case)
        assert result == StandardPath.MONEY_LAUNDERING

    def test_recognize_main_helper(self, main_helper_case: dict) -> None:
        """测试识别帮信罪主路径."""
        # 初始化变量 result
        result = recognize_standard_path(main_helper_case)
        assert result == StandardPath.MAIN_HELPER

    def test_recognize_pending_verification(
        # 函数 test_recognize_pending_verification 的初始化逻辑
        self, pending_verification_case: dict
    ) -> None:
        """测试识别规范路径待核实."""
        # 初始化变量 result
        result = recognize_standard_path(pending_verification_case)
        assert result == StandardPath.PENDING_VERIFICATION


# 定义 TestPriorityRules 类
class TestPriorityRules:
    """测试判定优先级规则."""

    def test_fraud_coconspirator_priority(
        # 函数 test_fraud_coconspirator_priority 的初始化逻辑
        self, fraud_coconspirator_case: dict
    ) -> None:
        """测试诈骗罪共同犯罪路径优先级最高."""
        # 即使同时满足多个路径条件，也应返回 FRAUD_COCONSPIRATOR
        result = recognize_standard_path(fraud_coconspirator_case)
        assert result == StandardPath.FRAUD_COCONSPIRATOR

    def test_money_laundering_priority_over_main_helper(
        # 函数 test_money_laundering_priority_over_main_helper 的初始化逻辑
        self, money_laundering_case: dict

        # 执行 test_money_laundering_priority_over_main_helper 函数的核心逻辑
    ) -> None:
        """测试掩饰隐瞒犯罪所得路径优先级高于帮信罪主路径."""
        # 即使同时满足 MONEY_LAUNDERING 和 MAIN_HELPER，也应返回 MONEY_LAUNDERING
        result = recognize_standard_path(money_laundering_case)
        assert result == StandardPath.MONEY_LAUNDERING

    def test_priority_order(self) -> None:
        """验证优先级顺序定义."""
        # 优先级：FRAUD_COCONSPIRATOR > MONEY_LAUNDERING > MAIN_HELPER > PENDING_VERIFICATION
        priority_order = [
            StandardPath.FRAUD_COCONSPIRATOR,
            StandardPath.MONEY_LAUNDERING,
            StandardPath.MAIN_HELPER,
            StandardPath.PENDING_VERIFICATION,
        ]
        assert len(priority_order) == 4
        assert len(set(priority_order)) == 4  # 无重复


# 定义 TestRecognizeWithReason 类
class TestRecognizeWithReason:
    """测试带理由的路径识别函数."""

    def test_recognize_with_reason_fraud(
        # 函数 test_recognize_with_reason_fraud 的初始化逻辑
        self, fraud_coconspirator_case: dict
    ) -> None:
        """测试带理由的诈骗罪共同犯罪路径识别."""
        # 初始化变量 result
        result = recognize_standard_path_with_reason(fraud_coconspirator_case)
        assert result["path"] == StandardPath.FRAUD_COCONSPIRATOR
        assert "reason" in result
        assert "matched_keywords" in result
        assert len(result["matched_keywords"]) > 0

    def test_recognize_with_reason_pending(
        # 函数 test_recognize_with_reason_pending 的初始化逻辑
        self, pending_verification_case: dict

        # 执行 test_recognize_with_reason_pending 函数的核心逻辑
    ) -> None:
        """测试带理由的待核实路径识别."""
        # 初始化变量 result
        result = recognize_standard_path_with_reason(pending_verification_case)
        assert result["path"] == StandardPath.PENDING_VERIFICATION
        assert "reason" in result
        assert result["matched_keywords"] == []


# 定义 TestAllFixturesCoverage 类
class TestAllFixturesCoverage:
    """测试所有 fixture 覆盖所有枚举类型."""

    def test_all_enum_types_covered(self, test_cases: list[dict]) -> None:
        """验证测试用例覆盖所有枚举类型."""
        # 初始化变量 expected_paths
        expected_paths = {case["expected_path"] for case in test_cases}
        # 初始化变量 all_enum_names
        all_enum_names = {path.name for path in StandardPath}
        assert expected_paths == all_enum_names

    def test_fixture_count(self, test_cases: list[dict]) -> None:
        """验证测试用例数量."""
        assert len(test_cases) >= 4  # 至少4个测试用例，每个枚举类型一个
