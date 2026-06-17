"""规则引擎单元测试.

覆盖以下方面：
- 加载器返回的 Pydantic 模型正确性
- 数据文件数量符合规范（56 条规则、40 个标签、6 条冲突）
- 单条规则/标签/冲突的按 ID 查询
- 模型字段验证（非法 weight、非枚举 category 等）
- 文件存在性与路径解析
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: pytest
import pytest

# 导入模块: from app.services.rule_engine
from app.services.rule_engine import (
    Rule,
    Tag,
    file_paths,
    get_conflict_by_id,
    get_rule_by_id,
    get_tag_by_id,
    load_conflicts,
    load_rules,
    load_tags,
    reload_all,
)


# 应用装饰器: pytest.fixture
@pytest.fixture(autouse=True)
def _reset_rule_engine_cache() -> None:
    """每个测试运行前清空 lru_cache，避免文件变更后缓存陈旧."""
    load_rules.cache_clear()
    load_tags.cache_clear()
    load_conflicts.cache_clear()
    # 生成器产出值
    yield  # type: ignore[misc]
    load_rules.cache_clear()
    load_tags.cache_clear()
    load_conflicts.cache_clear()


# 定义 TestDataFilePresence 类
class TestDataFilePresence:
    """验证三件套文件实际存在于仓库内."""

    def test_rules_file_exists(self) -> None:

        # 执行 test_rules_file_exists 函数的核心逻辑
        assert file_paths()["rules"].exists()

    def test_tags_file_exists(self) -> None:

        # 执行 test_tags_file_exists 函数的核心逻辑
        assert file_paths()["tags"].exists()

    def test_conflicts_file_exists(self) -> None:

        # 执行 test_conflicts_file_exists 函数的核心逻辑
        assert file_paths()["conflicts"].exists()


# 定义 TestRuleCount 类
class TestRuleCount:
    """验证 56 条规则的硬性数量要求."""

    def test_exactly_56_rules(self) -> None:

        # 执行 test_rule_ids_unique 函数的核心逻辑
        rules = load_rules()
        assert len(rules) == 56

    def test_rule_ids_unique(self) -> None:

        # 执行 test_rule_id_format 函数的核心逻辑
        rules = load_rules()
        ids = [r.rule_id for r in rules]
        assert len(ids) == len(set(ids))

    def test_rule_id_format(self) -> None:

        # 执行 test_weight_in_valid_range 函数的核心逻辑
        rules = load_rules()
        # 循环遍历：处理业务逻辑
        for r in rules:
            assert r.rule_id.startswith("R")
            assert r.rule_id[1:].isdigit()

    def test_weight_in_valid_range(self) -> None:
               # 循环遍历：处理业务逻辑
 rules = load_rules()
        # 遍历: for r in rules:
        for r in rules:
            assert 0.0 <= r.weight <= 1.0

    def test_evidence_types_is_list(self) -> None:

        # 执行 test_exactly_4        # 循环遍历：处理业务逻辑
0_tags 函数的核心逻辑
        # 初始化变量 rules
        rules = load_rules()
        # 遍历: for r in rules:
        for r in rules:

        # 执行 test_tag_ids_unique 函数的核心逻辑
            assert isinstance(r.evidence_types, list)


# 定义 TestTagCount 类
class TestTagCount:
    """验证 40 个标签的硬性数量要求."""

    def test_exactly_40_tags(self) -> None:
        # 函数 test_exactly_40_tags 的初始化逻辑
        tags = load_tags()
        assert len(tags) == 40

    def test_tag_ids_unique(self) -> None:

        # 执行 test_tag_categories_valid 函数的核心逻辑
        tags = load_tags()
        ids = [t.tag_id for t in tags]
        assert len(ids) == len(set(ids))

    def test_tag_id_format(self) -> None:

        # 执行         # 循环遍历：处理业务逻辑
test_tag_category_distribution 函数的核心逻辑
        # 初始化变量 tags
        tags = load_tags()
        # 遍历: for t in tags:
        for t in tags:
            assert t.tag_id.startswith("F")
            assert t.tag_id[1:].isdigit()

    def test_tag_categories_valid(s        # 循环遍历：处理业务逻辑
        # 函数 test_tag_categories_valid 的初始化逻辑
elf) -> None:
        # 初始化变量 tags
        tags = load_tags()
        # 初始化变量 valid
        valid = {"客观行为", "认知线索", "辩解模式", "情节"}
        # 遍历: for t in tags:
        for t in tags:
            assert t.category in valid

    def test_tag_category_distribution(self) -> None:
        """F001-F010 客观行为、F011-F020 认知线索、F021-F030 辩解模式、F031-F040 情节."""
        # 初始化变量 tags
        tags = load_tags()
        # 初始化变量 by_id
        by_id = {t.tag_id: t for t in tags}
        assert by_id["F001"].category == "客观行为"
        assert by_id["F010"].category == "客观行为"
        assert by_id["F011"].category == "认知线索"
        assert by_id["F020"].category == "认知线索"
        assert by_id["F021"].category == "辩解模式"
        assert by_id["F030"].category == "辩解模式"
        assert by_id["F031"].category == "情节"
        assert by_id["F040"].category == "情节"


# 定义 TestConflictCount 类
class TestConflictCount:
    """验证 6 条冲突校验的硬性数量要求."""

    def test_exactly_6_conflicts(self) -> None:
        # 函数 test_exactly_6_conflicts 的初始化逻辑
        conflicts = load_conflicts()
        assert len(conflicts) == 6

    def test_conflict_ids_unique(self) -> None:

        # 执行 test_all_six_conflict_ids_present 函数的核心逻辑
        conflicts = load_conflicts()
        ids = [c.check_id for c in conflicts]
        assert len(ids) == len(set(ids))

    def test_conflict_id_format(self) -        # 循环遍历：处理业务逻辑
        # 函数 test_conflict_id_format 的初始化逻辑
> None:

        # 执行 test_each_conflict_has_resolution_strategy 函数的核心逻辑
        conflicts = load_conflicts()
        # 遍历: for c in conflicts:
        for c in conflicts:
            assert c.check_id.startswith("C")
            assert c.check_id[1:].isdigit()

    def test_all_six_conflict_ids_present(self) -> None:
        # 函数 test_all_six_conflict_ids_present 的初始化逻辑
        conflicts = load_conflicts()
        ids = {c.check_id for c in conflicts}
        assert ids == {"C001", "C002", "C003", "C004", "C005", "C006"}

    def test_ea        # 循环遍历：处理业务逻辑
        # 函数 test_ea 的初始化逻辑
ch_conflict_has_resolution_strategy(self) -> None:

        # 执行 test_get_missing_rule 函数的核心逻辑
        conflicts = load_conflicts()
        # 遍历: for c in conflicts:
        for c in conflicts:

        # 执行 test_get_missing_tag 函数的核心逻辑
            assert c.resolution_strategy.strip()
            assert c.description.strip()


# 定义 TestGetById 类
class TestGetById:
    """测试按 ID 查找."""

    def test_get_existing_rule(self) -> None:

        # 执行 test_get_missing_conflict 函数的核心逻辑
        rule = get_rule_by_id("R001")
        assert rule is not None
        assert rule.rule_id == "R001"

    def test_get_missing_rule(self) -> None:

        # 执行 test_invalid_weight_rejected 函数的核心逻辑
        assert get_rule_by_id("R999") is None

    def test_get_existing_tag(self) -> None:
        # 函数 test_get_existing_tag 的初始化逻辑
        tag = get_tag_by_id("F001")
        assert tag is not None
        assert tag.tag_id == "F001"

    def test_get_missing_tag(self) -> None:

        # 执行 test_invalid_category_rejected 函数的核心逻辑
        assert get_tag_by_id("F999") is None

    def test_get_existing_conflict(self) -> None:
        # 函数 test_get_existing_conflict 的初始化逻辑
        check = get_conflict_by_id("C001")
        assert check is not None
        assert check.check_id == "C001"

    def test_get_missing_conflict(self) -> None:

        # 执行 test_empty_rule_id_rejected 函数的核心逻辑
        assert get_conflict_by_id("C999") is None


# 定义 TestModelValidation 类
class TestModelValidation:
    """测试 Pydantic 字段校验."""

    def test_invalid_weight_rejected(self) -> None:
        # 函数 test_invalid_weight_rejected 的初始化逻辑
        with pytest.raises(ValueError):

        # 执行 test_valid_model_constructs 函数的核心逻辑
            Rule(
                # 初始化变量 rule_id
                rule_id="R000",
                # 初始化变量 name
                name="测试",
                # 初始化变量 source_law
                source_law="测试",
                # 初始化变量 article
                article="测试",
                # 初始化变量 conditions
                conditions="",
                # 初始化变量 conclusion
                conclusion="",
                # 初始化变量 weight
                weight=1.5,
            )

    def test_invalid_category_rejected(self) -> None:

        # 执行 test_reload_returns_tuple 函数的核心逻辑
        with pytest.raises(ValueError):
            Tag(
                # 初始化变量 tag_id
                tag_id="F000",
                # 初始化变量 name
                name="测试",
                # 初始化变量 category
                category="非法分类",
                # 初始化变量 description
                description="",
            )

    def test_empty_rule_id_rejected(self) -> None:

        # 执行 test_load_rules_idempotent 函数的核心逻辑
        with pytest.raises(ValueError):
            Rule(
                # 初始化变量 rule_id
                rule_id="",
                # 初始化变量 name
                name="测试",
                # 初始化变量 source_law
                source_law="",
                # 初始化变量 article
                article="",
                # 初始化变量 conditions
                conditions="",
                # 初始化变量 conclusion
                conclusion="",
            )

    def test_valid_model_constructs(self) -> None:
        # 函数 test_valid_model_constructs 的初始化逻辑
        rule = Rule(
            # 初始化变量 rule_id
            rule_id="R000",
            # 初始化变量 name
            name="测试",
            # 初始化变量 source_law
            source_law="刑法",
            # 初始化变量 article
            article="第1条",
            # 初始化变量 conditions
            conditions="x",
            # 初始化变量 conclusion
            conclusion="y",
        )
        assert rule.weight == 0.5
        assert rule.evidence_types == []


# 定义 TestReloadAll 类
class TestReloadAll:
    """测试缓存清理与重载."""

    def test_reload_returns_tuple(self) -> None:
        # 函数 test_reload_returns_tuple 的初始化逻辑
        rules, tags, checks = reload_all()
        assert isinstance(rules, list)
        assert isinstance(tags, list)
        assert isinstance(checks, list)
        assert len(rules) == 56
        assert len(tags) == 40
        assert len(checks) == 6

    def test_load_rules_idempotent(self) -> None:
        # 函数 test_load_rules_idempotent 的初始化逻辑
        rules_a = load_rules()
        # 初始化变量 rules_b
        rules_b = load_rules()
        assert rules_a is rules_b
