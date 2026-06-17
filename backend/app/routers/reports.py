"""报告路由模块.

提供分析报告相关的 API 端点，包括报告生成、查询、导出和审查。
"""

# 导入模块: from fastapi
from fastapi import APIRouter, HTTPException, Query
# 导入模块: from fastapi.responses
from fastapi.responses import Response
# 导入模块: from pydantic
from pydantic import BaseModel, Field
# 导入模块: from sqlalchemy
from sqlalchemy import select

# 导入模块: from app.database
from app.database import get_async_db_session
# 导入模块: from app.models.analysis
from app.models.analysis import Analysis
# 导入模块: from app.models.case
from app.models.case import Case
# 导入模块: from app.models.report
from app.models.report import Report
# 导入模块: from app.services.report_exporter
from app.services.report_exporter import export_docx, export_pdf
# 导入模块: from app.services.report_generator
from app.services.report_generator import generate_report
# 导入模块: from app.services.report_service
from app.services.report_service import list_reports
# 导入模块: from app.services.review_checklist
from app.services.review_checklist import (
    complete_review,
    create_review,
    get_review_by_report_id,
)


# 初始化变量 router
router = APIRouter(prefix="/api/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------


# 定义 GenerateReportRequest 类
class GenerateReportRequest(BaseModel):
    """生成报告请求模型."""

    analysis_id: int = Field(..., description="分析结果ID")


# 定义 GenerateReportResponse 类
class GenerateReportResponse(BaseModel):
    """生成报告响应模型."""

    report_id: int = Field(..., description="报告ID")
    message: str = Field(default="报告生成成功", description="消息")


# 定义 ReviewRequest 类
class ReviewRequest(BaseModel):
    """审查请求模型."""

    items: dict[str, bool] = Field(default_factory=dict, description="审查项状态")
    comments: str | None = Field(default=None, description="审查意见")


# 定义 ReviewResponse 类
class ReviewResponse(BaseModel):
    """审查响应模型."""

    review_id: int = Field(..., description="审查记录ID")
    message: str = Field(default="审查保存成功", description="消息")


# 应用装饰器: router.get
@router.get("/")
async def get_reports(
    # 函数 get_reports 的初始化逻辑
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
) -> dict:
    """分页获取分析报告列表.

    Args:
        page: 页码（从 1 开始，默认 1）
        page_size: 每页条数（默认 20，最大 100）

    Returns:
        dict: 包含 total、page、page_size、total_pages、reports
    """
    async with get_async_db_session() as db:
        # 返回处理结果
        return await list_reports(db, page=page, page_size=page_size)


# 应用装饰器: router.post
@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report_endpoint(
    # 函数 generate_report_endpoint 的初始化逻辑
    request: GenerateReportRequest,
) -> GenerateReportResponse:
    """生成分析报告.

    Args:
        request: 生成报告请求，包含 analysis_id

    Returns:
        GenerateReportResponse: 包含生成的 report_id

    Raises:
        HTTPException: 当分析结果不存在或生成失败时
    """
    async with get_async_db_session() as db:
        # 查询分析结果
        result = await db.execute(
            select(Analysis).where(Analysis.id == request.analysis_id)
        )
        # 初始化变量 analysis
        analysis = result.scalar_one_or_none()

        # 条件判断: 检查 not analysis
        if not analysis:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=404, detail="分析结果不存在")

        # 查询关联案件
        case_result = await db.execute(select(Case).where(Case.id == analysis.case_id))
        # 初始化变量 case
        case = case_result.scalar_one_or_none()

        # 条件判断: 检查 not case
        if not case:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=404, detail="关联案件不存在")

        # 尝试执行可能抛出异常的代码
        try:
            # 生成报告内容
            report_content = generate_report(
                # 初始化变量 analysis_result
                analysis_result=analysis.result_data,
                # 初始化变量 case
                case=case,
                # 初始化变量 rule_hits
                rule_hits=analysis.result_data.get("triggered_rules", []),
                # 初始化变量 tags
                tags=analysis.result_data.get("matched_tags", []),
                # 初始化变量 similar_cases
                similar_cases=analysis.result_data.get("similar_cases", []),
            )

            # 创建报告记录
            report = Report(
                # 初始化变量 case_id
                case_id=case.id,
                # 初始化变量 analysis_id
                analysis_id=analysis.id,
                # 初始化变量 content_json
                content_json=report_content,
                # 初始化变量 version
                version="1.2.0",
            )
            db.add(report)
            # 异步等待操作完成
            await db.commit()
            # 异步等待操作完成
            await db.refresh(report)

            # 更新 report_id 到内容中
            report_content["report_id"] = report.id
            report.content_json = report_content
            # 异步等待操作完成
            await db.commit()

            # 返回处理结果
            return GenerateReportResponse(
                # 初始化变量 report_id
                report_id=report.id,
                # 初始化变量 message
                message="报告生成成功",
            )
        # 捕获异常：处理业务逻辑
        except Exception as e:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=500, detail=f"报告生成失败: {e!s}")


# 应用装饰器: router.get
@router.get("/{report_id}")
async def get_report(report_id: int) -> dict:
    """获取报告详情.

    Args:
        report_id: 报告ID

    Returns:
        dict: 报告内容

    Raises:
        HTTPException: 当报告不存在时
    """
    async with get_async_db_session() as db:
        # 初始化变量 result
        result = await db.execute(select(Report).where(Report.id == report_id))
        # 初始化变量 report
        report = result.scalar_one_or_none()

        # 条件判断: 检查 not report
        if not report:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=404, detail="报告不存在")

        # 返回处理结果
        return {
            "id": report.id,
            "case_id": report.case_id,
            "analysis_id": report.analysis_id,
            "content": report.content_json,
            "generated_at": report.generated_at.isoformat(),
            "version": report.version,
        }


# 应用装饰器: router.get
@router.get("/{report_id}/pdf")
async def download_report_pdf(report_id: int) -> Response:
    """下载报告 PDF 文件.

    Args:
        report_id: 报告ID

    Returns:
        Response: PDF 文件流

    Raises:
        HTTPException: 当报告不存在或导出失败时
    """
    async with get_async_db_session() as db:
        # 初始化变量 result
        result = await db.execute(select(Report).where(Report.id == report_id))
        # 初始化变量 report
        report = result.scalar_one_or_none()

        # 条件判断: 检查 not report
        if not report:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=404, detail="报告不存在")

        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 pdf_bytes
            pdf_bytes = export_pdf(
                # 初始化变量 report_content
                report_content=report.content_json,
                # 初始化变量 case_id
                case_id=report.case_id,
                # 初始化变量 generated_at
                generated_at=report.generated_at,
            )

            # 返回处理结果
            return Response(
                # 初始化变量 content
                content=pdf_bytes,
                # 初始化变量 media_type
                media_type="application/pdf",
                # 初始化变量 headers
                headers={
                    "Content-Disposition": f'attachment; filename="report_{report_id}.pdf"'
                   # 捕获异常：处理业务逻辑
     },
            )
        # 捕获并处理异常
        except Exception as e:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=500, detail=f"PDF 导出失败: {e!s}")


# 应用装饰器: router.get
@router.get("/{report_id}/docx")
async def download_report_docx(report_id: int) -> Response:
    """下载报告 DOCX 文件.

    Args:
        report_id: 报告ID

    Returns:
        Response: DOCX 文件流

    Raises:
        HTTPException: 当报告不存在或导出失败时
    """
    async with get_async_db_session() as db:
        # 初始化变量 result
        result = await db.execute(select(Report).where(Report.id == report_id))
        # 初始化变量 report
        report = result.scalar_one_or_none()

        # 条件判断: 检查 not report
        if not report:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=404, detail="报告不存在")

        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 docx_bytes
            docx_bytes = export_docx(
                # 初始化变量 report_content
                report_content=report.content_json,
                # 初始化变量 case_id
                case_id=report.case_id,
                # 初始化变量 generated_at
                generated_at=report.generated_at,
            )

            # 返回处理结果
            return Response(
                # 初始化变量 content
                content=docx_bytes,
                # 初始化变量 media_type
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                # 初始化变量 headers
                headers={
                    "Content-Disposition": f'attachment; filename="report_{report_        # 捕获异常：处理业务逻辑
id}.docx"'
                },
            )
        # 捕获并处理异常
        except Exception as e:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=500, detail=f"DOCX 导出失败: {e!s}")


# 应用装饰器: router.post
@router.post("/{report_id}/review", response_model=ReviewResponse)
async def submit_review(
    # 函数 submit_review 的初始化逻辑
    report_id: int,
    request: ReviewRequest,
) -> ReviewResponse:
    """提交报告审查结果.

    Args:
        report_id: 报告ID
        request: 审查请求，包含审查项状态和意见

    Returns:
        ReviewResponse: 包含审查记录ID

    Raises:
        HTTPException: 当报告不存在或保存失败时
    """
    async with get_async_db_session() as db:
        # 检查报告是否存在
        result = await db.execute(select(Report).where(Report.id == report_id))
        # 初始化变量 report
        report = result.scalar_one_or_none()

        # 条件判断: 检查 not report
        if not report:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=404, detail="报告不存在")

        # 尝试执行可能抛出异常的代码
        try:
            # 查询或创建审查记录
            review = await get_review_by_report_id(db, report_id)

            # 条件判断: 检查 not review
            if not review:
                # 初始化变量 review
                review = await create_review(db, report_id)

            # 更新审查内容
            review = await complete_review(
                db,
                review.id,
                # 初始化变量 items
                items=request.items,
                # 初始化变量 comments
                comments=request.comments,
            )

            # 返回处理结果
            return ReviewResponse(
                rev        # 捕获异常：处理业务逻辑
iew_id=review.id,
                # 初始化变量 message
                message="审查保存成功",
            )
        # 捕获并处理异常
        except Exception as e:
            # 抛出异常，处理错误情况
            raise HTTPException(status_code=500, detail=f"审查保存失败: {e!s}")
