"""报告内容生成器模块.

实现10章结构化报告内容的生成逻辑，每章包含引用段落指向案件原文。

@file: report_generator.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger

from app.models.case import Case
from app.types.analysis_v2 import AnalysisResultV2, TierEnum


# ---------------------------------------------------------------------------
# 引用段落类型定义
# ---------------------------------------------------------------------------


class Citation:
    """引用段落数据结构.

    指向案件原文的字符偏移量。

    Attributes:
        start: 起始字符位置
        end: 结束字符位置
        text: 引用文本内容
    """

    def __init__(self, start: int, end: int, text: str) -> None:
        """初始化引用段落.

        Args:
            start: 起始字符位置
            end: 结束字符位置
            text: 引用文本内容
        """
        self.start = start
        self.end = end
        self.text = text

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }


# ---------------------------------------------------------------------------
# 章节生成函数
# ---------------------------------------------------------------------------


def ch1_basic_info(
    case: Case,
    analysis_result: AnalysisResultV2,
    generated_at: datetime,
) -> dict[str, Any]:
    """生成基本信息章节.

    包含案件编号、案件名称、分析日期等元数据。

    Args:
        case: 案件对象
        analysis_result: 分析结果
        generated_at: 报告生成时间

    Returns:
        dict: 章节内容字典
    """
    logger.info(f"生成第1章：基本信息 - 案件ID={case.id}")

    return {
        "chapter_id": "ch1",
        "title": "基本信息",
        "sections": [
            {
                "heading": "案件基本信息",
                "content": {
                    "案件编号": str(case.id),
                    "案件名称": case.title,
                    "案件状态": case.status.value if case.status else "未知",
                    "分析日期": generated_at.strftime("%Y年%m月%d日 %H:%M:%S"),
                    "报告版本": "1.0.0",
                },
                "citations": [],
            }
        ],
    }


def ch2_fact_summary(
    case: Case,
    analysis_result: AnalysisResultV2,
) -> dict[str, Any]:
    """生成事实摘要章节.

    提炼案件核心事实要素。

    Args:
        case: 案件对象
        analysis_result: 分析结果

    Returns:
        dict: 章节内容字典
    """
    logger.info(f"生成第2章：事实摘要 - 案件ID={case.id}")

    # 提取案件描述作为事实摘要
    fact_text = case.description or "无案件描述"

    # 创建引用段落
    citations = []
    if case.description:
        citations.append(
            Citation(0, min(len(case.description), 200), case.description[:200]).to_dict()
        )

    return {
        "chapter_id": "ch2",
        "title": "事实摘要",
        "sections": [
            {
                "heading": "案件事实概述",
                "content": fact_text[:500] if len(fact_text) > 500 else fact_text,
                "citations": citations,
            }
        ],
    }


def ch3_dimensional_analysis(
    case: Case,
    analysis_result: AnalysisResultV2,
) -> dict[str, Any]:
    """生成维度分析章节.

    从多个维度对案件进行剖析。

    Args:
        case: 案件对象
        analysis_result: 分析结果

    Returns:
        dict: 章节内容字典
    """
    logger.info(f"生成第3章：维度分析 - 案件ID={case.id}")

    sections = []

    # 维度1：构成要件分析
    if "dimension1" in analysis_result:
        dim1 = analysis_result["dimension1"]
        sections.append({
            "heading": "维度1：构成要件分析",
            "content": dim1.get("reasoning", "无分析内容"),
            "tier": dim1.get("tier", "T2"),
            "confidence": dim1.get("confidence", 0.0),
            "key_indicators": dim1.get("key_indicators", []),
            "citations": [],
        })

    # 维度2：情节模式分析
    if "dimension2" in analysis_result:
        dim2 = analysis_result["dimension2"]
        sections.append({
            "heading": "维度2：情节模式分析",
            "content": dim2.get("reasoning", "无分析内容"),
            "tier": dim2.get("tier", "T2"),
            "confidence": dim2.get("confidence", 0.0),
            "pattern_match": dim2.get("pattern_match", ""),
            "citations": [],
        })

    # 维度3：矛盾分析
    if "dimension3" in analysis_result:
        dim3 = analysis_result["dimension3"]
        sections.append({
            "heading": "维度3：矛盾分析",
            "content": dim3.get("reasoning", "无分析内容"),
            "tier": dim3.get("tier", "T2"),
            "confidence": dim3.get("confidence", 0.0),
            "contradictions": dim3.get("contradictions", []),
            "citations": [],
        })

    return {
        "chapter_id": "ch3",
        "title": "维度分析",
        "sections": sections,
    }


def ch4_triggered_rules(
    case: Case,
    analysis_result: AnalysisResultV2,
    rule_hits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """生成触发规则章节.

    列出所有命中的规则及其详情。

    Args:
        case: 案件对象
        analysis_result: 分析结果
        rule_hits: 规则命中列表

    Returns:
        dict: 章节内容字典
    """
    logger.info(f"生成第4章：触发规则 - 案件ID={case.id}")

    triggered_rule_ids = analysis_result.get("triggered_rule_ids", [])

    sections = []
    if rule_hits:
        for rule in rule_hits:
            sections.append({
                "heading": f"规则 {rule.get('rule_id', '未知')}",
                "content": rule.get("description", "无描述"),
                "rule_id": rule.get("rule_id"),
                "severity": rule.get("severity"),
                "citations": [],
            })
    elif triggered_rule_ids:
        for rule_id in triggered_rule_ids:
            sections.append({
                "heading": f"规则 {rule_id}",
                "content": f"命中规则：{rule_id}",
                "rule_id": rule_id,
                "citations": [],
            })

    return {
        "chapter_id": "ch4",
        "title": "触发规则",
        "sections": sections or [{"heading": "无触发规则", "content": "本次分析未触发任何规则", "citations": []}],
    }


def ch5_fact_tags(
    case: Case,
    analysis_result: AnalysisResultV2,
    tags: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """生成事实标签章节.

    展示案件相关标签及分类。

    Args:
        case: 案件对象
        analysis_result: 分析结果
        tags: 标签列表

    Returns:
        dict: 章节内容字典
    """
    logger.info(f"生成第5章：事实标签 - 案件ID={case.id}")

    matched_tag_ids = analysis_result.get("matched_tag_ids", [])

    sections = []
    if tags:
        for tag in tags:
            sections.append({
                "heading": tag.get("name", "未知标签"),
                "content": tag.get("description", "无描述"),
                "tag_id": tag.get("tag_id"),
                "category": tag.get("category"),
                "citations": [],
            })
    elif matched_tag_ids:
        for tag_id in matched_tag_ids:
            sections.append({
                "heading": f"标签 {tag_id}",
                "content": f"命中标签：{tag_id}",
                "tag_id": tag_id,
                "citations": [],
            })

    return {
        "chapter_id": "ch5",
        "title": "事实标签",
        "sections": sections or [{"heading": "无事实标签", "content": "本次分析未匹配任何标签", "citations": []}],
    }


def ch6_conflict_results(
    case: Case,
    analysis_result: AnalysisResultV2,
) -> dict[str, Any]:
    """生成冲突结果章节.

    分析案件中的矛盾点及处理结果。

    Args:
        case: 案件对象
        analysis_result: 分析结果

    Returns:
        dict: 章节内容字典
    """
    logger.info(f"生成第6章：冲突结果 - 案件ID={case.id}")

    conflicts = analysis_result.get("conflicts", [])

    sections = []
    if conflicts:
        for conflict in conflicts:
            sections.append({
                "heading": conflict.get("type", "冲突"),
                "content": conflict.get("description", "无描述"),
                "severity": conflict.get("severity"),
                "resolution": conflict.get("resolution", "待处理"),
                "citations": [],
            })

    return {
        "chapter_id": "ch6",
        "title": "冲突结果",
        "sections": sections or [{"heading": "无冲突", "content": "本次分析未发现冲突项", "citations": []}],
    }


def ch7_similar_cases(
    case: Case,
    analysis_result: AnalysisResultV2,
    similar_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """生成相似案例章节.

    展示参考案例及其相似度分析。

    Args:
        case: 案件对象
        analysis_result: 分析结果
        similar_cases: 相似案例列表

    Returns:
        dict: 章节内容字典
    """
    logger.info(f"生成第7章：相似案例 - 案件ID={case.id}")

    sections = []
    if similar_cases:
        for similar in similar_cases:
            sections.append({
                "heading": similar.get("title", "未知案例"),
                "content": similar.get("summary", "无摘要"),
                "case_id": similar.get("case_id"),
                "similarity": similar.get("similarity", 0.0),
                "verdict": similar.get("verdict"),
                "citations": [],
            })

    return {
        "chapter_id": "ch7",
        "title": "相似案例",
        "sections": sections or [{"heading": "无相似案例", "content": "未找到相似案例", "citations": []}],
    }


def ch8_sentencing(
    case: Case,
    analysis_result: AnalysisResultV2,
) -> dict[str, Any]:
    """生成量刑建议章节.

    提供基于分析的量刑参考。

    Args:
        case: 案件对象
        analysis_result: 分析结果

    Returns:
        dict: 章节内容字典
    """
    logger.info(f"生成第8章：量刑建议 - 案件ID={case.id}")

    final_verdict = analysis_result.get("final_verdict", {})
    tier_str = final_verdict.get("final_tier", "T2")

    try:
        tier = TierEnum(tier_str)
        sentence_band = tier.sentence_band
        tier_label = tier.chinese_label
    except ValueError:
        tier = TierEnum.T2
        tier_str = tier.value
        sentence_band = tier.sentence_band
        tier_label = tier.chinese_label

    sections = [
        {
            "heading": "量刑建议",
            "content": f"根据综合分析，本案建议量刑区间为：{sentence_band}",
            "tier": tier_str,
            "tier_label": tier_label,
            "sentence_band": sentence_band,
            "confidence": final_verdict.get("confidence", 0.0),
            "citations": [],
        }
    ]

    # 添加主观明知程度
    if "subjective_knowledge" in analysis_result:
        sections.append({
            "heading": "主观明知程度",
            "content": analysis_result["subjective_knowledge"],
            "citations": [],
        })

    # 添加量刑建议文本
    if "sentence" in analysis_result:
        sections.append({
            "heading": "量刑建议详情",
            "content": analysis_result["sentence"],
            "citations": [],
        })

    return {
        "chapter_id": "ch8",
        "title": "量刑建议",
        "sections": sections,
    }


def ch9_legal_basis(
    case: Case,
    analysis_result: AnalysisResultV2,
) -> dict[str, Any]:
    """生成法律依据章节.

    列出案件涉及的法律法规。

    Args:
        case: 案件对象
        analysis_result: 分析结果

    Returns:
        dict: 章节内容字典
    """
    logger.info(f"生成第9章：法律依据 - 案件ID={case.id}")

    # 默认法律依据
    legal_basis = [
        {
            "law": "《中华人民共和国刑法》",
            "article": "第二百八十七条之二",
            "content": "帮助信息网络犯罪活动罪",
        },
        {
            "law": "《中华人民共和国刑法》",
            "article": "第二十五条",
            "content": "共同犯罪",
        },
    ]

    sections = [
        {
            "heading": "主要法律依据",
            "content": "本案涉及的主要法律法规",
            "laws": legal_basis,
            "citations": [],
        }
    ]

    return {
        "chapter_id": "ch9",
        "title": "法律依据",
        "sections": sections,
    }


def ch10_review_conclusion(
    case: Case,
    analysis_result: AnalysisResultV2,
) -> dict[str, Any]:
    """生成审查结论章节.

    总结分析结果及建议。

    Args:
        case: 案件对象
        analysis_result: 分析结果

    Returns:
        dict: 章节内容字典
    """
    logger.info(f"生成第10章：审查结论 - 案件ID={case.id}")

    final_verdict = analysis_result.get("final_verdict", {})
    tier_str = final_verdict.get("final_tier", "T2")

    try:
        tier = TierEnum(tier_str)
        tier_label = tier.chinese_label
    except ValueError:
        tier = TierEnum.T2
        tier_str = tier.value
        tier_label = tier.chinese_label

    conclusion_text = (
        f"经过对案件事实、证据及法律适用的综合分析，"
        f"本案建议认定为{tier_label}。"
        f"综合置信度为{final_verdict.get('confidence', 0.0):.2%}。"
    )

    sections = [
        {
            "heading": "审查结论",
            "content": conclusion_text,
            "final_tier": tier_str,
            "final_label": tier_label,
            "confidence": final_verdict.get("confidence", 0.0),
            "citations": [],
        }
    ]

    # 添加免责声明
    if "disclaimer" in analysis_result:
        sections.append({
            "heading": "免责声明",
            "content": analysis_result["disclaimer"],
            "citations": [],
        })

    return {
        "chapter_id": "ch10",
        "title": "审查结论",
        "sections": sections,
    }


# ---------------------------------------------------------------------------
# 核心生成函数
# ---------------------------------------------------------------------------


def generate_report(
    analysis_result: AnalysisResultV2,
    case: Case,
    rule_hits: list[dict[str, Any]] | None = None,
    tags: list[dict[str, Any]] | None = None,
    similar_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """生成完整报告内容.

    接收分析结果、案件信息、规则命中情况、标签及相似案例数据，
    返回包含10个章节的结构化报告内容。

    Args:
        analysis_result: 分析结果（V2格式）
        case: 案件对象
        rule_hits: 规则命中列表
        tags: 标签列表
        similar_cases: 相似案例列表

    Returns:
        dict: 包含10个章节的完整报告内容
    """
    logger.info(f"开始生成报告 - 案件ID={case.id}, 分析ID={analysis_result.get('timestamp')}")

    generated_at = datetime.now()

    # 生成10个章节
    chapters = [
        ch1_basic_info(case, analysis_result, generated_at),
        ch2_fact_summary(case, analysis_result),
        ch3_dimensional_analysis(case, analysis_result),
        ch4_triggered_rules(case, analysis_result, rule_hits),
        ch5_fact_tags(case, analysis_result, tags),
        ch6_conflict_results(case, analysis_result),
        ch7_similar_cases(case, analysis_result, similar_cases),
        ch8_sentencing(case, analysis_result),
        ch9_legal_basis(case, analysis_result),
        ch10_review_conclusion(case, analysis_result),
    ]

    # 组装完整报告
    report_content = {
        "report_id": None,  # 将在保存时设置
        "case_id": case.id,
        "generated_at": generated_at.isoformat(),
        "version": "1.0.0",
        "chapters": {ch["chapter_id"]: ch for ch in chapters},
        "metadata": {
            "total_chapters": len(chapters),
            "analysis_timestamp": analysis_result.get("timestamp"),
            "fallback": analysis_result.get("fallback", False),
        },
    }

    logger.info(f"报告生成完成 - 共{len(chapters)}章")

    return report_content


__all__ = [
    "Citation",
    "ch1_basic_info",
    "ch2_fact_summary",
    "ch3_dimensional_analysis",
    "ch4_triggered_rules",
    "ch5_fact_tags",
    "ch6_conflict_results",
    "ch7_similar_cases",
    "ch8_sentencing",
    "ch9_legal_basis",
    "ch10_review_conclusion",
    "generate_report",
]
