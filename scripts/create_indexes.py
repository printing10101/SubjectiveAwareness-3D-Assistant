"""数据库索引创建脚本.

根据模型定义创建所有优化的索引，包括复合索引。
支持创建前验证和创建后确认。
"""

import argparse
import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


# 索引定义：表名 → (索引名, 列定义, 是否唯一)
INDEX_DEFINITIONS: dict[str, list[tuple[str, str, bool]]] = {
    "cases": [
        ("ix_cases_status_created_at", "status, created_at", False),
    ],
    "analyses": [
        ("ix_analyses_case_id_created_at", "case_id, created_at", False),
    ],
    "system_logs": [
        ("ix_system_logs_level_created_at", "log_level, created_at", False),
    ],
}


async def get_existing_indexes(engine, table_name: str) -> set[str]:
    """获取指定表中已存在的索引名称."""
    async with engine.connect() as conn:
        if "postgresql" in str(engine.url):
            result = await conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = 'public' AND tablename = :table"
                ),
                {"table": table_name},
            )
        else:
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'index' AND tbl_name = :table"
                ),
                {"table": table_name},
            )
        return {row[0] for row in await result.fetchall()}


async def create_index(
    engine,
    table_name: str,
    index_name: str,
    columns: str,
    unique: bool = False,
) -> bool:
    """创建单个索引.

    Args:
        engine: 异步数据库引擎
        table_name: 表名
        index_name: 索引名
        columns: 列定义（逗号分隔）
        unique: 是否唯一索引

    Returns:
        bool: 创建成功返回 True
    """
    unique_keyword = "UNIQUE " if unique else ""
    sql = (
        f"CREATE {unique_keyword}INDEX IF NOT EXISTS {index_name} "
        f"ON {table_name} ({columns})"
    )

    async with engine.connect() as conn:
        async with conn.begin():
            try:
                await conn.execute(text(sql))
                return True
            except Exception as e:
                logger.error(f"创建索引失败 {index_name}: {e}")
                return False


async def create_all_indexes(
    database_url: str = settings.ASYNC_DATABASE_URL,
    dry_run: bool = False,
) -> dict[str, str]:
    """创建所有优化索引.

    Args:
        database_url: 数据库连接 URL
        dry_run: 试运行模式

    Returns:
        dict: {"created", "skipped", "failed"} 索引名 → 状态
    """
    engine = create_async_engine(database_url)
    results: dict[str, str] = {}

    try:
        for table_name, indexes in INDEX_DEFINITIONS.items():
            existing = await get_existing_indexes(engine, table_name)
            for index_name, columns, unique in indexes:
                if index_name in existing:
                    logger.info(f"索引已存在，跳过: {index_name} (ON {table_name})")
                    results[index_name] = "skipped"
                    continue

                if dry_run:
                    logger.info(
                        f"[DRY-RUN] 将创建索引: {index_name} ON {table_name} ({columns})"
                    )
                    results[index_name] = "dry_run"
                else:
                    success = await create_index(
                        engine, table_name, index_name, columns, unique
                    )
                    if success:
                        logger.info(f"索引已创建: {index_name} ON {table_name} ({columns})")
                        results[index_name] = "created"
                    else:
                        results[index_name] = "failed"
    finally:
        await engine.dispose()

    return results


async def verify_indexes(database_url: str) -> dict[str, bool]:
    """验证索引是否存在.

    Args:
        database_url: 数据库连接 URL

    Returns:
        dict: 索引名 → 是否存在
    """
    engine = create_async_engine(database_url)
    verification: dict[str, bool] = {}

    try:
        for table_name, indexes in INDEX_DEFINITIONS.items():
            existing = await get_existing_indexes(engine, table_name)
            for index_name, *_ in indexes:
                verification[index_name] = index_name in existing
    finally:
        await engine.dispose()

    return verification


def main() -> None:
    parser = argparse.ArgumentParser(description="创建数据库优化索引")
    parser.add_argument(
        "--database-url",
        default=settings.ASYNC_DATABASE_URL,
        help=f"数据库连接 URL (默认: {settings.ASYNC_DATABASE_URL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式，仅预览不执行",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="仅验证索引是否存在",
    )
    args = parser.parse_args()

    if args.verify:
        verification = asyncio.run(verify_indexes(args.database_url))
        all_ok = True
        for name, exists in verification.items():
            status = "✓ 存在" if exists else "✗ 缺失"
            if not exists:
                all_ok = False
            logger.info(f"  {name}: {status}")
        if all_ok:
            logger.info("所有索引验证通过。")
        else:
            logger.warning("部分索引缺失，请运行 --dry-run 预览后执行创建。")
    else:
        results = asyncio.run(
            create_all_indexes(args.database_url, dry_run=args.dry_run)
        )
        created = sum(1 for v in results.values() if v == "created")
        skipped = sum(1 for v in results.values() if v == "skipped")
        failed = sum(1 for v in results.values() if v == "failed")
        logger.info(
            f"索引创建完成: 新建 {created}, 已存在 {skipped}, 失败 {failed}"
        )


if __name__ == "__main__":
    main()
