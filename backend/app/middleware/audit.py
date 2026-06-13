"""审计日志中间件.

对 /api/cases/* 与 /api/analyses/* 路径下的 GET / POST / PUT / DELETE / PATCH
请求进行自动审计日志记录，捕获操作者、目标资源、客户端 IP、响应状态等
关键信息，并将记录持久化到 audit_logs 表中。

中间件设计原则：
    1. 不影响主请求链路：日志写入失败仅记录错误日志，绝不阻塞或破坏响应。
    2. 用户识别尽力而为：解析 Authorization 头部的 Bearer 令牌以识别用户；
       解析失败时记录为匿名用户，绝不抛错中断请求。
    3. 性能隔离：审计写入通过独立异步会话处理，避免污染请求级事务。
    4. 路径匹配保守：使用严格前缀匹配，仅审计明确列出的接口。
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs

import jwt
from fastapi import Request, Response
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.utils.auth import decode_token_with_fallback


# 审计生效的路径前缀
_AUDITED_PATH_PREFIXES: tuple[str, ...] = (
    "/api/cases",
    "/api/analyses",
)

# 审计生效的 HTTP 方法
_AUDITED_METHODS: frozenset[str] = frozenset(
    {"GET", "POST", "PUT", "DELETE", "PATCH"}
)

# 资源类型推断规则
_CASE_SEGMENT_KEYWORDS: tuple[str, ...] = ("cases", "case")
_ANALYSIS_SEGMENT_KEYWORDS: tuple[str, ...] = ("analyses", "analysis", "analyze")

# 资源 ID 字符串最大长度（避免写入超长 URL 片段污染审计表）
_TARGET_ID_MAX_LENGTH: int = 64

# Bearer 认证头部应包含两个分段（scheme + token）
_BEARER_PARTS_LENGTH: int = 2


def _match_audited_path(path: str) -> bool:
    """判断给定路径是否在审计范围内.

    使用严格前缀匹配，避免误审计其他相近路径。

    Args:
        path: 请求路径

    Returns:
        bool: 当且仅当路径位于受审计路径前缀下时返回 True
    """
    return any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in _AUDITED_PATH_PREFIXES
    )


def _infer_target_type(path: str) -> str:
    """根据请求路径推断目标资源类型.

    Args:
        path: 请求路径

    Returns:
        str: 资源类型标识符（case/analysis/other）
    """
    normalized: str = path.lower()
    for keyword in _CASE_SEGMENT_KEYWORDS:
        if keyword in normalized:
            return "case"
    for keyword in _ANALYSIS_SEGMENT_KEYWORDS:
        if keyword in normalized:
            return "analysis"
    return "other"


def _extract_target_id(path: str) -> str | None:
    """从请求路径中提取目标资源 ID.

    提取规则：
    1. 先剥离查询字符串
    2. 按 / 切分，取最后一个非空片段
    3. 仅在片段为纯数字或合法 ID 形式时返回

    Args:
        path: 完整请求路径（可能含查询字符串）

    Returns:
        str | None: 提取出的资源 ID，无法识别时返回 None
    """
    clean_path: str = path.split("?", 1)[0]
    segments: list[str] = [s for s in clean_path.split("/") if s]
    if not segments:
        return None
    last: str = segments[-1]
    # 过滤明显的非 ID 片段（如 "cases", "analyze"）
    if last.lower() in _CASE_SEGMENT_KEYWORDS or last.lower() in _ANALYSIS_SEGMENT_KEYWORDS:
        return None
    if not last or len(last) > _TARGET_ID_MAX_LENGTH:
        return None
    return last


def _resolve_user_from_token(authorization: str | None) -> tuple[int | None, str | None]:  # noqa: PLR0911
    """从 Authorization 头部解析用户身份.

    仅在头部存在且以 Bearer 开头时尝试解析，避免对无认证请求做无谓处理。
    任何解析异常均被吞掉并返回匿名结果，绝不向上抛出。

    Args:
        authorization: Authorization 头部原始值

    Returns:
        tuple[int | None, str | None]: (user_id, username)，解析失败时均为 None
    """
    if not authorization:
        return None, None
    parts: list[str] = authorization.split(None, 1)
    if len(parts) != _BEARER_PARTS_LENGTH or parts[0].lower() != "bearer":
        return None, None
    token: str = parts[1].strip()
    if not token:
        return None, None
    try:
        payload: dict[str, Any] = decode_token_with_fallback(token)
    except jwt.InvalidTokenError:
        return None, None
    except Exception as exc:  # noqa: BLE001
        logger.debug("审计中间件令牌解析异常: {}", exc)
        return None, None

    sub: Any = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        return None, None
    return None, sub


def _extract_client_ip(request: Request) -> str:
    """提取客户端真实 IP.

    优先从常见代理头部（X-Forwarded-For, X-Real-IP）读取，
    回退到 request.client.host。

    Args:
        request: FastAPI 请求对象

    Returns:
        str: 客户端 IP 字符串，无法识别时返回 "unknown"
    """
    for header in ("x-forwarded-for", "x-real-ip"):
        value: str | None = request.headers.get(header)
        if value:
            # X-Forwarded-For 可能为 "client, proxy1, proxy2"
            return value.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def _summarize_query(path: str, max_length: int = 500) -> str | None:
    """安全地摘要查询字符串，避免记录敏感参数.

    Args:
        path: 完整请求路径
        max_length: 返回字符串的最大长度

    Returns:
        str | None: 截断后的查询字符串，无查询参数时返回 None
    """
    if "?" not in path:
        return None
    query: str = path.split("?", 1)[1]
    if not query:
        return None
    # 简单遮蔽敏感参数
    sensitive_keys: tuple[str, ...] = ("password", "token", "secret", "apikey", "api_key")
    parsed: list[tuple[str, str]] = []
    for pair in parse_qs(query, keep_blank_values=True).items():
        key: str = pair[0]
        values: list[str] = pair[1]
        if any(s in key.lower() for s in sensitive_keys):
            parsed.append((key, "***"))
        else:
            parsed.extend((key, v) for v in values)
    rendered: str = "&".join(f"{k}={v}" for k, v in parsed)
    if len(rendered) > max_length:
        rendered = rendered[: max_length - 3] + "..."
    return rendered


def _build_audit_record(
    *,
    request: Request,
    response: Response,
    started_at: datetime,
) -> AuditLog:
    """根据请求与响应构建审计日志实例.

    Args:
        request: FastAPI 请求对象
        response: Starlette 响应对象
        started_at: 请求开始时间戳

    Returns:
        AuditLog: 待持久化的审计日志实例
    """
    method: str = request.method.upper()
    path: str = request.url.path
    full_path: str = str(request.url)

    user_id, username = _resolve_user_from_token(
        request.headers.get("authorization"),
    )

    return AuditLog(
        user_id=user_id,
        username=username or "anonymous",
        action=method,
        method=method,
        target_type=_infer_target_type(path),
        target_id=_extract_target_id(path),
        path=path,
        ip=_extract_client_ip(request),
        status_code=response.status_code,
        user_agent=(request.headers.get("user-agent") or "")[:500] or None,
        extra=_summarize_query(full_path),
        timestamp=started_at,
    )


async def _persist_audit_record(record: AuditLog) -> None:
    """将审计记录持久化到数据库.

    使用独立异步会话，写入失败仅记录错误日志，绝不向上抛出。

    Args:
        record: 待持久化的审计日志实例
    """
    try:
        async with AsyncSessionLocal() as session:
            try:
                session.add(record)
                await session.commit()
            except SQLAlchemyError as db_exc:
                await session.rollback()
                logger.error(
                    "审计日志写入数据库失败: action={}, path={}, error={}",
                    record.action,
                    record.path,
                    db_exc,
                )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "审计中间件创建会话失败: action={}, path={}, error={}",
            record.action,
            record.path,
            exc,
        )


class AuditLogMiddleware(BaseHTTPMiddleware):
    """审计日志中间件.

    对 /api/cases/* 与 /api/analyses/* 路径下的所有 GET / POST / PUT / DELETE /
    PATCH 请求进行审计日志记录。审计写入在响应返回后以 fire-and-forget 方式
    异步执行，主请求链路不被阻塞或污染。

    Attributes:
        继承自 BaseHTTPMiddleware，无需额外状态。
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        # 显式持有后台任务引用，避免被 GC 提前回收
        self._background_tasks: set[asyncio.Task[None]] = set()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """处理 HTTP 请求并记录审计日志.

        Args:
            request: FastAPI 请求对象
            call_next: 后续中间件或路由处理器

        Returns:
            Response: 下游响应对象
        """
        path: str = request.url.path
        method: str = request.method.upper()

        # 非受审计路径或方法：直接放行，不消耗任何资源
        if method not in _AUDITED_METHODS or not _match_audited_path(path):
            return await call_next(request)

        started_at: datetime = datetime.now(UTC)

        try:
            response: Response = await call_next(request)
        except Exception:
            # 即便下游异常也要尝试记录（状态码 500）
            error_response = Response(status_code=500)
            try:
                record = _build_audit_record(
                    request=request,
                    response=error_response,
                    started_at=started_at,
                )
                # 使用 create_task 异步持久化，不阻塞错误传播
                self._background_tasks.add(
                    asyncio.create_task(_persist_audit_record(record))
                )
            except Exception as build_exc:  # noqa: BLE001
                logger.error("审计日志构建失败: {}", build_exc)
            raise

        # fire-and-forget 持久化，避免阻塞响应返回
        try:
            record = _build_audit_record(
                request=request,
                response=response,
                started_at=started_at,
            )
            self._background_tasks.add(
                asyncio.create_task(_persist_audit_record(record))
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("审计日志构建失败: {}", exc)

        return response


__all__ = ["AuditLogMiddleware"]
