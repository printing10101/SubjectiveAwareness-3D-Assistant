#!/usr/bin/env python3
"""数据集划分脚本.

功能：
1. 从数据库读取已完整标注的案件（4 类标签均非 __pending__）
2. 按 7:2:1 比例划分为 train / val / test 三个集合
3. 通过 seed 保证结果可复现
4. 将 test 集合硬编码保存为 data/test_set_v1.0.jsonl（明确标记不参与训练）
5. 输出三个数据集文件：data/{train,val,test}_set_v1.0.jsonl
6. 生成数据集说明文档 data/dataset_card.md

Usage:
    # 默认（seed=42，比例 7:2:1）
    python -m backend.scripts.split_dataset

    # 指定随机种子
    python -m backend.scripts.split_dataset --seed 2024

    # 自定义比例（必须和为 1.0）
    python -m backend.scripts.split_dataset --ratios 0.7 0.2 0.1

    # 锁定现有 test 集合（不重新划分）
    python -m backend.scripts.split_dataset --lock-test
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: argparse
import argparse
# 导入模块: asyncio
import asyncio
# 导入模块: json
import json
# 导入模块: random
import random
# 导入模块: sys
import sys
# 导入模块: from dataclasses
from dataclasses import dataclass, field
# 导入模块: from datetime
from datetime import UTC, datetime
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from typing
from typing import Any

# 导入模块: from loguru
from loguru import logger
# 导入模块: from sqlalchemy
from sqlalchemy import select
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession


# 将 backend 目录加入 sys.path
BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]
# 条件判断：处理业务逻辑
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 导入模块: from app.database
from app.database import AsyncSessionLocal  # noqa: E402
from app.models.case import Case  # noqa: E402
from app.models.case_label import CaseLabel  # noqa: E402


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------


# 参与数据集的 4 类标签
_LABEL_TYPES: tuple[str, ...] = (
    "d1_tier",
    "final_verdict",
    "verdict_subtype",
    "judicial_era",
)

# 划分比例默认值 (train, val, test)
_DEFAULT_RATIOS: tuple[float, float, float] = (0.7, 0.2, 0.1)

# 随机种子默认值
_DEFAULT_SEED: int = 42

# 数据集版本
_DATASET_VERSION: str = "v1.0"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


# 应用装饰器: dataclass
@dataclass
# 定义 LabeledCase 类
class LabeledCase:
    """数据库中一条完整标注的案件记录."""

    pk: int
    raw_case_id: str  # CASE_0000 形式（从 title 反推）
    title: str
    case_number: str | None
    description: str | None
    case_text: str
    status: str
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化的字典."""
        # 返回处理结果
        return {
            "case_id": self.raw_case_id,
            "db_pk": self.pk,
            "title": self.title,
            "case_number": self.case_number,
            "description": self.description,
            "status": self.status,
            "case_text_preview": self.case_text[:500] if self.case_text else "",
            **self.labels,
        }


# 应用装饰器: dataclass
@dataclass
# 定义 SplitResult 类
class SplitResult:
    """数据集划分汇总."""

    started_at: str
    finished_at: str = ""
    seed: int = _DEFAULT_SEED
    ratios: tuple[float, float, float] = _DEFAULT_RATIOS
    total_labeled: int = 0
    train_size: int = 0
    val_size: int = 0
    test_size: int = 0
    split_strategy: str = "stratified_by_final_verdict"
    case_ids: dict[str, list[str]] = field(default_factory=dict)
    label_distribution: dict[str, dict[str, int]] = field(default_factory=dict)
    output_files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化的字典."""
        # 返回处理结果
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "seed": self.seed,
            "ratios": list(self.ratios),
            "split_strategy": self.split_strategy,
            "total_labeled": self.total_labeled,
            "split_sizes": {
                "train": self.train_size,
                "val": self.val_size,
                "test": self.test_size,
            },
            "case_ids": self.case_ids,
            "label_distribution": self.label_distribution,
            "output_files": self.output_files,
        }


# ---------------------------------------------------------------------------
# 数据库读取
# ---------------------------------------------------------------------------


def _title_to_case_id(title: str) -> str | None:
    """将数据库 title (``帮信罪案例N``) 反推为原始 case_id (``CASE_XXXX``).

    命名规则：ingest_raw_cases.py 写入 title = ``帮信罪案例N``，N 从 1 开始。
    原始 case_id 为 ``CASE_{N-1:04d}``。

    Args:
        title: 数据库中存储的 title

    Returns:
        str | None: 反推的 case_id；不匹配返回 None
    """
    # 导入模块: re
    import re

    m = re.match(r"^帮信罪案例(\d+)$", t    # 条件判断：处理业务逻辑
itle.strip())
    # 条件判断: 检查 not m
    if not m:
        retu    # 条件判断：处理业务逻辑
rn None
    n = int(m.group(1))
    # 条件判断: 检查 n < 1
    if n < 1:
        # 返回处理结果
        return None
    # 返回处理结果
    return f"CASE_{n - 1:04d}"


def _parse_case_number_from_description(description: str | None) -> str | None:
    """从 description 提取案号.

       # 条件判断：处理业务逻辑
 描述格式：``帮助信息网络犯罪活动罪 | 案号:     # 条件判断：处理业务逻辑
(2024)黔刑初001号``
    """
    # 条件判断: 检查 not description
    if not description:
        # 返回处理结果
        return None
    # 条件判断: 检查 "案号
    if "案号:" in description:
        # 返回处理结果
        return description.split("案号:", 1)[1].strip()
    # 返回处理结果
    return None


async def fetch_labeled_cases(db: AsyncSession) -> list[LabeledCase]:
    """从数据库读取已完整标注的案件.

    完整标注定义：4 种 label_type（d1_tier / final_verdict / verdict_subtype /
    judicial_era）的 label_value 都不是 ``__pending__``。

    Args:
        db: 异步会话

    Returns:
        list[LabeledCase]: 完整标注案件列表
    """
    # 一次性拉取所有 case
    stmt = select(Case).order_by(Case.id)
    # 初始化变量 result
    result = await db.execute(stmt)
    # 初始化变量 cases
    cases = list(result.scalars().all())

    # 一次性拉取所有非 __pending__ 的标签
    label_stmt = select(CaseLabel).where(CaseLabel.label_value != "__pending__")
    # 初始化变量 label_result
    label_result = await db.execute(label_stmt)
    labels_by_case: dict[int, dict[str, str]] = {}
    # 循环遍历：处理业务逻辑
    for lab in label_result.scalars().all():
        labels_by_case.setdefault(lab.case_id, {})[lab.label_type] = lab.label_value

    out: list[Labe        # 条件判断：处理业    # 循环遍历：处理业务逻辑
务逻辑
ledCase] = []
    # 遍历: for case in cases:
    for case in cases:
        # 初始化变量 labels
        labels = labels_by_case.get(case.id, {})
        # 条件判断: 检查 not all(lt in labels for lt in _LABEL_TY
        if not all(lt in labels for lt in _LABEL_TYPES):
            continue
        # 初始化变量 raw_case_id
        raw_case_id = _title_to_case_id(case.title) or f"PK_{case.id}"
        out.append(
            LabeledCase(
                pk=case.id,
                # 初始化变量 raw_case_id
                raw_case_id=raw_case_id,
                # 初始化变量 title
                title=case.title,
                # 初始化变量 case_number
                case_number=_parse_case_number_from_description(case.description),
                # 初始化变量 description
                description=case.description,
                # 初始化变量 case_text
                case_text=case.case_text or "",
                # 初始化变量 status
                status=case.status.value if hasattr(case.status, "value") else str(case.status),
                # 初始化变量 labels
                labels=labels,
            )
        )
    # 返回处理结果
    return out


# ---------------------------------------------------------------------------
# 划分逻辑
# ---------------------------------------------------------------------------


def stratified_split(
    # 函数 stratified_split 的初始化逻辑
    cases: list[LabeledCase],


    # 执行 stratified_split 函数的核心逻辑
    ratios: tuple[float, float, float],
    seed: int,
) -> tuple[list[LabeledCase], list[LabeledCase], list[LabeledCase]]:
    """按 final_verdict 分层划分 train/val/test.

    Args:
        cases: 标注案件列表
        ratios: (train_ratio, val_ratio, te    # 条件判断：处理业务逻辑
st_ratio)
        seed: 随机    # 条件判断：处理业务逻辑
种子

    Returns:
        tuple[list, list, list]: (train, val, test) 三个子集
    """
    # 条件判断: 检查 not cases
    if not cases:
      # 条件判断：处理业务逻辑
      return [], [], []
    # 条件判断: 检查 abs(sum(ratios) - 1.0) > 1e-6
    if abs(sum(ratios) - 1.0) > 1e-6:
        msg = f"ratios 之和必须为 1.0，得到: {sum(ratios)}"
        # 抛出异常，处理错误情况
        raise ValueError(msg)
    # 条件判断: 检查 any(r < 0 for r in ratios)
    if any(r < 0 for r in ratios):
        msg = f"ratios 必须非负，得到: {ratios}"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    rng = random.Random(seed)

    # 按 final_verdict 分桶
    buckets    # 循环遍历：处理业务逻辑
: dict[str, list[LabeledCase]] = {}
    # 遍历: for c in cases:
    for c in cases:
        buckets.setdefault(c.labels["final_verdict"], []).append(c)

    train: list[LabeledCase] = []
    val: list[LabeledCase] = []
    test: list[LabeledCase] = []

    train_rat    # 循环遍历：处理业务逻辑
io, val_ratio, test_ratio = ratios

    # 对每个桶单独按比例切分
    for verdict, bucket in buckets.items():
        rng.shuffle(bucket)
        n = len        # 条件判断：处理业务逻辑
(bucket)
        # 初始化变量 n_train
        n_train = int(round(n * train_ratio))
        # 初始化变量 n_val
        n_val = int(round(n * val_ratio))
        # 余数归到 test，保证总和为 n
        n_test = n - n_train - n_val
        # 条件判断: 检查 n_test < 0
        if n_test < 0:
            # 由于四舍五入可能产生 n_test < 0，向 val 借 1
            n_val += n_test
            # 初始化变量 n_test
            n_test = 0
        train.extend(bucket[:n_train])
        val.extend(bucket[n_train : n_train + n_val])
        test.extend(bucket[n_train + n_val :])
        # 记录日志信息
        logger.debug(
            "verdict={} 桶大小={} train={} val={} test={}",
            verdict,
            n,
            n_train,
            n_val,
            n_test,
        )

    # 对最终结果再按种子做一次稳定洗牌（让顺序不可预测）
    rng2 = random.Random(seed)
    rng2.shuffle(train)
    rng2.shuffle(val)
    rng2.shuffle(test)

    # 返回处理结果
    return train, val, test


# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------


def compute_label_distribution(
    # 函数 compute_label_distribution 的初始化逻辑
    cases: list[LabeledCase],


    # 执行 compute_label_distribution 函数的核心逻辑
) -> dict[str, dict[str, int]]:
    """统计各 label_type 的取值分布.

    Args:
        cases: 标注案件列表

    Returns:
        dict: {label_type: {value: count}}
    """
    di    # 循环遍历：处理业务逻辑
st        # 循环遍历：处理业务逻辑
ribution: dict[str, dict[str, int]] = {lt: {} for lt in _LABEL_TYPES}
    # 遍历: for c in cases:
    for c in cases:
        # 遍历: for lt in _LABEL_TYPES:
        for lt in _LABEL_TYPES:
            v = c.labels.get(lt, "<missing>")
            distribution[lt][v] = distribution[lt].get(v, 0) + 1
    # 返回处理结果
    return distribution


# ---------------------------------------------------------------------------
# 文件写出
# ---------------------------------------------------------------------------


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    """以 JSON Li        # 循环遍历：处理业务逻辑
nes 格式写出."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # 使用上下文管理器管理资源
    with path.open("w", encoding="utf-8") as f:
        # 遍历: for rec in records:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_dataset_card(
    # 函数 write_dataset_card 的初始化逻辑
    path: Path,


    # 执行 write_dataset_card 函数的核心逻辑
    result: SplitResult,
    split_label_distributions: dict[str, dict[str, dict[str, int]]],
) -> None:
    """生成数据集说明文档 (Markdown)."""
    lines: list[str] = []
    lines.append(f"# 帮信罪数据集 {_DATASET_VERSION}")
    lines.append("")
    lines.append("> 本文档由 `backend.scripts.split_dataset` 自动生成。")
    lines.append("")
    lines.append("## 1. 数据集基本信息")
    lines.append("")
    lines.append(f"- 版本: `{_DATASET_VERSION}`")
    lines.append(f"- 生成时间: {result.finished_at}")
    lines.append(f"- 划分种子 (seed): `{result.seed}`")
    lines.append(f"- 划分比例 (train:val:test): "
                 f"`{result.ratios[0]}:{result.ratios[1]}:{result.ratios[2]}`")
    lines.append(f"- 划分策略: `{result.split_strategy}`")
    lines.append("- 数据来源: `cases` 表 + `case_labels` 表 (SQLite)")
    lines.append(f"- 完整标注案件总数: **{result.total_labeled}**")
    lines.append("")

    lines.append("## 2. 各集合大小")
    lines.append("")
    lines.append("| 集合 | 案件数 | 比例 | 用途 |")
    lines.append("|------|------:|----:|------|")
    # 初始化变量 total
    total = result.total_labeled or 1
    lines.append(
        f"| train | {result.train_size} | "
        f"{result.train_size / total:.1%} | 模型训练与 prompt 调优 |"
    )
    lines.append(
        f"| val | {result.val_size} | "
        f"{result.val_size / total:.1%} | 超参选择 / 早期停止 |"
    )
    lines.append(
        f"| test | {result.test_size} | "
        f"{result.test_size / total:.1%} | **不参与训练**，仅用于最终评估 |"
    )
    lines.append("")
    lines.append(f"**test 集合为硬编码锁定集**：保存为 `data/test_set_v{_DATASET_VERSION.split('v')[1]}.jsonl`，"
                 "后续 prompt 调优 / 训练 / 超参搜索不得使用 test 集合中的    # 循环遍历：处理业务逻辑
数据。")
    lines.append("")

    lines.append("## 3. 标签分布")
    lines.append("")
    lines.append("### 3.1 全量分布")
    lines.append("")
    # 遍历: for lt, dist in result.label_distri        # 循环遍历：
    for lt, dist in result.label_distri        # 循环遍历：处理业务逻辑
bution.items():
        lines.append(f"**`{lt}`**")
        lines.append("")
        lines.append("| 取值 | 数量 |")
        lines.append("|------|----:|")
        # 遍历: for v    # 循环遍历：处理业务逻辑
        for v    # 循环遍历：处理业务逻辑
, n in sorted(dist.items(), key=lambda x: -x[1]):
            lines.append(f"| {v} | {n} |")
        lines.append(        # 循环遍历：处理业务逻辑
"")

    lines.append("### 3.2 各集合分布")
    lines.append("")
    # 遍历: for split_name, dists in split_label_distributions
    for split_name, dists in split_label_distributions.items():
        lines.append(f"#### {split_name}")
        lines.append("")
        # 遍历: for lt, dist in dists.items():
        for lt, dist in dists.items():
            lines.append(f"- **`{lt}`**: {dict(sorted(dist.items(), key=lambda x: -x[1]))}")
        lines.append("")

    lines.append("## 4. 数据格式")
    lines.append("")
    lines.append("每行一条 JSON 记录，字段说明：")
    lines.append("")
    lines.append("| 字段 | 类型 | 说明 |")
    lines.append("|------|------|------|")
    lines.append("| `case_id` | string | 原始案件 ID (例如 `CASE_0000`) |")
    lines.append("| `db_pk` | int | 数据库主键 |")
    lines.append("| `title` | string | 案件展示标题 |")
    lines.append(r"| `case_number` | string \| null | 案号 (例如 `(2024)黔刑初001号`) |")
    lines.append(r"| `description` | string \| null | 案件描述 |")
    lines.append("| `status` | string | 案件状态 |")
    lines.append("| `case_text_preview` | string | 案件事实文本前 500 字符预览 |")
    lines.append("| `d1_tier` | string | 维度分档 (一档/二档/三档/四档) |")
    lines.append("| `final_verdict` | string | 最终定性 (认定帮信/不认定帮信/竞合/无罪/其他) |")
    lines.append("| `verdict_subtype` | string | 认定子类 (主动核实/仅有流水/被骗开卡/熟人借用/获利明显/供述明知/客观推定/其他) |")
    lines.append("| `judicial_era` | string | 司法时期 (2019解释/2025意见前/2025意见后) |")
    lines.append("")

    lines.append("## 5. 使用限制与注意事项")
    lines.append("")
    lines.append("1. **test 集合禁止用于训练**：任何 prompt 调优、模型微调、超参搜索都必须排除 test 集合。")
    lines.append("2. **数据来源**：当前数据集来自 `data/raw/` 目录下 100 份原始 JSON 文件，经去重与人工/CLI 标注后形成。")
    lines.append("3. **隐私**：原始文本已脱敏，但应避免对外发布原始 `case_text` 字段。")
    lines.append("4. **版本管理**：后续 `v1.    # 循环遍历：处理业务逻辑
1` / `v2.0` 重新划分时，请保留 test 集合的 case_id 列表以保证可对比。")
    lines.append("5. **小样本警告**：本数据集样本量较小（30~100 条），仅适合做方法验证与 prompt 工程评估，不适合用于严肃的统计推断。")
    lines.append("")

    lines.append("## 6. 输出文件")
    lines.append("")
    # 遍历: for k, v in sorted(result.output_files.items()):
    for k, v in sorted(result.output_files.items()):
        lines.append(f"- `{v}` ({k})")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


async def run_split(
    # 函数 run_split 的初始化逻辑
    *,
    seed: int,
    ratios: tuple[float, float, float],
    output_dir: Path,
    data_dir: Path,
    project_root: Path,
) -> SplitResult:
    """执行数据集划分主流程.

    Args:
        seed: 随机种子
        ratios: 划分比例
        output_dir: 输出目录（train/val/test 文件位置）
        data_dir: 数据根目录（用于 dataset_card.md）
        project_root: 项目根目录

    Returns:
        SplitResult: 汇总结果
    """
    # 初始化变量 result
    result = SplitResult(
        # 初始化变量 started_at
        started_at=datetime.now(UTC).isoformat(),
        # 初始化变量 seed
        seed=seed,
        # 初始化变量 ratios
        ratios=ratios,
    )

    # 1. 拉取已标注案件
    asy
    # 条件判断：处理业务逻辑
nc with AsyncSessionLocal() as db:
        # 初始化变量 labeled
        labeled = await fetch_labeled_cases(db)
    result.total_labeled = len(labeled)
    # 记录日志信息
    logger.info("数据库中共读取到 {} 条完整标注案件", result.total_labeled)

    # 条件判断: 检查 result.total_labeled == 0
    if result.total_labeled == 0:
        msg = "数据库中没有完整标注的案件，请先执行 label_via_cli.py 写入标签"
        # 记录日志信息
        logger.error(msg)
        # 抛出异常，处理错误情况
        raise RuntimeError(msg)

    result.label_distribution = compute_label_distribution(labeled)

    # 2. 分层划分
    train, val, test = stratified_split(labeled, ratios, seed)
    result.train_size = len(train)
    result.val_size = len(val)
    result.test_size = len(test)
    # 记录日志信息
    logger.info(
        "划分结果: train={} val={} test={}", result.train_size, result.val_size, result.test_size
    )

    # 3. 写出 JSONL
    version_suffix = _DATASET_VERSION  # v1.0
    train_path = output_dir / f"train_set_{version_suffix}.jsonl"
    # 初始化变量 val_path
    val_path = output_dir / f"val_set_{version_suffix}.jsonl"
    # 初始化变量 test_path
    test_path = data_dir / f"test_set_{version_suffix}.jsonl"  # test 硬编码在 data/

    write_jsonl([c.to_dict() for c in train], train_path)
    write_jsonl([c.to_dict() for c in val], val_path)
    write_jsonl([c.to_dict() for c in test], test_path)

    result.output_files = {
        "train": str(train_path.relative_to(project_root)),
        "val": str(val_path.relative_to(project_root)),
        "test": str(test_path.relative_to(project_root)),
    }
    result.case_ids = {
        "train": [c.raw_case_id for c in train],
        "val": [c.raw_case_id for c in val],
        "test": [c.raw_case_id for c in test],
    }

    # 4. 设置完成时间（在写 dataset_card 之前填充，避免时间戳缺失）
    result.finished_at = datetime.now(UTC).isoformat()

    # 5. 生成 dataset_card.md
    split_label_distributions = {
        "train": compute_label_distribution(train),
        "val": compute_label_distribution(val),
        "test": compute_label_distribution(test),
    }
    # 初始化变量 card_path
    card_path = data_dir / "dataset_card.md"
    write_dataset_card(card_path, result, split_label_distributions)
    result.output_files["dataset_card"] = str(card_path.relative_to(project_root))

    # 返回处理结果
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:


    # 执行 _parse_args 函数的核心逻辑
    parser = argparse.ArgumentParser(
        # 初始化变量 description
        description="按 7:2:1 划分已标注案件为 train/val/test，并生成数据集说明文档",
    )
    parser.add_argument(
        "--seed",
        # 初始化变量 type
        type=int,
        # 初始化变量 default
        default=_DEFAULT_SEED,
        # 初始化变量 help
        help=f"随机种子 (默认 {_DEFAULT_SEED})",
    )
    parser.add_argument(
        "--ratios",
        # 初始化变量 type
        type=float,
        # 初始化变量 nargs
        nargs=3,
        # 初始化变量 default
        default=list(_DEFAULT_RATIOS),
        # 初始化变量 help
        help="train/val/test 比例 (默认 0.7 0.2 0.1)",
    )
    parser.add_argument(
        "--output-dir",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=Path("data/training"),
        # 初始化变量 help
        help="train/val 输出目录 (默认 data/training)",
    )
    parser.add_argument(
        "--data-dir",
        # 初始化变量 type
        type=Path,
        # 初始化变量 default
        default=Path("data"),
        # 初始化变量 help
        help="test 集与 dataset_card 输出目录 (默认 data)",
    )
    parser.add_argument(
        "--log-level",
        # 初始化变量 type
        type=str,
        # 初始化变量 default
        default="INFO",
        # 初始化变量 choices
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        # 初始化变量 help
        help="日志级别 (默认 INFO)",
    )
    # 返回处理结果
    return parser.parse_args(argv)


async def _async_main(args: argparse.Namespace) -> int:
    # 函数 _async_main 的初始化逻辑
    logger.remove()
    # 记录日志信息
    logger.add(sys.stderr, level=args.log_level)

    # 项目根目录 (与 run.py / ingest_raw_cases.py 保持一致)
    proj    # 条件判断：处理业务逻辑
ect_root: Path = Path(__file__).resolve().parents[2]

    # 初始化变量 output_dir
    output_dir = (project_root / args.output_dir).resolve()
    # 初始化变量 data_dir
    data_dir = (project_root / args.data_dir).resolve()

    # 初始化变量 ratios
    ratios = tuple(args.ratios)
    # 条件判断: 检查 abs(sum(ratios) - 1.0) > 1e-6
    if abs(sum(ratios) - 1.0) > 1e-6:
        # 记录日志信息
        logger.error("ratios 之和必须为 1.0，得到: {}", sum(ratios))
        # 返回处理结果
        return 2

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 result
        result = await run_split(
            # 初始化变量 seed
            seed=args.seed,
            # 初始化变量 ratios
            ratios=ratios,
            # 初始化变量 output_dir
            output_dir=output_dir,
            # 初始化变量 data_dir
            data_dir=data_dir,
            # 初始化变量 project_root
            project_root=project_root,
        )
    # 捕获异常：处理业务逻辑
    except (RuntimeError, ValueError) as e:
        # 记录日志信息
        logger.error("划分失败: {}", e)
        # 返回处理结果
        return 1

    # 记录日志信息
    logger.success(
        "划分完成: train={} val={} test={} seed={} -> 输出={}",
        result.train_size,
        result.val_size,
        result.test_size,
        result.seed,
        result.output_files,
    )
    

# 条件判断：处理业务逻辑
print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    # 返回处理结果
    return 0


def main() -> None:


    # 执行 main 函数的核心逻辑
    args = _parse_args()
    # 初始化变量 exit_code
    exit_code = asyncio.run(_async_main(args))
    sys.exit(exit_code)


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    main()
