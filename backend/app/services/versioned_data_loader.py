"""版本感知数据加载器.

提供与版本管理系统集成的数据加载功能，支持自动版本追踪和回滚。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from app.services.version_manager import get_version_manager


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
            # 加载当前版本
            rules_file = self.data_dir / "rules" / "v1.0.json"
            if not rules_file.exists():
                logger.warning(f"规则文件不存在: {rules_file}")
                return []

            with rules_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # 加载指定版本
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
        # 保存当前版本
        rules_file = self.data_dir / "rules" / "v1.0.json"
        with rules_file.open("w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

        # 创建版本记录
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
            # 获取目标版本数据
            target_version = self.version_manager.get_version("rule", version_id)
            if not target_version:
                logger.error(f"目标版本不存在: {version_id}")
                return False

            # 恢复数据
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

_data_loader: VersionedDataLoader | None = None


def get_versioned_data_loader() -> VersionedDataLoader:
    """获取全局版本感知数据加载器实例."""
    global _data_loader  # noqa: PLW0603
    if _data_loader is None:
        _data_loader = VersionedDataLoader()
    return _data_loader
