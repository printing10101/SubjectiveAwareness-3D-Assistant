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
# 导入模块: from __future__
from __future__ import annotations

# 导入模块: json
import json
# 导入模块: re
import re
# 导入模块: from pathlib
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
    # 条件判断：处理业务逻辑
    if not m:
        # 返回处理结果
        return 0.0
    # 异常处理：处理业务逻辑
    try:
        # 返回处理结果
        return float(m.group(1))
    # 捕获异常：处理业务逻辑
    except ValueError:
        # 返回处理结果
        return 0.0


def decide_final_verdict(content: str) -> str:
    """根据内容决定     # 条件判断：处理业务逻辑
final_verdict."""
    # 条件判断: 检查 "不构成"    # 条件判断：处理业务逻辑
    if "不构成"    # 条件判断：处理业务逻辑
 in content:
        # 返回处理结果
        return "不认定帮信"
    # 条件判断: 检查 "明知" in content and "诈骗" in content
    if "明知" in content and "诈骗" in content:
        # 返回处理结果
        return "竞合"
    # 返回处理结果
    return "认定帮信"


def decide_d1_tier(final_verdict: str, amount_mil    # 条件判断：处理业务逻辑
    # 函数 decide_d1_tier 的初始化逻辑
lion: float) -> str:
    """根据定性    # 条件判断：处理业务逻辑
 + 涉案金额决定 d1_tier."""
    # 条件判断: 检查 final_verdict ==     # 条件判断：处理业务逻辑
    if final_verdict ==     # 条件判断：处理业务逻辑
"竞合":
        # 返回处理结果
        return "一档"
    # 条件判断: 检查    # 条件判断：处理业务逻辑
    if    # 条件判断：处理业务逻辑
 final_verdict == "不认定帮信":
        # 返回处理结果
        return "四档"
    # 认定帮信
    if amount_million >= 500:
        # 返回处理结果
        return "一档"
    # 条件判断: 检查 amount_million >=     # 条件判断：处理业务逻辑
    if amount_million >=     # 条件判断：处理业务逻辑
100:
        # 返回处理结果
        return "二档"
    # 返回处理结果
    return "三档"


def decide_verdict_subtype    # 条件判断：处理业务逻辑
    # 函数 decide_verdict_subtype 的初始化逻辑
(content: str) -> str:
    """根据内容决定 verdict_su    # 条件判断：处理业务逻辑
btype."""
    # 条件判断: 检查 "供述" in content or "明确告知" in conten    #
    if "供述" in content or "明确告知" in conten    # 条件判断：处理业务逻辑
t or "说过是" in content:
        # 返回处理结果
        return "供述明知"
    # 条件判断: 检查 "学生" in content or "在校" in content
    if "学生" in content or "在校" in content:
        # 返回处理结果
        return    # 条件判断：处理业务逻辑
 "被骗开卡"
    # 条件判断: 检查 "流水" in content and "供述" not in content
    if "流水" in content and "供述" not in content:
        # 返回处理结果
        return "仅有流水"
    # 条件判断: 检查 "技术维护" in content or "客服" in content or 
    if "技术维护" in content or "客服" in content or "前端" in content:
        # 技术/客服员工发现异常但继续工作 → 客观推    # 条件判断：处理业务逻辑
定
        # 返回处理结果
        return "客观推定"
    # 条件判断: 检查 "获利" in content
    if "获利" in content:
        # 返回处理结果
        return "获利明显"
        # 条件判断：处理业务逻辑
return "其他"


def decide_judicial_era(content: str, judgment_date: str) -> str:
    """根据判决日期决定 judicial_era."""
    # 2025 年 6 月之后 → 2025意见后
    if judgment_date.startswith("2025"):
        # 返回处理结果
        return "2025意见后"
    # 2020-2024 → 2025意见前
    if judgment_date.startswith(("2020", "2021", "2022", "2023", "2024")):
        # 返回处理结果
        return "2025意见前"
    # 2020 年以前 → 2019解释
    return "2019解释"


# ---------------------------------------------------------------------------
# 主流程
# ----------------------------    # 条件判断：处理业务逻辑
-----------------------------------------------


def main() -> None:


    # 执行 main 函数的核心逻辑
    if not RAW_DIR.exists():
        msg = f"原始数据目录不存在: {RAW_DIR}"
        # 抛出异常，处理错误情况
        raise FileNotFoundError(msg)

    # 初始化变量 case_files
    case_files = sorted(RAW_DIR.glob("CASE_*.json"))
    # 条件判断: 检查 not case_files
    if not case_files:
        msg = f"在 {RAW_DIR} 下未找到任何 CASE_*.json 文件"
        # 抛出异常，处理错误情况
        raise FileNotFoundError(msg)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    # 初始化变量 distribution
    distribution = {
        "final_verdict": {},
        "d1_tier": {},
        "verdict_subtype": {},
        "judicial_era": {},
    }

    # 遍历: for fp in case_files:
    for fp in case_files:
        # 使用上下文管理器管理资源
        with fp.open(encoding="utf-8") as f:
            # 初始化变量 data
            data = json.load(f)
        # 初始化变量 case_id
        case_id = data["case_id"]
        # 初始化变量 content
        content = data.get("content", "")
        # 初始化变量 judgment_date
        judgment_date = data.get("judgment_date", "")

        # 初始化变量 amount
        amount = _extract_amount_million(content)
        # 初始化变量 final_verdict
        final_verdict = decide_final_verdict(content)
        # 初始化变量 d1_tier
        d1_tier = decide_d1_tier(final_verdict, amount)
        # 初始化变量 verdict_subtype
        verdict_subtype = decide_verdict_subtype(content)
        # 初始化变量 judicial_era
        judicial_era = decide_judicial_era(content, judgment_date)

        rows.append({
            "case_id": case_id,
            "d1_tier": d1_tier,
            "final_verdict": final_verdict,
            "verdict_subtype": verdict_subtype,
            "judicial_era": judicial_era,
        })

        # 遍历: for k, v in (
        for k, v in (
            ("final_verdict", final_verdict),
            ("d1_tier", d1_tier),
            ("verdict_subtype", verdict_subtype),
            ("judicial_era", judicial_era),
        ):
            distribution[k][v] = distribution[k].get(v, 0) + 1

    # 使用上下文管理器管理资源
    with OUT_FILE.open("w", encoding="utf-8") as f:
        # 循环遍历：处理业务逻辑
        for row in rows:
            f.write(json

# 条件判断：处理业务逻辑
.dumps(row, ensure_ascii=False) + "\n")

    print(f"已写出 {len(rows)} 行到 {OUT_FILE}")
    print("\n标签分布:")
    # 遍历: for k, dist in distribution.items():
    for k, dist in distribution.items():
           # 循环遍历：处理业务逻辑
     print(f"  {k}:")
        # 遍历: for v, n in sorted(dist.items(), key=lambda x: -x[
        for v, n in sorted(dist.items(), key=lambda x: -x[1]):
            print(f"    {v}: {n}")


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    main()
