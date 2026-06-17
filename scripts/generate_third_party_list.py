#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三方库使用清单生成脚本
扫描项目依赖文件，生成标准化的第三方库使用清单PDF文档
"""

import json
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os

# 注册 CID 中文字体
FONT_NAME = 'STSong-Light'
pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))


def parse_requirements_txt(filepath):
    """解析 requirements.txt 文件"""
    dependencies = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # 解析包名和版本
                match = re.match(r'^([a-zA-Z0-9_-]+(?:\[[a-zA-Z0-9_,]+\])?)(>=|==|<=|~=|!=)?(.*)?$', line)
                if match:
                    package_name = match.group(1).replace('[all]', '').replace('[asyncio]', '').replace('[standard]', '').replace('[fastapi]', '').replace('[lua]', '').replace('[bcrypt]', '')
                    version = match.group(3) if match.group(3) else 'latest'
                    dependencies.append({
                        'name': package_name,
                        'version': version,
                        'license': '待确认',
                        'purpose': '待补充'
                    })
    except FileNotFoundError:
        print(f"未找到文件: {filepath}")

    return dependencies


def parse_package_json(filepath):
    """解析 package.json 文件"""
    dependencies = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # 解析 dependencies
            for package, version in data.get('dependencies', {}).items():
                dependencies.append({
                    'name': package,
                    'version': version.replace('^', '').replace('~', ''),
                    'license': '待确认',
                    'purpose': '待补充'
                })

            # 解析 devDependencies
            for package, version in data.get('devDependencies', {}).items():
                dependencies.append({
                    'name': package,
                    'version': version.replace('^', '').replace('~', ''),
                    'license': '待确认',
                    'purpose': '待补充'
                })
    except FileNotFoundError:
        print(f"未找到文件: {filepath}")

    return dependencies


def create_third_party_library_list():
    """创建第三方库使用清单"""
    output_path = '04_证明材料/第三方库使用清单.pdf'

    # 解析依赖文件
    backend_deps = parse_requirements_txt('backend/requirements.txt')
    frontend_deps = parse_package_json('frontend/package.json')

    # 合并依赖
    all_deps = backend_deps + frontend_deps

    # 创建 PDF 文档
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
        fontName=FONT_NAME,
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20,
        leading=20
    )

    header_style = ParagraphStyle(
        'Header',
        fontName=FONT_NAME,
        fontSize=10.5,
        alignment=TA_CENTER,
        leading=14
    )

    cell_style = ParagraphStyle(
        'Cell',
        fontName=FONT_NAME,
        fontSize=9,
        alignment=TA_LEFT,
        leading=12
    )

    footer_style = ParagraphStyle(
        'Footer',
        fontName=FONT_NAME,
        fontSize=9,
        alignment=TA_RIGHT,
        spaceBefore=20,
        leading=12
    )

    # 构建内容
    story = []

    # 标题
    story.append(Paragraph('第三方库使用清单', title_style))
    story.append(Spacer(1, 15))

    # 准备表格数据
    table_data = [
        [
            Paragraph('库名', header_style),
            Paragraph('版本', header_style),
            Paragraph('License', header_style),
            Paragraph('用途', header_style)
        ]
    ]

    # 添加依赖项
    for dep in all_deps:
        table_data.append([
            Paragraph(dep['name'], cell_style),
            Paragraph(dep['version'], cell_style),
            Paragraph(dep['license'], cell_style),
            Paragraph(dep['purpose'], cell_style)
        ])

    # 创建表格
    table = Table(table_data, colWidths=[4*cm, 2.5*cm, 3*cm, 5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'SimHei'),
        ('FONTSIZE', (0, 0), (-1, 0), 10.5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))

    story.append(table)
    story.append(Spacer(1, 20))

    # 页尾声明
    story.append(Paragraph('上述库均按其License使用，未修改其源代码', footer_style))

    # 生成PDF
    doc.build(story)
    print(f'第三方库使用清单已生成: {output_path}')
    print(f'共包含 {len(all_deps)} 个第三方库')
    return output_path


if __name__ == '__main__':
    register_chinese_font()
    create_third_party_library_list()
