#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
权利归属声明和原创性声明生成脚本
使用 reportlab 生成标准格式的 PDF 声明文档
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os

# 注册 CID 中文字体
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))


def create_rights_declaration():
    """创建权利归属声明"""
    output_path = '04_证明材料/权利归属声明.pdf'

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=3.17 * cm,
        rightMargin=3.17 * cm,
        topMargin=2.54 * cm,
        bottomMargin=2.54 * cm
    )

    # 定义样式
    title_style = ParagraphStyle(
        'Title',
        fontName='STSong-Light',
        fontSize=22,
        alignment=TA_CENTER,
        spaceAfter=30,
        leading=30
    )

    body_style = ParagraphStyle(
        'Body',
        fontName='STSong-Light',
        fontSize=12,
        leading=1.5 * 12,
        spaceAfter=20,
        alignment=TA_LEFT
    )

    signature_style = ParagraphStyle(
        'Signature',
        fontName='STSong-Light',
        fontSize=12,
        leading=1.5 * 12,
        spaceAfter=10,
        alignment=TA_LEFT
    )

    story = []
    story.append(Paragraph('权利归属声明', title_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        '本软件由 [申请人姓名/公司] 独立开发，未与其他方共有',
        body_style
    ))
    story.append(Spacer(1, 40))
    story.append(Paragraph('申请人（签字/盖章）：待签字盖章', signature_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph('日期：                    ', signature_style))

    doc.build(story)
    print(f'权利归属声明已生成: {output_path}')
    return output_path


def create_originality_declaration():
    """创建原创性声明"""
    output_path = '04_证明材料/原创性声明.pdf'

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=3.17 * cm,
        rightMargin=3.17 * cm,
        topMargin=2.54 * cm,
        bottomMargin=2.54 * cm
    )

    title_style = ParagraphStyle(
        'Title',
        fontName='STSong-Light',
        fontSize=22,
        alignment=TA_CENTER,
        spaceAfter=30,
        leading=30
    )

    body_style = ParagraphStyle(
        'Body',
        fontName='STSong-Light',
        fontSize=12,
        leading=1.5 * 12,
        spaceAfter=20,
        alignment=TA_LEFT
    )

    signature_style = ParagraphStyle(
        'Signature',
        fontName='STSong-Light',
        fontSize=12,
        leading=1.5 * 12,
        spaceAfter=10,
        alignment=TA_LEFT
    )

    story = []
    story.append(Paragraph('原创性声明', title_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        '本软件为原创作品，未抄袭任何第三方软件',
        body_style
    ))
    story.append(Spacer(1, 40))
    story.append(Paragraph('申请人（签字/盖章）：待签字盖章', signature_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph('日期：                    ', signature_style))

    doc.build(story)
    print(f'原创性声明已生成: {output_path}')
    return output_path


if __name__ == '__main__':
    create_rights_declaration()
    create_originality_declaration()
