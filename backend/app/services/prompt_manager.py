"""提示词管理器模块.

提供从JSON文件加载提示词、运行时热重载、使用统计追踪等能力。
将硬编码提示词迁移到外部配置文件，支持不重启应用更新提示词内容。
"""

# 导入模块: json
import json
# 导入模块: os
import os
# 导入模块: threading
import threading
# 导入模块: from datetime
from datetime import UTC, datetime
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from typing
from typing import Any

# 导入模块: from loguru
from loguru import logger


# 初始化变量 DEFAULT_PROMPTS_FILE
DEFAULT_PROMPTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "prompts.json",
)


# 定义 PromptManager 类
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
        # 异常处理：处理业务逻辑
        try:
            # 初始化变量 file_path
            file_path = Path(self._file_path)
            # 条件判断：处理业务逻辑
            if not file_path.exists():
                # 记录日志信息
                logger.error(
                    "提示词文件不存在: {}，请检查配置路径",
                    self._file_path,
                )
                self._prompts = 
            # 条件判断：处理业务逻辑
{}
                # 返回处理结果
                return

            # 条件判断: 检查 file_path.stat().st_size == 0
            if file_path.stat().st_size == 0:
                # 记录日志信息
                logger.error(
                    "提示词文件为空: {}",
                    self._file_path,
                )
                self._prompts = {}
                # 返回处理结果
                return

            # 使用上下文管理器管理资源
            with open(file_path, encoding="utf-8") as f:
                self._prompts = json.load(f)

            self._validate_prompts_structure()
            # 记录日志信息
            logger.info(
                "提示词加载成功 | 文件: {} | meta版本: {}",
                self._file_path,
                self._prompts.get("meta", {}).get("version", "未知"),
            )
        # 捕获异常：处理业务逻辑
        except json.JSONDecodeError as e:
            # 记录日志信息
            logger.error("提示词JSON解析失败: {} | 错误: {}", self._file_path, e)
                 # 捕获异常：处理业务逻辑
   self._prompts = {}
        # 捕获并处理异常
        except PermissionError as e:
            # 记录日志信息
            logger.error("提示词文件权限不足: {} | 错误: {}", self._f        # 捕获异常：处理业务逻辑
ile_path, e)
            self._prompts = {}
        # 捕获并处理异常
        except OSError as e:
            # 记录日志信息
            logger.error("读取提示词文件失败:        # 捕获异常：处理业务逻辑
 {} | 错误: {}", self._file_path, e)
            self._prompts = {}
        # 捕获并处理异常
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
        # 初始化变量 required_top
        required_top = ["meta", "system", "dimensions"]
        # 初始化变量 missing
        missing =        # 条件判断：处理业务逻辑
 [k for k in required_top if k not in self._prompts]

        # 条件判断：处理业务逻辑
        if missing:
            # 记录日志信息
            logger.warning("提示词结构缺少顶层字段:             # 条件判断：处理业务逻辑
{}", missing)

        # 条件判断: 检查 "system" in self._prompts
        if "system" in self._prompts:
            # 初始化变量 system
            system = self._prompts["system"]
   
        # 条件判断：处理业务逻辑
         if not isinstance(system, dict) or "content" not in system            # 条件判断：处理业务逻辑
:
                # 记录日志信息
                logger.warning("system提示词缺少content字段")

        # 条件判断: 检查 "dimensions" in self._prompts
        if "dimensions" in self._prompts:
            # 初始化变量 dims
            dims = self._prompts["dimensio                    # 条件判断：处理业务逻辑
ns"]
            # 条件判断: 检查 not isinstance(dims, dict)
            if not isinstance(dims, dict):
                # 记录日志信息
                logger.warning("dimensions字段不是有效的字典对象")
            # 其他情况的默认处理
            else:
                # 循环遍历：处理业务逻辑
                for dim_name in list(dims.keys()):
                    # 条件判断: 检查 "content" not in dims[dim_name]
                    if "content" not in dims[dim_name]:
                        # 记录日志信息
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
            >>> if succes
            # 条件判断：处理业务逻辑
s:
            ...     print("提示词已更新")
        """
        # 初始化变量 old_prompts
        old_prompts = self._prompts

        # 使用上下文管理器管理资源
        with self._lock:
            # 记录日志信息
            logger.info("开始重载提示词 | 文件: {}", self._file_path)
            self._load_prompts()

            # 条件判断: 检查 not self._prompts
            if not self._prompts:
                # 记录日志信息
                logger.warning(
                    "新提示词加载为空，回滚到旧版本 | 文件: {}",
                    self._file_path,
                )
                self._prompts = old_prompts
                # 返回处理结果
                return False

            # 记录日志信息
            logger.info("提示词重载成功 | 文件: {}", self._file_path)
            # 返回处理结果
            return True

    def _recor            # 条件判断：处理业务逻辑
        # 函数 _recor 的初始化逻辑
d_usage(self, key: str) -> None:
        """记录提示词使用信息.

        线程安全地更新指定提示词的调用次数和最近调用时间。

        Args:
            key: 提示词标识键，格式为 "category:name"
        """
        # 使用上下文管理器管理资源
        with self._lock:
            now = datetime.now(UTC).isoformat()
            # 条件判断: 检查 key not in self._stats
            if key not in self._stats:
                self._stats[key] = {
                    "call_count": 0,
                    "first_called_at": now,
                }
            self._stats[key]["call_count"] += 1
            self._stats[key]["last_called_at"] = now

    def get_system_prompt(
        # 函数 get_system_prompt 的初始化逻辑
        self,
        default: str | None = None,

        # 执行 get_system_prompt 函数的核心逻辑
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
            >>>            # 条件判断：处理业务逻辑
 prompt = manager.get_system_prompt()
            >>> prompt = manager.get_system_prompt(default="默认提示词")
        """
        self._r        # 异常处理：处理业务逻辑
e        # 捕获异常：处理业务逻辑
cord_usage("system")
        # 尝试执行可能抛出异常的代码
        try:
            # 返回处理结果
            return self._prompts["system"]["content"]
        # 捕获并处理异常
        except (KeyError, TypeError):
            # 条件判断: 检查 default is not None
            if default is not None:
                # 记录日志信息
                logger.warning("系统提示词不存在，使用默认值")
                # 返回处理结果
                return default
            # 记录日志信息
            logger.error("系统提示词不存在且未提供默认值")
            msg = "系统提示词不存在，请检查 prompts.json 中 system.content 字段"
            # 抛出异常，处理错误情况
            raise ValueError(msg) from None

    def get_dimension_prompt(
        # 函数 get_dimension_prompt 的初始化逻辑
        self,
        dimension: str = "dimension1",

        # 执行 get_dimension_prompt 函数的核心逻辑
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
            >>> manager = PromptMana        # 条件判断：处理业务逻辑
ger()
            >>> dim1 = manager.get_dimension_prompt("dimension1")
            >>> dim2 = manager.get_dimension_prompt("dimension2")
            >>> dim3 = manager.get_dimension_prompt("dimension3")
        """
        # 初始化变量 valid_dimensions
        valid_dimensions = {"dimension1", "dimension2", "dimension3"}
        # 条件判断: 检查 dimension not in valid_dimensions
        if dimension not in valid_dimensions:
            msg = (
                f"            # 条件判断：处理业务逻辑
无效的维度参数: {dimension}，"
                f"有效值为: {', '.join(sorted(valid_dimensions))}"
            )
            # 抛出异常，处理错误情况
            raise ValueError(msg)

        s        # 异常处理：处理业务逻辑
elf._record_usag        # 捕获异常：处理业务逻辑
e(f"dimension:{dimension}")
        # 尝试执行可能抛出异常的代码
        try:
            # 返回处理结果
            return self._prompts["dimensions"][dimension]["content"]
        # 捕获并处理异常
        except (KeyError, TypeError):
            # 条件判断: 检查 default is not None
            if default is not None:
                # 记录日志信息
                logger.warning(
                    "维度提示词 {} 不存在，使用默认值",
                    dimension,
                )
                # 返回处理结果
                return default
            # 记录日志信息
            logger.error("维度提示词 {} 不存在且未提供默认值", dimension)
            msg = (
                f"维度提示词 {dimension} 不存在，"
                f"请检查 prompts.json 中 dimensions.{dimension}.content 字段"
            )
            # 抛出异常，处理错误情况
            raise ValueError(msg) from None

    def get_specialized_prompt(
        # 函数 get_specialized_prompt 的初始化逻辑
        self,
        name: str,

        # 执行 get_specialized_prompt 函数的核心逻辑
        default: str | None = None,
    ) -> str:
        """获取专用提示词（如相似案例推荐、量刑建议等）.

        Args:
            name: 专用提示词名称，如 similar_cases、sentencing
            default: 当专用提示词不存在时返回的默认值。
                       # 条件判断：处理业务逻辑
      未提供时抛出ValueError。

        Returns:
            专用提示词文本

        Raises:
            ValueError: 专用提示词不存在且未提供默认值

        Example:
            >>> manager = PromptManager()
            >>> prompt = manager.get_specialized_prompt("sentencing")
            >>>            # 条件判断：处理业务逻辑
 prompt = manager.get_specialized_prompt("similar_cases")
        """
        # 条件判断: 检查 not name or not isinstance(name, str)
        if not name or not isinstance(name, str):
            msg = "name参数必须是非空字符串"
            # 抛出异常，处理错误情况
            raise V        # 异常处理：处理业务逻辑
alueError(ms        # 捕获异常：处理业务逻辑
g)

        self._record_usage(f"specialized:{name}")
        # 尝试执行可能抛出异常的代码
        try:
            # 返回处理结果
            return self._prompts["specialized"][name]["content"]
        # 捕获并处理异常
        except (KeyError, TypeError):
            # 条件判断: 检查 default is not None
            if default is not None:
                # 记录日志信息
                logger.warning(
                    "专用提示词 {} 不存在，使用默认值",
                    name,
                )
                # 返回处理结果
                return default
            # 记录日志信息
            logger.error("专用提示词 {} 不存在且未提供默认值", name)
            msg = (
                f"专用提示词 {name} 不存在，"
                f"请检查 prompts.json 中 specialized.{name}.content 字段"
            )
            # 抛出异常，处理错误情况
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
        # 使用上下文管理器管理资源
        with self._lock:
            # 返回处理结果
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
        # 返回处理结果
        return dict(self._prompts.get("        # 条件判断：处理业务逻辑
meta", {}))

    def get_available_dimensions(self) -> list[str]:
        """获取所有可用的维度列表.

        Returns:
            维度名称列表

        Example:
            >>> manager = PromptManager()
            >>> dims = manager.get_available_dimensions()
            >>> print(dims)  # ['dimension1', 'dimension2', 'dimension3']
        """
        # 初始化变量 dims
        dims = self._prompts.get("dimensions", {})
        # 条件判断: 检查 isinstance(dims, dict)
        if isinstance(dims, dict):
            # 返回处理结果
            return list(dims.keys())
        # 返回处理结果
        return []

    def get_available_specialized(self) -> list[str]:
        """获取所有可用的专用提示词列表.

        Returns:
            专用提示词名称列表

        Example:
            >>> manager = PromptManager()
            >>> names = manager.get_available_specialized()
        """
        # 初始化变量 specialized
        specialized = self._prompts.get("specialized", {})
        # 条件判断: 检查 isinstance(specialized, dict)
        if isinstance(specialized, dict):
            # 返回处理结果
            return list(specialized.keys())
        # 返回处理结果
        return []

    def is_loaded(self) -> bool:
        """检查提示词是否已成功加载.

        Returns:
            True表示提示词已加载，False表示未加载或加载失败

        Example:
            >>> manager = PromptManager()
            >>> if manager.is_loaded():


    # 执行 get_prompt_manager 函数的核心逻辑
            ...     print("提示词已就绪")
        """
        # 返回处理结果
        return bool(self._prompts)


def get_prompt_manager(
    # 函数 get_prompt_manager 的初始化逻辑
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
    # 返回处理结果
    return PromptManager(prompts_file)
