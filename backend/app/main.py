"""FastAPI 应用程序入口模块.

负责应用初始化、中间件配置、路由注册、后台任务调度和生命周期管理。
"""

# 导入模块: asyncio
import asyncio
# 导入模块: json
import json
# 导入模块: time
import time
# 导入模块: uuid
import uuid
# 导入模块: from collections.abc
from collections.abc import AsyncGenerator
# 导入模块: from contextlib
from contextlib import asynccontextmanager
# 导入模块: from datetime
from datetime import UTC, datetime
# 导入模块: from typing
from typing import Any

# 导入模块: httpx
import httpx
# 导入模块: sentry_sdk
import sentry_sdk
# 导入模块: tenacity
import tenacity
# 导入模块: from fastapi
from fastapi import FastAPI, Request
# 导入模块: from fastapi.middleware.cors
from fastapi.middleware.cors import CORSMiddleware
# 导入模块: from fastapi.responses
from fastapi.responses import JSONResponse, Response
# 导入模块: from loguru
from loguru import logger
# 导入模块: from prometheus_client
from prometheus_client import generate_latest
# 导入模块: from sentry_sdk.integrations.fastapi
from sentry_sdk.integrations.fastapi import FastApiIntegration
# 导入模块: from slowapi
from slowapi import _rate_limit_exceeded_handler
# 导入模块: from slowapi.errors
from slowapi.errors import RateLimitExceeded
# 导入模块: from sqlalchemy
from sqlalchemy import select
# 导入模块: from sqlalchemy.exc
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
# 导入模块: from tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

# 导入模块: from app.config
from app.config import AnalysisConfig, settings
# 导入模块: from app.database
from app.database import (
    Base,
    async_engine,
    dispose_engines,
    get_async_db_session,
)
# 导入模块: from app.middleware.audit
from app.middleware.audit import AuditLogMiddleware
# 导入模块: from app.models.user
from app.models.user import User, UserRole
# 导入模块: from app.routers
from app.routers import (
    analysis,
    cases,
    documents,
    experiment,
    knowledge,
    labels,
    reports,
    system,
)
# 导入模块: from app.schemas.knowledge
from app.schemas.knowledge import KnowledgeTagCreate
# 导入模块: from app.services.knowledge_lifecycle_service
from app.services.knowledge_lifecycle_service import (
    KnowledgeLifecycleScheduler,
    ScheduleConfig,
)
# 导入模块: from app.services.knowledge_service
from app.services.knowledge_service import create_tag, get_all_tags
# 导入模块: from app.services.ollama_client
from app.services.ollama_client import (
    get_client,
    shutdown as ollama_shutdown,
    startup as ollama_startup,
)
# 导入模块: from app.services.pipeline
from app.services.pipeline import analyze_pipeline
# 导入模块: from app.utils.auth
from app.utils.auth import auth_router, get_password_hash
# 导入模块: from app.utils.logger
from app.utils.logger import request_id_var, setup_logging
# 导入模块: from app.utils.rate_limit
from app.utils.rate_limit import limiter, set_request_context


# Initialize logging system
setup_logging(
    # 初始化变量 log_level
    log_level=settings.LOG_LEVEL,
    # 初始化变量 log_dir
    log_dir=settings.LOG_DIR,
)

# Keep strong references to background tasks to prevent garbage collection
_background_tasks: set[asyncio.Task[Any]] = set()

# 知识生命周期定时任务调度器实例
_lifecycle_scheduler: KnowledgeLifecycleScheduler | None = None

# Disable rate limiter in debug/development mode
# 条件判断：处理业务逻辑
if settings.DEBUG:
    limiter.enabled = False


def init_sentry() -> None:
    """条件初始化 Sentry 错误追踪 SDK.

    仅当 SENTRY_DSN 配置值不为 None 且非空字符串时才进行初始化。
    集成 FastApiIntegration 以捕获 FastAPI 特定的错误和请求信息，
    包含异步中间件和请求上下文。

    当 SENTRY_DSN 未配置时（None 或空字符串），跳过初始化，
    应用正常运行且不会产生任何 Sentry 相关副作用。

    配置项：
        - environment: 区分部署环境，便于 Sentry 平台过滤
        - traces_sample_rate: 性能追踪采样率
        - attach_stacktrace: 事件附加堆栈跟踪
        - send_default_pii: 默认不上传个人身份信息以保护隐私
        - timeout: 事件发送超时
    """
    dsn = settings.SENTRY_DSN
    if not dsn or not dsn.strip():
        # 记录日志信息
        logger.info("SENTRY_DSN 未配置，跳过 Sentry 初始化")
        # 返回处理结果
        return

    # 初始化变量 environment
    environment = settings.SENTRY_ENVIRONMENT or settings.APP_ENV
    # 初始化变量 sample_rate
    sample_rate = max(0.0, min(1.0, settings.SENTRY_TRACES_SAMPLE_RATE))

    sentry_sdk.init(
        dsn=dsn,
        # 初始化变量 environment
        environment=environment,
        # 初始化变量 traces_sample_rate
        traces_sample_rate=sample_rate,
        # 初始化变量 attach_stacktrace
        attach_stacktrace=settings.SENTRY_ATTACH_STACKTRACE,
        # 初始化变量 send_default_pii
        send_default_pii=settings.SENTRY_SEND_DEFAULT_PII,
        # 初始化变量 timeout
        timeout=settings.SENTRY_TIMEOUT,
        # 初始化变量 integrations
        integrations=[FastApiIntegration()],
    )

    sentry_sdk.set_tag("app_name", "Case Analysis API")
    sentry_sdk.set_tag("app_env", environment)

    # 记录日志信息
    logger.info(
        "Sentry 初始化完成: environment={}, traces_sample_rate={}",
        environment,
        sample_rate,
    )


# 应用装饰器: asynccontextmanager
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理器.

    在启动时检查 Ollama 可用性、预缓存示例案件、创建默认管理员、
    初始化知识库默认数据、启动知识生命周期定时任务调度器；
    在关闭时执行清理操作。

    Args:
        app: FastAPI 应用实例
    """
    # Startup
    logger.info("正在启动案件分析 API...")
    init_sentry()
    # 记录日志信息
    logger.info(
        "Ollama URL: {}, Model: {}",
        settings.OLLAMA_BASE_URL,
        settings.OLLAMA_MODEL,
    )

    # 异步等待操作完成
    await ollama_startup()

    # 后台预缓存示例案件
    logger.info("后台预缓存示例案件...")
    # 初始化变量 task
    task = asyncio.create_task(pre_cache_demo_cases())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    # 通过异步引擎初始化数据库表结构
    async with async_engine.begin() as conn:
        # 异步等待操作完成
        await conn.run_sync(Base.metadata.create_all)

    # Create default admin user (run in thread pool to avoid blocking)
    await create_default_admin_async()

    # 初始化知识库默认数据（标签、分类）
    await init_knowledge_base_defaults()

    # 启动知识生命周期定时任务调度器
    await start_lifecycle_scheduler()

    # 生成器产出值
    yield

    # Shutdown
    logger.info("正在关闭案件分析 API...")

    # 停止知识生命周期定时任务调度器
    await stop_lifecycle_scheduler()

    # 异步等待操作完成
    await ollama_shutdown()
    # 异步等待操作完成
    await dispose_engines()


async def pre_cache_demo_cases() -> None:
    """后台预缓存示例案件，加速首次分析体验."""
    demo_cases: list[str] = [
        "嫌疑人声称案发时在家睡觉，但监控显示其车辆出现在案发现场附近。",
    ]
    # 循环遍历：处理业务逻辑
    for case_text in demo_cases:
        # 异常处理：处理业务逻辑
        try:
            await analyze_pipeline(case_text)
        except httpx.ConnectError as e:
            logger.warning(f"预缓存示例案件网络连接失败: {e}")
        except httpx.HTTPError as e:
            logger.error(f"预缓存示例案件 HTTP 请求失败: {e}")
        except TimeoutError as e:
            logger.error(f"预缓存示例案件异步操作超时: {e}")
        except json.JSONDecodeError as e:
            logger.warning(f"预缓存示例案件 JSON 解析失败: {e}")
        except IntegrityError as e:
            logger.warning(f"预缓存示例案件数据完整性错误: {e}")
        except SQLAlchemyError as e:
            logger.error(f"预缓存示例案件数据库错误: {e}")
        except OSError as e:
            logger.error(f"预缓存示例案件系统错误: {e}")
        except Exception as e:
            logger.exception(f"预缓存示例案件未预期错误: {e}")
            raise


# Initialize app
# 免责声明文本（与前端水印 SYSTEM_DISCLAIMER 完全一致）
_SYSTEM_DISCLAIMER: str = "本系统为辅助参考工具，不构成法律意见。所有结论须经人工审查。"

_OPENAPI_DESCRIPTION: str = (
    "## 帮信罪主观明知智能分析系统 API\n\n"
    f"**{_SYSTEM_DISCLAIMER}**\n\n"
    "本系统基于大语言模型（LLM）针对帮助信息网络犯罪活动罪（帮信罪）中"
    "“主观明知”这一核心要素，提供多维度、可溯源的辅助分析。\n\n"
    "### 主要能力\n"
    "- 案件事实文本的多维度智能分析（事实知识审查 / 模式匹配 / 矛盾分析）\n"
    "- 量刑建议与法条引用\n"
    "- 知识库与图谱增强推理\n"
    "- 相似案例检索\n\n"
    "### 数据合规\n"
    "所有接口在生产环境会通过审计日志中间件记录访问行为，"
    "并对用户数据执行脱敏处理（见 /api/cases 与 /api/analyses 路径）。\n"
)

app = FastAPI(
    # 初始化变量 title
    title="Case Analysis API",
    # 初始化变量 version
    version="1.1.0",
    # 初始化变量 description
    description=_OPENAPI_DESCRIPTION,
    # 初始化变量 lifespan
    lifespan=lifespan,
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# CORS
app.add_middleware(
    CORSMiddleware,
    # 初始化变量 allow_origins
    allow_origins=settings.cors_origins_list,
    # 初始化变量 allow_credentials
    allow_credentials=True,
    # 初始化变量 allow_methods
    allow_methods=settings.cors_methods_list,
    # 初始化变量 allow_headers
    allow_headers=settings.cors_headers_list,
)

# 审计日志中间件：对 /api/cases/* 与 /api/analyses/* 路径下的所有
# GET / POST / PUT / DELETE / PATCH 请求进行自动记录
app.add_middleware(AuditLogMiddleware)

# Include routers
app.include_router(analysis.router)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(knowledge.router)
app.include_router(labels.router)
app.include_router(reports.router)
app.include_router(system.router)
app.include_router(experiment.router)
app.include_router(auth_router)


# Middleware for request context and logging
@app.middleware("http")
async def request_context_middleware(request: Request, call_next: Any) -> Any:
    """请求上下文日志中间件.

    为每个HTTP请求生成唯一UUID作为request_id，通过contextvars和
    loguru.contextualize()注入到整个请求生命周期的所有日志中。

    记录每个请求的方法、路径、内容长度、响应时间和状态码。
    在异步并发请求场景下，确保每个请求的request_id正确关联，不会窜号。

    Args:
        request: 入站 HTTP 请求
        call_next: 下一个中间件或路由处理器

    Returns:
        响应对象
    """
    # 初始化变量 request_id
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    set_request_context(request)

    # 使用上下文管理器管理资源
    with logger.contextualize(request_id=request_id):
        start_time: float = time.time()
        # 初始化变量 response
        response = await call_next(request)

        content_length: str = request.headers.get("content-length", "N/A")
        response_time: int = int((time.time() - start_time) * 1000)

        # 记录日志信息
        logger.info(
            f"Request: {request.method} {request.url.path} | "
            f"Content-Length: {content_length} | "
            f"Response Time: {response_time}ms | "
            f"Status: {response.status_code}"
        )

        # 返回处理结果
        return response


# 应用装饰器: app.get
@app.get("/health")
async def health_check() -> JSONResponse:
    """健康检查端点.

    检查 API 服务和 Ollama 模型服务的可用性。

    Returns:
        JSONResponse: 包含状态信息的 JSON 响应

    Example:
        >>> # GET /health
        >>> {"status": "healthy", "ollama": "available", ...}
    """
    # 初始化变量 client
    client = get_client()
    # 初始化变量 ollama_available
    ollama_available = await client.check_health()

    # 返回处理结果
    return JSONResponse(
        # 初始化变量 content
        content={
            "status": "healthy",
            "ollama": "available" if ollama_available else "unavailable",
            "model": settings.OLLAMA_MODEL,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


# Create default admin user on first run
@retry(
    # 初始化变量 stop
    stop=stop_after_attempt(3),
    # 初始化变量 wait
    wait=wait_exponential(multiplier=1, min=4, max=10),
    # 初始化变量 retry
    retry=tenacity.retry_if_exception_type(OperationalError),
    # 初始化变量 reraise
    reraise=True,
    # 初始化变量 before_sleep
    before_sleep=lambda retry_state: logger.warning(
        "创建默认管理员失败，准备重试 ({}/{}): 异常={}",
        retry_state.attempt_number,
        3,
        retry_state.outcome.exception(),  # type: ignore[union-attr]
    ),
)
async def create_default_admin() -> None:
    """创建默认管理员用户.

    仅在用户不存在时创建，使用配置文件中的默认凭据。
    使用 get_async_db_session 上下文管理器自动处理事务提交、回滚和资源释放。

    Raises:
        数据库操作异常时记录错误日志但不中断启动流程
    """
    # 尝试执行可能抛出异常的代码
    try:
        async with get_async_db_session() as db:
            # 初始化变量 result
            result = await db.execute(
                select(User).filter(
                    User.username == settings.DEFAULT_ADMIN_USERNAME,
                )
            )
            existing = result.scalar_one_or_none()
            # 条件判断: 检查 not existing
            if not existing:
                # 初始化变量 admin
                admin = User(
                    # 初始化变量 username
                    username=settings.DEFAULT_ADMIN_USERNAME,
                    # 初始化变量 hashed_password
                    hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                    # 初始化变量 role
                    role=UserRole.admin,
                    # 初始化变量 is_active
                    is_active=True,
                    # 初始化变量 created_at
                    created_at=datetime.now(UTC),
                )
                db.add(admin)
                # 记录日志信息
                logger.info(
                    "已创建默认管理员用户: {}",
                    settings.DEFAULT_ADMIN_USERNAME,
                )
    # 捕获并处理异常
    except IntegrityError as e:
        # 记录日志信息
        logger.warning(
            "创建默认管理员数据完整性错误: username={}, error={}",
            settings.DEFAULT_ADMIN_USERNAME,
            e,
        )
    # 捕获并处理异常
    except OperationalError as e:
        # 记录日志信息
        logger.error(
            "创建默认管理员数据库连接失败: username={}, error={}",
            settings.DEFAULT_ADMIN_USERNAME,
            e,
        )
    # 捕获并处理异常
    except SQLAlchemyError as e:
        # 记录日志信息
        logger.error(
            "创建默认管理员数据库错误: username={}, error={}",
            settings.DEFAULT_ADMIN_USERNAME,
            e,
        )
    # 捕获并处理异常
    except ValueError as e:
        # 记录日志信息
        logger.error(
            "创建默认管理员配置错误: username={}, error={}",
            settings.DEFAULT_ADMIN_USERNAME,
            e,
        )
    # 捕获并处理异常
    except Exception as e:
        # 记录日志信息
        logger.exception(
            "创建默认管理员未预期错误: username={}, error={}",
            settings.DEFAULT_ADMIN_USERNAME,
            e,
        )
        raise


async def create_default_admin_async() -> None:
    """启动时调用 create_default_admin()，避免阻塞事件循环."""
    # 异步等待操作完成
    await create_default_admin()


# ---------------------------------------------------------------------------
# 知识库默认数据初始化
# ---------------------------------------------------------------------------

# 核心法律标签（启动时自动创建）
_DEFAULT_TAGS: list[dict[str, str]] = [
    {"name": "帮信罪", "description": "帮助信息网络犯罪活动罪相关", "color": "#ef4444"},
    {"name": "主观明知", "description": "主观明知要件的认定与判断", "color": "#3b82f6"},
    {"name": "量刑", "description": "量刑标准与量刑情节", "color": "#22c55e"},
    {"name": "帮助行为", "description": "帮助行为的认定与边界", "color": "#f59e0b"},
    {"name": "共同犯罪", "description": "共同犯罪相关法律问题", "color": "#8b5cf6"},
    {"name": "证据规则", "description": "证据采信与证明标准", "color": "#06b6d4"},
    {"name": "程序正义", "description": "程序合法性审查", "color": "#ec4899"},
    {"name": "司法解释", "description": "相关司法解释与指导意见", "color": "#14b8a6"},
    {"name": "典型案例", "description": "具有参考价值的典型案例", "color": "#f97316"},
]


# 应用装饰器: retry
@retry(
    # 初始化变量 stop
    stop=stop_after_attempt(3),
    # 初始化变量 wait
    wait=wait_exponential(multiplier=1, min=4, max=10),
    # 初始化变量 retry
    retry=tenacity.retry_if_exception_type(OperationalError),
    # 初始化变量 reraise
    reraise=True,
    # 初始化变量 before_sleep
    before_sleep=lambda retry_state: logger.warning(
        "初始化知识库默认数据失败，准备重试 ({}/{}): 异常={}",
        retry_state.attempt_number,
        3,
        retry_state.outcome.exception(),  # type: ignore[union-attr]
    ),
)
async def init_knowledge_base_defaults() -> None:
    """初始化知识库默认数据.

    检查并创建默认标签集，验证默认分类条目的完整性和正确性，
    确保知识库在首次使用时具备基础的标签分类体系。
    """
    # 尝试执行可能抛出异常的代码
    try:
        async with get_async_db_session() as db:
            # 初始化变量 existing_tags
            existing_tags = await get_all_tags(db)
            existing_tag_names: set[str] = {t.name for t in existing_tags}

            # 记录日志信息
            logger.info(
                "知识库默认标签检查: 现有标签 {} 个",
                len(existing_tags),
            )

            # 导入模块: from sqlalchemy
            from sqlalchemy import select  # noqa: PLC0415

            # 导入模块: from app.models.user
            from app.models.user import User  # noqa: PLC0415
            admin_user = await db.execute(select(User).where(User.username == "admin"))
            # 初始化变量 admin_user
            admin_user = admin_user.scalar_one_or_none()

            # 遍历: for tag_def in _DEFAULT_TAGS:
            for tag_def in _DEFAULT_TAGS:
                # 条件判断: 检查 tag_def["name"] not in existing_tag_name
                if tag_def["name"] not in existing_tag_names:
                    # 初始化变量 tag_data
                    tag_data = KnowledgeTagCreate(
                        name=tag_def["name"],
                    )
                    # 异步等待操作完成
                    await create_tag(db, tag_data, user=admin_user)
                    # 记录日志信息
                    logger.info(
                        "已创建默认知识标签: {}",
                        tag_def["name"],
                    )

            # 记录日志信息
            logger.info("知识库默认标签初始化完成")
    # 捕获并处理异常
    except IntegrityError as e:
        # 记录日志信息
        logger.warning(f"知识库默认数据完整性错误: {e}")
    # 捕获并处理异常
    except OperationalError as e:
        # 记录日志信息
        logger.error(f"知识库默认数据数据库连接失败: {e}")
    # 捕获并处理异常
    except SQLAlchemyError as e:
        # 记录日志信息
        logger.error(f"知识库默认数据数据库错误: {e}")
    # 捕获并处理异常
    except ValueError as e:
        # 记录日志信息
        logger.error(f"知识库默认数据配置错误: {e}")
    # 捕获并处理异常
    except Exception as e:
        # 记录日志信息
        logger.exception(f"知识库默认数据初始化未预期错误: {e}")
        raise


# ---------------------------------------------------------------------------
# 知识生命周期定时任务调度器管理
# ---------------------------------------------------------------------------


async def start_lifecycle_scheduler() -> None:
    """启动知识生命周期定时任务调度器.

    配置 apply_decay（每日执行）和 lint_knowledge_base（每周执行）的定时任务。
    """
    global _lifecycle_scheduler  # noqa: PLW0603

    # 条件判断: 检查 _lifecycle_scheduler is not None
    if _lifecycle_scheduler is not None:
        logger.warning("知识生命周期调度器已存在，跳过重复启动")
        return# 返回处理结果
        return

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 schedule_config
        schedule_config = ScheduleConfig(
            # 初始化变量 decay_interval
            decay_interval=AnalysisConfig.KNOWLEDGE_DECAY_SCHEDULE_INTERVAL,
            # 初始化变量 lint_interval
            lint_interval=AnalysisConfig.KNOWLEDGE_LINT_SCHEDULE_INTERVAL,
            # 初始化变量 decay_enabled
            decay_enabled=True,
            # 捕获异常：处理业务逻辑
    lint_enabled=True,
        )
        _lifecycle_scheduler = KnowledgeLifecycleScheduler(
            config=schedule_config,
        )
        # 异步等待操作完成
        await _lifecycle_scheduler.start()
        # 记录日志信息
        logger.info("知识生命周期定时任务调度器已启动")
    # 捕获并处理异常
    except SQLAlchemyError as e:
        # 记录日志信息
        logger.error(f"知识生命周期调度器启动数据库错误: {e}")
        _lifecycle_scheduler = None
    # 捕获并处理异常
    except RuntimeError as e:
        # 记录日志信息
        logger.error(f"知识生命周期调度器启动运行时错误: {e}")
        _lifecycle_scheduler = None
    # 捕获并处理异常
    except Exception as e:  # noqa: BLE001
        logger.exception(f"知识生命周期调度器启动未预期错误: {e}")
        _lifecycle_scheduler = None


async def stop_lifecycle_scheduler() -> None:
    """停止知识生命周期定时任务调度器."""
    global _lifecycle_scheduler  # noqa: PLW0603

    # 条件判断: 检查 _lifecycle_scheduler is None
    if _lifecycle_scheduler is None:
        # 返回处理结果
        return

    # 尝试执行可能抛出异常的代码
    try:
        # 异步等待操作完成
        await _lifecycle_scheduler.stop()
        # 记录日志信息
        logger.info("知识生命周期定时任务调度器已停止")
    # 捕获并处理异常
    except SQLAlchemyError as e:
        # 记录日志信息
        logger.error(f"知识生命周期调度器停止数据库错误: {e}")
    # 捕获并处理异常
    except RuntimeError as e:
        # 记录日志信息
        logger.error(f"知识生命周期调度器停止运行时错误: {e}")
    # 捕获并处理异常
    except Exception as e:  # noqa: BLE001
        logger.exception(f"知识生命周期调度器停止未预期错误: {e}")
    # 最终清理代码，无论是否异常都会执行
    finally:
        _lifecycle_scheduler = None


# 应用装饰器: app.get
@app.get("/metrics")
async def metrics() -> Response:
    """暴露 Prometheus 格式的监控指标."""
    # 返回处理结果
    return Response(generate_latest(), media_type="text/plain")


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    # 导入模块: uvicorn
    import uvicorn

    uvicorn.run(
        "app.main:app",
        # 初始化变量 host
        host=settings.SERVER_HOST,
        # 初始化变量 port
        port=settings.SERVER_PORT,
        # 初始化变量 reload
        reload=settings.DEBUG,
    )
