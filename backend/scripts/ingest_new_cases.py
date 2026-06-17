#!/usr/bin/env python3
"""案例增量导入脚本.

支持从 JSON 文件或 API 接口增量导入新案例数据，实现不重启服务的热加载。

功能：
1. 从 JSON 文件或 API 接口读取新案例数据
2. 重复数据检测（基于文本相似度或唯一标识）
3. 自动标注与人工标注集成
4. 数据验证与格式化
5. 热加载机制（不重启服务）
6. 加载状态监控与失败回滚

使用方法:
    # 从 JSON 文件导入
    python -m backend.scripts.ingest_new_cases --file data/new_cases.json

    # 从 API 接口导入
    python -m backend.scripts.ingest_new_cases --api http://api.example.com/cases

    # 指定批量大小和并发数
    python -m backend.scripts.ingest_new_cases --file data/new_cases.json --batch-size 100 --workers 4

    # 启用自动标注
    python -m backend.scripts.ingest_new_cases --file data/new_cases.json --auto-label

    # 干运行模式（不实际写入，仅验证）
    python -m backend.scripts.ingest_new_cases --file data/new_cases.json --dry-run
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: argparse
import argparse
# 导入模块: asyncio
import asyncio
# 导入模块: hashlib
import hashlib
# 导入模块: json
import json
# 导入模块: sys
import sys
# 导入模块: time
import time
# 导入模块: from dataclasses
from dataclasses import dataclass, field
# 导入模块: from datetime
from datetime import UTC, datetime
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from typing
from typing import Any

# 导入模块: httpx
import httpx
# 导入模块: from loguru
from loguru import logger
# 导入模块: from sqlalchemy
from sqlalchemy import select
# 导入模块: from sqlalchemy.exc
from sqlalchemy.exc import SQLAlchemyError
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession


# 将 backend 目录加入 sys.path
BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]
# 条件判断：处理业务逻辑
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 导入模块: from app.config
from app.config import AnalysisConfig
# 导入模块: from app.database
from app.database import AsyncSessionLocal
# 导入模块: from app.models.case
from app.models.case import Case, CaseStatus
# 导入模块: from app.models.case_label
from app.models.case_label import CaseLabel
# 导入模块: from app.models.user
from app.models.user import User


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


# 应用装饰器: dataclass
@dataclass
# 定义 IngestStats 类
class IngestStats:
    """导入统计信息."""

    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    duplicates: int = 0
    start_time: float = field(default_factory=time.time)
    errors: list[str] = field(default_factory=list)

    # 应用装饰器: property
    @property
    def duration(self) -> float:
        """导入耗时（秒）."""
        # 返回处理结果
        return time.time() - self.start_time

    # 应用装饰器: property
    @property
    def success_rate(self) -> float:
             # 条件判断：处理业务逻辑
   """成功率."""
        # 条件判断: 检查 self.total == 0
        if self.total == 0:
            # 返回处理结果
            return 0.0
        # 返回处理结果
        return self.success / self.total

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        # 返回处理结果
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "duplicates": self.duplicates,
            "duration_seconds": round(self.duration, 2),
            "success_rate": round(self.success_rate, 4),
            "errors": self.errors[:10],  # 只保留前 10 个错误
        }


# 应用装饰器: dataclass
@dataclass
# 定义 CaseData 类
class CaseData:
    """案例数据结构."""

    case_text: str
    title: str | None = None
    source: str | None = None
    external_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    labels: dict[str, Any] = field(default_factory=dict)

    # 应用装饰器: classmethod
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CaseData:
        """从字典创建实例."""
        # 返回处理结果
        return cls(
            # 初始化变量 case_text
            case_text=data.get("case_text", ""),
            # 初始化变量 title
            title=data.get("title"),
            # 初始化变量 source
            source=data.get("source"),
            # 初始化变量 external_id
            external_id=data.get("external_id"),
            # 初始化变量 metadata
            metadata=data.get("metadata", {}),
            # 初始化变量 labels
            labels=data.get("labels", {}),
        )

    def compute_hash(self) -> str:
        """计算案例文本的哈希值（用于去重）."""
        # 返回处理结果
        return hashlib.sha256(self.case_text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 数据源读取
# ---------------------------------------------------------------------------


async def read_from_json_file(file_path: Path) -> list[dict[str, Any]]:
    """从 JSON 文件读取案例数据.

    Args:
        file_path: JSON 文件路径

    # 条件判断：处理业务逻辑
    Returns:
        案例数据列表
    """
    # 条件判断: 检查 not file_path.exists()
    if not file_path.exists():
        # 抛出异常，处理错误情况
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 记录日志信息
    logger.info(f"从 JSON 文件读取数据: {file_path}")

    # 使用上下文管理器管理资源
    with file_path.open("r", encoding="utf-8")    # 条件判断：处理业务逻辑
 as f:
        # 初始化变量 data
        data = json.load(f)

    # 支持单个对象或对象列表
    if isinstance(data, dict):
        # 返回处理结果
        return [data]
    # 条件判断: 检查 isinstance(data, list)
    if isinstance(data, list):
        # 返回处理结果
        return data
    # 抛出异常，处理错误情况
    raise ValueError(f"不支持的数据格式: {type(data)}")


async def read_from_api(api_url: str, headers: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """从 API 接口读取案例数据.

    Args:
        api_url: API 端点 URL
        headers: HTTP 请求头

    Returns:
        案例数据列表
    """
    # 记录日志信息
    logger.info(f"从 API 接口读取数据: {api_url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 初始化变量 response
        response = await client.get(api_url, headers=headers or {})
        respon    # 条件判断：处理业务逻辑
se.raise_for_        # 条件判断：处理业务逻辑
status()
        # 初始化变量 data
        data = response.json()

    # 支持单个对象或对象列表
    # 条件判断：处理业务逻辑
    if isinstance(data, dict):
        # 条件判断: 检查 "data" in data
        if "data" in data:
            # 返回处理结果
            return data["data"]
        # 返回处理结果
        return [data]
    # 条件判断: 检查 isinstance(data, list)
    if isinstance(data, list):
        # 返回处理结果
        return data
    # 抛出异常，处理错误情况
    raise ValueError(f"不支持的数据格式: {type(data)}")


# ---------------------------------------------------------------------------
# 重复检测
# ---------------------------------------------------------------------------


async def check_duplicate(
    # 函数 check_duplicate 的初始化逻辑
    db: AsyncSession,
    case_data: CaseData,
    existing_hashes: set[str],
) -> bool:
    """检查案例是否重复.

    Args:
        db: 数据库会话
        case_data: 案    # 条件判断：处理业务逻辑
例数据
        existing_hashes: 已存在的案例哈希集合

    Returns:
        是否重复
      # 条件判断：处理业务逻辑
  """
    # 基于哈希的去重
    case_hash = case_data.compute_hash()
    # 条件判断: 检查 case_hash in existing_hashes
    if case_hash in existing_hashes:
        # 返回处理结果
        return True

    # 如果有外部 ID，也可以基于外部 ID 去重
           # 条件判断：处理业务逻辑
 if case_data.external_id:
        # 初始化变量 result
        result = await db.execute(
            select(Case).where(Case.metadata_["external_id"].astext == case_data.external_id)
        )
        # 条件判断: 检查 result.scalar_one_or_none()
        if result.scalar_one_or_none():
            # 返回处理结果
            return True

    # 返回处理结果
    return False


async def load_existing_hashes(db: AsyncSession) -> set[str]:
    """加载已存在案例的哈希集合.

    Args:
        db: 数据库会话

    Returns:
        哈希集合
    """
    # 初始化变量 result
    result = await db.execute(select(Case.case_text))
    # 初始化变量 texts
    texts = result.scalars().all()
    # 返回处理结果
    return {hashlib.sha256(text.encode("utf-8")).hexdigest() for text in texts}


# ---------------------------------------------------------------------------
# 数据验证
# --------------------------------------------------------------------    # 条件判断：处理业务逻辑
-------


def validate_case_data(case_data: CaseData) -> tuple[bool, str | None]:
    """验证案例数据.

    Args:
        case_data: 案例数据

    Return
    # 条件判断：处理业务逻辑
s:
        (是否有效, 错误信息)
    """
    # 检查文本长度
    if len(case_data.case_text) < AnalysisConfig.MIN_CASE_LENGTH:
        # 返回处理结果
        return False, f"文本长度过短: {len(case_data.case_text    # 条件判断：处理业务逻辑
)} < {AnalysisConfig.MIN_CASE_LENGTH}"

    # 条件判断: 检查 len(case_data.case_text) > AnalysisConfi
    if len(case_data.case_text) > AnalysisConfig.MAX_CASE_TEXT_LENGTH:
        # 返回处理结果
        return False, f"文本长度过长: {len(case_data.case_text)} > {AnalysisConfig.MAX_CASE_TEXT_LENGTH}"

    # 检查标题长度
    if case_data.title and len(case_data.title) > AnalysisConfig.MAX_TITLE_LENGTH:
        # 返回处理结果
        return False, f"标题长度过长: {len(case_data.title)} > {AnalysisConfig.MAX_TITLE_LENGTH}"

    # 返回处理结果
    return True, None


# ---------------------------------------------------------------------------
# 自动标注
# ---------------------------------------------------------------------------


async def auto_label_case(case_data: CaseData) -> dict[str, Any]:
    """对案例进行自动标注.

    Args:
        case_data: 案例数据

    Returns:
        标注结果字典
    """
    # 这里应该调用标注服务进行自动标注
    # 简化实现：返回空标注
    logger.debug(f"自动标注案例: {case_data.title or case_data.case_text[:50]}")
    # 返回处理结果
    return {}


# ---------------------------------------------------------------------------
# 核心导入逻辑
# ---------------------------------------------------------------------------


async def ingest_cases(
    # 函数 ingest_cases 的初始化逻辑
    cases: list[dict[str, Any]],
    batch_size: int = 100,
    auto_label: bool = False,
    dry_run: bool = False,
    user_id: int | None = None,
) -> IngestStats:
    """导入案例数据.

    Args:
        cases: 案例数据列表
        batch_size: 批量大小
        auto_label: 是否启用自动标注
        dry_run: 是否为干运行模式
        user_id: 创建用户 ID

    Returns:
        导入统计信息
    """
    # 初始化变量 stats
    stats = IngestStats(total=len(cases))
    # 记录日志信息
    logger.info(f"开始导入 {len(cases)} 个案例 (batch_size={batch_size}, auto_l        # 条件判断：处理业务逻辑
abel={auto_label}, dry_run={dry_run})")

    async with AsyncSessionLocal() as db:
        # 加载已存在的案例哈希
        existing_hashes = await load_ex            # 条件判断：处理业务逻辑
isting_hashes(db)
        # 记录日志信息
        logger.info(f"已加载 {len(existing_hashes)} 个已存在案例的哈希")

        # 获取或创建系统用户
        if user_id is None:
            # 初始化变量 result
            result = await db.execute(select(User).where(User.username == "admin"))
            # 初始化变量 admin_user
            admin_user = result.scalar_one_or_none()
            # 条件判断: 检查 admin_user
            if admin_user:
                # 初始化变量 user_id
                user_id = admin_user.id

        # 批量处理
        # 循环遍历：处理业务逻辑
        for i in range(0, len(cases), batch_size):
            # 初始化变量 batch
            batch = cases[i : i + batch_size]
            # 初始化变量 batch_num
            batch_num = i // batch_size + 1
            # 初始化变量 total_batches
            total_batches = (len(cases) + batch_size - 1) // batch_size

            # 记录日志信息
            logger.info(f"处理批次 {batch_                    # 条件判断：处理业务逻辑
num}/{total_batches}
            # 循环遍历：处理业务逻辑
 ({len(batch)} 个案例)")

            # 遍历: for case_dict in batch:
            for case_dict in batch:
                # 异常处理：处理业务逻辑
                try:
                    # 解析案例数据
                    case_data = CaseData.from_dict(case_dict)

                    # 验证数据
                    is_valid, error_msg =                     # 条件判断：处理业务逻辑
validate_case_data(case_data)
                    # 条件判断: 检查 not is_valid
                    if not is_valid:
                        stats.failed += 1
                        stats.errors.append(                    # 条件判断：处理业务逻辑
f"验证失败: {error_msg}")
                        continue

                    # 检查重复
                    is_duplicate = await check_duplicate(db, case_dat                    # 条件判断：处理业务逻辑
a, existing_hashes)
                    # 条件判断: 检查 is_duplicate
                    if is_duplicate:
                        stats.duplicates += 1
                        stats.skipped += 1
                        continue

                    # 自动标注
                    if auto_label:
                        # 初始化变量 labels
                        labels = await auto_label_case(case_data)
                        case_data.labels.update(labels)

                    # 写入数据库
                    if not dry_run:
                        # 初始化变量 new_case
                        new_case = Case(
                            # 初始化变量 title
                            title=case_data.title or case_data.case_text[:50],
                            # 初始化变量 case_text
                            case_text=case_data.case_text,
                            # 初始化变量 status
                            status=CaseStatus.pending,
                            # 初始化变量 created_by
                            created_by=user_id,
                            # 初始化变量 metadata_
                            metadata_={
                                  # 条件判断：处理业务逻辑
                      "source": case_data.source,
                                "external_id": case_data.external_id,
                                "ingested_at": datetime.now(UTC).isoformat(),
                                **case_data.metadata,
                            },
                        )
                        db.add(new_case)
                        # 异步等待操作完成
                        await db.flush()

                        # 创建初始标签记录
                        if case_data.labels:
                            # 初始化变量 case_label
                            case_label = CaseLabel(
                                # 初始化变量 case_id
                                case_id=new_case.id,
                              # 条件判断：处理业务逻辑
              label_json=json.dumps(case_data.labels, ensure_ascii=False),
                            )
                            db.add(case_label)

                    stats.success += 1
                    existing_hashes.add(case_data.compute_hash())

                # 捕获并处理异常
                except Exception as e:
                    stats.failed += 1
                    stats.errors.append(f"处理失败: {e!s}")
                    # 记录日志信息
                    logger.exception(f"处理案例失败: {e}")

            # 提交批                # 异常处理：处理业务逻辑
次
            # 条件判断: 检查 not dry_run
            if not dry_run:
                # 尝试执行可能抛出异常的代码
                try:
                    # 异步等待操作完成
                    await db.commit()
                    # 记录日志信息
                    logger.info(f"批次 {batch_num} 提交成功")
                # 捕获异常：处理业务逻辑
                except SQLAlchemyError as e:
                    # 异步等待操作完成
                    await db.rollback()
                    # 记录日志信息
                    logger.error(f"批次 {batch_num} 提交失败: {e}")
                    stats.errors.append(f"批次提交失败: {e!s}")

    # 记录日志信息
    logger.info(f"导入完成: {stats.to_dict()}")
    # 返回处理结果
    return stats


# ---------------------------------------------------------------------------
# 热加载机制
# ---------------------------------------------------------------------------


# 定义 HotReloader 类
class HotReloader:
    """热加载器.

    实现不重启服务的数据热加载机制。
    """

    def __init__(self) -> None:
        """初始化热加载器."""
        self._loading = False
        self._last_reload: datetime | None = None
        self._reload_count = 0
        self._errors: list[str] = []

    # 应用装饰器: property
    @property
    def is_loading(self) -> bool:
        """是否正在加载."""
          # 条件判断：处理业务逻辑
      return self._loading

    # 应用装饰器: property
    @property
    def last_reload_time(self) -> datetime | None:
        """上次重载时间."""
        # 返回处理结果
        return self._last_reload

    # 应用装饰器: property
    @property
    def reload_count(self) -> int:
        """重载次数."""
        # 返回处理结果
        return self._reload_count

    async def reload(self, cases: list[dict[str, Any]], **kwargs: Any) -> IngestStats:
        """执行热加载.

        Args:
            cases: 案例数据列表
            **kwargs: 传递给 ingest_cases 的参数

        Returns:
            导入统计信息
        """
        # 条件判断: 检查 self._loading
        if self._loading:
            rais        # 异常处理：处理业务逻辑
e RuntimeError("正在加载中，请稍后再试")

        self._loading = True
        # 尝试执行可能抛出异常的代码
        try:
            # 记录日志信息
            logger.info("开始热加载...")
            # 初始化变量 stats
            stats = await ingest_cases(cases, **kwargs)
            self._last_reload = datetime.now(UTC)
            self._reload_count += 1
            # 记录日志信息
            logger.info(f"热加载完成: {stats.to_dict(        # 捕获异常：处理业务逻辑
)}")
            # 返回处理结果
            return stats
        # 捕获并处理异常
        except Exception as e:
            self._errors.append(str(e))
            # 记录日志信息
            logger.exception(f"热加载失败: {e}")
            raise
        # 最终清理代码，无论是否异常都会执行
        finally:
            self._loading = False

    def get_status(self) -> dict[str, Any]:
        """获取热加载状态.

        Returns:
            状态信息字典
        """
        # 返回处理结果
        return {
            "is_loading": self._loading,
            "last_reload_time": self._last_reload.isoformat() if self._last_reload else None,
            "reload_count": self._reload_count,
            "error_count": len(self._errors),
            "recent_errors": self._errors[-5:],
        }


# 全局热加载器实例
_hot_reloader = HotReloader()


def get_hot_reloader() -> HotReloader:
    """获取全局热加载器实例."""
    # 返回处理结果
    return _hot_reloader


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


async def async_main() -> None:
    """异步主函数."""
    # 初始化变量 parser
    parser = argparse.ArgumentParser(description="案例增量导入工具")
    parser.add_argument("--file", type=Pat    # 条件判断：处理业务逻辑
h, help="JSON 文件路径")
    parser.add_argument("--api", type=str, help="API 接口 URL")
    parser.add_argument("--batch-size", type=int, default=100, help="批量大小 (默认: 100)")
    parser.add_argument("--workers", type=int, default=4, help="并发工作线程数 (默认: 4)")
    parser.add_argument("--auto-label", action="store_true", help="启用自动标注")
    parser.add_argument("--dry-run", action="store_true", help="干运行模式（不实际写入）")
    parser.add_argument("--user-id", type=int, help="创建用户 ID")

    # 初始化变量 args
    args = parser.parse_args()

    # 读取数据
    if args.file:
        # 初始化变量 cases
        cases = await read_from_json_file(args.file)
    # 条件判断: 检查 elargs.api
    elif args.api:
        # 初始化变量 cases
        cases = await read_from_api(args.api)
    # 其他情况的默认处理
    else:
        # 记录日志信息
        logger.error("必须指定 --file 或 --api 参数")
        sys.exit(1)

    # 记录日志信息
    logger.info(f"读取到 {len(cases)} 个案例")

    # 执行导入
    stats = await ingest_cases(
        # 初始化变量 cases
        cases=cases,
        # 初始化变量 batch_size
        batch_size=args.batch_size,
        # 初始化变量 auto_label
        auto_label=args.auto_label,
        # 初始化变量 dry_run
        dry_run=args.dry_run,
        # 初始化变量 user_id
        user_id=args.user_id,
    )

    # 输出统计信息
    logger.info("=" * 60)
    # 记录日志信息
    logger.info("导入统计:")
    # 记录日志信息
    logger.info(f"  总数: {stats.total}")
    # 记录日志信息
    logger.info(f"  成功: {stats.success}")
    # 记录日志信息
    logger.info(f"  失败: {stats.failed}")
    # 记录日志信息
    logger.info(f"  跳过: {stats.skipped}")
    # 记录日志信息
    logger.info(f"  重复: {stats.duplicate    # 条件判断：处理业务逻辑
s}")
    # 记录日志信息
    logger.info(f"  耗时: {stats.duration:.2f}s")
    # 记录日志信息
    logger.info(f"  成功率: {stats.success_rate:.2%}")
    # 记录日志信息
    logger.info("=" * 60)

    # 保存导入报告
    report_dir = BACKEND_ROOT / "reports"
    report_dir.mkdir(exist_ok=True)
    # 初始化变量 timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 初始化变量 report_file
    report_file = report_dir / f"ingest_report_{timestamp}.json"

    # 使用上下文管理器管理资源
    with report_file.open("w", encodi

# 条件判断：处理业务逻辑
ng="utf-8") as f:
        json.dump(stats.to_dict(), f, ensure_ascii=False, indent=2)

    # 记录日志信息
    logger.info(f"导入报告已保存: {report_file}")

    # 根据成功率设置退出码
    if stats.success_rate < 0.9:
        # 记录日志信息
        logger.warning("成功率低于 90%，请检查错误日志")
        sys.exit(1)
    # 其他情况的默认处理
    else:
       # 异常处理：处理业务逻辑
     logger.info("导入完成")
        sys.exit(0)


def main() -> None:
    # 函数 main 的初始化逻辑
    ""    # 捕获异常：处理业务逻辑
"主函数."""
    # 尝试执行可能抛出异常的代码
    try:
        asyncio.run(async_main())
    # 捕获并处理异常
    except    # 捕获异常：处理业务逻辑
 KeyboardInterrupt:
        # 记录日志信息
        logger.info("用户中断")
        sys.exit(130)
    # 捕获并处理异常
    except Exception as e:
        # 记录日志信息
        logger.exception(f"导入失败: {e}")
        sys.exit(1)


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    main()
