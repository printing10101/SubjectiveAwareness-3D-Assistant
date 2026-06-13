"""数据库性能基准测试工具.

对比优化前后数据库操作的响应时间和并发性能。
测试覆盖：单表查询、复合条件查询、聚合统计、N+1 模拟。
"""

import argparse
import asyncio
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import async_engine, sync_engine
from app.models.analysis import Analysis
from app.models.case import Case
from app.models.system_log import SystemLog
from app.models.user import User


SessionLocal = sessionmaker(bind=sync_engine)


# ─── 测试场景定义 ──────────────────────────────────────────


def test_sync_query(db) -> float:
    """同步测试：按状态分页查询案件."""
    start = time.perf_counter()
    _ = db.query(Case).filter(Case.status == "pending").limit(20).all()
    return (time.perf_counter() - start) * 1000


def test_sync_aggregate(db) -> float:
    """同步测试：系统统计聚合查询."""
    start = time.perf_counter()
    row = db.execute(
        select(
            func.count(Case.id).label("total_cases"),
            func.count(Analysis.id).label("total_analyses"),
            func.count(User.id).label("total_users"),
        )
    ).first()
    _ = row.total_cases, row.total_analyses, row.total_users
    return (time.perf_counter() - start) * 1000


def test_sync_log_query(db) -> float:
    """同步测试：日志按级别+分页查询."""
    start = time.perf_counter()
    _ = (
        db.query(SystemLog)
        .filter(SystemLog.log_level == "INFO")
        .order_by(SystemLog.created_at.desc())
        .limit(50)
        .all()
    )
    return (time.perf_counter() - start) * 1000


def test_sync_insert(db) -> float:
    """同步测试：插入一条日志记录."""
    start = time.perf_counter()
    log = SystemLog(
        log_level="INFO",
        username="benchmark",
        action="benchmark_test",
        message=f"Benchmark {datetime.now(UTC).isoformat()}",
        created_at=datetime.now(UTC),
    )
    db.add(log)
    db.flush()
    elapsed = (time.perf_counter() - start) * 1000
    db.rollback()
    return elapsed


# ─── 异步测试场景 ──────────────────────────────────────────


async def test_async_query(db: AsyncSession) -> float:
    """异步测试：按状态分页查询案件."""
    start = time.perf_counter()
    await db.execute(
        select(Case).filter(Case.status == "pending").limit(20)
    )
    return (time.perf_counter() - start) * 1000


async def test_async_aggregate(db: AsyncSession) -> float:
    """异步测试：系统统计聚合查询."""
    start = time.perf_counter()
    row = (await db.execute(
        select(
            func.count(Case.id).label("total_cases"),
            func.count(Analysis.id).label("total_analyses"),
            func.count(User.id).label("total_users"),
        )
    )).first()
    _ = row.total_cases, row.total_analyses, row.total_users
    return (time.perf_counter() - start) * 1000


async def test_async_log_query(db: AsyncSession) -> float:
    """异步测试：日志按级别+分页查询."""
    start = time.perf_counter()
    await db.execute(
        select(SystemLog)
        .filter(SystemLog.log_level == "INFO")
        .order_by(SystemLog.created_at.desc())
        .limit(50)
    )
    return (time.perf_counter() - start) * 1000


# ─── 并发测试 ──────────────────────────────────────────────


async def _concurrent_worker(engine, iterations: int) -> list[float]:
    """并发工作协程."""
    latencies: list[float] = []
    for _ in range(iterations):
        async with AsyncSession(engine) as db:
            start = time.perf_counter()
            await db.execute(
                select(Case).filter(Case.status == "pending").limit(10)
            )
            latencies.append((time.perf_counter() - start) * 1000)
    return latencies


async def test_concurrent(engine, concurrency: int, iterations: int) -> dict:
    """并发测试：多协程同时查询.

    Args:
        engine: 异步引擎
        concurrency: 并发协程数
        iterations: 每个协程的执行次数

    Returns:
        dict: {"avg": float, "p50": float, "p95": float, "p99": float, "total": float}
    """
    total_start = time.perf_counter()
    tasks = [_concurrent_worker(engine, iterations) for _ in range(concurrency)]
    results = await asyncio.gather(*tasks)
    total_time = (time.perf_counter() - total_start) * 1000

    all_latencies = [lat for sublist in results for lat in sublist]
    sorted_latencies = sorted(all_latencies)

    def percentile(data: list[float], p: float) -> float:
        idx = int(len(data) * p / 100)
        return data[min(idx, len(data) - 1)]

    return {
        "avg": statistics.mean(all_latencies),
        "p50": percentile(sorted_latencies, 50),
        "p95": percentile(sorted_latencies, 95),
        "p99": percentile(sorted_latencies, 99),
        "total": total_time,
    }


# ─── 主测试流程 ────────────────────────────────────────────


def run_sync_benchmarks(iterations: int = 100) -> dict:
    """运行同步基准测试."""
    benchmarks = {
        "sync_query": [],
        "sync_aggregate": [],
        "sync_log_query": [],
        "sync_insert": [],
    }

    for _ in range(iterations):
        db = SessionLocal()
        try:
            benchmarks["sync_query"].append(test_sync_query(db))
            benchmarks["sync_aggregate"].append(test_sync_aggregate(db))
            benchmarks["sync_log_query"].append(test_sync_log_query(db))
            benchmarks["sync_insert"].append(test_sync_insert(db))
        finally:
            db.close()

    return benchmarks


async def run_async_benchmarks(iterations: int = 100) -> dict:
    """运行异步基准测试."""
    benchmarks = {
        "async_query": [],
        "async_aggregate": [],
        "async_log_query": [],
    }

    for _ in range(iterations):
        async with AsyncSession(async_engine) as db:
            benchmarks["async_query"].append(await test_async_query(db))
            benchmarks["async_aggregate"].append(await test_async_aggregate(db))
            benchmarks["async_log_query"].append(await test_async_log_query(db))

    return benchmarks


def print_results(title: str, data: dict) -> None:
    """格式化输出测试结果."""
    logger.info(f"\n{'='*60}")
    logger.info(f"  {title}")
    logger.info(f"{'='*60}")
    for name, latencies in data.items():
        if not latencies:
            continue
        sorted_l = sorted(latencies)
        p50 = sorted_l[len(sorted_l) // 2]
        p95 = sorted_l[int(len(sorted_l) * 0.95)]
        p99 = sorted_l[int(len(sorted_l) * 0.99)]
        logger.info(
            f"  {name:25s} | avg={statistics.mean(latencies):8.2f}ms | "
            f"p50={p50:8.2f}ms | p95={p95:8.2f}ms | p99={p99:8.2f}ms"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="数据库性能基准测试")
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="每个测试场景的迭代次数 (默认: 100)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="并发测试的协程数 (默认: 10)",
    )
    parser.add_argument(
        "--concurrent-iterations",
        type=int,
        default=20,
        help="每个并发协程的查询次数 (默认: 20)",
    )
    args = parser.parse_args()

    logger.info(f"数据库 URL: {settings.ASYNC_DATABASE_URL}")
    logger.info(f"连接池: size={settings.DB_POOL_SIZE}, overflow={settings.DB_MAX_OVERFLOW}")
    logger.info(f"迭代次数: {args.iterations}")

    # ── 同步测试 ──
    logger.info("\n运行同步基准测试...")
    sync_results = run_sync_benchmarks(args.iterations)
    print_results("同步查询基准", sync_results)

    # ── 异步测试 ──
    logger.info("\n运行异步基准测试...")
    async_results = asyncio.run(run_async_benchmarks(args.iterations))
    print_results("异步查询基准", async_results)

    # ── 并发测试 ──
    logger.info(f"\n运行并发测试 ({args.concurrency} 协程 × {args.concurrent_iterations} 次)...")
    concurrent_results = asyncio.run(
        test_concurrent(async_engine, args.concurrency, args.concurrent_iterations)
    )
    logger.info(f"\n{'='*60}")
    logger.info("  并发查询测试")
    logger.info(f"{'='*60}")
    logger.info(f"  并发数: {args.concurrency}")
    logger.info(f"  总查询数: {args.concurrency * args.concurrent_iterations}")
    logger.info(f"  平均延迟: {concurrent_results['avg']:.2f}ms")
    logger.info(f"  P50 延迟: {concurrent_results['p50']:.2f}ms")
    logger.info(f"  P95 延迟: {concurrent_results['p95']:.2f}ms")
    logger.info(f"  P99 延迟: {concurrent_results['p99']:.2f}ms")
    logger.info(f"  总耗时: {concurrent_results['total']:.2f}ms")


if __name__ == "__main__":
    main()
