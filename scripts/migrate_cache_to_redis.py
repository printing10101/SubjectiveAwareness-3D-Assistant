"""文件缓存 → Redis 数据迁移工具.

将现有文件系统 JSON 缓存数据平滑迁移至 Redis。
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from loguru import logger

from app.config import AnalysisConfig
from app.utils.cache import NULL_MARKER, CACHE_DIR, RedisCache


async def migrate(
    redis_url: str = AnalysisConfig.REDIS_URL,
    cache_dir: str = CACHE_DIR,
    dry_run: bool = False,
) -> dict[str, int]:
    """将文件缓存数据迁移至 Redis.

    Args:
        redis_url: Redis 连接地址
        cache_dir: 文件缓存目录
        dry_run: 仅预览不执行

    Returns:
        dict: {"total": int, "migrated": int, "skipped": int, "expired": int}
    """
    redis_cache = RedisCache(redis_url)
    stats = {"total": 0, "migrated": 0, "skipped": 0, "expired": 0}

    if not os.path.isdir(cache_dir):
        logger.warning(f"缓存目录不存在: {cache_dir}")
        return stats

    json_files = sorted(
        f for f in os.listdir(cache_dir) if f.endswith(".json")
    )
    stats["total"] = len(json_files)

    if not json_files:
        logger.info("没有找到缓存文件，无需迁移。")
        return stats

    for filename in json_files:
        filepath = os.path.join(cache_dir, filename)
        key = filename.replace(".json", "")

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"跳过损坏文件 {filename}: {e}")
            stats["skipped"] += 1
            continue

        value = data.get("value")
        if value is None and data.get("value") is not None:
            pass
        elif value is None:
            value = NULL_MARKER

        ttl = data.get("ttl", AnalysisConfig.CACHE_TTL_SECONDS)
        timestamp = data.get("timestamp", 0)
        import time
        age = time.time() - timestamp
        if age > ttl:
            logger.debug(f"跳过过期文件 {filename} (年龄: {age:.0f}s, TTL: {ttl}s)")
            stats["expired"] += 1
            continue

        remaining_ttl = max(1, int(ttl - age))
        if dry_run:
            logger.info(f"[DRY-RUN] 将迁移: {key} (剩余TTL: {remaining_ttl}s)")
            stats["migrated"] += 1
        else:
            try:
                await redis_cache.set(key, value, ttl=remaining_ttl)
                logger.debug(f"已迁移: {key}")
                stats["migrated"] += 1
            except Exception as e:
                logger.error(f"迁移失败 {key}: {e}")
                stats["skipped"] += 1

    if not dry_run:
        await redis_cache.close()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="迁移文件缓存到 Redis")
    parser.add_argument(
        "--redis-url",
        default=AnalysisConfig.REDIS_URL,
        help=f"Redis 连接地址 (默认: {AnalysisConfig.REDIS_URL})",
    )
    parser.add_argument(
        "--cache-dir",
        default=CACHE_DIR,
        help=f"文件缓存目录 (默认: {CACHE_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际写入 Redis",
    )
    args = parser.parse_args()

    stats = asyncio.run(
        migrate(args.redis_url, args.cache_dir, dry_run=args.dry_run)
    )

    logger.info(
        f"迁移完成: 总计 {stats['total']} 个文件, "
        f"已迁移 {stats['migrated']}, "
        f"已跳过 {stats['skipped']}, "
        f"已过期 {stats['expired']}"
    )


if __name__ == "__main__":
    main()
