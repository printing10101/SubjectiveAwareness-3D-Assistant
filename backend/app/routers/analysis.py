"""分析路由模块.

提供案件分析 API 端点，支持直接文本分析和缓存机制。
所有数据库操作均使用异步 API。
"""

# 导入模块: json
import json
# 导入模块: from datetime
from datetime import UTC, datetime

# 导入模块: sentry_sdk
import sentry_sdk
# 导入模块: from fastapi
from fastapi import APIRouter, HTTPException, Request
# 导入模块: from fastapi.responses
from fastapi.responses import JSONResponse
# 导入模块: from loguru
from loguru import logger
# 导入模块: from sqlalchemy
from sqlalchemy import select

# 导入模块: from app.database
from app.database import get_async_db_session
# 导入模块: from app.models.analysis
from app.models.analysis import Analysis
# 导入模块: from app.models.case
from app.models.case import Case
# 导入模块: from app.models.user
from app.models.user import User, UserRole
# 导入模块: from app.schemas.analysis
from app.schemas.analysis import AnalyzeRequest
# 导入模块: from app.services.pipeline
from app.services.pipeline import analyze_pipeline
# 导入模块: from app.types.analysis_v2
from app.types.analysis_v2 import AnalysisResultV2
# 导入模块: from app.utils.auth
from app.utils.auth import optional_current_user_dep
# 导入模块: from app.utils.cache
from app.utils.cache import cache_manager
# 导入模块: from app.utils.common
from app.utils.common import generate_cache_key
# 导入模块: from app.utils.rate_limit
from app.utils.rate_limit import get_analyze_rate_limit, limiter


# 初始化变量 router
router = APIRouter(prefix="/api", tags=["analysis"])


# 应用装饰器: router.post
@router.post("/analyze")
# 应用装饰器: limiter.limit
@limiter.limit(get_analyze_rate_limit)
async def analyze_case(
    # 函数 analyze_case 的初始化逻辑
    request: Request,  # noqa: ARG001
    analyze_request: AnalyzeRequest,
    current_user: User | None = optional_current_user_dep,
) -> AnalysisResultV2:
    """执行案件分析.

    接收案件文本，调用分析管道进行智能分析。
    支持缓存机制，重复分析直接返回缓存结果。

    Args:
        request: HTTP 请求对象（由 FastAPI 自动注入）
        analyze_request: 分析请求体
        current_user: 当前用户（可选认证）

    Returns:
        AnalysisResult: 分析结果字典

    Raises:
        HTTPException 502: 分析服务不可用
        HTTPException 429: 请求过于频繁（由 slowapi 按角色差异化限流处理）
            - 匿名用户: 基于IP限流，配额由 AnalysisConfig.RATE_LIMIT_ANALYZE_ANONYMOUS 决定
            - 普通用户: 基于用户ID限流，配额由 AnalysisConfig.RATE_LIMIT_ANALYZE_USER 决定
            - 管理员: 基于用户ID限流，配额由 AnalysisConfig.RATE_LIMIT_ANALYZE_ADMIN 决定
    """
    case_text: str = analyze_request.case_text
    # Pydantic 在 use_enum_values=True 下，analyze_request.mode 已是字符串
    # （如 "auto"/"single"/"multi"），不能再访问 .value，这里统一转 str 兜底，
    # 兼容 AnalysisMode 枚举和裸字符串两种情况。
    mode_value: str = (
        analyze_request.mode.value
        # 条件判断：处理业务逻辑
        if hasattr(analyze_request.mode, "value")
        else str(analyze_request.mode)
    )
    case_id: int | None = analyze_request.case_id

    # 为 Sentry 提供丰富的业务上下文，便于错误定位
    sentry_sdk.set_context(
        "analysis_request",
        {
            "text_length": len(case_text),
            "mode": mode_value,
            "case_id": case_id,
            "has_existing_case": case_id is not None,
        },
    )
    sentry_sdk.set_tag("analys    # 条件判断：处理业务逻辑
is_mode", mode_value)
    # 条件判断: 检查 current_user
    if current_user:
        sentry_sdk.set_user(
            {
                "id": str(current_user.id),
                "username": current_user.username,
                        # 条件判断：处理业务逻辑
        "role": current_user.role.value
                # 条件判断: 检查 hasattr(current_user.role, "value")
                if hasattr(current_user.role, "value")
                else str(current_user.role),
            },
        )
    # 其他情况的默认处理
    else:
        sentry_sdk.set_user(None)

    sentry_sdk.add_breadcrumb(
        # 初始化变量 category
        category="business",
        # 初始化变量 message
        message="analyze_request_received",
        # 初始化变量 level
        level="info",
        # 初始化变量 data
        data={
            "text_length": len(case_text),
            "mode": mode_value,
            "case_id": case_id,
            "user": current_user.username if current_user else "anonymous",
        },
    )

    # 记录日志信息
    logger.info(
        f"收到分析请求 (文本长度: {len(case_text)}, "
  
    # 条件判断：处理业务逻辑
      f"用户: {current_user.username if current_user else '匿名'})"
    )

    # 条件判断: 检查 case_id
    if case_id:
        async with get_async_db_session() as db:
            # 初始化变量 result
            result = await db.execute(s
            # 条件判断：处理业务逻辑
elect(Case).where(Case.id == case_id))
            # 初始化变量 db_case
            db_case = result.scalar_one_or_none()

            # 条件判断: 检查 not db_case
            if not db_case:
                # 返回处理结果
                return JSONResponse(
                    # 初始化变量 status_code
                    status_code=404,
                    # 初始化变量 content
                    content={
                        "error_cod
            # 条件判断：处理业务逻辑
e": "CASE_NOT_FOUND",
                        "message": "Case not found",
                    },
                )

            # 条件判断: 检查 not current_user
            if not current_user:
                # 返回处理结果
                return JSONResponse(
                    # 初始化变量 status_code
                    status_code=403,
                    # 初始化变量 content
                    content={
                        "error_code": "PERMISSION_DENIED",
                        "message": "Permission denied to access this case",
                    }            # 条件判断：处理业务逻辑
,
                )

            # 初始化变量 is_creator
            is_creator = db_case.created_by == current_user.id
            # 初始化变量 is_admin
            is_admin = current_user.role == UserRole.admin
            # 条件判断: 检查 not is_creator and not is_admin
            if not is_creator and not is_admin:
                # 记录日志信息
                logger.warning(
                    f"权限不足: user={current_user.id} "
                    f"尝试分析 case={case_id}"
                )
                # 返回处理结果
                return JSONResponse(
                    # 初始化变量 status_code
                    status_code=403,
                    # 初始化变量 content
                    content={
                        "error_code": "PERMISSION_DENIED",
                        "message": "Permission denied to access this case",
     # 条件判断：处理业务逻辑
                   },
                )

    cache_key: str = generate_cache_key(case_text, mode_value)
    cached: AnalysisResult | None = cache_manager.get(cache_key)
    # 条件判断: 检查 cached
    if cached:
        # 记录日志信息
        logger.info("分析结果来自缓存")
        # 返回处理结果
        return cached

    # 尝试执行可能抛出异常的代码
    try:
        result: AnalysisResult = 
    # 条件判断：处理业务逻辑
await analyze_pipeline(case_text, mode=mode_value)
    # 捕获异常：处理业务逻辑
    except Exception as e:
        # 记录日志信息
        logger.error(f"分析管道失败: {e}")
        # 抛出异常，处理错误情况
        raise HTTPException(status_code=502, detail="分析服务暂时不可用") from e

    # 条件判断: 检查 case_id
    if case_id:
        async with get_async_db_session() as db:
            # 事务由 get_async_db_session 上下文管理器统一管理：
            #   - 正常退出 → 自动 commit
            #   - 异常发生 → 自动 rollback
            db_analysis = Analysis(
                # 初始化变量 case_id
                case_id=case_id,
                # 初始化变量 result_json
                result_json=json.dumps(result, ensure_ascii=False),
                # mode_value 已是字符串，存为字符串与结果保持一致
                mode=mode_value,
                # 初始化变量 created_at
                created_at=datetime.now(UTC),
            )
            db.add(db_analysis)
            # 不手动调用 db.commit()，避免与上下文管理器的自动 commit 形成双重提交

    cache_manager.set(cache_key, result)

    # 返回处理结果
    return result
