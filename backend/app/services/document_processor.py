"""文档处理服务模块.

支持 PDF、DOCX 和图像 OCR 等多种格式文档的文本提取。
"""

from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING

from fastapi import UploadFile
from loguru import logger


if TYPE_CHECKING:
    from paddleocr import PaddleOCR

_ocr_instance: PaddleOCR | None = None
_ocr_lock: asyncio.Lock = asyncio.Lock()

VALID_IMAGE_MAGIC_BYTES: dict[str, bytes] = {
    "jpg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
    "webp": b"RIFF",
    "bmp": b"BM",
    "gif": b"GIF8",
    "tiff_be": b"MM\x00\x2a",
    "tiff_le": b"II\x2a\x00",
}
SUPPORTED_OCR_EXTENSIONS: set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".gif",
    ".tiff",
    ".tif",
}


def _read_magic_bytes(file_path_or_buffer: bytes, num_bytes: int = 12) -> bytes:
    return file_path_or_buffer[:num_bytes]


def _validate_file_header(content: bytes) -> bool:
    magic = _read_magic_bytes(content)
    valid_headers = [
        VALID_IMAGE_MAGIC_BYTES[k]
        for k in ("jpg", "png", "webp", "bmp", "gif", "tiff_be", "tiff_le")
    ]
    return any(magic.startswith(header) for header in valid_headers)


def _init_ocr() -> PaddleOCR:
    from paddleocr import PaddleOCR  # noqa: PLC0415

    logger.info("正在初始化 PaddleOCR 实例...")
    ocr = PaddleOCR(use_angle_cls=True, lang="ch")
    logger.info("PaddleOCR 实例初始化完成")
    return ocr


async def _get_ocr() -> PaddleOCR:
    global _ocr_instance  # noqa: PLW0603
    if _ocr_instance is None:
        async with _ocr_lock:
            if _ocr_instance is None:
                _ocr_instance = await asyncio.to_thread(_init_ocr)
    return _ocr_instance


async def process_pdf(file: UploadFile) -> str:
    """从 PDF 文件中提取文本.

    使用 PyMuPDF (fitz) 库逐页读取并拼接文本。

    Args:
        file: 上传的 PDF 文件

    Returns:
        str: 提取的文本内容

    Raises:
        Exception: PDF 读取失败时向上抛出
    """
    try:
        import fitz  # noqa: PLC0415

        content: bytes = await file.read()
        doc = fitz.open(stream=content, filetype="pdf")
        text: str = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        logger.info(f"PDF 处理完成: {file.filename}, {len(text)} 字符")
        return text
    except Exception as e:
        logger.error(f"PDF 处理失败: {e}")
        raise


async def process_docx(file: UploadFile) -> str:
    """从 DOCX 文件中提取文本.

    使用 python-docx 库读取段落并拼接文本。

    Args:
        file: 上传的 DOCX 文件

    Returns:
        str: 提取的文本内容

    Raises:
        Exception: DOCX 读取失败时向上抛出
    """
    try:
        from docx import Document  # noqa: PLC0415

        content: bytes = await file.read()
        doc = Document(io.BytesIO(content))
        text: str = "\n".join([p.text for p in doc.paragraphs])
        logger.info(f"DOCX 处理完成: {file.filename}, {len(text)} 字符")
        return text
    except Exception as e:
        logger.error(f"DOCX 处理失败: {e}")
        raise


async def process_ocr(file: UploadFile) -> str:
    """通过 OCR 从图像中提取文本.

    使用 PaddleOCR 进行中文文字识别，采用单例模式管理实例。

    Args:
        file: 上传的图像文件

    Returns:
        str: 识别出的文本内容

    Raises:
        ValueError: 文件格式校验失败时抛出
        Exception: OCR 处理失败时向上抛出
    """
    try:
        import numpy as np  # noqa: PLC0415

        content: bytes = await file.read()

        if not _validate_file_header(content):
            filename: str = file.filename or "unknown"
            logger.warning(f"文件头校验失败，非有效图片格式: {filename}")
            msg: str = f"文件头校验失败，非有效图片格式: {filename}"
            raise ValueError(msg)

        ocr = await _get_ocr()
        nparr = np.frombuffer(content, np.uint8)
        result = ocr.ocr(nparr, cls=True)
        text: str = ""
        if result and result[0]:
            text = "\n".join([line[1][0] for line in result[0]])
        logger.info(f"OCR 处理完成: {file.filename}, {len(text)} 字符")
        return text
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"OCR 处理失败: {e}")
        raise


async def process_document(file: UploadFile) -> str:
    """根据文件类型自动选择合适的处理器提取文本.

    支持 PDF、DOCX 和常见图像格式，其他文件按纯文本读取。

    Args:
        file: 上传的文件

    Returns:
        str: 提取的文本内容
    """
    filename: str = (file.filename or "").lower()
    if filename.endswith(".pdf"):
        return await process_pdf(file)
    if filename.endswith(".docx"):
        return await process_docx(file)
    if filename.endswith(tuple(SUPPORTED_OCR_EXTENSIONS)):
        return await process_ocr(file)
    if not filename:
        msg: str = "无法识别的文件类型或无文件名"
        raise ValueError(msg)
    content: bytes = await file.read()
    return content.decode("utf-8", errors="ignore")
