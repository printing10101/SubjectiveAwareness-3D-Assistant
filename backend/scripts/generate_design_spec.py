#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设计说明书 PDF 生成脚本

基于 docs/综合技术文档.md 生成规范的设计说明书 PDF 文档。
输出路径：03_软件文档/设计说明书.pdf

要求:
- 总页数 >= 30 页
- 宋体小四字体
- 每章 1-2 张示意图（占位图，标注"图 X-X"格式）
- 页眉页脚格式规范
"""

import os
import sys
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image, KeepTogether
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "03_软件文档"
OUTPUT_FILE = OUTPUT_DIR / "设计说明书.pdf"

# 页面设置
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 2.5 * cm
RIGHT_MARGIN = 2.5 * cm
TOP_MARGIN = 2.5 * cm
BOTTOM_MARGIN = 2.5 * cm


def register_fonts():
    """注册中文字体"""
    font_paths = [
        "C:/Windows/Fonts/simsun.ttc",
        "/System/Library/Fonts/STSong.ttf",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('SimSun', font_path))
                return 'SimSun'
            except Exception:
                continue
    
    return 'Helvetica'


def create_styles(font_name: str):
    """创建文档样式"""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='CoverTitle',
        fontName=font_name,
        fontSize=28,
        leading=36,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.HexColor('#1a1a1a'),
    ))
    
    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        fontName=font_name,
        fontSize=16,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#4a4a4a'),
    ))
    
    styles.add(ParagraphStyle(
        name='Heading1Custom',
        fontName=font_name,
        fontSize=18,
        leading=28,
        alignment=TA_LEFT,
        spaceBefore=20,
        spaceAfter=15,
        textColor=colors.HexColor('#2c3e50'),
        keepWithNext=True,
    ))
    
    styles.add(ParagraphStyle(
        name='Heading2Custom',
        fontName=font_name,
        fontSize=14,
        leading=22,
        alignment=TA_LEFT,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor('#34495e'),
        keepWithNext=True,
    ))
    
    styles.add(ParagraphStyle(
        name='Heading3Custom',
        fontName=font_name,
        fontSize=12,
        leading=18,
        alignment=TA_LEFT,
        spaceBefore=10,
        spaceAfter=8,
        textColor=colors.HexColor('#5a6c7d'),
        keepWithNext=True,
    ))
    
    styles.add(ParagraphStyle(
        name='BodyTextCustom',
        fontName=font_name,
        fontSize=12,
        leading=20,
        alignment=TA_JUSTIFY,
        spaceBefore=6,
        spaceAfter=6,
        firstLineIndent=24,
    ))
    
    styles.add(ParagraphStyle(
        name='ListItem',
        fontName=font_name,
        fontSize=12,
        leading=20,
        alignment=TA_LEFT,
        spaceBefore=4,
        spaceAfter=4,
        leftIndent=20,
        bulletIndent=10,
    ))
    
    styles.add(ParagraphStyle(
        name='TableTitle',
        fontName=font_name,
        fontSize=11,
        leading=16,
        alignment=TA_CENTER,
        spaceBefore=10,
        spaceAfter=5,
        textColor=colors.HexColor('#2c3e50'),
    ))
    
    styles.add(ParagraphStyle(
        name='FigureCaption',
        fontName=font_name,
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        spaceBefore=5,
        spaceAfter=15,
        textColor=colors.HexColor('#666666'),
    ))
    
    styles.add(ParagraphStyle(
        name='Header',
        fontName=font_name,
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#888888'),
    ))
    
    styles.add(ParagraphStyle(
        name='Footer',
        fontName=font_name,
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#888888'),
    ))
    
    return styles


def create_placeholder_image(width: float = 12 * cm, height: float = 8 * cm, 
                             caption: str = "") -> list:
    """创建占位图"""
    elements = []
    
    data = [['[示意图占位区域]']]
    table = Table(data, colWidths=[width], rowHeights=[height])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f0f0')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#999999')),
    ]))
    elements.append(table)
    
    if caption:
        elements.append(Paragraph(caption, ParagraphStyle(
            name='Caption',
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            spaceBefore=5,
            spaceAfter=15,
            textColor=colors.HexColor('#666666'),
        )))
    
    return elements


def add_header_footer(canvas, doc):
    """添加页眉页脚"""
    canvas.saveState()
    
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(colors.HexColor('#888888'))
    header_text = "帮信罪主观明知分析系统 - 设计说明书"
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 1.5 * cm, header_text)
    
    canvas.setStrokeColor(colors.HexColor('#cccccc'))
    canvas.setLineWidth(0.5)
    canvas.line(LEFT_MARGIN, PAGE_HEIGHT - 1.8 * cm, 
                PAGE_WIDTH - RIGHT_MARGIN, PAGE_HEIGHT - 1.8 * cm)
    
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(colors.HexColor('#888888'))
    page_num = canvas.getPageNumber()
    canvas.drawCentredString(PAGE_WIDTH / 2, 1.5 * cm, f"- {page_num} -")
    
    canvas.line(LEFT_MARGIN, 2 * cm, PAGE_WIDTH - RIGHT_MARGIN, 2 * cm)
    
    canvas.restoreState()


def build_cover_page(styles) -> list:
    """构建封面页"""
    elements = []
    
    elements.append(Spacer(1, 3 * cm))
    
    title = Paragraph("帮信罪主观明知分析系统", styles['CoverTitle'])
    elements.append(title)
    
    subtitle = Paragraph("设计说明书", styles['CoverSubtitle'])
    elements.append(subtitle)
    
    elements.append(Spacer(1, 2 * cm))
    
    version_info = [
        ["文档版本", "V1.0"],
        ["编制日期", datetime.now().strftime("%Y年%m月%d日")],
        ["密级", "内部公开"],
    ]
    
    version_table = Table(version_info, colWidths=[4 * cm, 6 * cm])
    version_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2c3e50')),
    ]))
    elements.append(version_table)
    
    elements.append(Spacer(1, 3 * cm))
    
    copyright_text = """
    <b>版权声明</b><br/>
    本文档包含帮信罪主观明知分析系统的专有信息，版权所有。
    未经书面许可，不得复制、传播或向第三方披露。
    """
    elements.append(Paragraph(copyright_text, ParagraphStyle(
        name='Copyright',
        fontName='Helvetica',
        fontSize=10,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#888888'),
    )))
    
    elements.append(PageBreak())
    return elements


def build_toc(styles) -> list:
    """构建目录页"""
    elements = []
    
    elements.append(Paragraph("目  录", styles['Heading1Custom']))
    elements.append(Spacer(1, 1 * cm))
    
    toc_items = [
        ("第 1 章 引言", "1"),
        ("  1.1 编写目的", "1"),
        ("  1.2 项目背景", "1"),
        ("  1.3 关键术语", "2"),
        ("第 2 章 需求分析", "3"),
        ("  2.1 功能需求", "3"),
        ("  2.2 非功能需求", "4"),
        ("第 3 章 系统架构设计", "5"),
        ("  3.1 技术栈选型", "5"),
        ("  3.2 模块划分", "6"),
        ("  3.3 数据流图", "7"),
        ("第 4 章 数据库设计", "8"),
        ("  4.1 ER 图", "8"),
        ("  4.2 核心表结构", "9"),
        ("第 5 章 知识库设计", "10"),
        ("  5.1 规则体系", "10"),
        ("  5.2 标签体系", "11"),
        ("  5.3 冲突体系", "12"),
        ("第 6 章 推理引擎设计", "13"),
        ("  6.1 三维度模型", "13"),
        ("  6.2 规则引擎", "14"),
        ("  6.3 标签抽取", "15"),
        ("第 7 章 报告生成设计", "16"),
        ("  7.1 10 章模板", "16"),
        ("  7.2 实现机制", "17"),
        ("第 8 章 评测体系设计", "18"),
        ("  8.1 金标准", "18"),
        ("  8.2 消融实验", "19"),
        ("  8.3 竞品对标", "20"),
        ("第 9 章 前端设计", "21"),
        ("  9.1 页面结构", "21"),
        ("  9.2 交互流程", "22"),
        ("第 10 章 部署与运维设计", "23"),
        ("  10.1 部署方案", "23"),
        ("  10.2 运维策略", "24"),
        ("第 11 章 安全设计", "25"),
        ("  11.1 安全防护", "25"),
        ("第 12 章 接口设计", "26"),
        ("  12.1 API 列表", "26"),
        ("附录 A：术语表", "28"),
        ("附录 B：算法说明", "29"),
    ]
    
    for item, page in toc_items:
        if item.startswith("第") or item.startswith("附录"):
            style = ParagraphStyle(
                name='TOCChapter',
                fontName='Helvetica',
                fontSize=12,
                leading=20,
                leftIndent=0,
            )
        else:
            style = ParagraphStyle(
                name='TOCSection',
                fontName='Helvetica',
                fontSize=11,
                leading=18,
                leftIndent=20,
            )
        
        text = f"{item} {'.' * (50 - len(item))} {page}"
        elements.append(Paragraph(text, style))
    
    elements.append(PageBreak())
    return elements


def build_chapter1(styles) -> list:
    """第 1 章 引言"""
    elements = []
    
    elements.append(Paragraph("第 1 章 引言", styles['Heading1Custom']))
    
    elements.append(Paragraph("1.1 编写目的", styles['Heading2Custom']))
    elements.append(Paragraph(
        "本文档为帮信罪主观明知分析系统的设计说明书，旨在详细说明系统的架构设计、"
        "模块设计、数据库设计、算法设计等核心技术内容，为开发人员、测试人员、"
        "运维人员提供全面的技术参考。",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph("1.2 项目背景", styles['Heading2Custom']))
    elements.append(Paragraph(
        "帮助信息网络犯罪活动罪（帮信罪）是近年来司法实践中高发、频涉的罪名之一。"
        "该罪的核心构成要件——【主观明知】——在实务中往往难以认定。传统办案模式下，"
        "检察官需要人工梳理案件事实、比对既有案例、综合判断嫌疑人的主观认知状态，"
        "存在认定标准不统一、办案效率受限、经验传承困难等痛点。",
        styles['BodyTextCustom']
    ))
    elements.append(Paragraph(
        "本系统致力于通过人工智能技术，辅助检察官快速、一致地完成【主观明知】要素的"
        "审查判断，核心目标包括标准化分析框架、自动化审查辅助、智能类案参考、"
        "验证大模型在司法判断任务中的可行性。",
        styles['BodyTextCustom']
    ))
    
    elements.extend(create_placeholder_image(
        caption="图 1-1 系统建设目标示意图"
    ))
    
    elements.append(Paragraph("1.3 关键术语", styles['Heading2Custom']))
    
    terms_data = [
        ["术语", "解释"],
        ["帮信罪", "帮助信息网络犯罪活动罪（刑法第二百八十七条之二）"],
        ["主观明知", "帮信罪构成要件中行为人主观上【明知他人利用信息网络实施犯罪】的状态"],
        ["三维度", "客观行为异常度、认知能力与作案模式匹配度、辩解合理性"],
        ["知识图谱", "由特征节点、推定规则、推理路径、案例三层组成的图结构"],
        ["推定规则", "基于《帮信解释》第十一条的【可推定明知】的若干情形"],
        ["推理路径", "由证据→规则→结论组成的完整推理链"],
        ["LoRA", "Low-Rank Adaptation，一种参数高效的大模型微调方法"],
        ["推理管线", "两阶段推理（事实提取 + 维度分析）"],
    ]
    
    terms_table = Table(terms_data, colWidths=[3 * cm, 12 * cm])
    terms_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(terms_table)
    
    elements.append(PageBreak())
    return elements


def build_chapter2(styles) -> list:
    """第 2 章 需求分析"""
    elements = []
    
    elements.append(Paragraph("第 2 章 需求分析", styles['Heading1Custom']))
    
    elements.append(Paragraph("2.1 功能需求", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统需要实现以下核心功能需求：",
        styles['BodyTextCustom']
    ))
    
    func_reqs = [
        ("案件事实三维度智能分析", "系统能够从客观行为异常度、认知能力匹配度、辩解合理性三个维度对案件事实进行综合分析，输出评分、推理依据和结论"),
        ("PDF/DOCX 案件材料解析", "支持上传 PDF、DOCX 格式的案件文档，自动提取文本内容和关键实体信息"),
        ("基于知识图谱的相似案例检索", "基于三层知识图谱架构，实现法律推定规则匹配和相似案例推荐"),
        ("量刑辅助建议与证据溯源", "基于历史判例生成量刑建议，并支持证据片段在原文中的定位和回显"),
        ("回溯性对比实验", "支持 A/B 两组实验设计，采集人工判断和 AI 辅助判断数据，进行统计分析"),
        ("用户、案件、规则、日志管理", "提供完整的 CRUD 操作、权限控制、审计日志等管理能力"),
    ]
    
    for name, desc in func_reqs:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        caption="图 2-1 系统功能需求示意图"
    ))
    
    elements.append(Paragraph("2.2 非功能需求", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统需要满足以下非功能需求：",
        styles['BodyTextCustom']
    ))
    
    nonfunc_reqs = [
        ("性能需求", "首次分析响应时间 < 60 秒，缓存命中响应时间 < 1 秒，支持并发用户数 ≥ 10"),
        ("安全需求", "所有数据本地化存储，JWT 双 Token 认证，密码 bcrypt 哈希，敏感操作审计日志"),
        ("可用性需求", "系统可用性 ≥ 99%，关键服务（Ollama、Neo4j）具备回退方案"),
        ("可扩展性需求", "路由、服务、模型、规则、提示词均按模块拆分，便于功能扩展"),
        ("可解释性需求", "每个分析维度均输出评分、推理过程和关键依据，支持推理路径追溯"),
    ]
    
    for name, desc in nonfunc_reqs:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.append(PageBreak())
    return elements


def build_chapter3(styles) -> list:
    """第 3 章 系统架构设计"""
    elements = []
    
    elements.append(Paragraph("第 3 章 系统架构设计", styles['Heading1Custom']))
    
    elements.append(Paragraph("3.1 技术栈选型", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统采用前后端分离的 B/S 架构，技术栈选型如下：",
        styles['BodyTextCustom']
    ))
    
    tech_data = [
        ["层次", "技术", "版本", "选型理由"],
        ["前端", "Vue 3 + Vite", "3.4+", "组合式 API；轻量高效"],
        ["后端", "FastAPI", "0.100+", "高性能异步框架；原生 Pydantic 集成"],
        ["数据库", "SQLite/PostgreSQL", "—", "开发零配置；生产可一键切换"],
        ["图数据库", "Neo4j + 内存图回退", "5.x", "三层知识图谱存储"],
        ["AI 推理", "Ollama", "0.3+", "本地 LLM 推理服务；模型管理友好"],
        ["微调框架", "Unsloth", "—", "显存优化显著；训练速度快"],
    ]
    
    tech_table = Table(tech_data, colWidths=[2.5 * cm, 4 * cm, 2 * cm, 6.5 * cm])
    tech_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(tech_table)
    
    elements.append(Paragraph("3.2 模块划分", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统采用五层架构，各层职责清晰，便于维护和扩展：",
        styles['BodyTextCustom']
    ))
    
    layers = [
        ("展示层（Presentation Layer）", "Vue 3 SPA 单页应用，负责用户界面交互，包含 Pinia 状态管理、Vue Router 路由、Axios HTTP 客户端"),
        ("接入层（API Gateway Layer）", "FastAPI 接入层，负责请求路由、JWT 认证、CORS 跨域、请求日志、速率限制"),
        ("业务服务层（Service Layer）", "包含案件管理、分析推理、文档处理、类案推送、量刑辅助、知识图谱、实验数据、用户管理等 8 个核心服务"),
        ("AI 推理层（Inference Layer）", "两阶段推理管线，包含事实提取、三维度分析、Prompt 工程、分析缓存、Ollama 推理引擎"),
        ("数据存储层（Data Layer）", "SQLite/PostgreSQL 关系型数据库、Neo4j 图数据库、文件缓存系统、JSON 数据文件"),
    ]
    
    for name, desc in layers:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        height=10 * cm,
        caption="图 3-1 系统五层架构图"
    ))
    
    elements.append(Paragraph("3.3 数据流图", styles['Heading2Custom']))
    elements.append(Paragraph(
        "案件分析主流程的数据流如下：",
        styles['BodyTextCustom']
    ))
    
    flow_steps = [
        "用户通过前端提交案件文本到 FastAPI 接入层",
        "接入层进行 JWT 认证后，调用分析推理服务",
        "分析服务计算 MD5 查询缓存，缓存命中则直接返回",
        "缓存未命中时调用推理管线，根据复杂度选择单次或两阶段推理",
        "推理管线调用 Ollama LLM 进行 AI 分析",
        "分析结果写入缓存和数据库，返回给用户",
    ]
    
    for i, step in enumerate(flow_steps, 1):
        elements.append(Paragraph(f"{i}. {step}", styles['ListItem']))
    
    elements.extend(create_placeholder_image(
        height=8 * cm,
        caption="图 3-2 案件分析数据流图"
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter4(styles) -> list:
    """第 4 章 数据库设计"""
    elements = []
    
    elements.append(Paragraph("第 4 章 数据库设计", styles['Heading1Custom']))
    
    elements.append(Paragraph("4.1 ER 图", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统数据库包含以下核心实体及其关系：",
        styles['BodyTextCustom']
    ))
    
    entities = [
        ("User（用户）", "存储用户账号信息，包括用户名、密码哈希、角色、激活状态等"),
        ("Case（案件）", "存储案件基本信息，包括案件名称、事实文本、状态、创建时间等"),
        ("Analysis（分析记录）", "存储 AI 分析结果，包括三维度评分、结论、推理依据、置信度等"),
        ("LegalRule（法律规则）", "存储法律推定规则，包括规则名称、描述、适用条件、结论、权重等"),
        ("KnowledgeEntry（知识条目）", "存储知识图谱节点，包括节点类型、名称、描述、属性等"),
        ("KnowledgeTag（知识标签）", "存储知识标签，用于对案件特征进行分类标记"),
        ("ModelVersion（模型版本）", "存储 AI 模型版本信息，包括版本号、微调时间、评估指标等"),
        ("SystemLog（系统日志）", "存储系统操作日志，包括操作类型、用户、时间、详情等"),
    ]
    
    for name, desc in entities:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        height=10 * cm,
        caption="图 4-1 数据库 ER 图"
    ))
    
    elements.append(Paragraph("4.2 核心表结构", styles['Heading2Custom']))
    elements.append(Paragraph(
        "以下为核心数据表的结构说明：",
        styles['BodyTextCustom']
    ))
    
    # User 表
    elements.append(Paragraph("<b>User 表</b>", styles['Heading3Custom']))
    user_data = [
        ["字段名", "类型", "说明"],
        ["id", "Integer", "主键，自增"],
        ["username", "String", "用户名，唯一"],
        ["password_hash", "String", "密码哈希（bcrypt）"],
        ["role", "String", "角色（admin/user）"],
        ["is_active", "Boolean", "是否激活"],
        ["created_at", "DateTime", "创建时间"],
    ]
    user_table = Table(user_data, colWidths=[3.5 * cm, 3 * cm, 8.5 * cm])
    user_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(user_table)
    elements.append(Spacer(1, 0.5 * cm))
    
    # Case 表
    elements.append(Paragraph("<b>Case 表</b>", styles['Heading3Custom']))
    case_data = [
        ["字段名", "类型", "说明"],
        ["id", "Integer", "主键，自增"],
        ["name", "String", "案件名称"],
        ["fact_text", "Text", "案件事实文本"],
        ["status", "String", "案件状态"],
        ["user_id", "Integer", "创建用户 ID"],
        ["created_at", "DateTime", "创建时间"],
        ["updated_at", "DateTime", "更新时间"],
    ]
    case_table = Table(case_data, colWidths=[3.5 * cm, 3 * cm, 8.5 * cm])
    case_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(case_table)
    
    elements.append(PageBreak())
    return elements


def build_chapter5(styles) -> list:
    """第 5 章 知识库设计"""
    elements = []
    
    elements.append(Paragraph("第 5 章 知识库设计", styles['Heading1Custom']))
    
    elements.append(Paragraph("5.1 规则体系", styles['Heading2Custom']))
    elements.append(Paragraph(
        "知识库的规则体系基于《帮信解释》第十一条制定，包含以下法律推定规则：",
        styles['BodyTextCustom']
    ))
    
    rules = [
        ("规则 1：异常高额报酬", "行为人获得的报酬明显高于市场正常水平，且无法合理解释"),
        ("规则 2：资金快进快出", "银行账户资金流转呈现快进快出特征，与正常交易模式不符"),
        ("规则 3：频繁更换通讯工具", "行为人频繁更换手机号、银行卡等通讯工具，规避监管"),
        ("规则 4：逃避监管措施", "行为人采取隐蔽手段逃避银行、公安等部门的监管措施"),
        ("规则 5：拒不说明来源", "行为人拒不说明资金、物品的合法来源和用途"),
        ("规则 6：曾被告知风险", "行为人曾被银行、公安等部门告知涉嫌违法犯罪风险后仍继续实施"),
    ]
    
    for name, desc in rules:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        caption="图 5-1 法律推定规则体系示意图"
    ))
    
    elements.append(Paragraph("5.2 标签体系", styles['Heading2Custom']))
    elements.append(Paragraph(
        "标签体系用于对案件特征进行分类标记，包括三类标签：",
        styles['BodyTextCustom']
    ))
    
    tag_types = [
        ("行为特征标签", "如【异常高额报酬】、【资金快进快出】、【频繁更换通讯工具】等，用于标记客观行为异常"),
        ("认知能力标签", "如【长期从事相关工作】、【具备专业知识】、【曾被告知风险】等，用于标记行为人认知水平"),
        ("辩解类型标签", "如【不知情辩解】、【被蒙骗辩解】、【正常业务往来辩解】等，用于标记嫌疑人辩解类型"),
    ]
    
    for name, desc in tag_types:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.append(Paragraph("5.3 冲突体系", styles['Heading2Custom']))
    elements.append(Paragraph(
        "冲突检测功能用于发现规则之间或规则与案例之间的矛盾关系。系统会自动识别潜在的冲突，"
        "并提示管理员进行处理。冲突类型包括：",
        styles['BodyTextCustom']
    ))
    
    conflict_types = [
        "规则间冲突：两条规则的适用条件存在矛盾",
        "规则与案例冲突：规则结论与案例实际判决不一致",
        "案例间冲突：相似案例的判决结果差异过大",
    ]
    for ct in conflict_types:
        elements.append(Paragraph(f"• {ct}", styles['ListItem']))
    
    elements.extend(create_placeholder_image(
        caption="图 5-2 知识库三层体系示意图"
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter6(styles) -> list:
    """第 6 章 推理引擎设计"""
    elements = []
    
    elements.append(Paragraph("第 6 章 推理引擎设计", styles['Heading1Custom']))
    
    elements.append(Paragraph("6.1 三维度模型", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统从以下三个维度对案件进行综合分析：",
        styles['BodyTextCustom']
    ))
    
    dim_data = [
        ["分析维度", "评估内容", "评分范围"],
        ["客观行为异常度", "评估行为是否偏离正常交易/通讯模式", "0-10 分"],
        ["认知能力匹配度", "评估行为人认知水平与犯罪模式的匹配程度", "0-10 分"],
        ["辩解合理性", "评估嫌疑人辩解的逻辑合理性和可信度", "0-10 分"],
    ]
    
    dim_table = Table(dim_data, colWidths=[4 * cm, 8 * cm, 3 * cm])
    dim_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e67e22')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(dim_table)
    elements.append(Spacer(1, 0.5 * cm))
    
    elements.append(Paragraph(
        "综合评分（knowledge_score）范围为 0-10 分：0-3 分表示确实不明知，4-6 分表示边缘情况，"
        "7-10 分表示明显明知。",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph("6.2 规则引擎", styles['Heading2Custom']))
    elements.append(Paragraph(
        "规则引擎基于知识图谱的推定规则进行匹配和推理。核心流程包括：",
        styles['BodyTextCustom']
    ))
    
    engine_steps = [
        ("特征提取", "从案件文本中提取关键特征，如行为类型、交易金额、通讯方式等"),
        ("规则匹配", "基于 Jaccard 相似度计算，将提取的特征与知识图谱中的推定规则进行匹配"),
        ("推理路径生成", "根据匹配的规则，生成从证据到规则的完整推理链条"),
        ("结论生成", "综合多个规则的匹配结果，生成最终的分析结论和置信度"),
    ]
    
    for name, desc in engine_steps:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        caption="图 6-1 规则引擎推理流程"
    ))
    
    elements.append(Paragraph("6.3 标签抽取", styles['Heading2Custom']))
    elements.append(Paragraph(
        "标签抽取机制通过 LLM 从案件文本中自动提取关键特征标签。抽取过程包括：",
        styles['BodyTextCustom']
    ))
    
    extract_steps = [
        "文本预处理：去除无关字符，标准化格式",
        "LLM 抽取：调用大语言模型识别案件中的关键实体和特征",
        "标签分类：将抽取的特征映射到预定义的标签体系",
        "标签清洗：去除重复和矛盾的标签，确保一致性",
    ]
    for i, step in enumerate(extract_steps, 1):
        elements.append(Paragraph(f"{i}. {step}", styles['ListItem']))
    
    elements.append(PageBreak())
    return elements


def build_chapter7(styles) -> list:
    """第 7 章 报告生成设计"""
    elements = []
    
    elements.append(Paragraph("第 7 章 报告生成设计", styles['Heading1Custom']))
    
    elements.append(Paragraph("7.1 10 章模板", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统生成的分析报告包含以下 10 个章节：",
        styles['BodyTextCustom']
    ))
    
    chapters = [
        ("第 1 章 案件基本信息", "案件名称、编号、当事人信息、受理时间等"),
        ("第 2 章 案件事实概述", "案件事实的简要描述，包括行为过程、涉案金额等"),
        ("第 3 章 三维度分析结果", "客观行为异常度、认知能力匹配度、辩解合理性的评分和分析"),
        ("第 4 章 推理依据", "每个维度的推理过程、引用证据和相关法条"),
        ("第 5 章 类案参考", "相似案例推荐及量刑参考"),
        ("第 6 章 量刑建议", "基于历史判例的量刑建议，包括刑期、罚金区间"),
        ("第 7 章 证据清单", "案件涉及的所有证据及其证明目的"),
        ("第 8 章 法律适用", "适用的法律法规及司法解释"),
        ("第 9 章 分析结论", "综合分析结论及置信度"),
        ("第 10 章 建议与说明", "对案件处理的建议及注意事项"),
    ]
    
    for name, desc in chapters:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        caption="图 7-1 报告模板结构"
    ))
    
    elements.append(Paragraph("7.2 实现机制", styles['Heading2Custom']))
    elements.append(Paragraph(
        "报告生成采用前端导出方案，使用 html2canvas 和 jsPDF 库将 HTML 页面转换为 PDF 文件。"
        "实现流程如下：",
        styles['BodyTextCustom']
    ))
    
    impl_steps = [
        "前端页面渲染完整的分析报告 HTML",
        "用户点击【导出 PDF】按钮",
        "html2canvas 将 HTML 元素转换为 Canvas 图像",
        "jsPDF 将 Canvas 图像拼接为 PDF 文件",
        "浏览器下载生成的 PDF 文件",
    ]
    for i, step in enumerate(impl_steps, 1):
        elements.append(Paragraph(f"{i}. {step}", styles['ListItem']))
    
    elements.append(PageBreak())
    return elements


def build_chapter8(styles) -> list:
    """第 8 章 评测体系设计"""
    elements = []
    
    elements.append(Paragraph("第 8 章 评测体系设计", styles['Heading1Custom']))
    
    elements.append(Paragraph("8.1 金标准", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统评测采用人工标注的金标准数据集。金标准的构建过程如下：",
        styles['BodyTextCustom']
    ))
    
    gold_steps = [
        ("案例收集", "从公开裁判文书网收集贵州地区帮信罪案例，确保案例类型多样、事实清晰"),
        ("专家标注", "邀请 3 名资深检察官对每个案例进行独立标注，给出三维度评分和结论"),
        ("一致性校验", "计算 3 名专家标注的 Cohen's Kappa 系数，确保一致性 ≥ 0.8"),
        ("争议处理", "对于专家意见不一致的案例，组织讨论会形成最终 consensus"),
    ]
    
    for name, desc in gold_steps:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.append(Paragraph("8.2 消融实验", styles['Heading2Custom']))
    elements.append(Paragraph(
        "为验证系统各模块的有效性，设计以下消融实验：",
        styles['BodyTextCustom']
    ))
    
    ablation_data = [
        ["实验编号", "实验配置", "验证目标"],
        ["A/B-01", "完整系统 vs 无知识图谱", "验证知识图谱对分析准确性的贡献"],
        ["A/B-02", "两阶段推理 vs 单次推理", "验证两阶段推理对复杂案件的提升"],
        ["A/B-03", "微调模型 vs 通用模型", "验证领域微调对司法任务的效果"],
        ["A/B-04", "AI 辅助 vs 纯人工", "验证系统对办案效率的提升"],
    ]
    
    ablation_table = Table(ablation_data, colWidths=[2.5 * cm, 5 * cm, 7.5 * cm])
    ablation_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(ablation_table)
    
    elements.append(Paragraph("8.3 竞品对标", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统与市面上其他法律 AI 产品的对标分析，主要对比维度包括：",
        styles['BodyTextCustom']
    ))
    
    compare_items = [
        ("功能完整性", "是否支持三维度分析、知识图谱、类案推送、量刑辅助等完整功能"),
        ("分析准确性", "在金标准数据集上的准确率、召回率、F1 值对比"),
        ("可解释性", "是否提供推理路径追溯、证据引用、法条关联等可解释性功能"),
        ("部署便捷性", "是否支持本地化部署、一键启动、零配置使用"),
    ]
    
    for name, desc in compare_items:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        caption="图 8-1 竞品对标分析示意图"
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter9(styles) -> list:
    """第 9 章 前端设计"""
    elements = []
    
    elements.append(Paragraph("第 9 章 前端设计", styles['Heading1Custom']))
    
    elements.append(Paragraph("9.1 页面结构", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统前端采用 Vue 3 + Vite 构建，包含以下主要页面：",
        styles['BodyTextCustom']
    ))
    
    pages = [
        ("WelcomeView（/）", "系统欢迎页，提供 Demo 案例入口"),
        ("LoginView（/login）", "用户登录页面"),
        ("MainView（/main）", "分析主页，输入案件文本并触发 AI 分析"),
        ("ReportView（/report/:id）", "分析报告页面，展示综合结论和三维度详情"),
        ("CasesView（/cases）", "案件列表页面，支持创建、搜索、删除"),
        ("ReviewView（/review）", "智能阅卷页面，上传文档并提取文本"),
        ("KnowledgeView（/knowledge）", "知识图谱可视化与查询页面"),
        ("ExperimentView（/experiment）", "实验系统页面，案例分配和判断采集"),
        ("SettingsView（/settings）", "系统管理页面，规则、日志、用户管理"),
    ]
    
    for name, desc in pages:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        caption="图 9-1 前端页面结构图"
    ))
    
    elements.append(Paragraph("9.2 交互流程", styles['Heading2Custom']))
    elements.append(Paragraph(
        "用户案件分析的完整交互流程如下：",
        styles['BodyTextCustom']
    ))
    
    flow_steps = [
        "用户登录系统，进入分析主页",
        "输入或上传案件文本，点击【开始分析】按钮",
        "前端调用 API 提交案件文本，显示加载动画",
        "后端返回分析结果，前端跳转到报告页面",
        "用户查看报告，可复制或导出 PDF",
        "用户可在案件管理页面查看历史分析记录",
    ]
    for i, step in enumerate(flow_steps, 1):
        elements.append(Paragraph(f"{i}. {step}", styles['ListItem']))
    
    elements.extend(create_placeholder_image(
        height=8 * cm,
        caption="图 9-2 用户交互流程图"
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter10(styles) -> list:
    """第 10 章 部署与运维设计"""
    elements = []
    
    elements.append(Paragraph("第 10 章 部署与运维设计", styles['Heading1Custom']))
    
    elements.append(Paragraph("10.1 部署方案", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统支持多种部署方式，适应不同场景需求：",
        styles['BodyTextCustom']
    ))
    
    deploy_methods = [
        ("开发环境部署", "使用 Vite 开发服务器和 Uvicorn 热重载，适合开发和调试"),
        ("生产环境部署", "使用 Nginx 反向代理 + Uvicorn 生产模式，支持 HTTPS 和负载均衡"),
        ("Docker 容器化部署", "提供 Dockerfile 和 docker-compose.yml，一键启动完整环境"),
    ]
    
    for name, desc in deploy_methods:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.append(Paragraph(
        "生产环境部署的关键步骤包括：安装 Python 和 Node.js 环境、安装后端和前端依赖、"
        "配置数据库连接、启动 Ollama 服务、启动后端 API 服务、启动前端服务、配置 Nginx 反向代理。",
        styles['BodyTextCustom']
    ))
    
    elements.extend(create_placeholder_image(
        caption="图 10-1 生产环境部署架构图"
    ))
    
    elements.append(Paragraph("10.2 运维策略", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统运维包含以下关键策略：",
        styles['BodyTextCustom']
    ))
    
    ops_strategies = [
        ("日志管理", "使用 loguru 记录系统日志，支持文件轮转和结构化日志，便于问题排查"),
        ("监控告警", "提供健康检查端点 /api/health，监控服务状态；建议集成 Prometheus + Grafana 实现指标监控"),
        ("备份恢复", "定期备份 SQLite 数据库文件和 JSON 数据文件，建议每日增量备份、每周全量备份"),
        ("性能优化", "启用分析缓存机制，缓存有效期 7 天；建议使用 PostgreSQL 替代 SQLite 提升并发性能"),
        ("安全加固", "启用 HTTPS、配置防火墙、定期更新依赖包、审计日志分析"),
    ]
    
    for name, desc in ops_strategies:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.append(PageBreak())
    return elements


def build_chapter11(styles) -> list:
    """第 11 章 安全设计"""
    elements = []
    
    elements.append(Paragraph("第 11 章 安全设计", styles['Heading1Custom']))
    
    elements.append(Paragraph("11.1 安全防护", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统采用多层次安全防护措施，确保数据安全和系统稳定运行：",
        styles['BodyTextCustom']
    ))
    
    security_measures = [
        ("身份认证", "采用 JWT 双 Token 机制，Access Token 有效期 30 分钟，Refresh Token 有效期 7 天，支持 Token 黑名单和自动刷新"),
        ("密码安全", "密码使用 bcrypt 算法进行哈希存储，salt rounds=12，防止暴力破解和彩虹表攻击"),
        ("权限控制", "基于角色的访问控制（RBAC），区分 admin 和 user 角色，敏感操作（如用户管理、规则修改）仅限管理员"),
        ("数据加密", "敏感数据（如密码、Token）在传输和存储过程中均进行加密处理，建议生产环境启用 HTTPS"),
        ("审计日志", "记录所有用户操作和系统事件，包括登录、案件创建、分析请求、规则修改等，便于事后追溯"),
        ("输入校验", "使用 Pydantic 对所有 API 输入进行严格校验，防止 SQL 注入、XSS 攻击等常见安全漏洞"),
        ("速率限制", "提供速率限制中间件，防止恶意刷量和 DDoS 攻击，建议生产环境启用"),
        ("本地化存储", "所有数据、模型、推理均在本地完成，满足司法数据安全要求，防止数据泄露"),
    ]
    
    for name, desc in security_measures:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        caption="图 11-1 系统安全防护体系"
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter12(styles) -> list:
    """第 12 章 接口设计"""
    elements = []
    
    elements.append(Paragraph("第 12 章 接口设计", styles['Heading1Custom']))
    
    elements.append(Paragraph("12.1 API 列表", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统提供完整的 RESTful API，主要接口列表如下：",
        styles['BodyTextCustom']
    ))
    
    api_data = [
        ["接口路径", "方法", "功能说明"],
        ["/api/health", "GET", "健康检查"],
        ["/api/auth/login", "POST", "用户登录"],
        ["/api/auth/refresh", "POST", "刷新 Token"],
        ["/api/cases", "GET", "获取案件列表"],
        ["/api/cases", "POST", "创建案件"],
        ["/api/cases/{id}", "GET", "获取案件详情"],
        ["/api/cases/{id}", "PUT", "更新案件"],
        ["/api/cases/{id}", "DELETE", "删除案件"],
        ["/api/analyze", "POST", "分析案件文本"],
        ["/api/analyze/{id}", "GET", "获取分析结果"],
        ["/api/documents/upload", "POST", "上传文档"],
        ["/api/documents/extract", "POST", "提取文档文本"],
        ["/api/knowledge/graph", "GET", "获取知识图谱"],
        ["/api/knowledge/match-rules", "POST", "规则匹配"],
        ["/api/knowledge/similar-cases", "POST", "相似案例检索"],
        ["/api/knowledge/trace-reasoning", "POST", "推理路径追溯"],
        ["/api/experiment/assign", "POST", "实验案例分配"],
        ["/api/experiment/judge", "POST", "提交实验判断"],
        ["/api/system/rules", "GET", "获取法律规则"],
        ["/api/system/rules", "POST", "创建法律规则"],
        ["/api/system/logs", "GET", "获取系统日志"],
        ["/api/system/users", "GET", "获取用户列表"],
        ["/api/cache/stats", "GET", "缓存统计"],
        ["/api/cache/clear", "POST", "清除缓存"],
    ]
    
    api_table = Table(api_data, colWidths=[5 * cm, 2 * cm, 8 * cm])
    api_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(api_table)
    
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(
        "所有 API 均使用 JWT 认证（除 /api/health 和 /api/auth/login 外），请求头需携带 "
        "Authorization: Bearer <token>。详细接口说明请参考 docs/api_reference.md。",
        styles['BodyTextCustom']
    ))
    
    elements.append(PageBreak())
    return elements


def build_appendix_a(styles) -> list:
    """附录 A：术语表"""
    elements = []
    
    elements.append(Paragraph("附录 A：术语表", styles['Heading1Custom']))
    
    elements.append(Paragraph(
        "本附录对文档中涉及的专业术语进行详细解释：",
        styles['BodyTextCustom']
    ))
    
    terms = [
        ("帮信罪", "帮助信息网络犯罪活动罪，刑法第二百八十七条之二规定的罪名，指明知他人利用信息网络实施犯罪，为其犯罪提供互联网接入、服务器托管、网络存储、通讯传输等技术支持，或者提供广告推广、支付结算等帮助，情节严重的行为"),
        ("主观明知", "帮信罪构成要件中行为人主观上【明知他人利用信息网络实施犯罪】的心理状态，是认定帮信罪的关键要素"),
        ("三维度分析模型", "本系统提出的分析框架，从客观行为异常度、认知能力与作案模式匹配度、辩解合理性三个维度综合评估行为人的主观明知状态"),
        ("知识图谱", "由特征节点、推定规则、推理路径、案例三层组成的图结构，用于存储和查询法律知识"),
        ("推定规则", "基于《帮信解释》第十一条的【可推定明知】的若干情形，如异常高额报酬、资金快进快出等"),
        ("推理路径", "由证据→规则→结论组成的完整推理链，支持可解释性分析"),
        ("LoRA", "Low-Rank Adaptation，一种参数高效的大模型微调方法，通过低秩矩阵分解减少可训练参数量"),
        ("两阶段推理管线", "针对复杂案件设计的推理策略，第一阶段提取结构化事实，第二阶段基于事实进行维度分析"),
        ("Jaccard 相似度", "用于衡量两个集合相似度的指标，定义为交集大小除以并集大小，用于规则匹配和相似案例检索"),
        ("消融实验", "通过对比完整系统和去除某些模块的系统性能差异，验证各模块有效性的实验方法"),
        ("金标准", "由专家标注的高质量数据集，用于评测系统分析结果的准确性"),
    ]
    
    for term, definition in terms:
        elements.append(Paragraph(f"<b>{term}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(definition, styles['BodyTextCustom']))
        elements.append(Spacer(1, 0.3 * cm))
    
    return elements


def build_appendix_b(styles) -> list:
    """附录 B：算法说明"""
    elements = []
    
    elements.append(Paragraph("附录 B：算法说明", styles['Heading1Custom']))
    
    elements.append(Paragraph(
        "本附录对系统中使用的核心算法进行详细说明：",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph("<b>1. Jaccard 相似度算法</b>", styles['Heading3Custom']))
    elements.append(Paragraph(
        "Jaccard 相似度用于衡量两个集合的相似程度，计算公式为：J(A,B) = |A∩B| / |A∪B|。"
        "在系统中用于规则匹配和相似案例检索，将案件特征集合与规则特征集合或案例特征集合进行比较。",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph("<b>2. MD5 缓存索引算法</b>", styles['Heading3Custom']))
    elements.append(Paragraph(
        "系统使用 MD5 哈希算法对案件文本进行摘要，取前 16 位作为缓存索引键。"
        "相同文本的 MD5 摘要相同，可直接命中缓存，避免重复调用 LLM，提升响应速度。"
        "缓存有效期为 7 天，过期后自动清理。",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph("<b>3. bcrypt 密码哈希算法</b>", styles['Heading3Custom']))
    elements.append(Paragraph(
        "系统使用 bcrypt 算法对用户密码进行哈希存储。bcrypt 基于 Blowfish 密码算法，"
        "内置 salt 防止彩虹表攻击，cost factor（salt rounds=12）可调整计算复杂度，"
        "有效抵御暴力破解。",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph("<b>4. LoRA 微调算法</b>", styles['Heading3Custom']))
    elements.append(Paragraph(
        "LoRA（Low-Rank Adaptation）通过低秩矩阵分解实现参数高效微调。"
        "假设预训练权重为 W∈R^(d×k)，LoRA 将更新量分解为 ΔW = BA，"
        "其中 B∈R^(d×r)、A∈R^(r×k)，秩 r << min(d,k)。"
        "训练时冻结 W，只训练 A 和 B，大幅减少可训练参数量（约 0.1%-1%），"
        "降低显存需求，训练速度提升 2-3 倍。",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph("<b>5. 两阶段推理算法</b>", styles['Heading3Custom']))
    elements.append(Paragraph(
        "针对复杂案件（文本 > 2000 字或行为人 > 3），系统采用两阶段推理策略：",
        styles['BodyTextCustom']
    ))
    
    stage_desc = [
        ("Stage 1：事实提取", "从原始案件文本中提取 6 要素（行为人、行为、工具、通讯、获利、辩解），"
         "输出约 300 Token 的结构化事实 JSON"),
        ("Stage 2：维度分析", "基于结构化事实进行三维度分析，输出约 500 Token 的分析结果 JSON"),
    ]
    for name, desc in stage_desc:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.append(Paragraph(
        "两阶段推理相比单次推理 Token 消耗增加约 16%，但显著提升复杂案件的分析准确性。",
        styles['BodyTextCustom']
    ))
    
    elements.extend(create_placeholder_image(
        caption="图 B-1 两阶段推理流程图"
    ))
    
    return elements


def generate_design_spec():
    """生成设计说明书 PDF"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    font_name = register_fonts()
    styles = create_styles(font_name)
    
    doc = SimpleDocTemplate(
        str(OUTPUT_FILE),
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title="帮信罪主观明知分析系统 - 设计说明书",
        author="系统开发团队",
    )
    
    elements = []
    
    elements.extend(build_cover_page(styles))
    elements.extend(build_toc(styles))
    
    elements.extend(build_chapter1(styles))
    elements.extend(build_chapter2(styles))
    elements.extend(build_chapter3(styles))
    elements.extend(build_chapter4(styles))
    elements.extend(build_chapter5(styles))
    elements.extend(build_chapter6(styles))
    elements.extend(build_chapter7(styles))
    elements.extend(build_chapter8(styles))
    elements.extend(build_chapter9(styles))
    elements.extend(build_chapter10(styles))
    elements.extend(build_chapter11(styles))
    elements.extend(build_chapter12(styles))
    
    elements.extend(build_appendix_a(styles))
    elements.extend(build_appendix_b(styles))
    
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    
    print(f"[OK] 设计说明书已生成：{OUTPUT_FILE}")
    print(f"  文件大小：{OUTPUT_FILE.stat().st_size / 1024:.1f} KB")
    
    return OUTPUT_FILE


if __name__ == "__main__":
    try:
        output_file = generate_design_spec()
        print(f"\n生成成功！输出文件：{output_file}")
    except Exception as e:
        print(f"\n生成失败：{e}", file=sys.stderr)
        sys.exit(1)
