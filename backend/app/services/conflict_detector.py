"""冲突检测器.

负责在案件分析结果中检测以下 6 类冲突：

- C001 规则冲突
- C002 标签互斥冲突
- C003 维度间结论矛盾
- C004 证据不足
- C005 超量刑范围
- C006 适用法律版本冲突

输入包括：

- :class:`TagMatch` 列表（来自 :class:`app.services.tag_extractor`）
- 命中的 :class:`Rule` 列表
- 维度结果字典（``dimension1/2/3`` -> ``{score, reasoning}``）

输出为 :class:`Conflict` 列表，每项冲突包含冲突类型、严重程度与解决建议。
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: re
import re
# 导入模块: from collections.abc
from collections.abc import Mapping, Sequence
# 导入模块: from dataclasses
from dataclasses import dataclass, field
# 导入模块: from typing
from typing import Any

# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.services.rule_engine
from app.services.rule_engine import (
    ConflictCheck,
    Rule,
    Tag,
    load_conflicts,
    load_tags,
)
# 导入模块: from app.services.tag_extractor
from app.services.tag_extractor import TagMatch


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 严重程度
_SEVERITY_LOW: str = "low"
_SEVERITY_MEDIUM: str = "medium"
_SEVERITY_HIGH: str = "high"
_SEVERITY_CRITICAL: str = "critical"

# 标签互斥 ID 集合（与 data/tags/v1.0.json 的 mutually_exclusive_with 对应）
_OBJECTIVE_BEHAVIOR_TAGS: frozenset[str] = frozenset({"F001", "F002", "F009", "F010"})

# 量刑档位关键词，用于 C005
_TIER_KEYWORDS_PATTERN: re.Pattern[str] = re.compile(
    r"(一档|二档|三档|情节较轻|情节严重|情节特别严重|三年以下|三年以上|七年以下)",
)

# 法律版本标识
_LAW_VERSION_2019: str = "2019"
_LAW_VERSION_2025: str = "2025"

# C004 关键证据关键词
_CRITICAL_EVIDENCE_KEYWORDS: tuple[str, ...] = (
    "审计报告", "银行流水", "资金流水", "转账记录",
    "被害人陈述", "审计", "电子数据",
)

# C004 证据不足的最小关键词匹配数
_MIN_EVIDENCE_KEYWORD_HITS: int = 2

# 维度1（构成要件）、维度2（情节）、维度3（量刑参考）的默认名称
_DIM_CONSTITUTIVE: str = "dimension1"
_DIM_CIRCUMSTANCE: str = "dimension2"
_DIM_SENTENCING: str = "dimension3"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


# 应用装饰器: dataclass
@dataclass(slots=True)
# 定义 Conflict 类
class Conflict:
    """单条冲突检测结果.

    Attributes:
        check_id: 冲突 ID.
        name: 冲突名称.
        severity: 严重程度.
        involved: 涉及的规则/标签/维度 ID 列表.
        description: 冲突描述.
        resolution_strategy: 解决建议.
        raw_payload: 原始触发证据，便于审计.
    """

    check_id: str
    name: str
    severity: str
    involved: list[str]
    description: str
    resolution_strategy: str
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化字典."""
        # 返回处理结果
        return {
            "check_id": self.check_id,
            "name": self.name,
            "severity": self.severity,
            "involved": list(self.involved),
            "description": self.description,
            "resolution_strategy": self.resolution_strategy,
            "raw_payload": self.raw_payload,
        }


# ---------------------------------------------------------------------------
# 检测器
# ---------------------------------------------------------------------------


# 定义 ConflictDetector 类
class ConflictDetector:
    """帮信罪案件冲突检测器.

    复用 :func:`app.services.rule_engine.load_conflicts` 提供的元规则。
    """

    def __init__(self, checks: Sequence[ConflictCheck] | None = None) -> None:

        # 执行 __init__ 函数的核心逻辑
        self._checks: list[ConflictCheck] = (
            list(checks) if checks is not None else list(load_conflicts())
        )
        self._tag_index: dict[str, Tag] = {t.tag_id: t for t in load_tags()}

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def detect_conflicts(
        # 函数 detect_conflicts 的初始化逻辑
        self,
        tags: Sequence[TagMatch],

        # 执行 detect_conflicts 函数的核心逻辑
        rule_hits: Sequence[Rule],
        dimension_results: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> list[Conflict]:
        """运行所有冲突检查.

        Args:
            tags: 标签抽取结果.
            rule_hits: 命中的规则.
            dimension_results: 多维度分析结果，键为 ``dimension1/2/3``.

        Returns:
            :class:`Conflict` 列表.
        """
        results: list[Conflict] = []
        # 循环遍历：处理业务逻辑
        for check in self._checks:
            # 异常处理：处理业务逻辑
            try:
                # 条件判断：处理业务逻辑
                if check.check_id == "C001":
                    # 初始化变量 conflict
                    conflict = self._check_rule_conflict(rule_hits)
                # 条件判断: 检查 elcheck.check_id == "C002"
                elif check.check_id == "C002":
                    # 初始化变量 conflict
                    conflict = self._check_tag_mutex(tags)
                # 条件判断: 检查 elcheck.check_id == "C003"
                elif check.check_id == "C003":
                    # 初始化变量 conflict
                    conflict = self._check_dimension_contradiction(dimension_results)
                # 条件判断: 检查 elcheck.check_id == "C004"
                elif check.check_id == "C004":
                    # 初始化变量 conflict
                    conflict = self._check_evidence_shortage(tags, rule_hits, dimension_results)
                # 条件判断: 检查 elcheck.check_id == "C005"
                elif check.check_id == "C005":
                    # 初始化变量 conflict
                    conflict = self._check_sentence_out_of_range(dimension_results)
                # 条件判断: 检查 elcheck.check_id == "C006"
                elif check.check_id == "C006":
                    # 初始化变量 conflict
                    conflict = self._check_law_version_conflict(rule_hits)
                # 其他情况的默认处理
                else:
                    # 记录日志信息
                    logger.warning(f"未知的冲突检查 ID: {check.check_id}")
                    continue
            # 捕获并处理异常
            except Exception:  # noqa: BLE001
                logger.exception(f"冲突检测失败: {check.check_i
            # 条件判断：处理业务逻辑
d}")
                continue

            # 条件判断: 检查 conflict is not None
            if conflict is not None:
                results.append(conflict)

        # 返回处理结果
        return results

    # ------------------------------------------------------------------
    # C001 规则冲突
    # ------------------------------------------------------------------

    def _check_rule_conflict(self, rule_hits: Sequence[Rule]) -> Conflict | None:

        # 执行 _check_rule_conflict 函数的核心逻辑
        rule_ids = {r.rule_id for r in rule_hits}
        confli        # 循环遍历：处理业务逻辑
cting: list[str] = []
        # 遍历: for r in                 # 条件判断：处理业务逻辑
        for r in                 # 条件判断：处理业务逻辑
rule_hits:
            # 遍历: for other in r.conflicting_rules:
            for other in r.conflicting_rules:
                                # 条件判断：处理业务逻辑
    if other in rule_ids:
                    # 初始化变量 pair
                    pair = tuple(sort
        # 条件判断：处理业务逻辑
ed({r.rule_id, other}))
                    # 条件判断: 检查 pair not in conflicting
                    if pair not in conflicting:
                        conflicting.extend(pair)

        # 条件判断: 检查 not conflicting
        if not conflicting:
            # 返回处理结果
            return None

        # 初始化变量 check
        check = self._get_check("C001")
        # 返回处理结果
        return Conflict(
            # 初始化变量 check_id
            check_id=check.check_id,
            # 初始化变量 name
            name=check.name,
            # 初始化变量 severity
            severity=_SEVERITY_HIGH,
            # 初始化变量 involved
            involved=conflicting,
            # 初始化变量 description
            description=check.description,
            # 初始化变量 resolution_strategy
            resolution_strategy=check.resolution_strategy,
            # 初始化变量 raw_payload
            raw_payload={"conflicting_pairs": conflicting},
        )

    # ------------------------------------------------------------------
    # C002 标签互斥冲突
    # ------------------------------------------------------------------

    def _check_tag_mutex(self, tags: Sequence[TagMatch]) -> Conflict | None:

        # 执行 _check_tag_mutex 函数的核心逻辑
        tag_ids = {t.t            # 条件判断：处理业务逻辑
ag_id for t in tags}
           # 循环遍历：处理业务逻辑
     violations: list[tuple[str, str]] = []
        # 遍历: for                # 条件判断：处理业务逻辑
        for                # 条件判断：处理业务逻辑
 tag in tags:
            # 初始化变量 meta
            meta = self._tag_index.get(tag.tag_id)
                        # 条件判断：处理业务逻辑
        if not meta:
                continue
            for
        # 条件判断：处理业务逻辑
 other in meta.mutually_exclusive_with:
                # 条件判断: 检查 other in tag_ids
                if other in tag_ids:
                    # 初始化变量 pair
                    pair = tuple(sorted({tag.tag_id, other}))
                    # 条件判断: 检查 pair not in violations
                    if pair not in violations:
                        violations.append(pair)

        # 条件判断: 检查 not violations
        if not violations:
            # 返回处理结果
            return None

        # 初始化变量 check
        check = self._get_check("C002")
        # 返回处理结果
        return Conflict(
            # 初始化变量 check_id
            check_id=check.check_id,
            # 初始化变量 name
            name=check.name,
            # 初始化变量 severity
            severity=_SEVERITY_MEDIUM,
            # 初始化变量 involved
            involved=[tid for pair in violations for tid in pair],
            # 初始化变量 description
            description=check.description,
            # 初始化变量 resolution_strategy
            resolution_strategy=check.resolution_strategy,
            # 初始化变量 raw_payload
            raw_payload={"mutex_pairs": [list(p) for p in violations]},
        )

    # ------------------------------------------------------------------
    # C003 维度间结论矛盾
    # -----------        # 条件判断：处理业务逻辑
-------------------------------------------------------

    def _check_dimension_contradiction(
        # 函数 _check_dimension_contradiction 的初始化逻辑
        self,
        dimension_results: Mapping[str, Mapping[str, Any]] | None,

        # 执行 _check_dimension_contradiction 函数的核心逻辑
    ) -> Conflict | None:
        # 条件判断: 检查 not dimension_results
        if not dimension_results:
            # 返回处理结果
            return None

        # 初始化变量 constitutive
        constitutive = dimension_results.get(_DIM_CONSTITUTIVE) or {}
        # 初始化变量 circumstance
        circumstance = dimension_results.get(_DIM_CIRCUMSTANCE) or {}

        # 初始化变量 constitutive_text
        constitutive_text = _safe_text(constitutive.get("reasoning", ""))
        # 初始化变量 circumstance_text
        circumstance_text = _safe_text(circumstance.get("reasoning", ""))

        # 情形 1: 文本层面互相矛盾
        constitutive_text_hit = "情节严重" in constitutive_text
        # 初始化变量 circumstance_text_hit
        circumstance_text_hit = (
            "情节较轻" in circumstance_text
            or "情节显著轻微" in circumstance_text
            or "情节轻微" in circumstance_text
        )
        # 初始化变量 text_contradiction
        text_contradiction = constitutive_text_hit and circumstance_text_hit

        # 情形 2: 分数层面互相矛盾
        # 构成要件维度分高、情节维
        #         # 异常处理：处理业务逻辑
条件判断：处理业务逻辑
度文字明确说"较轻/轻微"
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 constitutive_score
            constitutive_score = float(constitutive.get("score", 0))
        # 捕获异常：处理业务逻辑
        except (TypeError, ValueError):
            # 初始化变量 constitutive_score
            constitutive_score = 0.0
        # 初始化变量 score_contradiction
        score_contradiction = (
            constitutive_score >= 7.0 and circumstance_text_hit
        )

        # 条件判断: 检查 not (text_contradiction or score_contrad
        if not (text_contradiction or score_contradiction):
            # 返回处理结果
            return None

        # 初始化变量 check
        check = self._get_check("C003")
        # 返回处理结果
        return Conflict(
            # 初始化变量 check_id
            check_id=check.check_id,
            # 初始化变量 name
            name=check.name,
            # 初始化变量 severity
            severity=_SEVERITY_HIGH,
            # 初始化变量 involved
            involved=[_DIM_CONSTITUTIVE, _DIM_CIRCUMSTANCE],
            # 初始化变量 description
            description=check.description,
            # 初始化变量 resolution_strategy
            resolution_strategy=check.resolution_strategy,
            # 初始化变量 raw_payload
            raw_payload={
                "constitutive_reasoning": constitutive_text,
                "constitutive_score": constitutive_score,
                "circumstance_reasoning": circumstance_text,
                "trigger": (
                    "text" if text_contradiction else "score"
                ),
            },
        )

    # ------------------------------------------------------------------
    # C004 证据不足
    # -----------------------        # 条件判断：处理业务逻辑
-------------------------------------------

    def _check_evidence_shortage(
        # 函数 _check_evidence_shortage 的初始化逻辑
        self,
        # 条件判断：处理业务逻辑
        tags: Sequence[TagMatch],

        # 执行 _check_evidence_shortage 函数        # 条件判断：处理业务逻辑
的核心逻辑
        rule_hits: Sequence[Rule],
        dimensio                # 条件判断：处理业务逻辑
n_results: Mapping[str, Mapping[str, Any]] | None,
    ) -> Conflict | None:
        # 条件判断: 检查 not rule_hits
        if not rule_hits:
            # 返回处理结果
            return None

        # 初始化变量 heavy_rules
        heavy_rules = [r for r in rule_hits if r.weight >= 0.8]
        # 条件判断: 检查 not heavy_rules
        if not heavy_rules:
            # 返回处理结果
            return None

        evidence_text_parts: l            # 循环遍历：处理业务逻辑
ist[str] = []
        # 条件判断: 检查        # 条件判断：处理业务逻辑
        if        # 条件判断：处理业务逻辑
 dimension_results:
            # 遍历: for v in dimension_results.values():
            for v in dimension_results.values():
                # 条件判断: 检查 isinstance(v, Mapping)
                if isinstance(v, Mapping):
                    evidence_text_parts.append(_safe_text(v.get("reasoning", "")))
        evidence_text_parts.extend(t.matched_text for t in tags)
        # 初始化变量 evidence_text
        evidence_text = "\n".join(evidence_text_parts)

        hit = sum(1 for kw in _CRITICAL_EVIDENCE_KEYWORDS if kw in evidence_text)
        # 条件判断: 检查 hit >= _MIN_EVIDENCE_KEYWORD_HITS
        if hit >= _MIN_EVIDENCE_KEYWORD_HITS:
            # 返回处理结果
            return None

        # 初始化变量 check
        check = self._get_check("C004")
        # 返回处理结果
        return Conflict(
            # 初始化变量 check_id
            check_id=check.check_id,
            # 初始化变量 name
            name=check.name,
            # 初始化变量 severity
            severity=_SEVERITY_MEDIUM,
            # 初始化变量 involved
            involved=[r.rule_id for r in heavy_rules],
            # 初始化变量 description
            description=check.description,
            # 初始化变量 resolution_strategy
            resolution_strategy=check.resolution_strategy,
            # 初始化变量 raw_payload
            raw_payload={
                "evidence_hits": hit,
                "missing_evidence": [
                    kw for kw in _CRITICAL_EVIDENCE_KEYWORDS if kw not in        # 条件判断：处理业务逻辑
 evidence_text
                ],
            },
        )

    # ------------------------------------------------------------------
    # C005 超量刑范围
    # ------------------------------------------------------------------

    def _check_sentence_out_of_range(
        # 函数 _check_sentence_out_of_range 的初始化逻辑
        self,
        dimension_results: Mapping[str, Mapping[str, Any]] | None,

        # 执行 _check_sentence_out_of_range 函数的核心逻辑
    ) -> Conflict |
        # 条件判断：处理业务逻辑
 None:
        # 条件判断: 检查 not dimension_results
        if not dimension_results:
            re        # 条件判断：处理业务逻辑
turn None

        # 初始化变量 sentencing
        sentencing = dimension_results.get(_DIM_SENTENCING) or {}
        # 初始化变量 circumstance
        circumstance = dimension_results.get(_DIM_CIRCUMSTANCE) or {}

        # 初始化变量 sent_text
        sent_text = _safe_text(sentencing.get("reasoning", ""))
        # 初始化变量 circum_text
        circum_text = _safe_text(circumstance.get("reasoning", ""))

        # 初始化变量 sent_tier
        sent_tier = _match_highest_tier(sent_text)
        # 初始化变量 circum_tier
        circum_tier = _match_highest_tier(circum_text)

        # 条件判断: 检查 sent_tier is None or circum_tier is None
        if sent_tier is None or circum_tier is None:
            # 返回处理结果
            return None
        # 条件判断: 检查 sent_tier <= circum_tier
        if sent_tier <= circum_tier:
            # 返回处理结果
            return None

        # 初始化变量 check
        check = self._get_check("C005")
        # 返回处理结果
        return Conflict(
            # 初始化变量 check_id
            check_id=check.check_id,
            # 初始化变量 name
            name=check.name,
            # 初始化变量 severity
            severity=_SEVERITY_HIGH,
            # 初始化变量 involved
            involved=[_DIM_SENTENCING, _DIM_CIRCUMSTANCE],
            # 初始化变量 description
            description=check.description,
            # 初始化变量 resolution_strategy
            resolution_strategy=check.resolution_strategy,
            # 初始化变量 raw_payload
            raw_payload={
                # 条件判断：处理业务逻辑
            "sentencing_tier": sent_tier,

        # 执行 _check_law_versi            # 条件判断：处理业务逻辑
on_conflict 函数的核心逻辑
                "circumstance_tier": circum_tier,
  
        # 条件判断：处理业务逻辑
          },
        )

    # ------------------------------------------------------------------
    # C006 适用法律版本冲突
    # ------------------------------------------------------------------

    def _check_law_version_confl        # 循环遍历：处理业务逻辑
        # 函数 _check_law_version_confl 的初始化逻辑
ict(self, rule_hits: Sequence[Rule]) -> Conflict | None:
        versions: set[str] = set()
        # 遍历: for r in rule_hits:
        for r in rule_hits:
            # 条件判断: 检查 _LAW_VERSION_2025 in r.source_law
            if _LAW_VERSION_2025 in r.source_law:
                versions.add(_LAW_VERSION_2025)
            # 条件判断: 检查 _LAW_VERSION_2019 in r.source_law
            if _LAW_VERSION_2019 in r.source_law:
                versions.add(_LAW_VERSION_2019)

        # 条件判断: 检查 len(versions) < 2
        if len(versions) < 2:
            # 返回处理结果
            return None

        # 初始化变量 check
        check = self._get_check("C006")
        # 返回处理结果
        return Conflict(
            # 初始化变量 check_id
            check_id=check.check_            # 条件判断：处理业务逻辑
id,
            # 初始化变量 name
            name=check.name,
            # 初始化变量 severity
            severity=_SEVERITY_CRITICAL,
            # 初始化变量 involved
            involved=sorted(versions),
            # 初始化变量 description
            description=check.description,
            # 初始化变量 resolution_strategy
            resolution_strategy=check.resolution_strategy,
            # 初始化变量 raw_payload
            raw_payload={"versions": sorted(versions)},

        # 执行 _get_check 函数的核心逻辑
        )

    # ------------------------------------------------------------------
    # 工具方法
    # ------------        # 循环遍历：处理业务逻辑
------------------------------------------------------

    def _get_check(self, check_id: str) -> ConflictCheck:
        # 函数 _get_check 的初始化逻辑
        for c in self._checks:
            # 条件判断: 检查 c.check_id == check_id
            if c.check_id == check_id:
                # 返回处理结果
                return c
        # 兜底：返回占位符对象，避免 None 引发 AttributeError
        return ConflictCheck(
            # 初始化变量 check_id
            check_id=check_id,
            # 初始化变量 name
            name="未注册",
            # 初始化变量 rule_a
            rule_a="",
            # 初始化变量 rule_b
            rule_b="",
            # 初始化变量 description
            description="",
            # 初始化变量 resolution_strategy
            resolution_strategy="",
        )


# ---------------------------------------------------------------------------
# 模块级便捷函数
# ---------------------------------------------------------------------------


def detect_conflicts(
    # 函数 detect_conflicts 的初始化逻辑
    tags: Sequence[TagMatch],


    # 执行 detect_conflicts 函数的核心逻辑
    rule_hits: Sequence[Rule],
    dimension_results: Mapping[str, Ma    # 条件判断：处理业务逻辑
pping[str, Any]] | Non    # 条件判断：处理业务逻辑
e = None,
) -> list[Conflict]:
    """便捷函数：执行 6 类冲突检查.

    Args:
        tags: 标签抽取结果.


    # 执行 _safe_text 函数的核心逻辑
        rule_hits: 命中的规则.
        dimension_results: 多维度分析结果.

    Returns:
        :class:`Conflict` 列表.
    """
        # 条件判断：处理业务逻辑
detector = ConflictDetector()
    # 返回处理结果
    return detector.detect_conflicts(tags, rule_hits, dimension_results)


# --------------------------------        # 条件判断：处理业务逻辑
-------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _safe_text(value: Any) -> str:
    """将任意输入安全地转为字符串."""
    # 条件判断: 检查 value is None
    if value is None:
               # 条件判断：处理业务逻辑
 return ""
    # 条件判断: 检查 isinstance(value, str)
    if isinstance(value, str):
        # 返回处理结果
        return value
    # 返回处理结果
    return str(value)


def _match_highest_tier(text: str) -> int | None:
    """从文本中匹配最高档位（数字越大档位越高）.

    Returns:
        1（情节较轻/一档    # 循环遍历：处理业务逻辑
）、2（情节严重/二档）、3（情节特别严重/三档），
        文本中无任何档位关键词则返回 ``None``。
    """
    # 条件判断: 检查 not text
    if not text:
        # 返回处理结果
        return None
    highest: int | None = None
    # 遍历: for match in _TIER_KEYWORDS_PATTERN.finditer(text)
    for match in _TIER_KEYWORDS_PATTERN.finditer(text):
        # 初始化变量 keyword
        keyword = match.group(1)
        # 条件判断: 检查 keyword in ("一档", "情节较轻", "三年以下")
        if keyword in ("一档", "情节较轻", "三年以下"):
            # 初始化变量 tier
            tier = 1
        # 条件判断: 检查 elkeyword in ("二档", "情节严重")
        elif keyword in ("二档", "情节严重"):
            # 初始化变量 tier
            tier = 2
        # 条件判断: 检查 elkeyword in ("三档", "情节特别严重", "三年以上", "七
        elif keyword in ("三档", "情节特别严重", "三年以上", "七年以下"):
            # 初始化变量 tier
            tier = 3
        # 其他情况的默认处理
        else:
            continue
        # 条件判断: 检查 highest is None or tier > highest
        if highest is None or tier > highest:
            # 初始化变量 highest
            highest = tier
    # 返回处理结果
    return highest
