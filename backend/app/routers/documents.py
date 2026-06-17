"""文档上传路由模块.

提供文档上传和文本提取的 API 端点。
"""

# 导入模块: from fastapi
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

# 导入模块: from app.config
from app.config import AnalysisConfig
# 导入模块: from app.models.user
from app.models.user import User
# 导入模块: from app.services.document_processor
from app.services.document_processor import process_document
# 导入模块: from app.utils.auth
from app.utils.auth import get_current_user


# 初始化变量 router
router = APIRouter(prefix="/api/documents", tags=["documents"])

_file_upload_dep = File(...)


# 应用装饰器: router.post
@router.post("/upload")
async def upload_document(
    # 函数 upload_document 的初始化逻辑
    file: UploadFile = _file_upload_dep,
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> dict[str, str | int]:
    """上传文档并自动提取文本（需要登录）.

    支持 PDF、DOCX、图像（OCR）和纯文本文件。
    对文件类型和大小进行校验。
    需要用户登录才能上传，防止匿名滥用。

    Args:
        file: 上传的文件
        current_user: 当前用户（必须登录）

    Returns:
        dict: 包含文件名、内容长度和预览内容的字典

    Raises:
        HTTPException 400: 不支持的文件类型
        HTTPException 401: 未登录
        HTTPException 413: 文件超过大小限制
    """
    # 文件类型校验（强制校验，不允许 content_type 为空）
    allowed = AnalysisConfig.ALLOWED_UPLOAD_CONTENT_TYPES
    # 条件判断：处理业务逻辑
    if not file.content_type or file.content_type not in allowed:
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_400_BAD_REQUEST,
            # 初始化变量 detail
            detail=f"不支持的文件类型: {file.content_type or '未知'}，"
                   f"允许的类型: {', '.join(sorted(allowed))}",
          # 条件判断：处理业务逻辑
  )

    # 文件大小校验
    if file.size and file.size > AnalysisConfig.MAX_FILE_SIZE_BYTES:
        # 初始化变量 size_mb
        size_mb = AnalysisConfig.MAX_FILE_SIZE_BYTES // 1024 // 1024
        # 抛出异常，处理错误情况
        raise HTTPException(
            # 初始化变量 status_code
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            # 初始化变量 detail
            detail=f"文件大小超过限制 (最大 {size_mb}MB)",
        )

    # 异步等待操作完成
    text: str = await process_document(file)
    # 返回处理结果
    return {
        "filename": file.filename or "unknown",
        "content_length": len(text),
        "content": text[: AnalysisConfig.MAX_UPLOAD_CONTENT_PREVIEW],
        "uploaded_by": current_user.username,
    }
