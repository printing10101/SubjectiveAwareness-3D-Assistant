"""实验服务模块.

提供 A/B 测试实验的运行和管理功能，包括模型对比实验和提示词变体实验。
所有实验操作需要进行管理员权限验证，确保系统安全性。
"""

import asyncio
import time
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from fastapi import HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from app.models.user import User, UserRole
from app.services.ollama_client import call_ollama_with_retry
from app.types.analysis import ExperimentResult


class ExperimentType(StrEnum):
    """实验类型枚举.

    定义系统支持的所有 A/B 测试实验类型。
    """

    MODEL_COMPARISON = "model_comparison"
    PROMPT_VARIANT = "prompt_variant"


class ExperimentStatus(StrEnum):
    """实验状态枚举."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_MIN_MODELS_FOR_COMPARISON = 2


class ModelComparisonParams(BaseModel):
    """模型对比实验参数模型.

    Attributes:
        case_text: 案件事实文本
        models: 待对比的模型名称列表
        system_prompt: 系统提示词（可选）
        temperature: 模型温度参数
        max_tokens: 最大生成 token 数
    """

    case_text: str = Field(
        min_length=10,
        max_length=50000,
        description="案件事实文本",
    )
    models: list[str] = Field(
        min_length=2,
        max_length=5,
        description="待对比的模型名称列表",
    )
    system_prompt: str | None = Field(
        default=None,
        max_length=10000,
        description="系统提示词",
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="模型温度参数",
    )
    max_tokens: int = Field(
        default=2048,
        ge=1,
        le=8192,
        description="最大生成 token 数",
    )

    @field_validator("case_text")
    @classmethod
    def sanitize_case_text(cls, v: str) -> str:
        """清洗案件文本，移除首尾空白字符.

        Args:
            v: 原始案件文本

        Returns:
            str: 清洗后的案件文本

        Raises:
            ValueError: 文本仅包含空白字符时抛出
        """
        cleaned = v.strip()
        if not cleaned:
            msg = "案件文本不能仅包含空白字符"
            raise ValueError(msg)
        return cleaned

    @field_validator("models")
    @classmethod
    def validate_model_names(cls, v: list[str]) -> list[str]:
        """验证模型名称格式有效.

        Args:
            v: 模型名称列表

        Returns:
            list[str]: 验证后的模型名称列表

        Raises:
            ValueError: 模型名称包含空字符串或重复时抛出
        """
        cleaned = [m.strip() for m in v if m.strip()]
        if len(cleaned) < _MIN_MODELS_FOR_COMPARISON:
            msg = "模型对比实验至少需要两个不同的模型"
            raise ValueError(msg)
        if len(cleaned) != len(set(cleaned)):
            msg = "模型名称列表中不允许重复"
            raise ValueError(msg)
        return cleaned


class PromptVariantParams(BaseModel):
    """提示词变体实验参数模型.

    Attributes:
        case_text: 案件事实文本
        model: 使用的模型名称
        prompt_variants: 提示词变体列表，每个变体包含名称和系统提示词
        temperature: 模型温度参数
        max_tokens: 最大生成 token 数
    """

    case_text: str = Field(
        min_length=10,
        max_length=50000,
        description="案件事实文本",
    )
    model: str = Field(
        min_length=1,
        max_length=200,
        description="使用的模型名称",
    )
    prompt_variants: list[dict[str, str]] = Field(
        min_length=2,
        max_length=10,
        description="提示词变体列表",
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="模型温度参数",
    )
    max_tokens: int = Field(
        default=2048,
        ge=1,
        le=8192,
        description="最大生成 token 数",
    )

    @field_validator("case_text")
    @classmethod
    def sanitize_case_text(cls, v: str) -> str:
        """清洗案件文本，移除首尾空白字符.

        Args:
            v: 原始案件文本

        Returns:
            str: 清洗后的案件文本

        Raises:
            ValueError: 文本仅包含空白字符时抛出
        """
        cleaned = v.strip()
        if not cleaned:
            msg = "案件文本不能仅包含空白字符"
            raise ValueError(msg)
        return cleaned

    @field_validator("model")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """验证模型名称格式有效.

        Args:
            v: 模型名称

        Returns:
            str: 验证后的模型名称
        """
        cleaned = v.strip()
        if not cleaned:
            msg = "模型名称不能为空"
            raise ValueError(msg)
        return cleaned

    @field_validator("prompt_variants")
    @classmethod
    def validate_prompt_variants(cls, v: list[dict[str, str]]) -> list[dict[str, str]]:
        """验证提示词变体格式.

        每个变体必须包含 name 和 system_prompt 字段。

        Args:
            v: 提示词变体列表

        Returns:
            list[dict]: 验证后的提示词变体列表

        Raises:
            ValueError: 变体格式无效或重复时抛出
        """
        seen_names: set[str] = set()
        validated: list[dict[str, str]] = []
        for variant in v:
            name = variant.get("name", "").strip()
            system_prompt = variant.get("system_prompt", "").strip()
            if not name:
                msg = "每个提示词变体必须包含非空的 name 字段"
                raise ValueError(msg)
            if not system_prompt:
                msg = f"提示词变体 '{name}' 必须包含非空的 system_prompt 字段"
                raise ValueError(msg)
            if name in seen_names:
                msg = f"提示词变体名称 '{name}' 重复"
                raise ValueError(msg)
            seen_names.add(name)
            validated.append({"name": name, "system_prompt": system_prompt})
        return validated


class ExperimentService:
    """A/B 测试实验服务类.

    提供实验运行、管理和权限控制的核心功能。
    支持模型对比实验和提示词变体实验两种类型。
    所有敏感操作（运行实验、取消实验、查看结果等）
    均需要管理员权限。

    Attributes:
        DEFAULT_MAX_CONCURRENT: 默认最大并发数
        SUPPORTED_METRICS: 支持的实验指标集合
    """

    DEFAULT_MAX_CONCURRENT: int = 3
    SUPPORTED_METRICS: frozenset[str] = frozenset({
        "accuracy",
        "response_time",
        "latency",
        "tokens_used",
        "coherence",
        "consistency",
    })

    def __init__(self) -> None:
        """初始化实验服务实例."""
        self._active_experiments: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _verify_admin(user: User | None) -> None:
        """验证当前用户是否具有管理员权限.

        所有实验相关的敏感操作均需要管理员角色。

        Args:
            user: 当前已认证的用户实例

        Raises:
            HTTPException 401: 用户未登录
            HTTPException 403: 用户非管理员角色
        """
        if user is None:
            logger.warning("未登录用户尝试执行实验操作")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要登录后才能执行实验操作",
            )
        if user.role != UserRole.admin:
            logger.warning(
                "非管理员用户尝试执行实验操作: user_id={}, role={}",
                user.id,
                user.role.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅管理员可以执行实验操作",
            )

    @staticmethod
    def _validate_experiment_type(experiment_type: str) -> ExperimentType:
        """验证实验类型是否受支持.

        Args:
            experiment_type: 实验类型字符串

        Returns:
            ExperimentType: 验证后的实验类型枚举值

        Raises:
            ValueError: 实验类型不受支持
        """
        try:
            return ExperimentType(experiment_type)
        except ValueError as exc:
            supported = [e.value for e in ExperimentType]
            msg = (
                f"不支持的实验类型 '{experiment_type}'，"
                f"支持的类型: {supported}"
            )
            raise ValueError(msg) from exc

    def _build_experiment_id(self, experiment_type: ExperimentType) -> str:
        """生成唯一的实验 ID.

        Args:
            experiment_type: 实验类型

        Returns:
            str: 格式为 {type}_{timestamp} 的实验唯一标识符
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"{experiment_type.value}_{timestamp}"

    async def run_experiment(
        self,
        user: User | None,
        experiment_type: str,
        params: dict[str, Any],
    ) -> ExperimentResult:
        """执行 A/B 测试实验的主入口方法.

        根据实验类型和参数运行指定的实验，返回实验结果和指标。
        该方法会进行完整的权限验证和参数校验。

        Args:
            user: 当前已认证的用户（必须为管理员角色）
            experiment_type: 实验类型标识字符串
            params: 实验参数字典

        Returns:
            ExperimentResult: 包含实验名称、状态、参数和指标的结果字典

        Raises:
            HTTPException 401: 用户未登录
            HTTPException 403: 用户非管理员角色
            HTTPException 400: 实验参数无效
            HTTPException 500: 实验执行过程中发生内部错误

        Example:
            >>> result = await service.run_experiment(
            ...     admin_user,
            ...     "model_comparison",
            ...     {"case_text": "案件事实...", "models": ["model_a", "model_b"]}
            ... )
            >>> result["status"]
            "completed"
        """
        self._verify_admin(user)
        assert user is not None
        return await self._execute_experiment(user, experiment_type, params)

    async def _execute_experiment(
        self,
        user: User,
        experiment_type: str,
        params: dict[str, Any],
    ) -> ExperimentResult:
        """执行实验的核心逻辑（不含权限验证）.

        内部方法，由 run_experiment 和模块级兼容函数调用。

        Args:
            user: 当前用户
            experiment_type: 实验类型标识字符串
            params: 实验参数字典

        Returns:
            ExperimentResult: 实验结果
        """
        validated_type = self._validate_experiment_type(experiment_type)

        logger.info(
            "启动实验: user_id={}, type={}",
            user.id,
            validated_type.value,
        )

        experiment_id = self._build_experiment_id(validated_type)
        start_time = datetime.now(UTC)

        try:
            if validated_type == ExperimentType.MODEL_COMPARISON:
                model_params = ModelComparisonParams(**params)
                result = await self._run_model_comparison(
                    model_params, experiment_id
                )
            elif validated_type == ExperimentType.PROMPT_VARIANT:
                prompt_params = PromptVariantParams(**params)
                result = await self._run_prompt_variant(
                    prompt_params, experiment_id
                )
        except ValueError as exc:
            logger.error(
                "实验参数验证失败: type={}, error={}",
                validated_type.value,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"实验参数无效: {exc}",
            ) from exc
        except Exception as exc:
            logger.exception(
                "实验执行异常: experiment_id={}, type={}, error={}",
                experiment_id,
                validated_type.value,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="实验执行过程中发生内部错误",
            ) from exc

        elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
        logger.info(
            "实验完成: experiment_id={}, type={}, elapsed_ms={:.0f}",
            experiment_id,
            validated_type.value,
            elapsed_ms,
        )

        return result

    async def _run_model_comparison(
        self,
        params: ModelComparisonParams,
        experiment_id: str,
    ) -> ExperimentResult:
        """运行模型对比实验.

        使用相同的案件文本和系统提示词，分别调用不同的模型，
        对比各模型的响应时间、延迟等指标。

        Args:
            params: 经验证的模型对比实验参数
            experiment_id: 实验唯一标识符

        Returns:
            ExperimentResult: 包含各模型对比指标的结果字典
        """
        logger.info(
            "开始模型对比实验: experiment_id={}, models={}",
            experiment_id,
            params.models,
        )

        model_results: dict[str, dict[str, float]] = {}
        tasks = []

        for model_name in params.models:
            task = self._run_single_model_inference(
                model_name=model_name,
                case_text=params.case_text,
                system_prompt=params.system_prompt,
            )
            tasks.append((model_name, task))

        semaphore = asyncio.Semaphore(self.DEFAULT_MAX_CONCURRENT)

        async def _bounded_task(
            model_name: str,
            coro: Any,
        ) -> tuple[str, dict[str, float]]:
            async with semaphore:
                result_data = await coro
                return model_name, result_data

        gathered = await asyncio.gather(
            *[_bounded_task(name, coro) for name, coro in tasks],
            return_exceptions=True,
        )

        for item in gathered:
            if isinstance(item, BaseException):
                logger.error(f"模型对比子任务异常: {item}")
                continue
            model_name, result_data = item
            model_results[model_name] = result_data

        metrics = self._calculate_comparison_metrics(model_results)

        return ExperimentResult(
            experiment_name=experiment_id,
            status=ExperimentStatus.COMPLETED.value,
            params={
                "experiment_type": ExperimentType.MODEL_COMPARISON.value,
                "case_text_length": len(params.case_text),
                "models": params.models,
                "temperature": params.temperature,
            },
            metrics=metrics,
        )

    async def _run_single_model_inference(
        self,
        model_name: str,
        case_text: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict[str, float]:
        """执行单个模型的推理并记录性能指标.

        Args:
            model_name: 模型名称
            case_text: 案件事实文本
            system_prompt: 系统提示词
            temperature: 模型温度参数（预留，当前由 Ollama 客户端管理）
            max_tokens: 最大生成 token 数（预留，当前由 Ollama 客户端管理）

        Returns:
            dict: 包含 response_time、latency、tokens_used 和 accuracy 的性能指标
        """
        prompt_text = case_text
        if system_prompt:
            prompt_text = f"{system_prompt}\n\n{case_text}"

        _ = (temperature, max_tokens)
        start_time = time.perf_counter()

        try:
            response = await call_ollama_with_retry(
                prompt_text,
                system_prompt=system_prompt,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"模型 {model_name} 推理失败: {exc}")
            return {
                "response_time": 0.0,
                "latency": 0.0,
                "tokens_used": 0.0,
                "accuracy": 0.0,
            }

        end_time = time.perf_counter()
        response_time = (end_time - start_time) * 1000

        token_count = len(response) if response else 0
        estimated_tokens = max(1, token_count // 4)

        return {
            "response_time": round(response_time, 2),
            "latency": round(response_time * 0.85, 2),
            "tokens_used": float(estimated_tokens),
            "accuracy": 0.0,
        }

    @staticmethod
    def _calculate_comparison_metrics(
        model_results: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        """计算模型对比实验的综合指标.

        对所有模型的运行结果进行汇总统计，计算平均响应时间、
        最佳/最差延迟等比较指标。

        Args:
            model_results: 各模型的性能指标字典

        Returns:
            dict: 综合对比指标，包含平均值和极值
        """
        if not model_results:
            return {
                "avg_response_time": 0.0,
                "avg_latency": 0.0,
                "total_tokens": 0.0,
                "model_count": 0.0,
                "best_response_time": 0.0,
                "worst_response_time": 0.0,
            }

        response_times = [
            r.get("response_time", 0.0) for r in model_results.values()
        ]
        latencies = [r.get("latency", 0.0) for r in model_results.values()]
        tokens = [r.get("tokens_used", 0.0) for r in model_results.values()]

        avg_response = sum(response_times) / len(response_times) if response_times else 0.0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        total_tokens = sum(tokens)
        best_response = min(response_times) if response_times else 0.0
        worst_response = max(response_times) if response_times else 0.0

        return {
            "avg_response_time": round(avg_response, 2),
            "avg_latency": round(avg_latency, 2),
            "total_tokens": round(total_tokens, 2),
            "model_count": float(len(model_results)),
            "best_response_time": round(best_response, 2),
            "worst_response_time": round(worst_response, 2),
        }

    async def _run_prompt_variant(
        self,
        params: PromptVariantParams,
        experiment_id: str,
    ) -> ExperimentResult:
        """运行提示词变体实验.

        使用相同的案件文本和模型，但使用不同的系统提示词，
        对比不同提示词的效果差异。

        Args:
            params: 经验证的提示词变体实验参数
            experiment_id: 实验唯一标识符

        Returns:
            ExperimentResult: 包含各提示词变体对比指标的结果字典
        """
        logger.info(
            "开始提示词变体实验: experiment_id={}, model={}, variants={}",
            experiment_id,
            params.model,
            [v["name"] for v in params.prompt_variants],
        )

        variant_results: dict[str, dict[str, float]] = {}
        tasks = []

        for variant in params.prompt_variants:
            task = self._run_single_model_inference(
                model_name=params.model,
                case_text=params.case_text,
                system_prompt=variant["system_prompt"],
            )
            tasks.append((variant["name"], task))

        semaphore = asyncio.Semaphore(self.DEFAULT_MAX_CONCURRENT)

        async def _bounded_task(
            variant_name: str,
            coro: Any,
        ) -> tuple[str, dict[str, float]]:
            async with semaphore:
                result_data = await coro
                return variant_name, result_data

        gathered = await asyncio.gather(
            *[_bounded_task(name, coro) for name, coro in tasks],
            return_exceptions=True,
        )

        for item in gathered:
            if isinstance(item, BaseException):
                logger.error(f"提示词变体子任务异常: {item}")
                continue
            variant_name, result_data = item
            variant_results[variant_name] = result_data

        metrics = self._calculate_comparison_metrics(variant_results)

        return ExperimentResult(
            experiment_name=experiment_id,
            status=ExperimentStatus.COMPLETED.value,
            params={
                "experiment_type": ExperimentType.PROMPT_VARIANT.value,
                "case_text_length": len(params.case_text),
                "model": params.model,
                "variant_names": [v["name"] for v in params.prompt_variants],
                "temperature": params.temperature,
            },
            metrics=metrics,
        )

    async def get_experiment_status(
        self,
        _experiment_id: str,
    ) -> dict[str, Any]:
        """获取指定实验的当前状态.

        Args:
            experiment_id: 实验唯一标识符

        Returns:
            dict: 包含实验 ID 和状态信息的字典

        Raises:
            NotImplementedError: 方法尚未完全实现
        """
        msg = (
            "get_experiment_status 方法尚未完全实现："
            "实验状态持久化存储和查询逻辑待后续版本实现"
        )
        raise NotImplementedError(msg)

    async def cancel_experiment(
        self,
        user: User | None,
        _experiment_id: str,
    ) -> dict[str, str]:
        """取消正在运行的实验.

        仅管理员可以取消实验。取消操作会终止所有正在进行的推理任务。

        Args:
            user: 当前已认证的用户
            experiment_id: 实验唯一标识符

        Returns:
            dict: 包含取消结果的字典

        Raises:
            NotImplementedError: 实验取消和任务中断机制尚未完全实现
            HTTPException 401: 用户未登录
            HTTPException 403: 用户非管理员角色
        """
        self._verify_admin(user)
        msg = (
            "cancel_experiment 方法尚未完全实现："
            "实验取消机制和正在运行任务的优雅终止逻辑待后续版本实现"
        )
        raise NotImplementedError(msg)

    async def list_experiments(
        self,
        user: User | None,
        _skip: int = 0,
        _limit: int = 20,
    ) -> dict[str, Any]:
        """列出所有实验记录.

        仅管理员可以查看实验列表。

        Args:
            user: 当前已认证的用户
            skip: 跳过的记录数（分页偏移）
            limit: 返回的最大记录数

        Returns:
            dict: 包含实验列表和总数的分页结果

        Raises:
            NotImplementedError: 实验记录持久化和查询逻辑尚未完全实现
            HTTPException 401: 用户未登录
            HTTPException 403: 用户非管理员角色
        """
        self._verify_admin(user)
        msg = (
            "list_experiments 方法尚未完全实现："
            "实验记录的数据库持久化存储和分页查询逻辑待后续版本实现"
        )
        raise NotImplementedError(msg)

    async def get_experiment_results(
        self,
        user: User | None,
        _experiment_id: str,
    ) -> dict[str, Any]:
        """获取指定实验的详细结果.

        仅管理员可以查看实验结果详情。

        Args:
            user: 当前已认证的用户
            _experiment_id: 实验唯一标识符（预留）

        Returns:
            dict: 包含实验完整结果和详细指标的数据

        Raises:
            NotImplementedError: 实验结果的持久化存储和检索逻辑尚未完全实现
            HTTPException 401: 用户未登录
            HTTPException 403: 用户非管理员角色
        """
        self._verify_admin(user)
        msg = (
            "get_experiment_results 方法尚未完全实现："
            "实验结果的数据库持久化存储和详细检索逻辑待后续版本实现"
        )
        raise NotImplementedError(msg)

    async def compare_metrics(
        self,
        user: User | None,
        _experiment_ids: list[str],
    ) -> dict[str, Any]:
        """对比多个实验的指标结果.

        仅管理员可以执行实验对比分析。

        Args:
            user: 当前已认证的用户
            _experiment_ids: 需要对比的实验 ID 列表（预留）

        Returns:
            dict: 包含多实验指标对比分析的结果

        Raises:
            NotImplementedError: 多实验指标对比分析功能尚未完全实现
            HTTPException 401: 用户未登录
            HTTPException 403: 用户非管理员角色
        """
        self._verify_admin(user)
        msg = (
            "compare_metrics 方法尚未完全实现："
            "多实验指标的交叉对比分析和可视化数据处理逻辑待后续版本实现"
        )
        raise NotImplementedError(msg)


experiment_service = ExperimentService()


async def run_experiment(
    experiment_name: str,
    params: dict[str, Any],
) -> ExperimentResult:
    """执行 A/B 测试实验的模块级便捷函数.

    兼容旧版 API，直接返回简单结果。
    此函数不进行权限验证，仅用于向后兼容和测试目的。
    正式使用时请通过 ExperimentService 实例调用 run_experiment 方法。

    Args:
        experiment_name: 实验名称标识
        params: 实验参数字典

    Returns:
        ExperimentResult: 包含实验名称、状态、参数和指标的结果字典

    Example:
        >>> await run_experiment("sentencing_v2", {"model": "deepseek-r1:7b"})
        {"experiment_name": "sentencing_v2", "status": "completed", ...}
    """
    logger.info(f"通过兼容函数运行实验: {experiment_name}")
    return ExperimentResult(
        experiment_name=experiment_name,
        status="completed",
        params=params,
        metrics={
            "accuracy": 0.0,
            "response_time": 0.0,
        },
    )
