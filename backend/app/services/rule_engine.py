"""规则引擎模块.

负责加载并管理法律规则、事实标签、冲突校验规则的三件套数据。
数据来源固定为 data/rules/v1.0.json、data/tags/v1.0.json、data/conflicts/v1.0.json。
使用 Pydantic 模型进行强类型校验，模块级缓存避免重复 IO。

典型用法：

    from app.services.rule_engine import load_rules, load_tags, load_conflicts

    rules = load_rules()
    tags = load_tags()
    checks = load_conflicts()
"""

from __future__ import annotations

import json
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------

_PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]
_DATA_DIR: Path = _PROJECT_ROOT / "data"

_RULES_FILE: Path = _DATA_DIR / "rules" / "v1.0.json"
_TAGS_FILE: Path = _DATA_DIR / "tags" / "v1.0.json"
_CONFLICTS_FILE: Path = _DATA_DIR / "conflicts" / "v1.0.json"

# 标签分类
_TAG_CATEGORY_OBJECTIVE: str = "客观行为"
_TAG_CATEGORY_COGNITION: str = "认知线索"
_TAG_CATEGORY_DEFENSE: str = "辩解模式"
_TAG_CATEGORY_CIRCUMSTANCE: str = "情节"

_VALID_TAG_CATEGORIES: frozenset[str] = frozenset(
    {
        _TAG_CATEGORY_OBJECTIVE,
        _TAG_CATEGORY_COGNITION,
        _TAG_CATEGORY_DEFENSE,
        _TAG_CATEGORY_CIRCUMSTANCE,
    }
)

# 规则权重上下限
_MIN_WEIGHT: float = 0.0
_MAX_WEIGHT: float = 1.0


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------


class Rule(BaseModel):
    """单条法律规则.

    Attributes:
        rule_id: 规则编号（如 R001）。
        name: 规则名称。
        source_law: 法源（司法解释/意见/法律/会议纪要等）。
        article: 具体条款。
        conditions: 触发条件（自然语言描述）。
        conclusion: 触发后的结论。
        evidence_types: 支持本规则所需的证据类型。
        weight: 规则权重（0~1）。
        applicable_scenarios: 适用场景标签。
        conflicting_rules: 与本规则冲突的规则 ID 列表。
    """

    rule_id: str
    name: str
    source_law: str
    article: str
    conditions: str
    conclusion: str
    evidence_types: list[str] = Field(default_factory=list)
    weight: float = 0.5
    applicable_scenarios: list[str] = Field(default_factory=list)
    conflicting_rules: list[str] = Field(default_factory=list)

    @field_validator("rule_id")
    @classmethod
    def _validate_rule_id(cls, value: str) -> str:
        if not value or not value.strip():
            msg = "rule_id 不能为空"
            raise ValueError(msg)
        return value

    @field_validator("weight")
    @classmethod
    def _validate_weight(cls, value: float) -> float:
        if value < _MIN_WEIGHT or value > _MAX_WEIGHT:
            msg = f"weight 必须在 [{_MIN_WEIGHT}, {_MAX_WEIGHT}] 区间"
            raise ValueError(msg)
        return value


class Tag(BaseModel):
    """事实标签.

    Attributes:
        tag_id: 标签编号（F001~F040）。
        name: 标签名称。
        category: 标签分类（客观行为/认知线索/辩解模式/情节）。
        description: 标签含义描述。
        extraction_hints: 抽取提示词（关键词/短语）。
        mutually_exclusive_with: 与本标签互斥的其他标签 ID。
    """

    tag_id: str
    name: str
    category: str
    description: str
    extraction_hints: list[str] = Field(default_factory=list)
    mutually_exclusive_with: list[str] = Field(default_factory=list)

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        if value not in _VALID_TAG_CATEGORIES:
            msg = (
                f"category 必须是 {_VALID_TAG_CATEGORIES} 之一，"
                f"实际传入 {value!r}"
            )
            raise ValueError(msg)
        return value

    @field_validator("tag_id")
    @classmethod
    def _validate_tag_id(cls, value: str) -> str:
        if not value or not value.strip():
            msg = "tag_id 不能为空"
            raise ValueError(msg)
        return value


class ConflictCheck(BaseModel):
    """冲突校验规则.

    Attributes:
        check_id: 冲突 ID（C001~C006）。
        name: 冲突名称。
        rule_a: 冲突一方（规则 ID 或标签 ID）。
        rule_b: 冲突另一方。
        description: 冲突描述。
        resolution_strategy: 解决策略。
    """

    check_id: str
    name: str
    rule_a: str
    rule_b: str
    description: str
    resolution_strategy: str

    @field_validator("check_id")
    @classmethod
    def _validate_check_id(cls, value: str) -> str:
        if not value or not value.strip():
            msg = "check_id 不能为空"
            raise ValueError(msg)
        return value


# ---------------------------------------------------------------------------
# 加载器
# ---------------------------------------------------------------------------


_load_lock = threading.Lock()


def _read_json(path: Path) -> list[dict[str, Any]]:
    """从指定路径读取 JSON 数组.

    Args:
        path: JSON 文件绝对路径.

    Returns:
        解析后的 Python 对象数组.

    Raises:
        FileNotFoundError: 文件不存在.
        ValueError: JSON 解析失败或根节点不是数组.
    """
    if not path.exists():
        msg = f"规则数据文件不存在: {path}"
        raise FileNotFoundError(msg)

    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)

    if not isinstance(payload, list):
        msg = f"规则文件根节点必须是数组，实际是 {type(payload).__name__}"
        raise ValueError(msg)
    return payload


@lru_cache(maxsize=1)
def load_rules() -> list[Rule]:
    """加载法律规则列表.

    使用 lru_cache 缓存，加载后多次调用不会重复读取磁盘。
    若需要强制重新加载，请调用 :func:`reload_all`.

    Returns:
        校验后的 :class:`Rule` 列表.
    """
    with _load_lock:
        data = _read_json(_RULES_FILE)
        return [Rule.model_validate(item) for item in data]


@lru_cache(maxsize=1)
def load_tags() -> list[Tag]:
    """加载事实标签列表.

    Returns:
        校验后的 :class:`Tag` 列表.
    """
    with _load_lock:
        data = _read_json(_TAGS_FILE)
        return [Tag.model_validate(item) for item in data]


@lru_cache(maxsize=1)
def load_conflicts() -> list[ConflictCheck]:
    """加载冲突校验规则列表.

    Returns:
        校验后的 :class:`ConflictCheck` 列表.
    """
    with _load_lock:
        data = _read_json(_CONFLICTS_FILE)
        return [ConflictCheck.model_validate(item) for item in data]


def reload_all() -> tuple[list[Rule], list[Tag], list[ConflictCheck]]:
    """强制清空缓存并重新加载三件套.

    主要用于测试或运维场景中热更新知识库。

    Returns:
        包含最新规则、标签、冲突的元组.
    """
    load_rules.cache_clear()
    load_tags.cache_clear()
    load_conflicts.cache_clear()
    return load_rules(), load_tags(), load_conflicts()


def get_rule_by_id(rule_id: str) -> Rule | None:
    """根据 ID 查找单条规则.

    Args:
        rule_id: 规则编号.

    Returns:
        命中的 :class:`Rule`，未命中返回 ``None``.
    """
    for r in load_rules():
        if r.rule_id == rule_id:
            return r
    return None


def get_tag_by_id(tag_id: str) -> Tag | None:
    """根据 ID 查找单条标签.

    Args:
        tag_id: 标签编号.

    Returns:
        命中的 :class:`Tag`，未命中返回 ``None``.
    """
    for t in load_tags():
        if t.tag_id == tag_id:
            return t
    return None


def get_conflict_by_id(check_id: str) -> ConflictCheck | None:
    """根据 ID 查找单条冲突规则.

    Args:
        check_id: 冲突 ID.

    Returns:
        命中的 :class:`ConflictCheck`，未命中返回 ``None``.
    """
    for c in load_conflicts():
        if c.check_id == check_id:
            return c
    return None


def file_paths() -> dict[str, Path]:
    """返回三件套数据文件的绝对路径，便于调试和测试断言."""
    return {
        "rules": _RULES_FILE,
        "tags": _TAGS_FILE,
        "conflicts": _CONFLICTS_FILE,
    }
