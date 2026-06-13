"""SQLite → PostgreSQL 数据库迁移工具.

将 SQLite 数据库中的所有表和数据完整迁移至 PostgreSQL。
支持试运行模式预览迁移内容，无需实际写入。
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
from app.database import Base


# 按外键依赖顺序排列的表名，确保迁移时不违反约束
TABLE_ORDER: list[str] = [
    "users",
    "cases",
    "analyses",
    "legal_rules",
    "model_versions",
    "system_logs",
]


async def get_table_names(engine) -> list[str]:
    """获取源数据库中存在的表名."""
    async with engine.connect() as conn:
        if "sqlite" in str(engine.url):
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            )
            return sorted(row[0] for row in await result.fetchall() if row[0] in TABLE_ORDER)
        else:
            result = await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            return sorted(row[0] for row in await result.fetchall() if row[0] in TABLE_ORDER)


async def migrate_table(
    source_url: str,
    target_url: str,
    table_name: str,
    dry_run: bool = False,
) -> dict[str, int]:
    """迁移单张表的数据.

    Args:
        source_url: 源 SQLite 数据库 URL
        target_url: 目标 PostgreSQL 数据库 URL
        table_name: 表名
        dry_run: 试运行模式

    Returns:
        dict: {"migrated": int, "failed": int}
    """
    source_engine = create_async_engine(source_url)
    target_engine = create_async_engine(target_url)
    stats = {"migrated": 0, "failed": 0}

    try:
        async with source_engine.connect() as src_conn:
            result = await src_conn.execute(text(f"SELECT * FROM {table_name}"))
            columns = list(result.keys())
            rows = await result.fetchall()

        if not rows:
            logger.info(f"表 {table_name}: 无数据，跳过。")
            return stats

        col_list = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])

        if dry_run:
            logger.info(f"[DRY-RUN] 将迁移表 {table_name}: {len(rows)} 行")
            stats["migrated"] = len(rows)
        else:
            async with target_engine.connect() as tgt_conn:
                async with tgt_conn.begin():
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        try:
                            await tgt_conn.execute(
                                text(
                                    f"INSERT INTO {table_name} ({col_list}) "
                                    f"VALUES ({placeholders}) "
                                    f"ON CONFLICT DO NOTHING"
                                ),
                                row_dict,
                            )
                            stats["migrated"] += 1
                        except Exception as e:
                            logger.warning(f"迁移行失败 (表 {table_name}): {e}")
                            stats["failed"] += 1

            logger.info(
                f"表 {table_name}: 已迁移 {stats['migrated']} 行, "
                f"失败 {stats['failed']} 行"
            )
    finally:
        await source_engine.dispose()
        await target_engine.dispose()

    return stats


async def ensure_schema(target_url: str) -> None:
    """在目标 PostgreSQL 数据库中创建所有表结构."""
    target_engine = create_async_engine(target_url)
    try:
        async with target_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("目标数据库表结构已创建/验证。")
    finally:
        await target_engine.dispose()


async def migrate_all(
    source_url: str,
    target_url: str,
    dry_run: bool = False,
) -> dict[str, int]:
    """执行完整迁移流程.

    Args:
        source_url: 源数据库 URL（SQLite）
        target_url: 目标数据库 URL（PostgreSQL）
        dry_run: 试运行模式

    Returns:
        dict: {"migrated": int, "failed": int}
    """
    if "asyncpg" not in target_url:
        logger.error("目标数据库 URL 必须使用 asyncpg 驱动 (postgresql+asyncpg://...)")
        return {"migrated": 0, "failed": 0}

    if "aiosqlite" not in source_url:
        source_url = source_url.replace("sqlite://", "sqlite+aiosqlite://")

    total_stats = {"migrated": 0, "failed": 0}

    if not dry_run:
        await ensure_schema(target_url)

    tables = await get_table_names(create_async_engine(source_url))
    logger.info(f"发现 {len(tables)} 个数据表: {tables}")

    for table in tables:
        stats = await migrate_table(source_url, target_url, table, dry_run=dry_run)
        total_stats["migrated"] += stats["migrated"]
        total_stats["failed"] += stats["failed"]

    return total_stats


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite → PostgreSQL 数据库迁移")
    parser.add_argument(
        "--source-url",
        default=settings.DATABASE_URL,
        help=f"源数据库 URL (默认: {settings.DATABASE_URL})",
    )
    parser.add_argument(
        "--target-url",
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/legal_analysis",
        help="目标 PostgreSQL URL (默认: postgresql+asyncpg://postgres:postgres@localhost:5432/legal_analysis)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式，仅预览不实际写入",
    )
    args = parser.parse_args()

    logger.info(f"源数据库: {args.source_url}")
    logger.info(f"目标数据库: {args.target_url}")
    if args.dry_run:
        logger.info("模式: 试运行（不会写入数据）")

    stats = asyncio.run(
        migrate_all(args.source_url, args.target_url, dry_run=args.dry_run)
    )

    logger.info(
        f"迁移完成: 总计 {stats['migrated']} 行已迁移, {stats['failed']} 行失败"
    )

    if stats["failed"] > 0:
        logger.warning("存在迁移失败的行，请检查日志。")


if __name__ == "__main__":
    main()
