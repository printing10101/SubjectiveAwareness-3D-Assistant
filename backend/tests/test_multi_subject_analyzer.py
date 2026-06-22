"""多主体分层分析器单元测试.

覆盖以下方面：
- SubjectRole 枚举定义
- SubjectAnalysis 数据结构
- 角色识别逻辑（ORGANIZER/INTERMEDIARY/ACCOUNT_HOLDER/WITHDRAWER/PROVIDER/UNKNOWN）
- 主体名称提取
- 客观行为提取
- 认知证据提取
- 辩解理由推断
- analyze_subjects 核心函数
- get_multi_subject_ratio 统计函数
- 边界情况：空文本、无主体、单主体、多主体场景
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: json
import json
# 导入模块: from pathlib
from pathlib import Path

# 导入模块: pytest
import pytest

# 导入模块: from app.services.subject
from app.services.subject import (
    SubjectAnalysis,
    SubjectRole,
    analyze_subjects,
    get_multi_subject_ratio,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# 应用装饰器: pytest.fixture
@pytest.fixture
def test_data_path() -> Path:
    """返回测试数据目录路径."""
    # 返回处理结果
    return Path(__file__).parent / "data"


# 应用装饰器: pytest.fixture
@pytest.fixture
def multi_subject_cases(test_data_path: Path) -> list[dict]:
    """加载多主体测试用例."""
    # 初始化变量 data_file
    data_file = test_data_path / "multi_subject_cases.json"
    # 使用上下文管理器管理资源
    with open(data_file, encoding="utf-8") as f:
        # 返回处理结果
        return json.load(f)


# 应用装饰器: pytest.fixture
@pytest.fixture
def single_subject_case(multi_subject_cases: list[dict]) -> dict:
    """单人案件场景."""
    # 返回处理结果
    return multi_subject_cases[0]


# 应用装饰器: pytest.fixture
@pytest.fixture
def dual_subject_case(multi_subject_cases: list[dict]) -> dict:
    """双人案件场景."""
    # 返回处理结果
    return multi_subject_cases[1]


# 应用装饰器: pytest.fixture
@pytest.fixture
def triple_subject_case(multi_subject_cases: list[dict]) -> dict:
    """三人案件场景."""
    # 返回处理结果
    return multi_subject_cases[2]


# ---------------------------------------------------------------------------
# SubjectRole 枚举测试
# ---------------------------------------------------------------------------


# 定义 TestSubjectRole 类
class TestSubjectRole:
    """SubjectRole 枚举测试."""

    def test_enum_values(self) -> None:
        """测试枚举值定义."""
        assert SubjectRole.ORGANIZER.value == "organizer"
        assert SubjectRole.INTERMEDIARY.value == "intermediary"
        assert SubjectRole.PROVIDER.value == "provider"
        assert SubjectRole.ACCOUNT_HOLDER.value == "account_holder"
        assert SubjectRole.WITHDRAWER.value == "withdrawer"
        assert SubjectRole.UNKNOWN.value == "unknown"

    def test_enum_count(self) -> None:
        """测试枚举成员数量."""
        assert len(SubjectRole) == 6

    def test_enum_is_string(self) -> None:
        """测试枚举继承自 str."""
        assert isinstance(SubjectRole.ORGANIZER, str)
        assert SubjectRole.ORGANIZER == "organizer"


# ---------------------------------------------------------------------------
# SubjectAnalysis 数据结构测试
# ---------------------------------------------------------------------------


# 定义 TestSubjectAnalysis 类
class TestSubjectAnalysis:
    """SubjectAnalysis 数据结构测试."""

    def test_dataclass_creation(self) -> None:
        """测试数据类创建."""
        # 初始化变量 analysis
        analysis = SubjectAnalysis(
            # 初始化变量 name
            name="张某",
            # 初始化变量 role
            role=SubjectRole.ACCOUNT_HOLDER,
            # 初始化变量 objective_behavior
            objective_behavior="提供银行卡",
            # 初始化变量 cognitive_evidence
            cognitive_evidence=["明知故犯"],
            # 初始化变量 defense
            defense="可能辩称不知情",
            # 初始化变量 matched_tags
            matched_tags=["交卡"],
        )
        assert analysis.name == "张某"
        assert analysis.role == SubjectRole.ACCOUNT_HOLDER
        assert analysis.objective_behavior == "提供银行卡"
        assert len(analysis.cognitive_evidence) == 1
        assert analysis.defense == "可能辩称不知情"
        assert "交卡" in analysis.matched_tags

    def test_dataclass_defaults(self) -> None:
        """测试数据类默认值."""
        # 初始化变量 analysis
        analysis = SubjectAnalysis(name="李某", role=SubjectRole.UNKNOWN)
        assert analysis.objective_behavior == ""
        assert analysis.cognitive_evidence == []
        assert analysis.defense == ""
        assert analysis.matched_tags == []


# ---------------------------------------------------------------------------
# 角色识别逻辑测试
# ---------------------------------------------------------------------------


# 定义 TestRoleIdentification 类
class TestRoleIdentification:
    """角色识别逻辑测试."""

    def test_organizer_role(self, triple_subject_case: dict) -> None:
        """测试组织者角色识别."""
        # 初始化变量 results
        results = analyze_subjects(triple_subject_case)
        # 初始化变量 organizer
        organizer = next((r for r in results if r.name == "赵某"), None)
        assert organizer is not None
        assert organizer.role == SubjectRole.ORGANIZER
        assert "招募他人" in organizer.matched_tags or "分工" in organizer.matched_tags

    def test_intermediary_role(self, triple_subject_case: dict) -> None:
        """测试中间人角色识别."""
        # 初始化变量 results
        results = analyze_subjects(triple_subject_case)
        # 初始化变量 intermediary
        intermediary = next((r for r in results if r.name == "钱某"), None)
        assert intermediary is not None
        assert intermediary.role == SubjectRole.INTERMEDIARY
        assert any(
            tag in intermediary.matched_tags
            # 循环遍历：处理业务逻辑
            for tag in ["联系上下线", "居间", "牵线", "介绍"]
        )

    def test_account_holder_role(self, single_subject_case: dict) -> None:
        """测试持卡人角色识别."""
        # 初始化变量 results
        results = analyze_subjects(single_subject_case)
        # 初始化变量 holder
        holder = next((r for r in results if r.name == "张某"), None)
        assert holder is not None
        assert holder.role == SubjectRole.ACCOUNT_HOLDER
        assert any(
            tag in holder.matched_tags
            # 遍历: for tag in ["交卡", "提供银行卡", "出借银行卡", "出售银行卡"]
            for tag in ["交卡", "提供银行卡", "出借银行卡", "出售银行卡"]
        )

    def test_withdrawer_role(self, dual_subject_case: dict) -> None:
        """测试取款人角色识别."""
        # 初始化变量 results
        results = analyze_subjects(dual_subject_case)
        # 初始化变量 withdrawer
        withdrawer = next((r for r in results if r.name == "李某"), None)
        assert withdrawer is not None
        assert withdrawer.role == SubjectRole.WITHDRAWER
        assert any(
            tag in withdrawer.matched_tags
            # 遍历: for tag in ["ATM操作", "ATM取款", "取现", "取款"]
            for tag in ["ATM操作", "ATM取款", "取现", "取款"]
        )

    def test_unknown_role(self) -> None:
        """测试未知角色识别."""
        # 初始化变量 case
        case = {"case_text": "被告人陈某参与了犯罪活动，具体行为待查。"}
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) > 0
        # 陈某应该被识别为 UNKNOWN（无明确角色标签）
        chen = next((r for r in results if r.name == "陈某"), None)
        # 条件判断：处理业务逻辑
        if chen:
            assert chen.role == SubjectRole.UNKNOWN


# ---------------------------------------------------------------------------
# 主体名称提取测试
# ---------------------------------------------------------------------------


# 定义 TestSubjectExtraction 类
class TestSubjectExtraction:
    """主体名称提取测试."""

    def test_extract_single_subject(self, single_subject_case: dict) -> None:
        """测试单主体提取."""
        # 初始化变量 results
        results = analyze_subjects(single_subject_case)
        assert len(results) == 1
        assert results[0].name == "张某"

    def test_extract_dual_subjects(self, dual_subject_case: dict) -> None:
        """测试双主体提取."""
        # 初始化变量 results
        results = analyze_subjects(dual_subject_case)
        assert len(results) == 2
        # 初始化变量 names
        names = {r.name for r in results}
        assert "王某" in names
        assert "李某" in names

    def test_extract_triple_subjects(self, triple_subject_case: dict) -> None:
        """测试三主体提取."""
        # 初始化变量 results
        results = analyze_subjects(triple_subject_case)
        assert len(results) == 3
        # 初始化变量 names
        names = {r.name for r in results}
        assert "赵某" in names
        assert "钱某" in names
        assert "孙某" in names


# ---------------------------------------------------------------------------
# 客观行为提取测试
# ---------------------------------------------------------------------------


# 定义 TestObjectiveBehavior 类
class TestObjectiveBehavior:
    """客观行为提取测试."""

    def test_behavior_extraction(self, single_subject_case: dict) -> None:
        """测试行为描述提取."""
        # 初始化变量 results
        results = analyze_subjects(single_subject_case)
        assert len(results) > 0
        # 初始化变量 behavior
        behavior = results[0].objective_behavior
        assert behavior != ""
        # 行为描述应包含相关关键词
        assert any(
            keyword in behavior
            # 遍历: for keyword in ["银行卡", "交卡", "提供", "转账", "涉案资金"]
            for keyword in ["银行卡", "交卡", "提供", "转账", "涉案资金"]
        )

    def test_organizer_behavior(self, triple_subject_case: dict) -> None:
        """测试组织者行为提取."""
        # 初始化变量 results
        results = analyze_subjects(triple_subject_case)
        # 初始化变量 organizer
        organizer = next((r for r in results if r.name == "赵某"), None)
        assert organizer is not None
        # 初始化变量 behavior
        behavior = organizer.objective_behavior
        assert any(
            keyword in behavior for keyword in ["招募", "组织", "分工", "安排"]
        )


# ---------------------------------------------------------------------------
# 认知证据提取测试
# ---------------------------------------------------------------------------


# 定义 TestCognitiveEvidence 类
class TestCognitiveEvidence:
    """认知证据提取测试."""

    def test_evidence_extraction(self, single_subject_case: dict) -> None:
        """测试认知证据提取."""
        # 初始化变量 results
        results = analyze_subjects(single_subject_case)
        assert len(results) > 0
        # 初始化变量 evidence
        evidence = results[0].cognitive_evidence
        assert isinstance(evidence, list)
        assert len(evidence) > 0
        # 应包含"明知"相关证据
        assert any("明知" in e for e in evidence)

    def test_evidence_with_confession(self) -> None:
        """测试包含认罪情节的证据提取."""
        # 初始化变量 case
        case = {
            "case_text": "被告人周某明知他人实施犯罪，仍提供银行卡。周某到案后如实供述，认罪认罚。"
        }
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) > 0
        # 初始化变量 evidence
        evidence = results[0].cognitive_evidence
        # 应提取到供述相关证据
        assert any("供述" in e or "认罪" in e for e in evidence)


# ---------------------------------------------------------------------------
# 辩解理由推断测试
# ---------------------------------------------------------------------------


# 定义 TestDefenseInference 类
class TestDefenseInference:
    """辩解理由推断测试."""

    def test_defense_inference(self, single_subject_case: dict) -> None:
        """测试辩解理由推断."""
        # 初始化变量 results
        results = analyze_subjects(single_subject_case)
        assert len(results) > 0
        # 初始化变量 defense
        defense = results[0].defense
        assert defense != ""
        # 持卡人应包含相关辩解
        assert "银行卡" in defense or "不知情" in defense

    def test_defense_with_confession(self) -> None:
        """测试包含认罪情节的辩解推断."""
        # 初始化变量 case
        case = {
            "case_text": "被告人吴某明知是犯罪所得仍帮助取款，到案后认罪认罚。"
        }
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) > 0
        # 初始化变量 defense
        defense = results[0].defense
        # 应包含认罪/坦白情节说明
        assert "认罪" in defense or "坦白" in defense


# ---------------------------------------------------------------------------
# analyze_subjects 核心函数测试
# ---------------------------------------------------------------------------


# 定义 TestAnalyzeSubjects 类
class TestAnalyzeSubjects:
    """analyze_subjects 核心函数测试."""

    def test_empty_case_text(self) -> None:
        """测试空文本处理."""
        # 初始化变量 case
        case = {"case_text": ""}
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) == 1
        assert results[0].name == "未知主体"
        assert results[0].role == SubjectRole.UNKNOWN

    def test_no_subject_identified(self) -> None:
        """测试无法识别主体的情况."""
        # 初始化变量 case
        case = {"case_text": "案件事实描述中没有提到具体人名。"}
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) == 1
        assert results[0].name == "未知主体"
        assert results[0].role == SubjectRole.UNKNOWN

    def test_dict_input(self, single_subject_case: dict) -> None:
        """测试字典类型输入."""
        # 初始化变量 results
        results = analyze_subjects(single_subject_case)
        assert len(results) > 0
        assert all(isinstance(r, SubjectAnalysis) for r in results)

    def test_object_input(self) -> None:
        """测试对象类型输入."""

        # 定义 MockCase 类
        class MockCase:

            # MockCase 类定义，封装相关属性和方法
            def __init__(self, text: str):
                # 执行 __init__ 函数的核心逻辑
                self.case_text = text

        # 初始化变量 case
        case = MockCase("被告人郑某提供银行卡给他人使用。")
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) > 0

    def test_none_input(self) -> None:
        """测试 None 输入."""
        # 初始化变量 results
        results = analyze_subjects(None)
        assert len(results) == 1
        assert results[0].role == SubjectRole.UNKNOWN

    def test_complete_analysis(self, triple_subject_case: dict) -> None:
        """测试完整分析流程."""
        # 初始化变量 results
        results = analyze_subjects(triple_subject_case)
        assert len(results) == 3

        # 遍历: for result in results:
        for result in results:
            # 每个结果都应包含完整信息
            assert result.name != ""
            assert isinstance(result.role, SubjectRole)
            assert result.objective_behavior != ""
            assert isinstance(result.cognitive_evidence, list)
            assert len(result.cognitive_evidence) > 0
            assert result.defense != ""
            assert isinstance(result.matched_tags, list)


# ---------------------------------------------------------------------------
# get_multi_subject_ratio 统计函数测试
# ---------------------------------------------------------------------------


# 定义 TestGetMultiSubjectRatio 类
class TestGetMultiSubjectRatio:
    """get_multi_subject_ratio 统计函数测试."""

    def test_single_subject_cases(self) -> None:
        """测试全部单主体案件."""
        # 初始化变量 cases
        cases = [
            {"case_text": "被告人张某提供银行卡。"},
            {"case_text": "被告人李某交卡给上线。"},
        ]
        # 初始化变量 result
        result = get_multi_subject_ratio(cases)
        assert result["total_cases"] == 2
        assert result["multi_subject_cases"] == 0
        assert result["single_subject_cases"] == 2
        assert result["ratio"] == 0.0

    def test_multi_subject_cases(self) -> None:
        """测试包含多主体案件."""
        # 初始化变量 cases
        cases = [
            {"case_text": "被告人张某提供银行卡。"},
            {
                "case_text": "被告人王某招募他人并安排分工，被告人李某负责ATM取款。"
            },
        ]
        # 初始化变量 result
        result = get_multi_subject_ratio(cases)
        assert result["total_cases"] == 2
        assert result["multi_subject_cases"] == 1
        assert result["single_subject_cases"] == 1
        assert result["ratio"] == 0.5
        assert result["ratio_percent"] == "50.00%"

    def test_empty_cases_list(self) -> None:
        """测试空案件列表."""
        # 初始化变量 result
        result = get_multi_subject_ratio([])
        assert result["total_cases"] == 0
        assert result["multi_subject_cases"] == 0
        assert result["ratio"] == 0.0

    def test_details_structure(self, multi_subject_cases: list[dict]) -> None:
        """测试详情结构."""
        # 初始化变量 result
        result = get_multi_subject_ratio(multi_subject_cases)
        assert "details" in result
        assert isinstance(result["details"], list)
        # 应包含双人和三人案件的详情
        assert len(result["details"]) >= 2
        # 遍历: for detail in result["details"]:
        for detail in result["details"]:
            assert "index" in detail
            assert "subject_count" in detail
            assert "roles" in detail
            assert detail["subject_count"] > 1


# ---------------------------------------------------------------------------
# 边界情况和异常处理测试
# ---------------------------------------------------------------------------


# 定义 TestEdgeCases 类
class TestEdgeCases:
    """边界情况和异常处理测试."""

    def test_whitespace_only_text(self) -> None:
        """测试仅包含空白字符的文本."""
        # 初始化变量 case
        case = {"case_text": "   \n\t  "}
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) == 1
        assert results[0].role == SubjectRole.UNKNOWN

    def test_case_without_case_text_key(self) -> None:
        """测试字典中无 case_text 键."""
        # 初始化变量 case
        case = {"other_field": "some value"}
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) == 1
        assert results[0].role == SubjectRole.UNKNOWN

    def test_multiple_roles_in_text(self) -> None:
        """测试文本中包含多个角色标签."""
        # 初始化变量 case
        case = {
            "case_text": "被告人冯某既招募他人又联系上下线，还亲自交卡给上线使用。"
        }
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) > 0
        # 应识别为优先级最高的角色（组织者）
        assert results[0].role == SubjectRole.ORGANIZER

    def test_role_priority_organizer_over_provider(self) -> None:
        """测试组织者优先级高于提供者."""
        # 初始化变量 case
        case = {
            "case_text": "被告人韩某招募他人并提供银行卡，安排分工明确各人职责。"
        }
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) > 0
        # 应识别为组织者而非提供者
        assert results[0].role == SubjectRole.ORGANIZER

    def test_role_priority_withdrawer_over_provider(self) -> None:
        """测试取款人优先级高于提供者."""
        # 初始化变量 case
        case = {
            "case_text": "被告人杨某提供银行卡并负责ATM取款操作。"
        }
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) > 0
        # 应识别为取款人而非提供者
        assert results[0].role == SubjectRole.WITHDRAWER


# ---------------------------------------------------------------------------
# 性能测试
# ---------------------------------------------------------------------------


# 定义 TestPerformance 类
class TestPerformance:
    """性能测试."""

    def test_large_text_processing(self) -> None:
        """测试大文本处理性能."""
        # 构造一个包含大量文本的案件
        large_text = "被告人朱某提供银行卡。" * 1000
        # 初始化变量 case
        case = {"case_text": large_text}
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) > 0

    def test_many_subjects(self) -> None:
        """测试多主体处理."""
        # 构造包含多个主体的案件
        text_parts = []
        # 遍历: for surname in "赵钱孙李周吴郑王":
        for surname in "赵钱孙李周吴郑王":
            text_parts.append(f"被告人{surname}某提供银行卡给上线使用。")
        # 初始化变量 case
        case = {"case_text": "".join(text_parts)}
        # 初始化变量 results
        results = analyze_subjects(case)
        assert len(results) >= 8  # 至少识别出8个主体
