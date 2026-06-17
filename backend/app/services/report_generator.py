"""报告内容生成器模块.

实现10章结构化报告内容的生成逻辑，每章包含引用段落指向案件原文。

# 应用装饰器: file: report_generator.py
@file: report_generator.py
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: from datetime
from datetime import datetime
# 导入模块: from typing
from typing import Any, Literal

# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.models.case
from app.models.case import Case
# 导入模块: from app.types.analysis_v2
from app.types.analysis_v2 import AnalysisResultV2, TierEnum


# ---------------------------------------------------------------------------
# V1.2 新增字段提取函数
# ---------------------------------------------------------------------------


def _extract_standard_path(analysis_result: AnalysisResultV2) -> str:
    """提取标准路径.

    取值必须为①/②/③/④中的其中一个选项。

    Args:
        analysis_result: 分析结果

    Returns:
        str: 标准路径标识
    """
    # 初始化变量 path_map
    path_map = {
        "帮信罪主路径": "①",
        "诈骗罪共同犯罪路径": "②",
        "掩饰隐瞒犯罪所得路径": "③",
        "规范路径待核实": "④",
    }
    # 初始化变量 identified_path
    identified_path = analysis_result.get("identified_path", "帮信罪主路径")
    # 返回处理结果
    return path_map.get(identified_path, "①")


def _extract_subject_analyses(analysis_result: AnalysisResultV2) -> list[dict[str, Any]]:
    """提取主体分析信息.

    仅在多主体情况下包含该字段。

    Args:
        analysis_result: 分析结果

    Returns:
        list[dict]: 主体分析列表
    """
    # 初始化变量 subjects
    subjects = analysis_result.get("subject_analyses", [])
    # 条件判断：处理业务逻辑
    if not subjects:
        # 返回处理结果
        return []
    # 返回处理结果
    return [
        {
            "name": s.get("name", ""),
            "role": s.get("role", ""),
            "objective_behavior": s.get("objective_behavior", ""),
            "cognitive_evidence": s.get("cognitive_evidence", []),
            "defense": s.get("defense", ""),
            "disputes": s.get("disputes", []),
        }
        # 循环遍历：处理业务逻辑
        for s in subjects
    ]


def _extract_evidence_layers(analysis_result: AnalysisResultV2) -> list[dict[str, Any]]:
    """提取证据层信息.

    实现4层结构，每层包含N条证据信息。
    该字段仅在报告内部可见，前端展示时不得包含任何分数信息。

    Args:
        analysis_result: 分析结果

    Returns:
        list[dict]: 证据层列表
    """
    # 初始化变量 layers
    layers = analysis_result.get("evid    # 条件判断：处理业务逻辑
ence_layers", [])
    # 条件判断: 检查 not layers
    if not layers:
        # 返回处理结果
        return []
    # 返回处理结果
    return [
        {
            "strength": layer.get("strength", ""),
            "facts": layer.get("facts", []),
            "legal_basis": layer.get("legal_b        # 循环遍历：处理业务逻辑
asis", ""),
        }
        # 遍历: for layer in layers
        for layer in layers
    ]


def _extract_boundary_alerts(analysis_result: AnalysisResultV2) -> list[dict[str, Any]]:
    """提取边界提醒信息.

    Args:
        analysis_result: 分析结果

    Returns:
        list[dict]: 边界提醒列表
    """
    # 初始化变量 alerts
    alerts = analysi    # 条件判断：处理业务逻辑
s_result.get("boundary_alerts", [])
    # 条件判断: 检查 not alerts
    if not alerts:
        # 返回处理结果
        return []
    # 返回处理结果
    return [
        {
            "alert_type": alert.get("alert_type", ""),
            "description": alert.get("description", ""),
            "severity":        # 循环遍历：处理业务逻辑
 alert.get("severity", "medium"),
        }
        # 遍历: for alert in alerts
        for alert in alerts
    ]


def _extract_factor_matrix(analysis_result: AnalysisResultV2) -> dict[str, Any]:
    """提取判断因素矩阵.

    包含每个维度的具体判断因素详情。

    Args:
        analysis_result: 分析结果

    Returns:
        dict: 因素矩阵
    """
    # 返回处理结果
    return {
        "dimension1": {
            "key_indicators": analysis_result.get("dimension1", {}).get("key_indicators", []),
            "triggered_rules": analysis_result.get("dimension1", {}).get("triggered_rules", []),
        },
        "dimension2": {
            "pattern_match": analysis_result.get("dimension2", {}).get("pattern_match", ""),
            "triggered_rules": analysis_result.get("dimension2", {}).get("triggered_rules", []),
        },
        "dimension3": {
            "contradictions": analysis_result.get("dimension3", {}).get("contradictions", []),
            "triggered_rules": analysis_result.get("dimension3", {}).get("triggered_rules", []),
        },
    }


def _extract_proof_gap(analysis_result: AnalysisResultV2) -> list[str]:
    """提取证明薄弱点.

    明确标识证明薄弱点内容。

    Args:
        analysis_result: 分析结果

    Returns:
        list[str]: 证明薄弱点列表
    """
    # 返回处理结果
    return analysis_result.get("proof_gap", [])


def _extract_supplementary_advice(analysis_result: AnalysisResultV2) -> list[str]:
    """提取补充审查建议.

    提供补充审查建议内容。

    Args:
        analysis_result: 分析结果

    Returns:
        list[str]: 补充建议列表
    """
    # 返回处理结果
    return analysis_result.get("supplementary_advice", [])


def _extract_review_checklist(analysis_result: AnalysisResultV2) -> list[dict[str, Any]]:
    """提取审查清单.

    Args:
        analysis_result: 分析结果

    Returns:
        list[dict]: 审查清单列表
    """
    # 返回处理结果
    return analysis_result.get("review_checklist", [])


def _extract_conflict_analysis(analysis_result: AnalysisResultV2) -> list[dict[str, Any]]:
    """提取冲突分析.

    Args:
        analysis_result: 分析结果

    Returns:
        list[dict]: 冲突分析列表
    """
    # 初始化变量 conflicts
    conflicts = analysis_result.get("conflicts", [])
    # 返回处理结果
    return [
        {
            "type": c.get("type", ""),
            "description": c.get("description", ""),
            "severity": c.get("severity",         # 循环遍历：处理业务逻辑
""),
            "resolution": c.get("resolution", ""),
        }
        # 遍历: for c in conflicts
        for c in conflicts
    ]


# ---------------------------------------------------------------------------
# 引用段落类型定义
# ---------------------------------------------------------------------------


# 定义 Citation 类
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
        # 返回处理结果
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }


# ---------------------------------------------------------------------------
# 章节生成函数
# ---------------------------------------------------------------------------


def ch1_basic_info(
    # 函数 ch1_basic_info 的初始化逻辑
    case: Case,


    # 执行 ch1_basic_info 函数的核心逻辑
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
    # 记录日志信息
    logger.info(f"生成第1章：基本信息 - 案件ID={case.id}")

    # 返回处理结果
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
                    "报告版本": "1.2.0",
                },
                "citations": [],
            }
        ],
    }


def ch2_fact_summary(
    # 函数 ch2_fact_summary 的初始化逻辑
    case: Case,


    # 执行 ch2_fact_summary 函数的核心逻辑
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
    # 记录日志信息
    logger.info(f"生成第2章：事实摘要 - 案件ID={case.id}")

    # 提取案件描述作为事实摘要
    fact_text = case.de    # 条件判断：处理业务逻辑
scription or "无案件描述"

    # 创建引用段落
    citations = []
    # 条件判断: 检查 case.description
    if case.description:
        citations.append(
            Citation(0, min(len(case.description), 200), case.description[:200]).to_dict()
        )

    # 返回处理结果
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
    # 函数 ch3_dimensional_analysis 的初始化逻辑
    case: Case,


    # 执行 ch3_dimensional_analysis 函数的核心逻辑
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
    # 记录日志信息
    logger.in    # 条件判断：处理业务逻辑
fo(f"生成第3章：维度分析 - 案件ID={case.id}")

    # 初始化变量 sections
    sections = []

    # 维度1：构成要件分析
    if "dimension1" in analysis_result:
        # 初始化变量 dim1
        dim1 = analysis_result["dimension1"]
        sections.append({
            "heading": "维度1：构成要件分析",
            "content": dim1.get("reasoning", "无分析内容"),
            "tier": dim1.get("tier", "T2"),
            "key_indicators":     # 条件判断：处理业务逻辑
dim1.get("key_indicators", []),
            "citations": [],
        })

    # 维度2：情节模式分析
    if "dimension2" in analysis_result:
        # 初始化变量 dim2
        dim2 = analysis_result["dimension2"]
        sections.append({
            "heading": "维度2：情节模式分析",
            "content": dim2.get("reasoning", "无分析内容"),
            "tier": dim2.get("tier", "T2"),
            # 条件判断：处理业务逻辑
    "pattern_match": dim2.get("pattern_match", ""),
            "citations": [],
        })

    # 维度3：矛盾分析
    if "dimension3" in analysis_result:
        # 初始化变量 dim3
        dim3 = analysis_result["dimension3"]
        sections.append({
            "heading": "维度3：矛盾分析",
            "content": dim3.get("reasoning", "无分析内容"),
            "tier": dim3.get("tier", "T2"),
            "contradictions": dim3.get("contradictions", []),
            "citations": [],
        })

    # 返回处理结果
    return {
        "chapter_id": "ch3",


    # 执行 ch4_triggered_rules 函数的核心逻辑
        "title": "维度分析",
        "sections": sections,
    }


def ch4_triggered_rules(
    # 函数 ch4_triggered_rules 的初始化逻辑
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
    # 记录日志信息
    logger.in    # 条件判断：处理业务逻辑
fo(f"生成第4章：触发规则 - 案件ID={case.id}")

    triggered_rule_i        # 循环遍历：处理业务逻辑
ds = analysis_result.get("triggered_rule_ids", [])

    # 初始化变量 sections
    sections = []
    # 条件判断: 检查 rule_hits
    if rule_hits:
        # 遍历: for rule in rule_hits:
        for rule in rule_hits:
            sections.append({
                "heading": f"规则 {rule.get('rule_id', '未知')}",
                "content": rule.get("description", "无描述"),
                "rule_id": rule.get("rule_id"),
                "        # 循环遍历：处理业务逻辑
severity": rule.get("severity"),
                "citations": [],
            })
    # 条件判断: 检查 eltriggered_rule_ids
    elif triggered_rule_ids:
        # 遍历: for rule_id in triggered_rule_ids:
        for rule_id in triggered_rule_ids:
            sections.append({
                "heading": f"规则 {rule_id}",
                "content": f"命中规则：{rule_id}",
                "rule_id": rule_id,
                "citations": [],
            })

    # 返回处理结果
    return {
        "chapter_id": "ch4",
        "title": "触发规则",


    # 执行 ch5_fact_tags 函数的核心逻辑
        "sections": sections or [{"heading": "无触发规则", "content": "本次分析未触发任何规则", "citations": []}],
    }


def ch5_fact_tags(
    # 函数 ch5_fact_tags 的初始化逻辑
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
        dict: 章节内容    # 条件判断：处理业务逻辑
字典
    """
    # 记录日志信息
    logger.inf        # 循环遍历：处理业务逻辑
o(f"生成第5章：事实标签 - 案件ID={case.id}")

    # 初始化变量 matched_tag_ids
    matched_tag_ids = analysis_result.get("matched_tag_ids", [])

    # 初始化变量 sections
    sections = []
    # 条件判断: 检查 tags
    if tags:
        # 遍历: for tag in tags:
        for tag in tags:
            sections.append({
                "heading": tag.get("name", "未知标签"),
                "content": tag.get("description", "无描述"),
                      # 循环遍历：处理业务逻辑
  "tag_id": tag.get("tag_id"),
                "category": tag.get("category"),
                "citations": [],
            })
    # 条件判断: 检查 elmatched_tag_ids
    elif matched_tag_ids:
        # 遍历: for tag_id in matched_tag_ids:
        for tag_id in matched_tag_ids:
            sections.append({
                "heading": f"标签 {tag_id}",
                "content": f"命中标签：{tag_id}",
                "tag_id": tag_id,
                "citations": [],
            })

    # 返回处理结果
    return {
        "chapter_id": "ch5",


    # 执行 ch6_conflict_results 函数的核心逻辑
        "title": "事实标签",
        "sections": sections or [{"heading": "无事实标签", "content": "本次分析未匹配任何标签", "citations": []}],
    }


def ch6_conflict_results(
    # 函数 ch6_conflict_results 的初始化逻辑
    case: Case,
    analysis_result: AnalysisResultV2,
) -> dict[str, Any]:
    """生成冲突结果章节.

    分析案件中的矛盾点及处理结果。

    Args:
        case: 案件对象
        analysis_result: 分析结果

     # 条件判断：处理业务逻辑
   R        # 循环遍历：处理业务逻辑
eturns:
        dict: 章节内容字典
    """
    # 记录日志信息
    logger.info(f"生成第6章：冲突结果 - 案件ID={case.id}")

    # 初始化变量 conflicts
    conflicts = analysis_result.get("conflicts", [])

    # 初始化变量 sections
    sections = []
    # 条件判断: 检查 conflicts
    if conflicts:
        # 遍历: for conflict in conflicts:
        for conflict in conflicts:
            sections.append({
                "heading": conflict.get("type", "冲突"),
                "content": conflict.get("description", "无描述"),
                "severity": conflict.get("severity"),
                "resolution": conflict.get("resolution", "待处理"),
                "citations": [],


    # 执行 ch7_similar_cases 函数的核心逻辑
            })

    # 返回处理结果
    return {
        "chapter_id": "ch6",
        "title": "冲突结果",
        "sections": sections or [{"heading": "无冲突", "content": "本次分析未发现冲突项", "citations": []}],
    }


def ch7_similar_cases(
    # 函数 ch7_similar_cases 的初始化逻辑
    case: Case,
    analysis_result: AnalysisResultV2,
    similar_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """生成相似案例章节.

    展示参考案例及其相似度分析。

    Args:
        c    # 条件判断：处理业务逻辑
ase:        # 循环遍历：处理业务逻辑
 案件对象
        analysis_result: 分析结果
        similar_cases: 相似案例列表

    Returns:
        dict: 章节内容字典
    """
    # 记录日志信息
    logger.info(f"生成第7章：相似案例 - 案件ID={case.id}")

    # 初始化变量 sections
    sections = []
    # 条件判断: 检查 similar_cases
    if similar_cases:
        # 遍历: for similar in similar_cases:
        for similar in similar_cases:
            sections.append({
                "heading": similar.get("title", "未知案例"),
                "content": similar.get("summary", "无摘要"),
                "case_id": similar.get("case_id"),
                "similarity": similar.get("similarity", 0.0),
                "verdict": similar.get("verdict"),
                "citations": [],


    # 执行 ch8_legal_analysis 函数的核心逻辑
            })

    # 返回处理结果
    return {
        "chapter_id": "ch7",
        "title": "相似案例",
        "sections": sections or [{"heading": "无相似案例", "content": "未找到相似案例", "citations": []}],
    }


def ch8_legal_analysis(
    # 函数 ch8_legal_analysis 的初始化逻辑
    case: Case,
    analysis_result: AnalysisResultV2,
) -> dict[str, Any]:
    """生成法律分析章节.

    替代原有的量刑建议章节，提供法律适用分析。

    Args:
        case: 案件对象
        analysis_result: 分析结果

    Returns:
        dict: 章节内容字典
    """
    # 记录日志信息
    logger.info(f"生成第8章：法律分析 - 案件ID={case.id}")

    # 初始化变量 final_verdict
    final_verdict = analysis_result.get("final_verdict", {})
    # 初始化变量 tier_str
    tier_str = final_verdict.get("final_tier", "T2")

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 tier
        tier = TierEnum(tier_str)
        # 初始化变量 tier_label
        tier_label = tier.chinese_label
    # 捕获异常：处理业务逻辑
    except ValueError:
        # 初始化变量 tier
        tier = TierEnum.T2
        # 初始化变量 tier_str
        tier_str = tier.value
        # 初始化变量 tier_label
        tier_label = tier.chinese_label

    # 初始化变量 sections
    sections = [
        {
            "headin    # 条件判断：处理业务逻辑
g": "法律适用分析",
            "content": f"根据综合分析，本案建议认定为{tier_label}。",
            "tier": tier_str,
            "tier_label": tier_label,
            "citations": [],
        }
    ]

    # 添加主观明知程度
    if "subjective_knowledge" in analysis_result:


    # 执行 ch9_legal_basis 函数的核心逻辑
        sections.append({
            "heading": "主观明知程度",
            "content": analysis_result["subjective_knowledge"],
            "citations": [],
        })

    # 返回处理结果
    return {
        "chapter_id": "ch8",
        "title": "法律分析",
        "sections": sections,
    }


def ch9_legal_basis(
    # 函数 ch9_legal_basis 的初始化逻辑
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
    # 记录日志信息
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

    # 初始化变量 sections
    sections = [
        {
            "heading": "主要法律依据",


    # 执行 ch10_review_conclusion 函数的核心逻辑
            "content": "本案涉及的主要法律法规",
            "laws": legal_basis,
            "citations": [],
        }
    ]

    # 返回处理结果
    return {
        "chapter_id": "ch9",
        "title": "法律依据",
        "sections": sections,
    }


def ch10_review_conclusion(
    # 函数 ch10_review_conclusion 的初始化逻辑
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
    # 记录日志信息
    logger.info(f"生成第10章：审查结论 - 案件ID={case.id}")

    # 初始化变量 final_verdict
    final_verdict = analysis_result.get("final_verdict", {})
    # 初始化变量 tier_str
    tier_str = final_verdict.get("final_tier", "T2")

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 tier
        tier = TierEnum(tier_str)
        # 初始化变量 tier_label
        tier_label = t    # 捕获异常：处理业务逻辑
ier.chinese_label
    # 捕获并处理异常
    except ValueError:
        # 初始化变量 tier
        tier = TierEnum.T2
        # 初始化变量 tier_str
        tier_str = tier.value
        # 初始化变量 tier_label
        tier_label = tier.chinese_label

    # 初始化变量 conclusion_text
    conclusion_text = (
        f"经过对案件事实、证据及法律适用的综合分析，"
        f"本案建议认定为{tier_label}。"
    )

    # 初始化变量 sections
    sections = [
        {
            "heading": "审查结论",
            "content": conclusion_text,
            "final_tier": tier_str,
            "final_label": tier_label,
            "citations": [],
        }
    ]

    # 添加免责声明
    if "disclaimer" in analysis_result:
        sections.append({
            "heading": "免责声明",
            "content": analysis_result["disclaimer"],


    # 执行 generate_report 函数的核心逻辑
            "citations": [],
        })

    # 返回处理结果
    return {
        "chapter_id": "ch10",
        "title": "审查结论",
        "sections": sections,
    }


# ---------------------------------------------------------------------------
# 核心生成函数
# ---------------------------------------------------------------------------


def generate_report(
    # 函数 generate_report 的初始化逻辑
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
    # 记录日志信息
    logger.info(f"开始生成报告 - 案件ID={case.id}, 分析ID={analysis_result.get('timestamp')}")

    # 初始化变量 generated_at
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
        ch8_legal_analysis(case, analysis_result),
        ch9_legal_basis(case, analysis_result),
        ch10_review_conclusion(case, analysis_result),
    ]

    # 组装完整报告
    report_content = {
        "report_id": None,  # 将在保存时设置
        "case_id": case.id,
        "generated_at": generated_at.isoformat(),
        "version": "1.2.0",
        "chapters": {ch["chapter_id"]: ch for ch in chapters},
        "metadata": {
            "total_chapters": len(chapters),
            "analysis_timestamp": analysis_result.get("timestamp"),
            "fallback": analysis_result.get("fallback", False),
        },
        # V1.2 新增字段
        "standard_path": _extract_standard_path(analysis_result),
        "subject_analyses": _extract_subject_analyses(analysis_result),
        "evidence_layers": _extract_evidence_layers(analysis_result),
        "boundary_alerts": _extract_boundary_alerts(analysis_result),
        "factor_matrix": _extract_factor_matrix(analysis_result),
        "proof_gap": _extract_proof_gap(analysis_result),
        "supplementary_advice": _extract_supplementary_advice(analysis_result),
        "review_checklist": _extract_review_checklist(analysis_result),
        "conflict_analysis": _extract_conflict_analysis(analysis_result),
    }

    # 记录日志信息
    logger.info(f"报告生成完成 - 共{len(chapters)}章")

    # 返回处理结果
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
    "ch8_legal_analysis",
    "ch9_legal_basis",
    "ch10_review_conclusion",
    "generate_report",
]
