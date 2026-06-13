"""报告导出服务模块.

实现报告内容的PDF和DOCX格式导出功能。

@file: report_exporter.py
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import fitz  # PyMuPDF
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from loguru import logger


# ---------------------------------------------------------------------------
# PDF导出功能
# ---------------------------------------------------------------------------


def export_pdf(
    report_content: dict[str, Any],
    case_id: int,
    generated_at: datetime | None = None,
) -> bytes:
    """将报告内容导出为PDF格式.

    Args:
        report_content: 报告内容字典
        case_id: 案件ID
        generated_at: 生成时间（可选，默认使用当前时间）

    Returns:
        bytes: PDF文件字节流
    """
    if generated_at is None:
        generated_at = datetime.now()

    logger.info(f"开始导出PDF - 案件ID={case_id}")

    # 创建PDF文档
    doc = fitz.open()

    # 添加页面
    page = doc.new_page(width=595, height=842)  # A4尺寸

    # 页面边距
    margin_left = 50
    margin_right = 50
    margin_top = 70
    margin_bottom = 70

    # 可用区域
    content_width = page.rect.width - margin_left - margin_right
    y_position = margin_top

    # 添加页眉
    y_position = _add_pdf_header(
        page, case_id, generated_at, margin_left, margin_top, content_width
    )

    # 添加标题
    y_position = _add_pdf_title(
        page, "帮信罪辅助裁定分析报告", y_position + 20, margin_left, content_width
    )

    # 添加报告元信息
    y_position = _add_pdf_metadata(
        page, report_content, y_position + 10, margin_left
    )

    # 添加章节内容
    chapters = report_content.get("chapters", {})
    chapter_order = [
        "ch1", "ch2", "ch3", "ch4", "ch5",
        "ch6", "ch7", "ch8", "ch9", "ch10"
    ]

    for chapter_id in chapter_order:
        if chapter_id in chapters:
            chapter = chapters[chapter_id]

            # 检查是否需要新页面
            if y_position > page.rect.height - margin_bottom - 100:
                page = doc.new_page(width=595, height=842)
                y_position = margin_top
                y_position = _add_pdf_header(
                    page, case_id, generated_at, margin_left, margin_top, content_width
                )

            # 添加章节标题
            chapter_title = chapter.get("title", "未知章节")
            y_position = _add_pdf_chapter_title(
                page, chapter_title, y_position + 15, margin_left
            )

            # 添加章节内容
            sections = chapter.get("sections", [])
            for section in sections:
                # 检查是否需要新页面
                if y_position > page.rect.height - margin_bottom - 50:
                    page = doc.new_page(width=595, height=842)
                    y_position = margin_top
                    y_position = _add_pdf_header(
                        page, case_id, generated_at, margin_left, margin_top, content_width
                    )

                y_position = _add_pdf_section(
                    page, section, y_position + 10, margin_left, content_width
                )

    # 添加水印
    _add_pdf_watermark(doc, "帮信罪辅助裁定系统")

    # 保存为字节流
    pdf_bytes = doc.tobytes()
    doc.close()

    logger.info(f"PDF导出完成 - 案件ID={case_id}, 大小={len(pdf_bytes)}字节")

    return pdf_bytes


def _add_pdf_header(
    page: fitz.Page,
    case_id: int,
    generated_at: datetime,
    x: float,
    y: float,
    width: float,
) -> float:
    """添加PDF页眉.

    Args:
        page: PDF页面对象
        case_id: 案件ID
        generated_at: 生成时间
        x: 起始X坐标
        y: 起始Y坐标
        width: 可用宽度

    Returns:
        float: 页眉底部Y坐标
    """
    # 左侧：案件ID
    page.insert_text(
        (x, y),
        f"案件ID: {case_id}",
        fontsize=9,
        color=(0.4, 0.4, 0.4),
    )

    # 右侧：生成时间
    time_text = generated_at.strftime("%Y-%m-%d %H:%M:%S")
    page.insert_text(
        (x + width - 150, y),
        f"生成时间: {time_text}",
        fontsize=9,
        color=(0.4, 0.4, 0.4),
    )

    # 绘制分隔线
    page.draw_line((x, y + 5), (x + width, y + 5), color=(0.7, 0.7, 0.7), width=0.5)

    return y + 15


def _add_pdf_title(
    page: fitz.Page,
    title: str,
    y: float,
    x: float,
    width: float,
) -> float:
    """添加PDF标题.

    Args:
        page: PDF页面对象
        title: 标题文本
        y: 起始Y坐标
        x: 起始X坐标
        width: 可用宽度

    Returns:
        float: 标题底部Y坐标
    """
    # 计算居中位置
    text_width = fitz.get_text_length(title, fontsize=18)
    text_x = x + (width - text_width) / 2

    page.insert_text(
        (text_x, y),
        title,
        fontsize=18,
        color=(0.1, 0.1, 0.1),
    )

    return y + 25


def _add_pdf_metadata(
    page: fitz.Page,
    report_content: dict[str, Any],
    y: float,
    x: float,
) -> float:
    """添加PDF元信息.

    Args:
        page: PDF页面对象
        report_content: 报告内容
        y: 起始Y坐标
        x: 起始X坐标

    Returns:
        float: 元信息底部Y坐标
    """
    metadata = report_content.get("metadata", {})
    version = report_content.get("version", "1.0.0")

    page.insert_text(
        (x, y),
        f"报告版本: {version}",
        fontsize=10,
        color=(0.3, 0.3, 0.3),
    )

    return y + 15


def _add_pdf_chapter_title(
    page: fitz.Page,
    title: str,
    y: float,
    x: float,
) -> float:
    """添加PDF章节标题.

    Args:
        page: PDF页面对象
        title: 章节标题
        y: 起始Y坐标
        x: 起始X坐标

    Returns:
        float: 标题底部Y坐标
    """
    # 添加背景色块
    rect = fitz.Rect(x - 5, y - 5, x + 500, y + 15)
    page.draw_rect(rect, color=(0.2, 0.4, 0.6), fill=(0.9, 0.95, 1.0))

    page.insert_text(
        (x, y),
        title,
        fontsize=14,
        color=(0.1, 0.2, 0.4),
    )

    return y + 20


def _add_pdf_section(
    page: fitz.Page,
    section: dict[str, Any],
    y: float,
    x: float,
    width: float,
) -> float:
    """添加PDF章节内容.

    Args:
        page: PDF页面对象
        section: 章节内容字典
        y: 起始Y坐标
        x: 起始X坐标
        width: 可用宽度

    Returns:
        float: 内容底部Y坐标
    """
    # 添加小节标题
    heading = section.get("heading", "")
    if heading:
        page.insert_text(
            (x, y),
            heading,
            fontsize=12,
            color=(0.2, 0.2, 0.2),
        )
        y += 18

    # 添加内容
    content = section.get("content", "")
    if isinstance(content, str) and content:
        # 文本换行处理
        lines = _wrap_text(content, width - 20, fontsize=10)
        for line in lines:
            if y > page.rect.height - 70:
                # 超出页面，返回当前位置
                break
            page.insert_text(
                (x + 10, y),
                line,
                fontsize=10,
                color=(0.15, 0.15, 0.15),
            )
            y += 14

    return y + 5


def _wrap_text(text: str, max_width: float, fontsize: int = 10) -> list[str]:
    """文本换行处理.

    Args:
        text: 原始文本
        max_width: 最大宽度
        fontsize: 字体大小

    Returns:
        list[str]: 换行后的文本列表
    """
    lines = []
    current_line = ""

    for char in text:
        test_line = current_line + char
        if fitz.get_text_length(test_line, fontsize=fontsize) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char

    if current_line:
        lines.append(current_line)

    return lines


def _add_pdf_watermark(doc: fitz.Document, watermark_text: str) -> None:
    """添加PDF水印.

    Args:
        doc: PDF文档对象
        watermark_text: 水印文本
    """
    for page in doc:
        # 在页面中心添加半透明水印
        center_x = page.rect.width / 2
        center_y = page.rect.height / 2

        # 旋转-45度
        page.insert_text(
            (center_x - 100, center_y),
            watermark_text,
            fontsize=30,
            color=(0.8, 0.8, 0.8),
            rotate=45,
            overlay=False,
        )


# ---------------------------------------------------------------------------
# DOCX导出功能
# ---------------------------------------------------------------------------


def export_docx(
    report_content: dict[str, Any],
    case_id: int,
    generated_at: datetime | None = None,
) -> bytes:
    """将报告内容导出为DOCX格式.

    Args:
        report_content: 报告内容字典
        case_id: 案件ID
        generated_at: 生成时间（可选，默认使用当前时间）

    Returns:
        bytes: DOCX文件字节流
    """
    if generated_at is None:
        generated_at = datetime.now()

    logger.info(f"开始导出DOCX - 案件ID={case_id}")

    # 创建文档
    doc = Document()

    # 添加页眉
    section = doc.sections[0]
    header = section.header
    header_para = header.paragraphs[0]
    header_para.text = f"案件ID: {case_id} | 生成时间: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}"
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 设置页眉字体
    for run in header_para.runs:
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(128, 128, 128)

    # 添加标题
    title = doc.add_heading("帮信罪辅助裁定分析报告", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 添加报告元信息
    version = report_content.get("version", "1.0.0")
    meta_para = doc.add_paragraph()
    meta_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_run = meta_para.add_run(f"报告版本: {version}")
    meta_run.font.size = Pt(10)
    meta_run.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_paragraph()  # 空行

    # 添加章节内容
    chapters = report_content.get("chapters", {})
    chapter_order = [
        "ch1", "ch2", "ch3", "ch4", "ch5",
        "ch6", "ch7", "ch8", "ch9", "ch10"
    ]

    for chapter_id in chapter_order:
        if chapter_id in chapters:
            chapter = chapters[chapter_id]

            # 添加章节标题
            chapter_title = chapter.get("title", "未知章节")
            doc.add_heading(chapter_title, level=1)

            # 添加章节内容
            sections = chapter.get("sections", [])
            for section_data in sections:
                _add_docx_section(doc, section_data)

    # 添加水印（通过页脚实现）
    _add_docx_watermark(doc, "帮信罪辅助裁定系统")

    # 保存为字节流
    docx_buffer = io.BytesIO()
    doc.save(docx_buffer)
    docx_bytes = docx_buffer.getvalue()
    docx_buffer.close()

    logger.info(f"DOCX导出完成 - 案件ID={case_id}, 大小={len(docx_bytes)}字节")

    return docx_bytes


def _add_docx_section(doc: Document, section: dict[str, Any]) -> None:
    """添加DOCX章节内容.

    Args:
        doc: DOCX文档对象
        section: 章节内容字典
    """
    # 添加小节标题
    heading = section.get("heading", "")
    if heading:
        doc.add_heading(heading, level=2)

    # 添加内容
    content = section.get("content", "")
    if isinstance(content, str) and content:
        para = doc.add_paragraph(content)
        para.paragraph_format.first_line_indent = Pt(20)
        for run in para.runs:
            run.font.size = Pt(10.5)

    # 添加特殊字段
    if "tier_label" in section:
        tier_para = doc.add_paragraph()
        tier_para.add_run(f"档级: {section['tier_label']}").bold = True

    if "sentence_band" in section:
        sentence_para = doc.add_paragraph()
        sentence_para.add_run(f"量刑区间: {section['sentence_band']}")

    if "confidence" in section:
        conf_para = doc.add_paragraph()
        conf_para.add_run(f"置信度: {section['confidence']:.2%}")

    # 添加列表项
    if "key_indicators" in section:
        doc.add_paragraph("关键指标:", style="Heading 3")
        for indicator in section["key_indicators"]:
            doc.add_paragraph(indicator, style="List Bullet")

    if "contradictions" in section:
        doc.add_paragraph("矛盾点:", style="Heading 3")
        for contradiction in section["contradictions"]:
            doc.add_paragraph(contradiction, style="List Bullet")

    if "laws" in section:
        doc.add_paragraph("法律依据:", style="Heading 3")
        for law in section["laws"]:
            law_text = f"{law['law']} {law['article']}: {law['content']}"
            doc.add_paragraph(law_text, style="List Bullet")


def _add_docx_watermark(doc: Document, watermark_text: str) -> None:
    """添加DOCX水印.

    注: python-docx对水印支持有限，这里通过页脚添加标识。

    Args:
        doc: DOCX文档对象
        watermark_text: 水印文本
    """
    # 在页脚添加标识
    for section in doc.sections:
        footer = section.footer
        footer_para = footer.paragraphs[0]
        footer_para.text = watermark_text
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        for run in footer_para.runs:
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor(180, 180, 180)


# ---------------------------------------------------------------------------
# 导出函数导出
# ---------------------------------------------------------------------------


__all__ = [
    "export_docx",
    "export_pdf",
]
