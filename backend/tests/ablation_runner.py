"""消融实验框架 — 阶段 6 评测体系核心组件.

通过控制系统组件开关（规则引擎、标签抽取、冲突检测、维度模式、量刑计算），
评估各组件对系统性能的贡献度。从 2^6=64 种组合中选择 10 个关键组合进行实验。

组件开关：
- rules_on/off: 规则引擎启用/禁用
- tags_on/off: 标签抽取启用/禁用
- conflicts_on/off: 冲突检测启用/禁用
- single/multi dimension: 单维度/多维度分析
- sc_on/off: 量刑计算启用/禁用
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


# 确保 backend 在 sys.path 中
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------

_TESTS_DIR = Path(__file__).resolve().parent
_DATA_DIR = _TESTS_DIR / "data"
_REPORTS_DIR = _TESTS_DIR / "reports"
_GOLD_STANDARD_PATH = _DATA_DIR / "gold_standard_v1.0.json"
_ABLATION_REPORT_PATH = _REPORTS_DIR / "ablation_v1.0.json"


# ---------------------------------------------------------------------------
# 组件配置
# ---------------------------------------------------------------------------


@dataclass
class ComponentConfig:
    """系统组件配置."""

    rules_on: bool = True
    tags_on: bool = True
    conflicts_on: bool = True
    multi_dimension: bool = True  # True=多维度, False=单维度
    sc_on: bool = True  # 量刑计算启用

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "rules_on": self.rules_on,
            "tags_on": self.tags_on,
            "conflicts_on": self.conflicts_on,
            "multi_dimension": self.multi_dimension,
            "sc_on": self.sc_on,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> ComponentConfig:
        """从字典创建配置."""
        return ComponentConfig(
            rules_on=d.get("rules_on", True),
            tags_on=d.get("tags_on", True),
            conflicts_on=d.get("conflicts_on", True),
            multi_dimension=d.get("multi_dimension", True),
            sc_on=d.get("sc_on", True),
        )


# ---------------------------------------------------------------------------
# 关键消融组合定义
# ---------------------------------------------------------------------------


def get_ablation_combinations() -> list[tuple[str, ComponentConfig]]:
    """获取消融实验的关键组合.

    从 2^6=64 种组合中选择 10 个关键组合：
    1. 完整系统（所有组件启用）
    2. 无规则引擎
    3. 无标签抽取
    4. 无冲突检测
    5. 单维度分析（非多维度）
    6. 无量刑计算
    7. 仅规则+标签（无冲突、无量刑）
    8. 仅多维度（无规则、标签、冲突）
    9. 最小系统（仅多维度+量刑）
    10. 无规则+无标签（仅冲突+多维度+量刑）

    Returns:
        包含 (组合名称, 组件配置) 的列表
    """
    return [
        # 1. 完整系统
        (
            "full_system",
            ComponentConfig(
                rules_on=True,
                tags_on=True,
                conflicts_on=True,
                multi_dimension=True,
                sc_on=True,
            ),
        ),
        # 2. 无规则引擎
        (
            "no_rules",
            ComponentConfig(
                rules_on=False,
                tags_on=True,
                conflicts_on=True,
                multi_dimension=True,
                sc_on=True,
            ),
        ),
        # 3. 无标签抽取
        (
            "no_tags",
            ComponentConfig(
                rules_on=True,
                tags_on=False,
                conflicts_on=True,
                multi_dimension=True,
                sc_on=True,
            ),
        ),
        # 4. 无冲突检测
        (
            "no_conflicts",
            ComponentConfig(
                rules_on=True,
                tags_on=True,
                conflicts_on=False,
                multi_dimension=True,
                sc_on=True,
            ),
        ),
        # 5. 单维度分析
        (
            "single_dimension",
            ComponentConfig(
                rules_on=True,
                tags_on=True,
                conflicts_on=True,
                multi_dimension=False,
                sc_on=True,
            ),
        ),
        # 6. 无量刑计算
        (
            "no_sc",
            ComponentConfig(
                rules_on=True,
                tags_on=True,
                conflicts_on=True,
                multi_dimension=True,
                sc_on=False,
            ),
        ),
        # 7. 仅规则+标签
        (
            "rules_tags_only",
            ComponentConfig(
                rules_on=True,
                tags_on=True,
                conflicts_on=False,
                multi_dimension=True,
                sc_on=False,
            ),
        ),
        # 8. 仅多维度
        (
            "multi_dim_only",
            ComponentConfig(
                rules_on=False,
                tags_on=False,
                conflicts_on=False,
                multi_dimension=True,
                sc_on=True,
            ),
        ),
        # 9. 最小系统
        (
            "minimal",
            ComponentConfig(
                rules_on=False,
                tags_on=False,
                conflicts_on=False,
                multi_dimension=True,
                sc_on=True,
            ),
        ),
        # 10. 无规则+无标签
        (
            "no_rules_tags",
            ComponentConfig(
                rules_on=False,
                tags_on=False,
                conflicts_on=True,
                multi_dimension=True,
                sc_on=True,
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# 带组件控制的 Pipeline 执行
# ---------------------------------------------------------------------------


async def run_pipeline_with_config(
    case_text: str,
    config: ComponentConfig,
) -> dict[str, Any]:
    """使用指定组件配置运行 pipeline.

    Args:
        case_text: 案例文本
        config: 组件配置

    Returns:
        pipeline 执行结果
    """
    from app.services.pipeline import analyze_pipeline_v2

    # 运行完整 pipeline
    result = await analyze_pipeline_v2(case_text, mode="auto")

    # 根据配置调整结果
    adjusted_result = _adjust_result_by_config(result, config)

    return adjusted_result


def _adjust_result_by_config(
    result: dict[str, Any],
    config: ComponentConfig,
) -> dict[str, Any]:
    """根据组件配置调整 pipeline 结果.

    模拟组件禁用效果：
    - rules_on=False: 清空 triggered_rule_ids
    - tags_on=False: 清空 matched_tag_ids
    - conflicts_on=False: 清空 conflicts
    - multi_dimension=False: 使用单维度结果（简化为取维度1）
    - sc_on=False: 使用默认量刑区间
    """

    adjusted = result.copy()

    # 禁用规则引擎
    if not config.rules_on:
        adjusted["triggered_rule_ids"] = []
        # 重新计算档级（无规则影响）
        dim1 = adjusted.get("dimension1", {}).get("tier", "T2")
        dim2 = adjusted.get("dimension2", {}).get("tier", "T2")
        dim3 = adjusted.get("dimension3", {}).get("tier", "T2")
        try:
            verdict = combine_tiers(dim1, dim2, dim3, rule_hits=[])
            adjusted["final_verdict"] = verdict
        except Exception:
            pass

    # 禁用标签抽取
    if not config.tags_on:
        adjusted["matched_tag_ids"] = []

    # 禁用冲突检测
    if not config.conflicts_on:
        adjusted["conflicts"] = []

    # 单维度模式（简化处理：仅使用维度1结果）
    if not config.multi_dimension:
        dim1_tier = adjusted.get("dimension1", {}).get("tier", "T2")
        # 将三个维度都设置为维度1的结果
        adjusted["dimension2"] = adjusted.get("dimension1", {}).copy()
        adjusted["dimension3"] = adjusted.get("dimension1", {}).copy()
        # 重新计算档级
        try:
            verdict = combine_tiers(dim1_tier, dim1_tier, dim1_tier, rule_hits=[])
            adjusted["final_verdict"] = verdict
        except Exception:
            pass

    # 禁用量刑计算
    if not config.sc_on:
        if "final_verdict" in adjusted:
            adjusted["final_verdict"]["sentence_band"] = "待定"

    return adjusted


# ---------------------------------------------------------------------------
# 消融实验执行
# ---------------------------------------------------------------------------


async def run_ablation_experiment(
    gold_standard_path: Path = _GOLD_STANDARD_PATH,
    report_path: Path = _ABLATION_REPORT_PATH,
) -> dict[str, Any]:
    """运行消融实验并生成报告.

    Args:
        gold_standard_path: 金标准测试集路径
        report_path: 消融实验报告输出路径

    Returns:
        消融实验报告字典
    """
    # 导入 eval_runner 中的评估函数
    from eval_runner import (
        _aggregate_metrics,
        _load_case_text,
    )

    print(f"[ablation_runner] 加载测试集: {gold_standard_path}")
    with open(gold_standard_path, encoding="utf-8") as f:
        test_cases = json.load(f)

    total = len(test_cases)
    print(f"[ablation_runner] 测试案例数: {total}")

    # 获取消融组合
    combinations = get_ablation_combinations()
    print(f"[ablation_runner] 消融组合数: {len(combinations)}")

    # 存储每个组合的结果
    combination_results: list[dict[str, Any]] = []

    for combo_name, config in combinations:
        print(f"\n[ablation_runner] 运行组合: {combo_name}")
        print(f"  配置: {config.to_dict()}")

        # 运行所有测试案例
        case_results: list[dict[str, Any]] = []
        for i, case in enumerate(test_cases):
            case_id = case["case_id"]
            print(f"  ({i + 1}/{total}) 评估 {case_id} ...")

            case_text = _load_case_text(case_id)

            # 使用配置运行 pipeline
            start = time.perf_counter()
            try:
                result = await run_pipeline_with_config(case_text, config)
                status = "success"
            except Exception as exc:
                result = None
                status = f"error: {exc}"

            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            # 构建案例结果（与 eval_runner 格式一致）
            from eval_runner import (
                _cn_tier_to_rank,
                _extract_predictions,
                _infer_final_tier_from_dims,
            )

            from app.types.analysis_v2 import TierEnum

            pred = _extract_predictions(result)
            ground_truth = case["ground_truth"]

            gt_d1_rank = _cn_tier_to_rank(ground_truth["d1_tier"])
            gt_d2_rank = _cn_tier_to_rank(ground_truth["d2_tier"])
            gt_d3_rank = _cn_tier_to_rank(ground_truth["d3_tier"])
            gt_verdict = ground_truth["verdict"]

            gt_final_rank = _cn_tier_to_rank(
                _infer_final_tier_from_dims(gt_d1_rank, gt_d2_rank, gt_d3_rank)
            )
            gt_sentence_band = TierEnum(f"T{gt_final_rank}").sentence_band

            has_conflict = case.get("agreement_kappa", 1.0) < 0.75

            case_result = {
                "case_id": case_id,
                "status": status,
                "duration_ms": duration_ms,
                "predictions": pred,
                "ground_truth": {
                    "d1_rank": gt_d1_rank,
                    "d2_rank": gt_d2_rank,
                    "d3_rank": gt_d3_rank,
                    "verdict": gt_verdict,
                    "sentence_band": gt_sentence_band,
                    "has_conflict": has_conflict,
                },
            }
            case_results.append(case_result)

        # 汇总该组合的指标
        metrics = _aggregate_metrics(case_results)

        combination_results.append({
            "combination_name": combo_name,
            "config": config.to_dict(),
            "metrics": metrics,
            "successful_cases": sum(
                1 for r in case_results if r["status"] == "success"
            ),
            "failed_cases": sum(
                1 for r in case_results if r["status"] != "success"
            ),
        })

    # 构建报告
    report: dict[str, Any] = {
        "version": "1.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "test_set_size": total,
        "combination_count": len(combinations),
        "combinations": combination_results,
    }

    # 写入报告
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[ablation_runner] 消融实验报告已生成: {report_path}")
    _print_ablation_summary(report)

    return report


def _print_ablation_summary(report: dict[str, Any]) -> None:
    """打印消融实验结果摘要."""
    print("\n" + "=" * 80)
    print("消融实验结果摘要")
    print("=" * 80)
    print(f"测试集大小: {report['test_set_size']}")
    print(f"组合数量: {report['combination_count']}")
    print("-" * 80)

    # 表头
    header = f"{'组合名称':<20} {'verdict准确率':<12} {'D1精确':<10} {'D1容忍':<10} {'标签F1':<10} {'冲突召回':<10}"
    print(header)
    print("-" * 80)

    for combo in report["combinations"]:
        name = combo["combination_name"]
        metrics = combo["metrics"]

        verdict_acc = metrics.get("verdict_accuracy", {}).get("accuracy", 0.0)
        d1_exact = metrics.get("dimension1_accuracy", {}).get("exact_match", 0.0)
        d1_tol = metrics.get("dimension1_accuracy", {}).get("tolerance_match", 0.0)
        tag_f1 = metrics.get("tag_extraction_f1", {}).get("f1", 0.0)
        conflict_recall = metrics.get("conflict_detection_recall", {}).get("recall", 0.0)

        row = (
            f"{name:<20} "
            f"{verdict_acc:<12.2%} "
            f"{d1_exact:<10.2%} "
            f"{d1_tol:<10.2%} "
            f"{tag_f1:<10.2%} "
            f"{conflict_recall:<10.2%}"
        )
        print(row)

    print("=" * 80)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------


def main() -> None:
    """命令行入口."""
    parser = argparse.ArgumentParser(description="消融实验运行器")
    parser.add_argument(
        "--gold-standard",
        type=Path,
        default=_GOLD_STANDARD_PATH,
        help="金标准测试集路径",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=_ABLATION_REPORT_PATH,
        help="消融实验报告输出路径",
    )
    args = parser.parse_args()

    asyncio.run(run_ablation_experiment(args.gold_standard, args.report))


if __name__ == "__main__":
    main()
