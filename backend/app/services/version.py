"""版本管理与版本感知数据加载服务.

提供实体版本控制功能（prompt、rule、tag、conflict、case 的版本创建、查询、回滚、比较、删除），
以及与版本管理系统集成的数据加载功能（rules、tags、conflicts 的自动版本追踪和回滚）。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from loguru import logger

__all__ = [
    "EntityType",
    "VersionManager",
    "VersionedDataLoader",
    "create_version",
    "get_latest_version",
    "get_version",
    "get_version_manager",
    "get_versioned_data_loader",
    "list_versions",
    "rollback_version",
]

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
# 版本感知数据加载器
# ---------------------------------------------------------------------------


class VersionedDataLoader:
    """版本感知数据加载器.

    负责加载 rules、tags、conflicts 等数据，并自动创建版本记录。
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        """初始化数据加载器.

        Args:
            data_dir: 数据目录，默认为项目根目录下的 data 文件夹
        """
        self.data_dir = data_dir or Path(__file__).parents[3] / "data"
        self.version_manager = get_version_manager()

        logger.info(f"版本感知数据加载器初始化: data_dir={self.data_dir}")

    # -----------------------------------------------------------------------
    # 数据加载
    # -----------------------------------------------------------------------

    def load_rules(self, version: str = "latest") -> list[dict[str, Any]]:
        """加载规则数据.

        Args:
            version: 版本号，"latest" 表示最新版本

        Returns:
            规则列表
        """
        if version == "latest":
            rules_file = self.data_dir / "rules" / "v1.0.json"
            if not rules_file.exists():
                logger.warning(f"规则文件不存在: {rules_file}")
                return []

            with rules_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        else:
            versions = self.version_manager.list_versions("rule", limit=100)
            for v in versions:
                if v["version_id"] == version:
                    return v["data"].get("rules", [])

            logger.warning(f"未找到规则版本: {version}")
            return []

    def save_rules(
        self,
        rules: list[dict[str, Any]],
        user_id: str | None = None,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """保存规则数据并创建版本记录.

        Args:
            rules: 规则列表
            user_id: 操作用户 ID
            comment: 版本备注

        Returns:
            版本信息字典
        """
        rules_file = self.data_dir / "rules" / "v1.0.json"
        with rules_file.open("w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

        version = self.version_manager.create_version(
            entity_type="rule",
            entity_id="rules_v1",
            data={"rules": rules},
            user_id=user_id,
            comment=comment,
        )

        logger.info(f"规则已保存并创建版本: {version['version_id']}")
        return version

    def load_tags(self, version: str = "latest") -> list[dict[str, Any]]:
        """加载标签数据.

        Args:
            version: 版本号

        Returns:
            标签列表
        """
        if version == "latest":
            tags_file = self.data_dir / "tags" / "v1.0.json"
            if not tags_file.exists():
                logger.warning(f"标签文件不存在: {tags_file}")
                return []

            with tags_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        else:
            versions = self.version_manager.list_versions("tag", limit=100)
            for v in versions:
                if v["version_id"] == version:
                    return v["data"].get("tags", [])

            logger.warning(f"未找到标签版本: {version}")
            return []

    def save_tags(
        self,
        tags: list[dict[str, Any]],
        user_id: str | None = None,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """保存标签数据并创建版本记录.

        Args:
            tags: 标签列表
            user_id: 操作用户 ID
            comment: 版本备注

        Returns:
            版本信息字典
        """
        tags_file = self.data_dir / "tags" / "v1.0.json"
        with tags_file.open("w", encoding="utf-8") as f:
            json.dump(tags, f, ensure_ascii=False, indent=2)

        version = self.version_manager.create_version(
            entity_type="tag",
            entity_id="tags_v1",
            data={"tags": tags},
            user_id=user_id,
            comment=comment,
        )

        logger.info(f"标签已保存并创建版本: {version['version_id']}")
        return version

    def load_conflicts(self, version: str = "latest") -> list[dict[str, Any]]:
        """加载冲突数据.

        Args:
            version: 版本号

        Returns:
            冲突列表
        """
        if version == "latest":
            conflicts_file = self.data_dir / "conflicts" / "v1.0.json"
            if not conflicts_file.exists():
                logger.warning(f"冲突文件不存在: {conflicts_file}")
                return []

            with conflicts_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        else:
            versions = self.version_manager.list_versions("conflict", limit=100)
            for v in versions:
                if v["version_id"] == version:
                    return v["data"].get("conflicts", [])

            logger.warning(f"未找到冲突版本: {version}")
            return []

    def save_conflicts(
        self,
        conflicts: list[dict[str, Any]],
        user_id: str | None = None,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """保存冲突数据并创建版本记录.

        Args:
            conflicts: 冲突列表
            user_id: 操作用户 ID
            comment: 版本备注

        Returns:
            版本信息字典
        """
        conflicts_file = self.data_dir / "conflicts" / "v1.0.json"
        with conflicts_file.open("w", encoding="utf-8") as f:
            json.dump(conflicts, f, ensure_ascii=False, indent=2)

        version = self.version_manager.create_version(
            entity_type="conflict",
            entity_id="conflicts_v1",
            data={"conflicts": conflicts},
            user_id=user_id,
            comment=comment,
        )

        logger.info(f"冲突数据已保存并创建版本: {version['version_id']}")
        return version

    # -----------------------------------------------------------------------
    # 版本回滚
    # -----------------------------------------------------------------------

    def rollback_rules(self, version_id: str, user_id: str | None = None) -> bool:
        """回滚规则到指定版本.

        Args:
            version_id: 目标版本 ID
            user_id: 操作用户 ID

        Returns:
            是否回滚成功
        """
        try:
            target_version = self.version_manager.get_version("rule", version_id)
            if not target_version:
                logger.error(f"目标版本不存在: {version_id}")
                return False

            rules = target_version["data"].get("rules", [])
            self.save_rules(rules, user_id, f"回滚自版本 {version_id}")

            logger.info(f"规则已回滚到版本: {version_id}")
            return True
        except Exception as e:
            logger.exception(f"规则回滚失败: {e}")
            return False

    def rollback_tags(self, version_id: str, user_id: str | None = None) -> bool:
        """回滚标签到指定版本.

        Args:
            version_id: 目标版本 ID
            user_id: 操作用户 ID

        Returns:
            是否回滚成功
        """
        try:
            target_version = self.version_manager.get_version("tag", version_id)
            if not target_version:
                logger.error(f"目标版本不存在: {version_id}")
                return False

            tags = target_version["data"].get("tags", [])
            self.save_tags(tags, user_id, f"回滚自版本 {version_id}")

            logger.info(f"标签已回滚到版本: {version_id}")
            return True
        except Exception as e:
            logger.exception(f"标签回滚失败: {e}")
            return False

    def rollback_conflicts(self, version_id: str, user_id: str | None = None) -> bool:
        """回滚冲突数据到指定版本.

        Args:
            version_id: 目标版本 ID
            user_id: 操作用户 ID

        Returns:
            是否回滚成功
        """
        try:
            target_version = self.version_manager.get_version("conflict", version_id)
            if not target_version:
                logger.error(f"目标版本不存在: {version_id}")
                return False

            conflicts = target_version["data"].get("conflicts", [])
            self.save_conflicts(conflicts, user_id, f"回滚自版本 {version_id}")

            logger.info(f"冲突数据已回滚到版本: {version_id}")
            return True
        except Exception as e:
            logger.exception(f"冲突数据回滚失败: {e}")
            return False


# ---------------------------------------------------------------------------
# 全局实例
# ---------------------------------------------------------------------------

_version_manager: VersionManager | None = None
_data_loader: VersionedDataLoader | None = None


def get_version_manager() -> VersionManager:
    """获取全局版本管理器实例."""
    global _version_manager  # noqa: PLW0603
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager


def get_versioned_data_loader() -> VersionedDataLoader:
    """获取全局版本感知数据加载器实例."""
    global _data_loader  # noqa: PLW0603
    if _data_loader is None:
        _data_loader = VersionedDataLoader()
    return _data_loader


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


def get_latest_version(entity_type: EntityType, entity_id: str | int) -> dict[str, Any] | None:
    """获取最新版本信息的便捷函数."""
    return get_version_manager().get_latest_version(entity_type, entity_id)


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
