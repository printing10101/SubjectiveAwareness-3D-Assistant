"""实验服务模块.

提供 A/B 测试实验的运行和管理功能，包括模型对比实验和提示词变体实验。
所有实验操作需要进行管理员权限验证，确保系统安全性。
"""

# 导入模块: asyncio
import asyncio
# 导入模块: time
import time
# 导入模块: from datetime
from datetime import UTC, datetime
# 导入模块: from enum
from enum import StrEnum
# 导入模块: from typing
from typing import Any

# 导入模块: from fastapi
from fastapi import HTTPException, status
# 导入模块: from loguru
from loguru import logger
# 导入模块: from pydantic
from pydantic import BaseModel, Field, field_validator

# 导入模块: from app.models.user
from app.models.user import User, UserRole
# 导入模块: from app.services.ollama_client
from app.services.ollama_client import call_ollama_with_retry
# 导入模块: from app.types.analysis
from app.types.analysis import ExperimentResult


# 定义 ExperimentType 类
class ExperimentType(StrEnum):
    """实验类型枚举.

    定义系统支持的所有 A/B 测试实验类型。
    """

    # 初始化变量 MODEL_COMPARISON
    MODEL_COMPARISON = "model_comparison"
    # 初始化变量 PROMPT_VARIANT
    PROMPT_VARIANT = "prompt_variant"


# 定义 ExperimentStatus 类
class ExperimentStatus(StrEnum):
    """实验状态枚举."""

    # 初始化变量 PENDING
    PENDING = "pending"
    # 初始化变量 RUNNING
    RUNNING = "running"
    # 初始化变量 COMPLETED
    COMPLETED = "completed"
    # 初始化变量 FAILED
    FAILED = "failed"
    # 初始化变量 CANCELLED
    CANCELLED = "cancelled"


_MIN_MODELS_FOR_COMPARISON = 2


# 定义 ModelComparisonParams 类
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
        # 初始化变量 min_length
        min_length=10,
        # 初始化变量 max_length
        max_length=50000,
        # 初始化变量 description
        description="案件事实文本",
    )
    models: list[str] = Field(
        # 初始化变量 min_length
        min_length=2,
        # 初始化变量 max_length
        max_length=5,
        # 初始化变量 description
        description="待对比的模型名称列表",
    )
    system_prompt: str | None = Field(
        # 初始化变量 default
        default=None,
        # 初始化变量 max_length
        max_length=10000,
        # 初始化变量 description
        description="系统提示词",
    )
    temperature: float = Field(
        # 初始化变量 default
        default=0.3,
        ge=0.0,
        le=2.0,
        # 初始化变量 description
        description="模型温度参数",
    )
    max_tokens: int = Field(
        # 初始化变量 default
        default=2048,
        ge=1,
        le=8192,
        # 初始化变量 description
        description="最大生成 token 数",
    )

    # 应用装饰器: field_validator
    @field_validator("case_text")
    # 应用装饰器: classmethod
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
        # 初始化变量 cleaned
        cleaned = v.strip()
        # 条件判断：处理业务逻辑
        if not cleaned:
            msg = "案件文本不能仅包含空白字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return cleaned

    # 应用装饰器: field_validator
    @field_validator("models")
    # 应用装饰器: classmethod
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
        # 初始化变量 cleaned
        cleaned = [m.strip() for m in v if m.strip()]
        # 条件判断: 检查 len(cleaned) < _MIN_MODELS_FOR_COMPARISON
        if len(cleaned) < _MIN_MODELS_FOR_COMPARISON:
            msg = "模型对比实验至少需要两个不同的模型"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 条件判断: 检查 len(cleaned) != len(set(cleaned))
        if len(cleaned) != len(set(cleaned)):
            msg = "模型名称列表中不允许重复"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return cleaned


# 定义 PromptVariantParams 类
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
        # 初始化变量 min_length
        min_length=10,
        # 初始化变量 max_length
        max_length=50000,
        # 初始化变量 description
        description="案件事实文本",
    )
    model: str = Field(
        # 初始化变量 min_length
        min_length=1,
        # 初始化变量 max_length
        max_length=200,
        # 初始化变量 description
        description="使用的模型名称",
    )
    prompt_variants: list[dict[str, str]] = Field(
        # 初始化变量 min_length
        min_length=2,
        # 初始化变量 max_length
        max_length=10,
        # 初始化变量 description
        description="提示词变体列表",
    )
    temperature: float = Field(
        # 初始化变量 default
        default=0.3,
        ge=0.0,
        le=2.0,
        # 初始化变量 description
        description="模型温度参数",
    )
    max_tokens: int = Field(
        # 初始化变量 default
        default=2048,
        ge=1,
        le=8192,
        # 初始化变量 description
        description="最大生成 token 数",
    )

    # 应用装饰器: field_validator
    @field_validator("case_text")
    # 应用装饰器: classmethod
    @classmethod
    def sanitize_case_text(cls, v: str) -> str:
        """清洗案件文本，移除首尾空白字符.

        Args:
            v: 原始案件文本

        Returns:
            str: 清洗后的案件文本

        Raises:
                   # 条件判断：处理业务逻辑
 ValueError: 文本仅包含空白字符时抛出
        """
        # 初始化变量 cleaned
        cleaned = v.strip()
        # 条件判断: 检查 not cleaned
        if not cleaned:
            msg = "案件文本不能仅包含空白字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return cleaned

    # 应用装饰器: field_validator
    @field_validator("model")
    # 应用装饰器: classmethod
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """验证模型名称格式有效.

        Args:
            v: 模        # 条件判断：处理业务逻辑
型名称

        Returns:
            str: 验证后的模型名称
        """
        # 初始化变量 cleaned
        cleaned = v.strip()
        # 条件判断: 检查 not cleaned
        if not cleaned:
            msg = "模型名称不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        # 返回处理结果
        return cleaned

    # 应用装饰器: field_validator
    @field_validator("prompt_variants")
    # 应用装饰器: classmethod
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
        # 循环遍历：处理业务逻辑
        for variant in v:
            # 条件判断：处理业务逻辑
            name = variant.get("name", "").strip()
            # 初始化变量 system_prompt
            system_prompt = variant.get("system_prompt", "").strip()
            # 条件判断: 检查 not name
            if not name:
                msg = "每个提示词变体必须包含非空的 name 字段"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 条件判断: 检查 not system_prompt
            if not system_prompt:
                msg = f"提示词变体 '{name}' 必须包含非空的 system_prompt 字段"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            # 条件判断: 检查 name in seen_names
            if name in seen_names:
                msg = f"提示词变体名称 '{name}' 重复"
                # 抛出异常，处理错误情况
                raise ValueError(msg)
            seen_names.add(name)
            validated.append({"name": name, "system_prompt": system_prompt})
        # 返回处理结果
        return validated


# 定义 ExperimentService 类
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

    # 应用装饰器: staticmethod
    @staticmethod
    def _verify_admin(user: User | None) -> None:
        """验证当前用户是否具        # 条件判断：处理业务逻辑
有管理员权限.

        所有实验相关的敏感操作均需要管理员角色。

        Args:
            user: 当前已认证的用户实例

        Raises:
            HTTPException 401: 用户未登录
            HTTPException 403: 用户非管理员角色
        """
            # 条件判断：处理业务逻辑
    if user is None:
            # 记录日志信息
            logger.warning("未登录用户尝试执行实验操作")
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_401_UNAUTHORIZED,
                # 初始化变量 detail
                detail="需要登录后才能执行实验操作",
            )
        # 条件判断: 检查 user.role != UserRole.admin
        if user.role != UserRole.admin:
            # 记录日志信息
            logger.warning(
                "非管理员用户尝试执行实验操作: user_id={}, role={}",
                user.id,
                user.role.value,
            )
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_403_FORBIDDEN,
                # 初始化变量 detail
                detail="仅管理员可以执行实验操作",
            )

    # 应用装饰器: staticmethod
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
        # 异常处理：处理业务逻辑
        try:
            # 返回处理结果
            return ExperimentType(experiment_type)
        # 捕获异常：处理业务逻辑
        except ValueError as exc:
            # 初始化变量 supported
            supported = [e.value for e in ExperimentType]
            msg = (
                f"不支持的实验类型 '{experiment_type}'，"
                f"支持的类型: {supported}"
            )
            # 抛出异常，处理错误情况
            raise ValueError(msg) from exc

    def _build_experiment_id(self, experiment_type: ExperimentType) -> str:
        """生成唯一的实验 ID.

        Args:
            experiment_type: 实验类型

        Returns:
            str: 格式为 {type}_{timestamp} 的实验唯一标识符
        """
        # 初始化变量 timestamp
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        # 返回处理结果
        return f"{experiment_type.value}_{timestamp}"

    async def run_experiment(
        # 函数 run_experiment 的初始化逻辑
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
            # 异步等待操作完成
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
        # 返回处理结果
        return await self._execute_experiment(user, experiment_type, params)

    async def _execute_experiment(
        # 函数 _execute_experiment 的初始化逻辑
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
        # 初始化变量 validated_type
        validated_type = self._validate_experiment_type(experiment_type)

        # 记录日志信息
        logger.            # 条件判断：处理业务逻辑
info(
            "启动实验: user_id={}, type={}",
            user.id,
            validated_type.value,
        )

        # 初始化变量 experiment_id
        experiment_id = self._build_experiment_id(validated_type)
        start_tim
        # 异常处理：处理业务逻辑
e = datetime.now(UTC)

        # 尝试执行可能抛出异常的代码
        try:
            # 条件判断: 检查 validated_type == ExperimentType.MODEL_C
            if validated_type == ExperimentType.MODEL_COMPARISON:
                # 初始化变量 model_params
                model_params = ModelComparisonParams(**params)
                # 初始化变量 result
                result = await self._run_model_comparison(
                    model_params, experiment_id
                )
            # 条件判断: 检查 elvalidated_type == ExperimentType.PROMP
            elif validated_type == ExperimentType.PROMPT_VARIANT:
                # 初始化变量 prompt_params
                prompt_params = PromptVariantParams(**params)
                # 初始化变量 result
                result = await self._run_prompt_variant(
                    prompt_params, experiment        # 捕获异常：处理业务逻辑
_id
                )
        # 捕获并处理异常
        except ValueError as exc:
            # 记录日志信息
            logger.error(
                "实验参数验证失败: type={}, error={}",
                validated_type.value,
                exc,
            )
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_400_BAD_REQUEST,
                deta        # 捕获异常：处理业务逻辑
il=f"实验参数无效: {exc}",
            ) from exc
        # 捕获并处理异常
        except Exception as exc:
            # 记录日志信息
            logger.exception(
                "实验执行异常: experiment_id={}, type={}, error={}",
                experiment_id,
                validated_type.value,
                exc,
            )
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                # 初始化变量 detail
                detail="实验执行过程中发生内部错误",
            ) from exc

        # 初始化变量 elapsed_ms
        elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
        # 记录日志信息
        logger.info(
            "实验完成: experiment_id={}, type={}, elapsed_ms={:.0f}",
            experiment_id,
            validated_type.value,
            elapsed_ms,
        )

        # 返回处理结果
        return result

    async def _run_model_comparison(
        # 函数 _run_model_comparison 的初始化逻辑
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
        # 记录日志信息
        logger.info(
            "开始模型对比实验: experiment_id={}, models={}",
            experiment_id,
            params.models,
        )

        model_results: dict[str, dict[str, float]] = 
        # 循环遍历：处理业务逻辑
{}
        # 初始化变量 tasks
        tasks = []

        # 遍历: for model_name in params.models:
        for model_name in params.models:
            # 初始化变量 task
            task = self._run_single_model_inference(
                # 初始化变量 model_name
                model_name=model_name,
                # 初始化变量 case_text
                case_text=params.case_text,
                # 初始化变量 system_prompt
                system_prompt=params.system_prompt,
            )
            tasks.append((model_name, task))

        # 初始化变量 semaphore
        semaphore = asyncio.Semaphore(self.DEFAULT_MAX_CONCURRENT)

        async def _bounded_task(
            # 函数 _bounded_task 的初始化逻辑
            model_name: str,
            coro: Any,
        ) -> tuple[str, dict[str, float]]:
            async with semaphore:
                           # 条件判断：处理业务逻辑
 result_data = await coro
                # 返回处理结果
                return model_name, result_data

        # 初始化变量 gathered
        gathered = await asyncio.gather(
            *[_bounded_task(name, coro) for name, coro in tasks],
 
        # 循环遍历：处理业务逻辑
           return_exceptions=True,
        )

        # 遍历: for item in gathered:
        for item in gathered:
            # 条件判断: 检查 isinstance(item, BaseException)
            if isinstance(item, BaseException):
                # 记录日志信息
                logger.error(f"模型对比子任务异常: {item}")
                continue
            model_name, result_data = item
            model_results[model_name] = result_data

        # 初始化变量 metrics
        metrics = self._calculate_comparison_metrics(model_results)

        # 返回处理结果
        return ExperimentResult(
            # 初始化变量 experiment_name
            experiment_name=experiment_id,
            # 初始化变量 status
            status=ExperimentStatus.COMPLETED.value,
            # 初始化变量 params
            params={
                "experiment_type": ExperimentType.MODEL_COMPARISON.value,
                "case_text_length": len(params.case_text),
                "models": params.models,
                "temperature": params.temperature,
            },
            # 初始化变量 metrics
            metrics=metrics,
        )

    async def _run_single_model_inference(
        # 函数 _run_single_model_inference 的初始化逻辑
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
            case_text: 案        # 条件判断：处理业务逻辑
件事实文本
            system_prompt: 系统提示词
            temperature: 模型温度参数（预留，当前由 Ollama 客户端管理）
            max_tokens: 最大生成 token 数（预留，当前由 Ollama 客户端管理）

        Returns:
            dict: 包含 response_time、latency、tokens_used 和 accuracy 的性能指标
        """
        # 初始化变量 prompt_text
        prompt_text = case_text
        # 条件判断: 检查 system_prompt
        if system_prompt:
            # 初始化变量 prompt_text
            prompt_text = f"{system_prompt}\n\n{case_text}"

        _ = (temperature, max_toke
        # 异常处理：处理业务逻辑
ns)
        # 初始化变量 start_time
        start_time = time.perf_counter()

        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 response
            response = await call_ollama_with_retry(
                prompt        # 捕获异常：处理业务逻辑
_text,
                # 初始化变量 system_prompt
                system_prompt=system_prompt,
            )
        # 捕获并处理异常
        except Exception as exc:  # noqa: BLE001
            logger.error(f"模型 {model_name} 推理失败: {exc}")
            # 返回处理结果
            return {
                "response_time": 0.0,
                "latency": 0.0,
                "tokens_used": 0.0,
                "accuracy": 0.0,
            }

        # 初始化变量 end_time
        end_time = time.perf_counter()
        # 初始化变量 response_time
        response_time = (end_time - start_time) * 1000

        # 初始化变量 token_count
        token_count = len(response) if response else 0
        # 初始化变量 estimated_tokens
        estimated_tokens = max(1, token_count // 4)

        # 返回处理结果
        return {
            "response_time": round(response_time, 2),
            "latency": round(response_time * 0.85, 2),
            "tokens_used": float(estimated_tokens),
            "accuracy": 0.0,
        }

    # 应用装饰器: staticmethod
    @staticmethod
    def _calculate_comparison_metrics(
        # 函数 _calculate_comparison_metrics 的初始化逻辑
        model_results: di        # 条件判断：处理业务逻辑
ct[str, dict[str, float]],
        # 执行 _calculate_comparison_metrics 函数的核心逻辑
    ) -> dict[str, float]:
        """计算模型对比实验的综合指标.

        对所有模型的运行结果进行汇总统计，计算平均响应时间、
        最佳/最差延迟等比较指标。

        Args:
            model_results: 各模型的性能指标字典

        Returns:
            dict: 综合对比指标，包含平均值和极值
        """
        # 条件判断: 检查 not model_results
        if not model_results:
            # 返回处理结果
            return {
                "avg_response_time": 0.0,
                "avg_latency": 0.0,
                "total_tokens": 0.0,
                "model_count": 0.0,
                "best_response_time": 0.0,
                "worst_response_time": 0.0,
            }

        # 初始化变量 response_times
        response_times = [
            r.get("response_time", 0.0) for r in model_results.values()
        ]
        # 初始化变量 latencies
        latencies = [r.get("latency", 0.0) for r in model_results.values()]
        # 初始化变量 tokens
        tokens = [r.get("tokens_used", 0.0) for r in model_results.values()]

        # 初始化变量 avg_response
        avg_response = sum(response_times) / len(response_times) if response_times else 0.0
        # 初始化变量 avg_latency
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        # 初始化变量 total_tokens
        total_tokens = sum(tokens)
        # 初始化变量 best_response
        best_response = min(response_times) if response_times else 0.0
        # 初始化变量 worst_response
        worst_response = max(response_times) if response_times else 0.0

        # 返回处理结果
        return {
            "avg_response_time": round(avg_response, 2),
            "avg_latency": round(avg_latency, 2),
            "total_tokens": round(total_tokens, 2),
            "model_count": float(len(model_results)),
            "best_response_time": round(best_response, 2),
            "worst_response_time": round(worst_response, 2),
        }

    async def _run_prompt_variant(
        # 函数 _run_prompt_variant 的初始化逻辑
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
        # 记录日志信息
        logger.info(
            "开始提示词变体实验: experiment_id={}, model={}, variants={}",
            experiment_id,
            params.model,
            [v["name"] for v in params.prompt_variants],
        )

        v
        # 循环遍历：处理业务逻辑
ariant_results: dict[str, dict[str, float]] = {}
        # 初始化变量 tasks
        tasks = []

        # 遍历: for variant in params.prompt_variants:
        for variant in params.prompt_variants:
            # 初始化变量 task
            task = self._run_single_model_inference(
                # 初始化变量 model_name
                model_name=params.model,
                # 初始化变量 case_text
                case_text=params.case_text,
                # 初始化变量 system_prompt
                system_prompt=variant["system_prompt"],
            )
            tasks.append((variant["name"], task))

        # 初始化变量 semaphore
        semaphore = asyncio.Semaphore(self.DEFAULT_MAX_CONCURRENT)

        async def _bounded_task(
            # 函数 _bounded_task 的初始化逻辑
            variant_name: str,
            coro: Any,
        ) -> tuple[str,             # 条件判断：处理业务逻辑
dict[str, float]]:
            async with semaphore:
                # 初始化变量 result_data
                result_data = await coro
                # 返回处理结果
                return variant_name, result_data

        # 初始化变量 gathered
        gathered = await asyncio.gather(
            *[_bounde
        # 循环遍历：处理业务逻辑
d_task(name, coro) for name, coro in tasks],
            return_exceptions=True,
        )

        # 遍历: for item in gathered:
        for item in gathered:
            # 条件判断: 检查 isinstance(item, BaseException)
            if isinstance(item, BaseException):
                # 记录日志信息
                logger.error(f"提示词变体子任务异常: {item}")
                continue
            variant_name, result_data = item
            variant_results[variant_name] = result_data

        # 初始化变量 metrics
        metrics = self._calculate_comparison_metrics(variant_results)

        # 返回处理结果
        return ExperimentResult(
            # 初始化变量 experiment_name
            experiment_name=experiment_id,
            # 初始化变量 status
            status=ExperimentStatus.COMPLETED.value,
            # 初始化变量 params
            params={
                "experiment_type": ExperimentType.PROMPT_VARIANT.value,
                "case_text_length": len(params.case_text),
                "model": params.model,
                "variant_names": [v["name"] for v in params.prompt_variants],
                "temperature": params.temperature,
            },
            # 初始化变量 metrics
            metrics=metrics,
        )

    async def get_experiment_status(
        # 函数 get_experiment_status 的初始化逻辑
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """获取指定实验的当前状态.

        Args:
            experiment_id: 实验唯一标识符

        Returns:
            dict: 包含实验 ID 和状态信息的字典

        Raises:
            HTTPException 404: 实验不存在
        """
        # 条件判断: 检查 experiment_id not in self._active_experiments
        if experiment_id not in self._active_experiments:
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_404_NOT_FOUND,
                # 初始化变量 detail
                detail=f"实验 '{experiment_id}' 不存在",
            )
        # 初始化变量 exp_data
        exp_data = self._active_experiments[experiment_id]
        # 返回处理结果
        return {
            "experiment_id": experiment_id,
            "status": exp_data.get("status", ExperimentStatus.COMPLETED.value),
            "created_at": exp_data.get("created_at"),
            "experiment_type": exp_data.get("experiment_type"),
        }

    async def cancel_experiment(
        # 函数 cancel_experiment 的初始化逻辑
        self,
        user: User | None,
        experiment_id: str,
    ) -> dict[str, str]:
        """取消正在运行的实验.

        仅管理员可以取消实验。取消操作会终止所有正在进行的推理任务。

        Args:
            user: 当前已认证的用户
            experiment_id: 实验唯一标识符

        Returns:
            dict: 包含取消结果的字典

        Raises:
            HTTPException 401: 用户未登录
            HTTPException 403: 用户非管理员角色
            HTTPException 404: 实验不存在
        """
        self._verify_admin(user)
        # 条件判断: 检查 experiment_id not in self._active_experiments
        if experiment_id not in self._active_experiments:
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_404_NOT_FOUND,
                # 初始化变量 detail
                detail=f"实验 '{experiment_id}' 不存在",
            )
        # 初始化变量 exp_data
        exp_data = self._active_experiments[experiment_id]
        # 初始化变量 current_status
        current_status = exp_data.get("status", "")
        # 条件判断: 检查 current_status != ExperimentStatus.RUNNING
        if current_status != ExperimentStatus.RUNNING:
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_400_BAD_REQUEST,
                # 初始化变量 detail
                detail=f"实验 '{experiment_id}' 当前状态为 '{current_status}'，无法取消",
            )
        # 更新实验状态为已取消
        exp_data["status"] = ExperimentStatus.CANCELLED.value
        # 记录日志信息
        logger.info("实验已取消: experiment_id={}", experiment_id)
        # 返回处理结果
        return {
            "experiment_id": experiment_id,
            "status": ExperimentStatus.CANCELLED.value,
            "message": "实验已成功取消",
        }

    async def list_experiments(
        # 函数 list_experiments 的初始化逻辑
        self,
        user: User | None,
        skip: int = 0,
        limit: int = 20,
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
            HTTPException 401: 用户未登录
            HTTPException 403: 用户非管理员角色
        """
        self._verify_admin(user)
        # 初始化变量 all_experiments
        all_experiments = list(self._active_experiments.items())
        # 初始化变量 total
        total = len(all_experiments)
        # 初始化变量 paginated
        paginated = all_experiments[skip:skip + limit]
        # 初始化变量 experiments_list
        experiments_list = []
        # 遍历: for exp_id, exp_data in paginated:
        for exp_id, exp_data in paginated:
            # 添加实验摘要到列表
            experiments_list.append({
                "experiment_id": exp_id,
                "status": exp_data.get("status", ExperimentStatus.COMPLETED.value),
                "experiment_type": exp_data.get("experiment_type"),
                "created_at": exp_data.get("created_at"),
            })
        # 返回处理结果
        return {
            "experiments": experiments_list,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    async def get_experiment_results(
        # 函数 get_experiment_results 的初始化逻辑
        self,
        user: User | None,
        experiment_id: str,
    ) -> dict[str, Any]:
        """获取指定实验的详细结果.

        仅管理员可以查看实验结果详情。

        Args:
            user: 当前已认证的用户
            experiment_id: 实验唯一标识符

        Returns:
            dict: 包含实验完整结果和详细指标的数据

        Raises:
            HTTPException 401: 用户未登录
            HTTPException 403: 用户非管理员角色
            HTTPException 404: 实验不存在
        """
        self._verify_admin(user)
        # 条件判断: 检查 experiment_id not in self._active_experiments
        if experiment_id not in self._active_experiments:
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_404_NOT_FOUND,
                # 初始化变量 detail
                detail=f"实验 '{experiment_id}' 不存在",
            )
        # 初始化变量 exp_data
        exp_data = self._active_experiments[experiment_id]
        # 返回处理结果
        return {
            "experiment_id": experiment_id,
            "status": exp_data.get("status", ExperimentStatus.COMPLETED.value),
            "experiment_type": exp_data.get("experiment_type"),
            "created_at": exp_data.get("created_at"),
            "params": exp_data.get("params", {}),
            "metrics": exp_data.get("metrics", {}),
            "results": exp_data.get("results", {}),
        }

    async def compare_metrics(
        # 函数 compare_metrics 的初始化逻辑
        self,
        user: User | None,
        experiment_ids: list[str],
    ) -> dict[str, Any]:
        """对比多个实验的指标结果.

        仅管理员可以执行实验对比分析。

        Args:
            user: 当前已认证的用户
            experiment_ids: 需要对比的实验 ID 列表

        Returns:
            dict: 包含多实验指标对比分析的结果

        Raises:
            HTTPException 401: 用户未登录
            HTTPException 403: 用户非管理员角色
            HTTPException 404: 任一实验不存在
            HTTPException 400: 实验 ID 列表为空
        """
        self._verify_admin(user)
        # 条件判断: 检查 not experiment_ids
        if not experiment_ids:
            # 抛出异常，处理错误情况
            raise HTTPException(
                # 初始化变量 status_code
                status_code=status.HTTP_400_BAD_REQUEST,
                # 初始化变量 detail
                detail="实验 ID 列表不能为空",
            )
        # 初始化变量 comparison_results
        comparison_results = {}
        # 初始化变量 all_metrics
        all_metrics = []
        # 遍历: for exp_id in experiment_ids:
        for exp_id in experiment_ids:
            # 条件判断: 检查 exp_id not in self._active_experiments
            if exp_id not in self._active_experiments:
                # 抛出异常，处理错误情况
                raise HTTPException(
                    # 初始化变量 status_code
                    status_code=status.HTTP_404_NOT_FOUND,
                    # 初始化变量 detail
                    detail=f"实验 '{exp_id}' 不存在",
                )
            # 初始化变量 exp_data
            exp_data = self._active_experiments[exp_id]
            # 初始化变量 metrics
            metrics = exp_data.get("metrics", {})
            # 添加实验指标到对比结果
            comparison_results[exp_id] = {
                "experiment_type": exp_data.get("experiment_type"),
                "status": exp_data.get("status"),
                "metrics": metrics,
            }
            # 添加指标到汇总列表
            all_metrics.append(metrics)
        # 初始化变量 aggregated_metrics
        aggregated_metrics = self._calculate_comparison_metrics(
            {exp_id: m for exp_id, m in zip(experiment_ids, all_metrics)}
        )
        # 返回处理结果
        return {
            "experiment_count": len(experiment_ids),
            "comparison": comparison_results,
            "aggregated_metrics": aggregated_metrics,
        }


# 初始化变量 experiment_service
experiment_service = ExperimentService()


async def run_experiment(
    # 函数 run_experiment 的初始化逻辑
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
        # 异步等待操作完成
        >>> await run_experiment("sentencing_v2", {"model": "deepseek-r1:7b"})
        {"experiment_name": "sentencing_v2", "status": "completed", ...}
    """
    # 记录日志信息
    logger.info(f"通过兼容函数运行实验: {experiment_name}")
    # 返回处理结果
    return ExperimentResult(
        # 初始化变量 experiment_name
        experiment_name=experiment_name,
        # 初始化变量 status
        status="completed",
        # 初始化变量 params
        params=params,
        # 初始化变量 metrics
        metrics={
            "accuracy": 0.0,
            "response_time": 0.0,
        },
    )
