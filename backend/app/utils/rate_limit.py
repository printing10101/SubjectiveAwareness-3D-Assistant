"""限流工具模块.

提供基于 slowapi 的角色感知分级限流功能，
支持按用户角色（匿名/普通/管理员）和 IP/用户ID 进行差异化限流。
所有限流参数均从 AnalysisConfig 动态读取，无硬编码数值。
"""

from contextvars import ContextVar
from datetime import UTC, datetime

from fastapi import Request
from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import AnalysisConfig


_request_ctx: ContextVar[Request | None] = ContextVar(
    "rate_limit_request", default=None
)


def set_request_context(request: Request) -> None:
    """在中间件中设置当前请求上下文，供限流回调使用."""
    _request_ctx.set(request)


def _extract_user_info(request: Request) -> tuple[str | None, str | None, str | None]:
    """从请求中提取用户身份信息.

    解析 Authorization 头中的 JWT 令牌，提取用户名和角色。
    不抛出异常，解析失败时返回 None。

    Args:
        request: HTTP 请求对象

    Returns:
        (user_id, role, ip) 三元组，匿名用户仅 ip 有值
    """
    ip = get_remote_address(request)
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            from app.utils.auth import decode_token_with_fallback  # noqa: PLC0415

            token = auth_header.split(" ")[1]
            payload = decode_token_with_fallback(token)
            username = payload.get("sub", "")
            role = payload.get("role", "user")
            if username:
                return username, role, ip
    except Exception:  # noqa: BLE001
        logger.debug("限流标识解析失败，回退为匿名用户")
    return None, None, ip


def _resolve_rate_limit_key(request: Request) -> str:
    """获取角色感知的限流标识键.

    已认证用户基于用户ID + 角色进行分级限流，
    匿名用户基于 IP 地址限流。

    Returns:
        限流标识字符串，格式为 "角色:标识符"
    """
    user_id, role, ip = _extract_user_info(request)
    if user_id and role:
        return f"{role}:{user_id}"
    return f"anon:{ip}"


def _log_rate_limit_breach(request: Request, response_headers: dict[str, str]) -> None:  # noqa: ARG001
    """记录限流触发日志.

    包含用户身份、角色、IP、请求路径和触发时间等完整信息，
    便于后续问题排查和策略优化。

    Args:
        request: HTTP 请求对象
        response_headers: 限流响应头（未使用，保留以兼容 slowapi 接口）
    """
    user_id, role, ip = _extract_user_info(request)
    role_display = role or "匿名用户"
    user_display = user_id or ip

    logger.warning(
        f"限流触发 | 角色: {role_display} | "
        f"标识: {user_display} | "
        f"IP: {ip} | "
        f"路径: {request.url.path} | "
        f"时间: {datetime.now(UTC).isoformat()}"
    )


def get_analyze_rate_limit() -> str:
    """根据用户角色动态返回分析端点的限流值.

    从 AnalysisConfig 读取各角色的限流配置，无硬编码。
    已认证用户按角色（admin/user）区分配额，
    匿名用户使用独立的低配额。
    通过 contextvars 获取当前请求上下文，适配 slowapi 零参数回调接口。

    Returns:
        限流字符串，格式由 AnalysisConfig 中的对应配置项决定
    """
    request = _request_ctx.get()
    if request is None:
        return AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS
    user_id, role, _ip = _extract_user_info(request)
    if not user_id or not role:
        return AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS
    if role == "admin":
        return AnalysisConfig.RATE_LIMIT_ANALYZE_ADMIN
    return AnalysisConfig.RATE_LIMIT_ANALYZE_USER


# 初始化 Limiter，使用角色感知的键函数
limiter = Limiter(
    key_func=_resolve_rate_limit_key,
    default_limits=[AnalysisConfig.RATE_LIMIT_DEFAULT],
)
# 注入自定义限流触发日志回调
limiter._on_breach = _log_rate_limit_breach  # type: ignore[attr-defined]
