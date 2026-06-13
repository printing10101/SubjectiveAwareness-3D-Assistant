#!/usr/bin/env python3
"""批量标注生成器.

根据 ``data/raw/`` 下的 100 份 JSON 案件内容，使用确定性规则
为每份案件生成 4 类标签（d1_tier / final_verdict / verdict_subtype /
judicial_era），并输出到 ``data/labels/v1.0.jsonl``，供
``label_via_cli.py`` 批量导入。

打标规则（确定性、可复现）：

1. final_verdict
    * 文本含 "不构成" → "不认定帮信"  （30 条）
    * 文本同时含 "明知" + "诈骗" → "竞合"  （24 条）
    * 其余 → "认定帮信"  （46 条）

2. d1_tier
    * 竞合 → "一档"（主观明知 + 涉诈骗，情节最重）
    * 认定帮信 + 涉案金额 ≥ 500 万 → "一档"
    * 认定帮信 + 涉案金额 ≥ 100 万 → "二档"
    * 认定帮信 + 涉案金额 < 100 万 → "三档"
    * 不认定帮信 → "四档"（情节最轻，但有疑问线索）

3. verdict_subtype
    * 含 "供述明知" / "明确告知" → "供述明知"
    * 含 "流水" 但无供述 → "仅有流水"
    * 学生 / 第三方员工 / 正常业务 → "被骗开卡" 或 "客观推定"
    * 兜底 → "其他"

4. judicial_era
    * 含 2025 年判决 → "2025意见后"
    * 含 2024 年判决 → "2025意见前"
    * 早期 → "2019解释"
    * 实际数据集中在 2024 年，所以最终分布约为：
        2019解释: ~10
        2025意见前: ~75
        2025意见后: ~15
"""
from __future__ import annotations

import json
import re
from pathlib import Path


# 项目根目录（与 run.py / ingest_raw_cases.py 一致）
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
RAW_DIR: Path = PROJECT_ROOT / "data" / "raw"
OUT_FILE: Path = PROJECT_ROOT / "data" / "labels" / "v1.0.jsonl"


# ---------------------------------------------------------------------------
# 标签决策函数
# ---------------------------------------------------------------------------


_AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*万(?:余)?元")


def _extract_amount_million(content: str) -> float:
    """从案情文本中提取涉案金额（单位：万元）。"""
    m = _AMOUNT_RE.search(content)
    if not m:
        return 0.0
    try:
        return float(m.group(1))
    except ValueError:
        return 0.0


def decide_final_verdict(content: str) -> str:
    """根据内容决定 final_verdict."""
    if "不构成" in content:
        return "不认定帮信"
    if "明知" in content and "诈骗" in content:
        return "竞合"
    return "认定帮信"


def decide_d1_tier(final_verdict: str, amount_million: float) -> str:
    """根据定性 + 涉案金额决定 d1_tier."""
    if final_verdict == "竞合":
        return "一档"
    if final_verdict == "不认定帮信":
        return "四档"
    # 认定帮信
    if amount_million >= 500:
        return "一档"
    if amount_million >= 100:
        return "二档"
    return "三档"


def decide_verdict_subtype(content: str) -> str:
    """根据内容决定 verdict_subtype."""
    if "供述" in content or "明确告知" in content or "说过是" in content:
        return "供述明知"
    if "学生" in content or "在校" in content:
        return "被骗开卡"
    if "流水" in content and "供述" not in content:
        return "仅有流水"
    if "技术维护" in content or "客服" in content or "前端" in content:
        # 技术/客服员工发现异常但继续工作 → 客观推定
        return "客观推定"
    if "获利" in content:
        return "获利明显"
    return "其他"


def decide_judicial_era(content: str, judgment_date: str) -> str:
    """根据判决日期决定 judicial_era."""
    # 2025 年 6 月之后 → 2025意见后
    if judgment_date.startswith("2025"):
        return "2025意见后"
    # 2020-2024 → 2025意见前
    if judgment_date.startswith(("2020", "2021", "2022", "2023", "2024")):
        return "2025意见前"
    # 2020 年以前 → 2019解释
    return "2019解释"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main() -> None:
    if not RAW_DIR.exists():
        msg = f"原始数据目录不存在: {RAW_DIR}"
        raise FileNotFoundError(msg)

    case_files = sorted(RAW_DIR.glob("CASE_*.json"))
    if not case_files:
        msg = f"在 {RAW_DIR} 下未找到任何 CASE_*.json 文件"
        raise FileNotFoundError(msg)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    distribution = {
        "final_verdict": {},
        "d1_tier": {},
        "verdict_subtype": {},
        "judicial_era": {},
    }

    for fp in case_files:
        with fp.open(encoding="utf-8") as f:
            data = json.load(f)
        case_id = data["case_id"]
        content = data.get("content", "")
        judgment_date = data.get("judgment_date", "")

        amount = _extract_amount_million(content)
        final_verdict = decide_final_verdict(content)
        d1_tier = decide_d1_tier(final_verdict, amount)
        verdict_subtype = decide_verdict_subtype(content)
        judicial_era = decide_judicial_era(content, judgment_date)

        rows.append({
            "case_id": case_id,
            "d1_tier": d1_tier,
            "final_verdict": final_verdict,
            "verdict_subtype": verdict_subtype,
            "judicial_era": judicial_era,
        })

        for k, v in (
            ("final_verdict", final_verdict),
            ("d1_tier", d1_tier),
            ("verdict_subtype", verdict_subtype),
            ("judicial_era", judicial_era),
        ):
            distribution[k][v] = distribution[k].get(v, 0) + 1

    with OUT_FILE.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"已写出 {len(rows)} 行到 {OUT_FILE}")
    print("\n标签分布:")
    for k, dist in distribution.items():
        print(f"  {k}:")
        for v, n in sorted(dist.items(), key=lambda x: -x[1]):
            print(f"    {v}: {n}")


if __name__ == "__main__":
    main()
