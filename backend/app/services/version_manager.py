"""版本管理服务模块.

提供实体版本控制功能，支持 prompt、rule、tag、conflict 等实体的版本管理。
包括版本创建、查询、回滚等功能。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from loguru import logger


# ---------------------------------------------------------------------------
# 类型定义
# ---------------------------------------------------------------------------

EntityType = Literal["prompt", "rule", "tag", "conflict", "case"]


# ---------------------------------------------------------------------------
# 版本管理核心类
# ---------------------------------------------------------------------------


class VersionManager:
    """版本管理器.

    负责管理各类实体的版本历史，支持版本创建、查询、回滚等操作。

    Attributes:
        data_dir: 数据存储根目录
        version_dir: 版本历史存储目录
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        """初始化版本管理器.

        Args:
            data_dir: 数据存储根目录，默认为项目根目录下的 data 文件夹
        """
        self.data_dir = data_dir or Path(__file__).parents[3] / "data"
        self.version_dir = self.data_dir / ".versions"
        self.version_dir.mkdir(parents=True, exist_ok=True)

        # 确保各实体类型的版本目录存在
        for entity_type in ["prompt", "rule", "tag", "conflict", "case"]:
            (self.version_dir / entity_type).mkdir(parents=True, exist_ok=True)

        logger.info(f"版本管理器初始化完成: data_dir={self.data_dir}, version_dir={self.version_dir}")

    # -----------------------------------------------------------------------
    # 版本创建
    # -----------------------------------------------------------------------

    def create_version(
        self,
        entity_type: EntityType,
        entity_id: str | int,
        data: dict[str, Any],
        user_id: str | None = None,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """创建新版本.

        Args:
            entity_type: 实体类型（prompt/rule/tag/conflict/case）
            entity_id: 实体唯一标识
            data: 实体数据（将被序列化为 JSON 存储）
            user_id: 操作用户 ID（可选）
            comment: 版本备注（可选）

        Returns:
            版本信息字典，包含 version_id, timestamp, entity_type, entity_id 等

        Example:
            >>> vm = VersionManager()
            >>> version = vm.create_version(
            ...     entity_type="rule",
            ...     entity_id="rule_001",
            ...     data={"name": "新规则", "content": "..."},
            ...     user_id="user_123",
            ...     comment="初始版本"
            ... )
        """
        timestamp = datetime.now(UTC)
        version_id = f"{entity_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        version_info = {
            "version_id": version_id,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "timestamp": timestamp.isoformat(),
            "user_id": user_id,
            "comment": comment,
            "data": data,
        }

        # 保存版本文件
        version_file = self.version_dir / entity_type / f"{version_id}.json"
        with version_file.open("w", encoding="utf-8") as f:
            json.dump(version_info, f, ensure_ascii=False, indent=2)

        logger.info(f"创建新版本: {entity_type}/{entity_id} -> {version_id}")
        return version_info

    # -----------------------------------------------------------------------
    # 版本查询
    # -----------------------------------------------------------------------

    def get_version(self, entity_type: EntityType, version_id: str) -> dict[str, Any] | None:
        """获取指定版本信息.

        Args:
            entity_type: 实体类型
            version_id: 版本 ID

        Returns:
            版本信息字典，不存在则返回 None
        """
        version_file = self.version_dir / entity_type / f"{version_id}.json"
        if not version_file.exists():
            logger.warning(f"版本不存在: {entity_type}/{version_id}")
            return None

        with version_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    def list_versions(
        self,
        entity_type: EntityType,
        entity_id: str | int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """列出实体的版本历史.

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID（可选，不指定则返回该类型所有版本）
            limit: 返回数量限制，默认 50

        Returns:
            版本信息列表，按时间倒序排列
        """
        entity_dir = self.version_dir / entity_type
        if not entity_dir.exists():
            return []

        versions = []
        for version_file in entity_dir.glob("*.json"):
            try:
                with version_file.open("r", encoding="utf-8") as f:
                    version_info = json.load(f)

                # 如果指定了 entity_id，则过滤
                if entity_id is not None and str(version_info["entity_id"]) != str(entity_id):
                    continue

                versions.append(version_info)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"版本文件解析失败: {version_file}, error={e}")
                continue

        # 按时间倒序排列
        versions.sort(key=lambda v: v["timestamp"], reverse=True)
        return versions[:limit]

    def get_latest_version(self, entity_type: EntityType, entity_id: str | int) -> dict[str, Any] | None:
        """获取实体的最新版本.

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID

        Returns:
            最新版本信息字典，不存在则返回 None
        """
        versions = self.list_versions(entity_type, entity_id, limit=1)
        return versions[0] if versions else None

    # -----------------------------------------------------------------------
    # 版本回滚
    # -----------------------------------------------------------------------

    def rollback(
        self,
        entity_type: EntityType,
        entity_id: str | int,
        version_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """回滚到指定版本.

        将实体的当前数据替换为指定版本的数据，并创建一个新的版本记录。

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            version_id: 目标版本 ID
            user_id: 操作用户 ID（可选）

        Returns:
            新版本信息字典

        Raises:
            ValueError: 目标版本不存在
        """
        # 获取目标版本
        target_version = self.get_version(entity_type, version_id)
        if not target_version:
            raise ValueError(f"目标版本不存在: {entity_type}/{version_id}")

        # 创建新版本（基于目标版本的数据）
        new_version = self.create_version(
            entity_type=entity_type,
            entity_id=entity_id,
            data=target_version["data"],
            user_id=user_id,
            comment=f"回滚自版本 {version_id}",
        )

        logger.info(f"版本回滚完成: {entity_type}/{entity_id} -> {version_id}")
        return new_version

    # -----------------------------------------------------------------------
    # 版本比较
    # -----------------------------------------------------------------------

    def compare_versions(
        self,
        entity_type: EntityType,
        version_id_1: str,
        version_id_2: str,
    ) -> dict[str, Any]:
        """比较两个版本的差异.

        Args:
            entity_type: 实体类型
            version_id_1: 第一个版本 ID
            version_id_2: 第二个版本 ID

        Returns:
            差异信息字典，包含 added, removed, modified 字段

        Raises:
            ValueError: 任一版本不存在
        """
        version_1 = self.get_version(entity_type, version_id_1)
        version_2 = self.get_version(entity_type, version_id_2)

        if not version_1:
            raise ValueError(f"版本不存在: {entity_type}/{version_id_1}")
        if not version_2:
            raise ValueError(f"版本不存在: {entity_type}/{version_id_2}")

        data_1 = version_1["data"]
        data_2 = version_2["data"]

        # 简单的键值比较
        added = {k: v for k, v in data_2.items() if k not in data_1}
        removed = {k: v for k, v in data_1.items() if k not in data_2}
        modified = {}

        for key in set(data_1.keys()) & set(data_2.keys()):
            if data_1[key] != data_2[key]:
                modified[key] = {"old": data_1[key], "new": data_2[key]}

        return {
            "version_1": version_id_1,
            "version_2": version_id_2,
            "added": added,
            "removed": removed,
            "modified": modified,
        }

    # -----------------------------------------------------------------------
    # 版本删除
    # -----------------------------------------------------------------------

    def delete_version(self, entity_type: EntityType, version_id: str) -> bool:
        """删除指定版本.

        Args:
            entity_type: 实体类型
            version_id: 版本 ID

        Returns:
            是否删除成功
        """
        version_file = self.version_dir / entity_type / f"{version_id}.json"
        if not version_file.exists():
            logger.warning(f"版本不存在，无法删除: {entity_type}/{version_id}")
            return False

        version_file.unlink()
        logger.info(f"删除版本: {entity_type}/{version_id}")
        return True

    # -----------------------------------------------------------------------
    # 批量操作
    # -----------------------------------------------------------------------

    def create_backup(self, entity_type: EntityType, entity_id: str | int) -> str:
        """创建实体当前状态的备份.

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID

        Returns:
            备份版本 ID
        """
        # 这里应该从实际数据源读取，简化实现中直接返回空数据
        # 实际使用时需要结合具体的实体加载逻辑
        logger.warning(f"create_backup 需要结合具体实体加载逻辑实现: {entity_type}/{entity_id}")
        return ""

    def restore_from_backup(self, entity_type: EntityType, version_id: str) -> bool:
        """从备份恢复实体.

        Args:
            entity_type: 实体类型
            version_id: 备份版本 ID

        Returns:
            是否恢复成功
        """
        logger.warning(f"restore_from_backup 需要结合具体实体恢复逻辑实现: {entity_type}/{version_id}")
        return False


# ---------------------------------------------------------------------------
# 全局实例
# ---------------------------------------------------------------------------

_version_manager: VersionManager | None = None


def get_version_manager() -> VersionManager:
    """获取全局版本管理器实例."""
    global _version_manager  # noqa: PLW0603
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------


def create_version(
    entity_type: EntityType,
    entity_id: str | int,
    data: dict[str, Any],
    user_id: str | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    """创建新版本的便捷函数."""
    return get_version_manager().create_version(entity_type, entity_id, data, user_id, comment)


def get_version(entity_type: EntityType, version_id: str) -> dict[str, Any] | None:
    """获取版本信息的便捷函数."""
    return get_version_manager().get_version(entity_type, version_id)


def list_versions(
    entity_type: EntityType,
    entity_id: str | int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """列出版本历史的便捷函数."""
    return get_version_manager().list_versions(entity_type, entity_id, limit)


def rollback_version(
    entity_type: EntityType,
    entity_id: str | int,
    version_id: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """回滚版本的便捷函数."""
    return get_version_manager().rollback(entity_type, entity_id, version_id, user_id)
