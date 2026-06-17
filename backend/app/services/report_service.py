"""报告服务模块.

提供分析报告的查询和格式化功能。
所有数据库操作均使用异步 API。
"""

# 导入模块: from math
from math import ceil

# 导入模块: from sqlalchemy
from sqlalchemy import func, select
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# 导入模块: from app.models.analysis
from app.models.analysis import Analysis
# 导入模块: from app.types.analysis
from app.types.analysis import AnalysisReport


async def list_reports(
    # 函数 list_reports 的初始化逻辑
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询分析报告列表.

    Args:
        db: 异步数据库会话
        page: 页码（从 1 开始）
        page_size: 每页条数

    Returns:
        dict: 包含 total、page、page_size、total_pages、reports 的字典
    """
    # 初始化变量 page
    page = max(1, page)
    # 初始化变量 page_size
    page_size = min(max(1, page_size), 100)

    # 初始化变量 count_result
    count_result = await db.execute(select(func.count(Analysis.id)))
    total: int = count_result.scalar() or 0

    # 初始化变量 offset
    offset = (page - 1) * page_size
    # 初始化变量 result
    result = await db.execute(
        select(Analysis)
        .order_by(Analysis.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    # 初始化变量 analyses
    analyses = list(result.scalars().all())

    # 初始化变量 reports
    reports = [_format_analysis(a) for a in analyses]

    # 返回处理结果
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)) if total > 0 else 0,
        "reports": reports,
    }


def _format_analysis(a: Analysis) -> AnalysisReport:
    """格式化单条分析记录.

    Args:
        a: 分析记录实例

    Returns:
        AnalysisReport: 格式化后的字典
    """
    # 返回处理结果
    return {
        "id": a.id if a.id is not None else 0,
        "case_id": int(a.case_id) if a.case_id is not None else None,
        "knowledge_score": (
            float(a.knowledge_score) if a.knowledge_score is not None else None
        ),
        "mode": str(a.mode),
        "result": str(a.result_json),
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
