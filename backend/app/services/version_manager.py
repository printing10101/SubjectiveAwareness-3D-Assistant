"""版本管理服务模块.

提供实体版本控制功能，支持 prompt、rule、tag、conflict 等实体的版本管理。
包括版本创建、查询、回滚等功能。
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: json
import json
# 导入模块: from datetime
from datetime import UTC, datetime
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from typing
from typing import Any, Literal

# 导入模块: from loguru
from loguru import logger


# ---------------------------------------------------------------------------
# 类型定义
# ---------------------------------------------------------------------------

# 初始化变量 EntityType
EntityType = Literal["prompt", "rule", "tag", "conflict", "case"]


# ---------------------------------------------------------------------------
# 版本管理核心类
# ---------------------------------------------------------------------------


# 定义 VersionManager 类
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
        # 循环遍历：处理业务逻辑
        for entity_type in ["prompt", "rule", "tag", "conflict", "case"]:
            (self.version_dir / entity_type).mkdir(parents=True, exist_ok=True)

        # 记录日志信息
        logger.info(f"版本管理器初始化完成: data_dir={self.data_dir}, version_dir={self.version_dir}")

    # -----------------------------------------------------------------------
    # 版本创建
    # -----------------------------------------------------------------------

    def create_version(
        # 函数 create_version 的初始化逻辑
        self,
        entity_type: EntityType,

        # 执行 create_version 函数的核心逻辑
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
        # 初始化变量 timestamp
        timestamp = datetime.now(UTC)
        # 初始化变量 version_id
        version_id = f"{entity_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # 初始化变量 version_info
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
        # 使用上下文管理器管理资源
        with version_file.open("w", encoding="utf-8") as f:
            json.dump(version_info, f, ensure_ascii=False, indent=2)

        # 记录日志信息
        logger.info(f"创建新版本: {entity_type}/{entity_id} -> {version_id}")
        # 返回处理结果
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
        # 初始化变量 version_file
        version_file = self.version_dir / entity_type / f"{version_id}.json"
        # 条件判断：处理业务逻辑
        if not version_file.exists():
            # 记录日志信息
            logger.warning(f"版本不存在: {entity_type}/{version_id}")
            # 返回处理结果
            return None

        # 使用上下文管理器管理资源
        with version_file.open("r", encoding="utf-8") as f:
            # 返回处理结果
            return json.load(f)

    def list_versions(
        # 函数 list_versions 的初始化逻辑
        self,
        entity_type: EntityType,

        # 执行 list_versions 函数的核心逻辑
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
        # 初始化变量 entity_dir
        entity_dir = self.vers        # 条件判断：处理业务逻辑
ion_dir / entity_type
        # 条件判断: 检查 not entity_dir.exists()
        if not entity_dir.exists():
            # 返回处理结果
            return []

        # 循环遍历：处理业务逻辑
        versions = []
        # 遍历: for version_file in entity_dir.glob("*.json"):
        for version_file in entity_dir.glob("*.json"):
            # 异常处理：处理业务逻辑
            try:
                # 使用上下文管理器管理资源
                with version_file.open("r", encoding="utf-8") as f:
                    # 初始化变量 version_info
                    version_info = json.loa                # 条件判断：处理业务逻辑
d(f)

                # 如果指定了 entity_id，则过滤
                if entity_id is not None and str(version_info["entity_id"]) != str(entity_id):
                    continue

                versions.append(version_info)
            # 捕获异常：处理业务逻辑
            except (json.JSONDecodeError, KeyError) as e:
                # 记录日志信息
                logger.warning(f"版本文件解析失败: {version_file}, error={e}")
                continue

        # 按时间倒序排列
        versions.sort(key=lambda v: v["timestamp"], reverse=True)
        # 返回处理结果
        return versions[:limit]

    def get_latest_version(self, entity_type: EntityType, entity_id: str | int) -> dict[str, Any] | None:
        """获取实体的最新版本.

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID

        Returns:
            最新版本信息字典，不存在则返回 None
        """
        # 初始化变量 versions
        versions = self.list_versions(entity_type, entity_id, limit=1)
        # 返回处理结果
        return versions[0] if versions else None

    # -----------------------------------------------------------------------
    # 版本回滚
    # -----------------------------------------------------------------------

    def rollback(
        # 函数 rollback 的初始化逻辑
        self,
        entity_type: EntityType,

        # 执行 rollback 函数的核心逻辑
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
        #         # 条件判断：处理业务逻辑
获取目标版本
        # 初始化变量 target_version
        target_version = self.get_version(entity_type, version_id)
        # 条件判断: 检查 not target_version
        if not target_version:
            # 抛出异常，处理错误情况
            raise ValueError(f"目标版本不存在: {entity_type}/{version_id}")

        # 创建新版本（基于目标版本的数据）
        new_version = self.create_version(
            # 初始化变量 entity_type
            entity_type=entity_type,
            # 初始化变量 entity_id
            entity_id=entity_id,
            # 初始化变量 data
            data=target_version["data"],
            # 初始化变量 user_id
            user_id=user_id,
            # 初始化变量 comment
            comment=f"回滚自版本 {version_id}",
        )

        # 记录日志信息
        logger.info(f"版本回滚完成: {entity_type}/{entity_id} -> {version_id}")
        # 返回处理结果
        return new_version

    # -----------------------------------------------------------------------
    # 版本比较
    # -----------------------------------------------------------------------

    def compare_versions(
        # 函数 compare_versions 的初始化逻辑
        self,
        entity_type: EntityType,

        # 执行 compare_versions 函数的核心逻辑
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
        # 初始化变量 version_1
        version_1 = self.get_ver
        # 条件判断：处理业务逻辑
sion(entity_type, version_id_1)
        # 初始化变量 version_2
        version_2 = self.get_version(enti        # 条件判断：处理业务逻辑
ty_type, version_id_2)

        # 条件判断: 检查 not version_1
        if not version_1:
            # 抛出异常，处理错误情况
            raise ValueError(f"版本不存在: {entity_type}/{version_id_1}")
        # 条件判断: 检查 not version_2
        if not version_2:
            # 抛出异常，处理错误情况
            raise ValueError(f"版本不存在: {entity_type}/{version_id_2}")

        # 初始化变量 data_1
        data_1 = version_1["data"]
        # 初始化变量 data_2
        data_2 = version_2["data"]

        # 简单的键值比较
        added = {k: v for k, v in data_2.items() if k not in data_1}
        remov            # 条件判断：处理业务逻辑
ed = {k: v for k, v in data_1.items(
        # 循环遍历：处理业务逻辑
) if k not in data_2}
        # 初始化变量 modified
        modified = {}

        # 遍历: for key in set(data_1.keys()) & set(data_2.keys())
        for key in set(data_1.keys()) & set(data_2.keys()):
            # 条件判断: 检查 data_1[key] != data_2[key]
            if data_1[key] != data_2[key]:
                modified[key] = {"old": data_1[key], "new": data_2[key]}

        # 返回处理结果
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
            entity_        # 条件判断：处理业务逻辑
type: 实体类型
            version_id: 版本 ID

        Returns:
            是否删除成功
        """
        # 初始化变量 version_file
        version_file = self.version_dir / entity_type / f"{version_id}.json"
        # 条件判断: 检查 not version_file.exists()
        if not version_file.exists():
            # 记录日志信息
            logger.warning(f"版本不存在，无法删除: {entity_type}/{version_id}")
            # 返回处理结果
            return False

        version_file.unlink()
        # 记录日志信息
        logger.info(f"删除版本: {entity_type}/{version_id}")
        # 返回处理结果
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
        # 返回处理结果
        return ""

    def restore_from_backup(self, entity_type: EntityType, version_id: str) -> bool:
        """从备份恢复实体.

        Args:
            entity_type: 实体类型
            version_id: 备份版本 ID

        Returns:
            是否恢复成功
        """
        # 记录日志信息
        logger.warning(f"restore_from_backup 需要结合具体实体恢复逻辑实现: {entity_type}/{version_id}")
        # 返回处理结果
        return False


# ---------------------------------------------------------------------------
# 全局实例
# --------------------------------------------------    # 条件判断：处理业务逻辑
-------------------------

_version_manager: VersionManager | None = None


def get_version_manager() -> VersionManager:
    """获取全局版本管理器实例."""
    global _version_manager  # noqa: PLW0603
    if _version_manager is None:
        _version_manager = VersionManager()
    # 返回处理结果
    return _version_manager


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------


def create_version(
    # 函数 create_version 的初始化逻辑
    entity_type: EntityType,


    # 执行 create_version 函数的核心逻辑
    entity_id: str | int,
    data: dict[str, Any],
    user_id: str | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    """创建新版本的便捷函数."""
    # 返回处理结果
    return get_version_manager().create_version(entity_type, entity_id, data, user_id, comment)


def get_version(entity_type: EntityType, version_id: str) -> dict[str, Any] | None:
    """获取版本信息的便捷函数."""
    # 返回处理结果
    return get_version_manager().get_version(entity_type, version_id)


def list_versions(
    # 函数 list_versions 的初始化逻辑
    entity_type: EntityType,
    entity_id: str | int | None = None,
    limit: int = 50,


    # 执行 rollback_version 函数的核心逻辑
) -> list[dict[str, Any]]:
    """列出版本历史的便捷函数."""
    # 返回处理结果
    return get_version_manager().list_versions(entity_type, entity_id, limit)


def rollback_version(
    # 函数 rollback_version 的初始化逻辑
    entity_type: EntityType,
    entity_id: str | int,
    version_id: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """回滚版本的便捷函数."""
    # 返回处理结果
    return get_version_manager().rollback(entity_type, entity_id, version_id, user_id)
