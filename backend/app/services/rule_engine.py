"""规则引擎模块.

负责加载并管理法律规则、事实标签、冲突校验规则的三件套数据。
数据来源固定为 data/rules/v1.0.json、data/tags/v1.0.json、data/conflicts/v1.0.json。
使用 Pydantic 模型进行强类型校验，模块级缓存避免重复 IO。

典型用法：

    # 导入模块: from app.services.rule_engine
    from app.services.rule_engine import load_rules, load_tags, load_conflicts

    # 初始化变量 rules
    rules = load_rules()
    # 初始化变量 tags
    tags = load_tags()
    # 初始化变量 checks
    checks = load_conflicts()
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: json
import json
# 导入模块: threading
import threading
# 导入模块: from functools
from functools import lru_cache
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from typing
from typing import Any

# 导入模块: from pydantic
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


# 定义 Rule 类
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

    # 应用装饰器: field_validator
    @field_validator("rule_id")
    # 应用装饰器: classmethod
    @classmethod
    def _validate_rule_id(cls, value: str) -> str:
        # 执行 _validate_rule_id 函数的核心逻辑
        # 条件判断：处理业务逻辑
        if not value or not value.strip():
            msg = "rule_id 不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return value

    # 应用装饰器: field_validator
    @field_validator("weight")
    # 应用装饰器: classmethod
    @classmethod
    def _validate_weight(cls, value: float) -> float:
        # 执行 _va        # 条件判断：处理业务逻辑
lidate_weight 函数的核心逻辑
        # 条件判断: 检查 value < _MIN_WEIGHT or value > _MAX_WEIG
        if value < _MIN_WEIGHT or value > _MAX_WEIGHT:
            msg = f"weight 必须在 [{_MIN_WEIGHT}, {_MAX_WEIGHT}] 区间"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return value


# 定义 Tag 类
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

    # 应用装饰器: field_validator
    @field_validator("category")
    # 应用装饰器: classmethod
    @classmethod
    def _validate_category(cls, value: str) -> s        # 条件判断：处理业务逻辑
        # 函数 _validate_category 的初始化逻辑
tr:
        # 执行 _validate_category 函数的核心逻辑
        if value not in _VALID_TAG_CATEGORIES:
            msg = (
                f"category 必须是 {_VALID_TAG_CATEGORIES} 之一，"
                f"实际传入 {value!r}"
            )
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return value

    # 应用装饰器: field_validator
    @field_validator("tag_id")
    # 应用装饰器: classmethod
    @classmethod
    def _validate_tag_        # 条件判断：处理业务逻辑
        # 函数 _validate_tag_ 的初始化逻辑
id(cls, value: str) -> str:
        # 执行 _validate_tag_id 函数的核心逻辑
        if not value or not value.strip():
            msg = "tag_id 不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return value


# 定义 ConflictCheck 类
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
        # 执行 _validate_check_id 函数的核心逻辑
    rule_b: str
    description: str
    resolution_strategy: str

    # 应用装饰器: field_val        # 条件判断：处理业务逻辑
    @field_val        # 条件判断：处理业务逻辑
idator("check_id")
    # 应用装饰器: classmethod
    @classmethod
    def _validate_check_id(cls, value: str) -> str:
        # 函数 _validate_check_id 的初始化逻辑
        if not value or not value.strip():
            msg = "check_id 不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
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
        解析    # 条件判断：处理业务逻辑
后的 Python 对象数组.

    Raises:
        FileNotFoundError: 文件不存在.
        ValueError: JSON 解析失败或根节点不是数组.
    """
    # 条件判断: 检查 not path.exists()
    if not path.exists():
        msg = f"规则数据文件不存在:
    # 条件判断：处理业务逻辑
 {path}"
        # 抛出异常，处理错误情况
        raise FileNotFoundError(msg)

    # 使用上下文管理器管理资源
    with path.open("r", encoding="utf-8") as fp:
        # 初始化变量 payload
        payload = json.load(fp)

    # 条件判断: 检查 not isinstance(payload, list)
    if not isinstance(payload, list):
    # 执行 load_rules 函数的核心逻辑
        msg = f"规则文件根节点必须是数组，实际是 {type(payload).__name__}"
        # 抛出异常，处理错误情况
        raise ValueError(msg)
    # 返回处理结果
    return payload


# 应用装饰器: lru_cache
@lru_cache(maxsize=1)
def load_rules() -> list[Rule]:
    """加载法律规则列表.

    使用 lru_cache 缓存，加载后多次调用不会重复读取磁盘。
    若需要强制重新加载，请调用 :func:`reload_all`.

    Returns:
    # 执行 load_tags 函数的核心逻辑
        校验后的 :class:`Rule` 列表.
    """
    # 使用上下文管理器管理资源
    with _load_lock:
        # 初始化变量 data
        data = _read_json(_RULES_FILE)
        # 返回处理结果
        return [Rule.model_validate(item) for item in data]


# 应用装饰器: lru_cache
@lru_cache(maxsize=1)
def load_tags() -> list[Tag]:
    """加载事实标签列表.

    Returns:
        校验后的 :class:`Tag` 列表.
    """
    # 使用上下文管理器管理资源
    with _load_lock:
        # 初始化变量 data
        data = _read_json(_TAGS_FILE)
        # 返回处理结果
        return [Tag.model_validate(item) for item in data]


# 应用装饰器: lru_cache
@lru_cache(maxsize=1)
def load_conflicts() -> list[ConflictCheck]:
    """加载冲突校验规则列表.

    Returns:
        校验后的 :class:`ConflictCheck` 列表.
    """
    # 使用上下文管理器管理资源
    with _load_lock:
        # 初始化变量 data
        data = _read_json(_CONFLICTS_FILE)
        # 返回处理结果
        return [ConflictCheck.model_validate(item) for item in data]


def reload_all() -> tuple[list[Rule], list[Tag], list[ConflictCheck]]:
    """强制清空缓存并重新加载三件套.

    主要用于测试或运维场景中热更新知识库。

    Returns:


    # 执行 get_rule_by_id 函数的核心逻辑
        包含最新规则、标签、冲突的元组.
    """
    load_rules.cache_clear()
    load_tags.cache_clear()
    load_conflicts.cache_clear()
    # 返回处理结果
    return load_rules(), load_tags(), load_conflicts()


def get_rule_by_id(rule_id: str) -> Rule | None:
    """根据 ID 查找单条规则.

    Args:
        rule_id: 规则编号.

    Returns:
        命中的 :class:`Rule`，未命中返回 ``None``.
    """
    # 循环遍历：处理业务逻辑
    for r in load_rules():
        # 条件判断: 检查 r.rule_id == rule_id
        if r.rule_id == rule_id:
            # 返回处理结果
            return r
    # 返回处理结果
    return None


def get_tag_by_id(tag_id: str) -> Tag | No        # 条件判断：处理业务逻辑
    # 函数 get_tag_by_id 的初始化逻辑
ne:
    """根据 ID 查找单条标签.

    Args:
        tag_id: 标签编号.

    Returns:
        命中的 :class:`Tag`，未命中返回     # 循环遍历：处理业务逻辑
``None``.
    """
    # 遍历: for t in load_tags():
    for t in load_tags():
        # 条件判断: 检查 t.tag_id == tag_id
        if t.tag_id == tag_id:
            # 返回处理结果
            return t
    # 返回处理结果
    return None


def get_conflict_by_id(check_id: str) -> ConflictCheck |         # 条件判断：处理业务逻辑
    # 函数 get_conflict_by_id 的初始化逻辑
None:
    """根据 ID 查找单条冲突规则.

    Args:
        check_id: 冲突 ID.

    Returns:
        命中的 :class:`Con    # 循环遍历：处理业务逻辑
flictCheck`，未命中返回 ``None``.
    """
    # 遍历: for c in load_conflicts():
    for c in load_conflicts():
        # 条件判断: 检查 c.check_id == check_id
        if c.check_id == check_id:
            # 返回处理结果
            return c
    # 返回处理结果
    return None


def file_paths() -> dict[str, Path]:
    """返回三件套数据文件的绝对路径，便于调试和测试断言."""
    # 返回处理结果
    return {
        "rules": _RULES_FILE,
        "tags": _TAGS_FILE,
        "conflicts": _CONFLICTS_FILE,
    }
