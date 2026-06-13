"""提示词管理器模块.

提供从JSON文件加载提示词、运行时热重载、使用统计追踪等能力。
将硬编码提示词迁移到外部配置文件，支持不重启应用更新提示词内容。
"""

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger


DEFAULT_PROMPTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "prompts.json",
)


class PromptManager:
    """提示词管理器.

    从JSON配置文件加载系统提示词和维度提示词，
    支持运行时热重载和使用统计追踪。

    Attributes:
        _prompts: 当前加载的提示词字典
        _stats: 各提示词的使用统计信息
        _lock: 线程安全锁，保护提示词加载和统计更新
        _file_path: 提示词JSON文件的路径

    Example:
        >>> manager = PromptManager()
        >>> system_prompt = manager.get_system_prompt()
        >>> dim1 = manager.get_dimension_prompt("dimension1")
        >>> stats = manager.get_stats()
    """

    def __init__(self, prompts_file: str | None = None) -> None:
        """初始化提示词管理器.

        Args:
            prompts_file: 提示词JSON文件路径，默认使用项目内置配置

        Raises:
            FileNotFoundError: 提示词文件不存在且无法使用默认路径
        """
        self._prompts: dict[str, Any] = {}
        self._stats: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._file_path = prompts_file or DEFAULT_PROMPTS_FILE
        self._load_prompts()

    def _load_prompts(self) -> None:
        """从JSON文件加载提示词到内存.

        内部方法，不直接暴露给外部调用。
        加载过程包含完整的错误处理：
        - 文件不存在 → 记录错误并初始化为空字典
        - JSON格式错误 → 记录错误并初始化为空字典
        - 结构验证失败 → 记录警告日志

        Raises:
            不会向外抛出异常，所有异常在内部捕获并记录日志
        """
        try:
            file_path = Path(self._file_path)
            if not file_path.exists():
                logger.error(
                    "提示词文件不存在: {}，请检查配置路径",
                    self._file_path,
                )
                self._prompts = {}
                return

            if file_path.stat().st_size == 0:
                logger.error(
                    "提示词文件为空: {}",
                    self._file_path,
                )
                self._prompts = {}
                return

            with open(file_path, encoding="utf-8") as f:
                self._prompts = json.load(f)

            self._validate_prompts_structure()
            logger.info(
                "提示词加载成功 | 文件: {} | meta版本: {}",
                self._file_path,
                self._prompts.get("meta", {}).get("version", "未知"),
            )
        except json.JSONDecodeError as e:
            logger.error("提示词JSON解析失败: {} | 错误: {}", self._file_path, e)
            self._prompts = {}
        except PermissionError as e:
            logger.error("提示词文件权限不足: {} | 错误: {}", self._file_path, e)
            self._prompts = {}
        except OSError as e:
            logger.error("读取提示词文件失败: {} | 错误: {}", self._file_path, e)
            self._prompts = {}
        except Exception as e:  # noqa: BLE001
            logger.error(
                "加载提示词时发生未预期异常: {} | 错误: {}",
                self._file_path,
                e,
            )
            self._prompts = {}

    def _validate_prompts_structure(self) -> None:
        """验证提示词JSON结构的完整性.

        检查必需的顶层字段是否存在，记录缺少的字段。
        仅发出警告，不会中断加载流程。
        """
        required_top = ["meta", "system", "dimensions"]
        missing = [k for k in required_top if k not in self._prompts]
        if missing:
            logger.warning("提示词结构缺少顶层字段: {}", missing)

        if "system" in self._prompts:
            system = self._prompts["system"]
            if not isinstance(system, dict) or "content" not in system:
                logger.warning("system提示词缺少content字段")

        if "dimensions" in self._prompts:
            dims = self._prompts["dimensions"]
            if not isinstance(dims, dict):
                logger.warning("dimensions字段不是有效的字典对象")
            else:
                for dim_name in list(dims.keys()):
                    if "content" not in dims[dim_name]:
                        logger.warning("维度 {} 缺少content字段", dim_name)

    def reload_prompts(self) -> bool:
        """运行时重载提示词，无需重启应用.

        线程安全的重载操作，使用锁保护整个重载过程。
        重载前会保留旧提示词副本，若新提示词加载失败则回滚。

        Returns:
            True表示重载成功，False表示重载失败（已回滚到旧版本）

        Example:
            >>> manager = PromptManager()
            >>> success = manager.reload_prompts()
            >>> if success:
            ...     print("提示词已更新")
        """
        old_prompts = self._prompts

        with self._lock:
            logger.info("开始重载提示词 | 文件: {}", self._file_path)
            self._load_prompts()

            if not self._prompts:
                logger.warning(
                    "新提示词加载为空，回滚到旧版本 | 文件: {}",
                    self._file_path,
                )
                self._prompts = old_prompts
                return False

            logger.info("提示词重载成功 | 文件: {}", self._file_path)
            return True

    def _record_usage(self, key: str) -> None:
        """记录提示词使用信息.

        线程安全地更新指定提示词的调用次数和最近调用时间。

        Args:
            key: 提示词标识键，格式为 "category:name"
        """
        with self._lock:
            now = datetime.now(UTC).isoformat()
            if key not in self._stats:
                self._stats[key] = {
                    "call_count": 0,
                    "first_called_at": now,
                }
            self._stats[key]["call_count"] += 1
            self._stats[key]["last_called_at"] = now

    def get_system_prompt(
        self,
        default: str | None = None,
    ) -> str:
        """获取系统提示词.

        Args:
            default: 当系统提示词不存在时返回的默认值。
                     未提供时抛出ValueError。

        Returns:
            系统提示词文本

        Raises:
            ValueError: 系统提示词不存在且未提供默认值

        Example:
            >>> manager = PromptManager()
            >>> prompt = manager.get_system_prompt()
            >>> prompt = manager.get_system_prompt(default="默认提示词")
        """
        self._record_usage("system")
        try:
            return self._prompts["system"]["content"]
        except (KeyError, TypeError):
            if default is not None:
                logger.warning("系统提示词不存在，使用默认值")
                return default
            logger.error("系统提示词不存在且未提供默认值")
            msg = "系统提示词不存在，请检查 prompts.json 中 system.content 字段"
            raise ValueError(msg) from None

    def get_dimension_prompt(
        self,
        dimension: str = "dimension1",
        default: str | None = None,
    ) -> str:
        """获取指定维度的分析提示词.

        Args:
            dimension: 维度标识，可选 dimension1/dimension2/dimension3，
                       默认 dimension1
            default: 当维度提示词不存在时返回的默认值。
                     未提供时抛出ValueError。

        Returns:
            维度提示词文本

        Raises:
            ValueError: 维度值不在有效范围内（dimension1~3）
            ValueError: 维度提示词不存在且未提供默认值

        Example:
            >>> manager = PromptManager()
            >>> dim1 = manager.get_dimension_prompt("dimension1")
            >>> dim2 = manager.get_dimension_prompt("dimension2")
            >>> dim3 = manager.get_dimension_prompt("dimension3")
        """
        valid_dimensions = {"dimension1", "dimension2", "dimension3"}
        if dimension not in valid_dimensions:
            msg = (
                f"无效的维度参数: {dimension}，"
                f"有效值为: {', '.join(sorted(valid_dimensions))}"
            )
            raise ValueError(msg)

        self._record_usage(f"dimension:{dimension}")
        try:
            return self._prompts["dimensions"][dimension]["content"]
        except (KeyError, TypeError):
            if default is not None:
                logger.warning(
                    "维度提示词 {} 不存在，使用默认值",
                    dimension,
                )
                return default
            logger.error("维度提示词 {} 不存在且未提供默认值", dimension)
            msg = (
                f"维度提示词 {dimension} 不存在，"
                f"请检查 prompts.json 中 dimensions.{dimension}.content 字段"
            )
            raise ValueError(msg) from None

    def get_specialized_prompt(
        self,
        name: str,
        default: str | None = None,
    ) -> str:
        """获取专用提示词（如相似案例推荐、量刑建议等）.

        Args:
            name: 专用提示词名称，如 similar_cases、sentencing
            default: 当专用提示词不存在时返回的默认值。
                     未提供时抛出ValueError。

        Returns:
            专用提示词文本

        Raises:
            ValueError: 专用提示词不存在且未提供默认值

        Example:
            >>> manager = PromptManager()
            >>> prompt = manager.get_specialized_prompt("sentencing")
            >>> prompt = manager.get_specialized_prompt("similar_cases")
        """
        if not name or not isinstance(name, str):
            msg = "name参数必须是非空字符串"
            raise ValueError(msg)

        self._record_usage(f"specialized:{name}")
        try:
            return self._prompts["specialized"][name]["content"]
        except (KeyError, TypeError):
            if default is not None:
                logger.warning(
                    "专用提示词 {} 不存在，使用默认值",
                    name,
                )
                return default
            logger.error("专用提示词 {} 不存在且未提供默认值", name)
            msg = (
                f"专用提示词 {name} 不存在，"
                f"请检查 prompts.json 中 specialized.{name}.content 字段"
            )
            raise ValueError(msg) from None

    def get_stats(self) -> dict[str, dict[str, Any]]:
        """获取提示词使用统计信息.

        返回每个提示词的调用次数、首次调用时间和最近调用时间的快照。

        Returns:
            统计信息字典，键为提示词标识，值为包含调用统计的字典

        Example:
            >>> manager = PromptManager()
            >>> stats = manager.get_stats()
            >>> print(stats["system"]["call_count"])
        """
        with self._lock:
            return dict(self._stats)

    def get_prompt_info(self) -> dict[str, Any]:
        """获取提示词元信息.

        返回提示词配置的元信息，包括版本号、描述和更新时间。

        Returns:
            元信息字典，包含 version、description、updated_at 等字段

        Example:
            >>> manager = PromptManager()
            >>> info = manager.get_prompt_info()
            >>> print(info["version"])
        """
        return dict(self._prompts.get("meta", {}))

    def get_available_dimensions(self) -> list[str]:
        """获取所有可用的维度列表.

        Returns:
            维度名称列表

        Example:
            >>> manager = PromptManager()
            >>> dims = manager.get_available_dimensions()
            >>> print(dims)  # ['dimension1', 'dimension2', 'dimension3']
        """
        dims = self._prompts.get("dimensions", {})
        if isinstance(dims, dict):
            return list(dims.keys())
        return []

    def get_available_specialized(self) -> list[str]:
        """获取所有可用的专用提示词列表.

        Returns:
            专用提示词名称列表

        Example:
            >>> manager = PromptManager()
            >>> names = manager.get_available_specialized()
        """
        specialized = self._prompts.get("specialized", {})
        if isinstance(specialized, dict):
            return list(specialized.keys())
        return []

    def is_loaded(self) -> bool:
        """检查提示词是否已成功加载.

        Returns:
            True表示提示词已加载，False表示未加载或加载失败

        Example:
            >>> manager = PromptManager()
            >>> if manager.is_loaded():
            ...     print("提示词已就绪")
        """
        return bool(self._prompts)


def get_prompt_manager(
    prompts_file: str | None = None,
) -> PromptManager:
    """获取PromptManager单例实例.

    创建或返回全局唯一的PromptManager实例，
    确保整个应用中提示词配置的一致性和统计数据的完整性。

    Args:
        prompts_file: 可选的提示词文件路径，仅在首次创建时生效

    Returns:
        全局唯一的PromptManager实例

    Example:
        >>> manager = get_prompt_manager()
    """
    return PromptManager(prompts_file)
