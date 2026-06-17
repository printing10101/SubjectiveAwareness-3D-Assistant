"""FastAPI 应用程序入口模块.

负责应用初始化、中间件配置、路由注册、后台任务调度和生命周期管理。
"""

import asyncio
import json
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import httpx
import sentry_sdk
import tenacity
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from loguru import logger
from prometheus_client import generate_latest
from sentry_sdk.integrations.fastapi import FastApiIntegration
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import AnalysisConfig, settings
from app.database import (
    Base,
    async_engine,
    dispose_engines,
    get_async_db_session,
)
from app.models.user import User, UserRole
from app.routers import (
    analysis,
    cases,
    documents,
    experiment,
    knowledge,
    reports,
    system,
)
from app.schemas.knowledge import KnowledgeTagCreate
from app.services.knowledge_lifecycle_service import (
    KnowledgeLifecycleScheduler,
    ScheduleConfig,
)
from app.services.knowledge_service import create_tag, get_all_tags
from app.services.ollama_client import (
    get_client,
    shutdown as ollama_shutdown,
    startup as ollama_startup,
)
from app.services.pipeline import analyze_pipeline
from app.utils.auth import auth_router, get_password_hash
from app.utils.logger import request_id_var, setup_logging
from app.utils.rate_limit import limiter, set_request_context


# Initialize logging system
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_dir=settings.LOG_DIR,
)

# Keep strong references to background tasks to prevent garbage collection
_background_tasks: set[asyncio.Task[Any]] = set()

# 知识生命周期定时任务调度器实例
_lifecycle_scheduler: KnowledgeLifecycleScheduler | None = None

# Disable rate limiter in debug/development mode
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
        logger.info("SENTRY_DSN 未配置，跳过 Sentry 初始化")
        return

    environment = settings.SENTRY_ENVIRONMENT or settings.APP_ENV
    sample_rate = max(0.0, min(1.0, settings.SENTRY_TRACES_SAMPLE_RATE))

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=sample_rate,
        attach_stacktrace=settings.SENTRY_ATTACH_STACKTRACE,
        send_default_pii=settings.SENTRY_SEND_DEFAULT_PII,
        timeout=settings.SENTRY_TIMEOUT,
        integrations=[FastApiIntegration()],
    )

    sentry_sdk.set_tag("app_name", "Case Analysis API")
    sentry_sdk.set_tag("app_env", environment)

    logger.info(
        "Sentry 初始化完成: environment={}, traces_sample_rate={}",
        environment,
        sample_rate,
    )


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
    if settings.OLLAMA_ENABLED:
        logger.info(
            "Ollama URL: {}, Model: {}",
            settings.OLLAMA_BASE_URL,
            settings.OLLAMA_MODEL,
        )
        await ollama_startup()
    else:
        logger.info(
            "本地 Ollama 推理引擎未启用；系统将优先使用 DeepSeek 云端模型，未配置时使用规则化专业分析兜底。"
        )

    # 后台预缓存示例案件
    logger.info("后台预缓存示例案件...")
    task = asyncio.create_task(pre_cache_demo_cases())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    # 通过异步引擎初始化数据库表结构
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create default admin user (run in thread pool to avoid blocking)
    await create_default_admin_async()

    # 初始化知识库默认数据（标签、分类）
    await init_knowledge_base_defaults()

    # 启动知识生命周期定时任务调度器
    await start_lifecycle_scheduler()

    yield

    # Shutdown
    logger.info("正在关闭案件分析 API...")

    # 停止知识生命周期定时任务调度器
    await stop_lifecycle_scheduler()

    if settings.OLLAMA_ENABLED:
        await ollama_shutdown()
    await dispose_engines()


async def pre_cache_demo_cases() -> None:
    """后台预缓存示例案件，加速首次分析体验."""
    demo_cases: list[str] = [
        "嫌疑人声称案发时在家睡觉，但监控显示其车辆出现在案发现场附近。",
    ]
    for case_text in demo_cases:
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
app = FastAPI(title="Case Analysis API", version="1.0.0", lifespan=lifespan)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=settings.cors_methods_list,
    allow_headers=settings.cors_headers_list,
)

# Include routers
app.include_router(analysis.router)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(knowledge.router)
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
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    set_request_context(request)

    with logger.contextualize(request_id=request_id):
        start_time: float = time.time()
        response = await call_next(request)

        content_length: str = request.headers.get("content-length", "N/A")
        response_time: int = int((time.time() - start_time) * 1000)

        logger.info(
            f"Request: {request.method} {request.url.path} | "
            f"Content-Length: {content_length} | "
            f"Response Time: {response_time}ms | "
            f"Status: {response.status_code}"
        )

        return response


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
    ollama_available = False
    if getattr(settings, "OLLAMA_ENABLED", False):
        client = get_client()
        ollama_available = await client.check_health()

    return JSONResponse(
        content={
            "status": "healthy",
            "ollama": "available" if ollama_available else "disabled",
            "deepseek_cloud": "configured" if getattr(settings, "DEEPSEEK_API_KEY", None) else "not_configured",
            "model": getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat"),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


# Create default admin user on first run
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=tenacity.retry_if_exception_type(OperationalError),
    reraise=True,
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
    try:
        async with get_async_db_session() as db:
            result = await db.execute(
                select(User).filter(
                    User.username == settings.DEFAULT_ADMIN_USERNAME,
                )
            )
            existing = result.scalar_one_or_none()
            if not existing:
                admin = User(
                    username=settings.DEFAULT_ADMIN_USERNAME,
                    hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                    role=UserRole.admin,
                    is_active=True,
                    created_at=datetime.now(UTC),
                )
                db.add(admin)
                logger.info(
                    "已创建默认管理员用户: {}",
                    settings.DEFAULT_ADMIN_USERNAME,
                )
    except IntegrityError as e:
        logger.warning(
            "创建默认管理员数据完整性错误: username={}, error={}",
            settings.DEFAULT_ADMIN_USERNAME,
            e,
        )
    except OperationalError as e:
        logger.error(
            "创建默认管理员数据库连接失败: username={}, error={}",
            settings.DEFAULT_ADMIN_USERNAME,
            e,
        )
    except SQLAlchemyError as e:
        logger.error(
            "创建默认管理员数据库错误: username={}, error={}",
            settings.DEFAULT_ADMIN_USERNAME,
            e,
        )
    except ValueError as e:
        logger.error(
            "创建默认管理员配置错误: username={}, error={}",
            settings.DEFAULT_ADMIN_USERNAME,
            e,
        )
    except Exception as e:
        logger.exception(
            "创建默认管理员未预期错误: username={}, error={}",
            settings.DEFAULT_ADMIN_USERNAME,
            e,
        )
        raise


async def create_default_admin_async() -> None:
    """启动时调用 create_default_admin()，避免阻塞事件循环."""
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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=tenacity.retry_if_exception_type(OperationalError),
    reraise=True,
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
    try:
        async with get_async_db_session() as db:
            existing_tags = await get_all_tags(db)
            existing_tag_names: set[str] = {t.name for t in existing_tags}

            logger.info(
                "知识库默认标签检查: 现有标签 {} 个",
                len(existing_tags),
            )

            from app.models.knowledge_tag import KnowledgeTag  # noqa: PLC0415

            for tag_def in _DEFAULT_TAGS:
                if tag_def["name"] not in existing_tag_names:
                    # 启动期默认标签属于系统初始化数据，不应依赖登录态，
                    # 直接写入以保证新环境可启动、可运行。
                    db.add(KnowledgeTag(
                        name=tag_def["name"],
                        description=tag_def.get("description"),
                        color=tag_def.get("color"),
                    ))
                    logger.info(
                        "已创建默认知识标签: {}",
                        tag_def["name"],
                    )

            logger.info("知识库默认标签初始化完成")
    except IntegrityError as e:
        logger.warning(f"知识库默认数据完整性错误: {e}")
    except OperationalError as e:
        logger.error(f"知识库默认数据数据库连接失败: {e}")
    except SQLAlchemyError as e:
        logger.error(f"知识库默认数据数据库错误: {e}")
    except ValueError as e:
        logger.error(f"知识库默认数据配置错误: {e}")
    except Exception as e:
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

    if _lifecycle_scheduler is not None:
        logger.warning("知识生命周期调度器已存在，跳过重复启动")
        return

    try:
        schedule_config = ScheduleConfig(
            decay_interval=AnalysisConfig.KNOWLEDGE_DECAY_SCHEDULE_INTERVAL,
            lint_interval=AnalysisConfig.KNOWLEDGE_LINT_SCHEDULE_INTERVAL,
            decay_enabled=True,
            lint_enabled=True,
        )
        _lifecycle_scheduler = KnowledgeLifecycleScheduler(
            config=schedule_config,
        )
        await _lifecycle_scheduler.start()
        logger.info("知识生命周期定时任务调度器已启动")
    except SQLAlchemyError as e:
        logger.error(f"知识生命周期调度器启动数据库错误: {e}")
        _lifecycle_scheduler = None
    except RuntimeError as e:
        logger.error(f"知识生命周期调度器启动运行时错误: {e}")
        _lifecycle_scheduler = None
    except Exception as e:  # noqa: BLE001
        logger.exception(f"知识生命周期调度器启动未预期错误: {e}")
        _lifecycle_scheduler = None


async def stop_lifecycle_scheduler() -> None:
    """停止知识生命周期定时任务调度器."""
    global _lifecycle_scheduler  # noqa: PLW0603

    if _lifecycle_scheduler is None:
        return

    try:
        await _lifecycle_scheduler.stop()
        logger.info("知识生命周期定时任务调度器已停止")
    except SQLAlchemyError as e:
        logger.error(f"知识生命周期调度器停止数据库错误: {e}")
    except RuntimeError as e:
        logger.error(f"知识生命周期调度器停止运行时错误: {e}")
    except Exception as e:  # noqa: BLE001
        logger.exception(f"知识生命周期调度器停止未预期错误: {e}")
    finally:
        _lifecycle_scheduler = None


@app.get("/metrics")
async def metrics() -> Response:
    """暴露 Prometheus 格式的监控指标."""
    return Response(generate_latest(), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn  # noqa: PLC0415

    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
    )
