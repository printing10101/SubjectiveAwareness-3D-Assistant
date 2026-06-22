"""规则引擎单元测试.

覆盖以下方面：
- 加载器返回的 Pydantic 模型正确性
- 数据文件数量符合规范（56 条规则、40 个标签、6 条冲突）
- 单条规则/标签/冲突的按 ID 查询
- 模型字段验证（非法 weight、非枚举 category 等）
- 文件存在性与路径解析
"""

from __future__ import annotations

import pytest

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


@pytest.fixture(autouse=True)
def _reset_rule_engine_cache() -> None:
    """每个测试运行前清空 lru_cache，避免文件变更后缓存陈旧."""
    load_rules.cache_clear()
    load_tags.cache_clear()
    load_conflicts.cache_clear()
    yield  # type: ignore[misc]
    load_rules.cache_clear()
    load_tags.cache_clear()
    load_conflicts.cache_clear()


class TestDataFilePresence:
    """验证三件套文件实际存在于仓库内."""

    def test_rules_file_exists(self) -> None:
        assert file_paths()["rules"].exists()

    def test_tags_file_exists(self) -> None:
        assert file_paths()["tags"].exists()

    def test_conflicts_file_exists(self) -> None:
        assert file_paths()["conflicts"].exists()


class TestRuleCount:
    """验证 56 条规则的硬性数量要求."""

    def test_exactly_56_rules(self) -> None:
        rules = load_rules()
        assert len(rules) == 56

    def test_rule_ids_unique(self) -> None:
        rules = load_rules()
        ids = [r.rule_id for r in rules]
        assert len(ids) == len(set(ids))

    def test_rule_id_format(self) -> None:
        rules = load_rules()
        for r in rules:
            assert r.rule_id.startswith("R")
            assert r.rule_id[1:].isdigit()

    def test_weight_in_valid_range(self) -> None:
        rules = load_rules()
        for r in rules:
            assert 0.0 <= r.weight <= 1.0

    def test_evidence_types_is_list(self) -> None:
        rules = load_rules()
        for r in rules:
            assert isinstance(r.evidence_types, list)


class TestTagCount:
    """验证 40 个标签的硬性数量要求."""

    def test_exactly_40_tags(self) -> None:
        tags = load_tags()
        assert len(tags) == 40

    def test_tag_ids_unique(self) -> None:
        tags = load_tags()
        ids = [t.tag_id for t in tags]
        assert len(ids) == len(set(ids))

    def test_tag_id_format(self) -> None:
        tags = load_tags()
        for t in tags:
            assert t.tag_id.startswith("F")
            assert t.tag_id[1:].isdigit()

    def test_tag_categories_valid(self) -> None:
        tags = load_tags()
        valid = {"客观行为", "认知线索", "辩解模式", "情节"}
        for t in tags:
            assert t.category in valid

    def test_tag_category_distribution(self) -> None:
        """F001-F010 客观行为、F011-F020 认知线索、F021-F030 辩解模式、F031-F040 情节."""
        tags = load_tags()
        by_id = {t.tag_id: t for t in tags}
        assert by_id["F001"].category == "客观行为"
        assert by_id["F010"].category == "客观行为"
        assert by_id["F011"].category == "认知线索"
        assert by_id["F020"].category == "认知线索"
        assert by_id["F021"].category == "辩解模式"
        assert by_id["F030"].category == "辩解模式"
        assert by_id["F031"].category == "情节"
        assert by_id["F040"].category == "情节"


class TestConflictCount:
    """验证 6 条冲突校验的硬性数量要求."""

    def test_exactly_6_conflicts(self) -> None:
        conflicts = load_conflicts()
        assert len(conflicts) == 6

    def test_conflict_ids_unique(self) -> None:
        conflicts = load_conflicts()
        ids = [c.check_id for c in conflicts]
        assert len(ids) == len(set(ids))

    def test_conflict_id_format(self) -> None:
        conflicts = load_conflicts()
        for c in conflicts:
            assert c.check_id.startswith("C")
            assert c.check_id[1:].isdigit()

    def test_all_six_conflict_ids_present(self) -> None:
        conflicts = load_conflicts()
        ids = {c.check_id for c in conflicts}
        assert ids == {"C001", "C002", "C003", "C004", "C005", "C006"}

    def test_each_conflict_has_resolution_strategy(self) -> None:
        conflicts = load_conflicts()
        for c in conflicts:
            assert c.resolution_strategy.strip()
            assert c.description.strip()


class TestGetById:
    """测试按 ID 查找."""

    def test_get_existing_rule(self) -> None:
        rule = get_rule_by_id("R001")
        assert rule is not None
        assert rule.rule_id == "R001"

    def test_get_missing_rule(self) -> None:
        assert get_rule_by_id("R999") is None

    def test_get_existing_tag(self) -> None:
        tag = get_tag_by_id("F001")
        assert tag is not None
        assert tag.tag_id == "F001"

    def test_get_missing_tag(self) -> None:
        assert get_tag_by_id("F999") is None

    def test_get_existing_conflict(self) -> None:
        check = get_conflict_by_id("C001")
        assert check is not None
        assert check.check_id == "C001"

    def test_get_missing_conflict(self) -> None:
        assert get_conflict_by_id("C999") is None


class TestModelValidation:
    """测试 Pydantic 字段校验."""

    def test_invalid_weight_rejected(self) -> None:
        with pytest.raises(ValueError):
            Rule(
                rule_id="R000",
                name="测试",
                source_law="测试",
                article="测试",
                conditions="",
                conclusion="",
                weight=1.5,
            )

    def test_invalid_category_rejected(self) -> None:
        with pytest.raises(ValueError):
            Tag(
                tag_id="F000",
                name="测试",
                category="非法分类",
                description="",
            )

    def test_empty_rule_id_rejected(self) -> None:
        with pytest.raises(ValueError):
            Rule(
                rule_id="",
                name="测试",
                source_law="",
                article="",
                conditions="",
                conclusion="",
            )

    def test_valid_model_constructs(self) -> None:
        rule = Rule(
            rule_id="R000",
            name="测试",
            source_law="刑法",
            article="第1条",
            conditions="x",
            conclusion="y",
        )
        assert rule.weight == 0.5
        assert rule.evidence_types == []


class TestReloadAll:
    """测试缓存清理与重载."""

    def test_reload_returns_tuple(self) -> None:
        rules, tags, checks = reload_all()
        assert isinstance(rules, list)
        assert isinstance(tags, list)
        assert isinstance(checks, list)
        assert len(rules) == 56
        assert len(tags) == 40
        assert len(checks) == 6

    def test_load_rules_idempotent(self) -> None:
        rules_a = load_rules()
        rules_b = load_rules()
        assert rules_a is rules_b
