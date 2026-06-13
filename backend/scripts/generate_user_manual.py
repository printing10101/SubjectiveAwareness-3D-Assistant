#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户手册 PDF 生成脚本

基于 docs/user_guide.md 生成规范的用户手册 PDF 文档。
输出路径: 03_软件文档/用户手册.pdf

要求:
- 总页数 >= 15 页
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
OUTPUT_FILE = OUTPUT_DIR / "用户手册.pdf"

# 页面设置
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 2.5 * cm
RIGHT_MARGIN = 2.5 * cm
TOP_MARGIN = 2.5 * cm
BOTTOM_MARGIN = 2.5 * cm


def register_fonts():
    """注册中文字体"""
    # 尝试注册宋体
    font_paths = [
        "C:/Windows/Fonts/simsun.ttc",  # Windows
        "/System/Library/Fonts/STSong.ttf",  # macOS
        "/usr/share/fonts/truetype/arphic/uming.ttc",  # Linux
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('SimSun', font_path))
                return 'SimSun'
            except Exception:
                continue
    
    # 如果找不到宋体，使用默认字体
    return 'Helvetica'


def create_styles(font_name: str):
    """创建文档样式"""
    styles = getSampleStyleSheet()
    
    # 封面标题样式
    styles.add(ParagraphStyle(
        name='CoverTitle',
        fontName=font_name,
        fontSize=28,
        leading=36,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.HexColor('#1a1a1a'),
    ))
    
    # 封面副标题样式
    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        fontName=font_name,
        fontSize=16,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#4a4a4a'),
    ))
    
    # 一级标题样式（章标题）
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
    
    # 二级标题样式
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
    
    # 三级标题样式
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
    
    # 正文样式（小四号 = 12pt）
    styles.add(ParagraphStyle(
        name='BodyTextCustom',
        fontName=font_name,
        fontSize=12,
        leading=20,
        alignment=TA_JUSTIFY,
        spaceBefore=6,
        spaceAfter=6,
        firstLineIndent=24,  # 首行缩进2字符
    ))
    
    # 列表项样式
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
    
    # 表格标题样式
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
    
    # 图片说明样式
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
    
    # 页眉样式
    styles.add(ParagraphStyle(
        name='Header',
        fontName=font_name,
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#888888'),
    ))
    
    # 页脚样式
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
    
    # 创建占位图表格
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
    
    # 页眉
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(colors.HexColor('#888888'))
    header_text = "帮信罪主观明知分析系统 - 用户手册"
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 1.5 * cm, header_text)
    
    # 页眉线
    canvas.setStrokeColor(colors.HexColor('#cccccc'))
    canvas.setLineWidth(0.5)
    canvas.line(LEFT_MARGIN, PAGE_HEIGHT - 1.8 * cm, 
                PAGE_WIDTH - RIGHT_MARGIN, PAGE_HEIGHT - 1.8 * cm)
    
    # 页脚
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(colors.HexColor('#888888'))
    page_num = canvas.getPageNumber()
    canvas.drawCentredString(PAGE_WIDTH / 2, 1.5 * cm, f"- {page_num} -")
    
    # 页脚线
    canvas.line(LEFT_MARGIN, 2 * cm, PAGE_WIDTH - RIGHT_MARGIN, 2 * cm)
    
    canvas.restoreState()


def build_cover_page(styles) -> list:
    """构建封面页"""
    elements = []
    
    # 空行
    elements.append(Spacer(1, 3 * cm))
    
    # 主标题
    title = Paragraph("帮信罪主观明知分析系统", styles['CoverTitle'])
    elements.append(title)
    
    # 副标题
    subtitle = Paragraph("用户手册", styles['CoverSubtitle'])
    elements.append(subtitle)
    
    elements.append(Spacer(1, 2 * cm))
    
    # 版本信息
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
    
    # 版权声明
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
        ("第1章 系统概述", "1"),
        ("  1.1 系统简介", "1"),
        ("  1.2 核心功能", "1"),
        ("  1.3 目标用户", "2"),
        ("第2章 系统架构", "3"),
        ("  2.1 整体架构", "3"),
        ("  2.2 主要模块", "3"),
        ("第3章 安装部署", "5"),
        ("  3.1 环境要求", "5"),
        ("  3.2 安装步骤", "5"),
        ("  3.3 系统启动", "6"),
        ("第4章 快速上手", "7"),
        ("  4.1 用户登录", "7"),
        ("  4.2 案件上传", "7"),
        ("  4.3 分析结果查看", "8"),
        ("  4.4 报告生成", "8"),
        ("第5章 案件分析", "9"),
        ("  5.1 分析流程", "9"),
        ("  5.2 三维度分析", "10"),
        ("第6章 报告管理", "11"),
        ("  6.1 报告查看", "11"),
        ("  6.2 报告下载", "11"),
        ("  6.3 报告审查", "12"),
        ("第7章 知识库", "13"),
        ("  7.1 规则查看", "13"),
        ("  7.2 标签查看", "13"),
        ("  7.3 冲突查看", "14"),
        ("第8章 系统设置", "15"),
        ("  8.1 配置调整", "15"),
        ("第9章 常见问题FAQ", "16"),
        ("第10章 错误码表", "18"),
    ]
    
    for item, page in toc_items:
        if item.startswith("第"):
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
    """第1章 系统概述"""
    elements = []
    
    elements.append(Paragraph("第1章 系统概述", styles['Heading1Custom']))
    
    elements.append(Paragraph("1.1 系统简介", styles['Heading2Custom']))
    elements.append(Paragraph(
        "帮信罪主观明知分析系统是一款基于大语言模型（LLM）和知识图谱技术的司法智能辅助工具，"
        "专用于帮助信息网络犯罪活动罪（帮信罪）案件中的【主观明知】要素分析。",
        styles['BodyTextCustom']
    ))
    elements.append(Paragraph(
        "系统从客观行为异常度、认知能力与作案模式匹配度、辩解合理性三个维度进行综合评估，"
        "辅助检察官、法官等司法人员进行标准化案件分析。",
        styles['BodyTextCustom']
    ))
    
    elements.extend(create_placeholder_image(
        caption="图 1-1 系统主界面示意图"
    ))
    
    elements.append(Paragraph("1.2 核心功能", styles['Heading2Custom']))
    elements.append(Paragraph(
        "本系统提供以下核心功能模块，全面覆盖帮信罪案件分析的业务需求：",
        styles['BodyTextCustom']
    ))
    
    # 功能表格
    func_data = [
        ["功能模块", "功能说明"],
        ["智能分析", "输入案件事实文本，AI自动进行三维度分析并生成分析报告"],
        ["智能阅卷", "上传PDF/DOCX文档，自动提取文本和实体信息"],
        ["类案推送", "基于知识图谱的相似案例推荐"],
        ["量刑辅助", "基于历史判例的量刑参考建议"],
        ["知识图谱", "法律法规与案例的知识网络查询"],
        ["实验系统", "支持回溯性对比实验的数据采集"],
        ["案件管理", "案件的创建、查看、搜索和删除"],
    ]
    
    func_table = Table(func_data, colWidths=[3 * cm, 12 * cm])
    func_table.setStyle(TableStyle([
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
    elements.append(func_table)
    elements.append(Spacer(1, 0.5 * cm))
    
    elements.append(Paragraph("1.3 目标用户", styles['Heading2Custom']))
    elements.append(Paragraph(
        "本系统主要面向以下用户群体：",
        styles['BodyTextCustom']
    ))
    
    users = [
        "检察官：负责案件审查起诉，需要快速准确地判断嫌疑人主观明知状态",
        "法官：负责案件审理裁判，需要参考AI分析结果辅助判决",
        "公安干警：负责案件侦查，需要初步判断案件性质",
        "法律研究人员：进行帮信罪相关研究和数据分析",
    ]
    for user in users:
        elements.append(Paragraph(f"• {user}", styles['ListItem']))
    
    elements.extend(create_placeholder_image(
        caption="图 1-2 系统用户角色示意图"
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter2(styles) -> list:
    """第2章 系统架构"""
    elements = []
    
    elements.append(Paragraph("第2章 系统架构", styles['Heading1Custom']))
    
    elements.append(Paragraph("2.1 整体架构", styles['Heading2Custom']))
    elements.append(Paragraph(
        "本系统采用前后端分离的B/S架构，分为展示层、接入层、业务层、推理层和数据层五个层次。"
        "各层职责清晰，便于维护和扩展。",
        styles['BodyTextCustom']
    ))
    
    elements.extend(create_placeholder_image(
        height=10 * cm,
        caption="图 2-1 系统五层架构图"
    ))
    
    elements.append(Paragraph("2.2 主要模块", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统主要包含以下功能模块：",
        styles['BodyTextCustom']
    ))
    
    modules = [
        ("案件管理模块", "负责案件的CRUD操作、状态管理、搜索筛选等功能"),
        ("分析推理模块", "核心AI分析引擎，实现三维度分析和报告生成"),
        ("文档处理模块", "处理PDF/DOCX文档上传、文本提取、实体抽取"),
        ("知识图谱模块", "管理法律规则、案例知识、推理路径"),
        ("用户管理模块", "用户认证、权限控制、角色管理"),
        ("系统管理模块", "系统配置、日志管理、版本控制"),
    ]
    
    for name, desc in modules:
        elements.append(Paragraph(f"<b>{name}</b>：{desc}", styles['ListItem']))
    
    elements.extend(create_placeholder_image(
        caption="图 2-2 系统模块关系图"
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter3(styles) -> list:
    """第3章 安装部署"""
    elements = []
    
    elements.append(Paragraph("第3章 安装部署", styles['Heading1Custom']))
    
    elements.append(Paragraph("3.1 环境要求", styles['Heading2Custom']))
    elements.append(Paragraph(
        "部署本系统需要满足以下硬件和软件环境要求：",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph("<b>硬件要求</b>", styles['Heading3Custom']))
    hw_reqs = [
        "CPU：4核及以上处理器",
        "内存：8GB RAM及以上（推荐16GB）",
        "硬盘：50GB可用存储空间",
        "网络：稳定的局域网或互联网连接",
    ]
    for req in hw_reqs:
        elements.append(Paragraph(f"• {req}", styles['ListItem']))
    
    elements.append(Paragraph("<b>软件要求</b>", styles['Heading3Custom']))
    sw_reqs = [
        "操作系统：Windows 10/11、Linux（Ubuntu 20.04+）、macOS",
        "Python：3.10及以上版本",
        "Node.js：18.x及以上版本",
        "数据库：SQLite（内置）或PostgreSQL 14+",
        "AI模型：Ollama服务及DeepSeek-R1模型",
    ]
    for req in sw_reqs:
        elements.append(Paragraph(f"• {req}", styles['ListItem']))
    
    elements.append(Paragraph("3.2 安装步骤", styles['Heading2Custom']))
    elements.append(Paragraph(
        "请按照以下步骤完成系统安装：",
        styles['BodyTextCustom']
    ))
    
    steps = [
        ("步骤1：获取源代码", "从代码仓库克隆或下载项目源代码到本地目录"),
        ("步骤2：安装后端依赖", "进入backend目录，执行 pip install -r requirements.txt"),
        ("步骤3：安装前端依赖", "进入frontend目录，执行 npm install"),
        ("步骤4：配置数据库", "复制.env.example为.env，配置数据库连接信息"),
        ("步骤5：初始化数据", "执行数据库迁移脚本，导入初始数据"),
        ("步骤6：启动Ollama", "确保Ollama服务正常运行，加载所需模型"),
    ]
    
    for i, (title, desc) in enumerate(steps, 1):
        elements.append(Paragraph(f"<b>{title}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        caption="图 3-1 安装部署流程图"
    ))
    
    elements.append(Paragraph("3.3 系统启动", styles['Heading2Custom']))
    elements.append(Paragraph(
        "完成安装后，按以下顺序启动系统：",
        styles['BodyTextCustom']
    ))
    
    start_steps = [
        "启动数据库服务（如使用PostgreSQL）",
        "启动Ollama AI推理服务",
        "启动后端API服务：cd backend && python run.py",
        "启动前端开发服务器：cd frontend && npm run dev",
        "访问 http://localhost:5173 进入系统",
    ]
    for i, step in enumerate(start_steps, 1):
        elements.append(Paragraph(f"{i}. {step}", styles['ListItem']))
    
    elements.append(PageBreak())
    return elements


def build_chapter4(styles) -> list:
    """第4章 快速上手"""
    elements = []
    
    elements.append(Paragraph("第4章 快速上手", styles['Heading1Custom']))
    
    elements.append(Paragraph("4.1 用户登录", styles['Heading2Custom']))
    elements.append(Paragraph(
        "首次使用系统时，需要进行用户登录：",
        styles['BodyTextCustom']
    ))
    
    login_steps = [
        "打开浏览器，访问系统地址（开发环境：http://localhost:5173）",
        "在登录页面输入用户名和密码（默认管理员账号：admin / admin123）",
        "点击【登录】按钮",
        "登录成功后自动跳转到分析主页面",
    ]
    for i, step in enumerate(login_steps, 1):
        elements.append(Paragraph(f"{i}. {step}", styles['ListItem']))
    
    elements.extend(create_placeholder_image(
        caption="图 4-1 用户登录界面"
    ))
    
    elements.append(Paragraph("4.2 案件上传", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统支持多种方式上传案件信息：",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph("<b>方式一：手动输入</b>", styles['Heading3Custom']))
    elements.append(Paragraph(
        "在分析主页面直接输入或粘贴案件事实文本，文本长度限制为10-50000字符。",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph("<b>方式二：文档上传</b>", styles['Heading3Custom']))
    elements.append(Paragraph(
        "进入【智能阅卷】页面，上传PDF或DOCX格式的案件文档，系统自动提取文本内容。",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph("<b>方式三：使用Demo案例</b>", styles['Heading3Custom']))
    elements.append(Paragraph(
        "点击页面上的Demo案例按钮，系统提供三种类型的预设案例供测试使用。",
        styles['BodyTextCustom']
    ))
    
    elements.extend(create_placeholder_image(
        caption="图 4-2 案件上传界面"
    ))
    
    elements.append(Paragraph("4.3 分析结果查看", styles['Heading2Custom']))
    elements.append(Paragraph(
        "案件分析完成后，系统自动展示分析结果，包括：",
        styles['BodyTextCustom']
    ))
    
    result_items = [
        "综合结论：明显明知/边缘情况/确实不明知",
        "三维度评分：客观行为异常度、认知能力匹配度、辩解合理性",
        "推理依据：每个维度的分析说明和证据引用",
        "置信度：分析结果的可信程度百分比",
    ]
    for item in result_items:
        elements.append(Paragraph(f"• {item}", styles['ListItem']))
    
    elements.append(Paragraph("4.4 报告生成", styles['Heading2Custom']))
    elements.append(Paragraph(
        "分析结果页面提供报告导出功能：",
        styles['BodyTextCustom']
    ))
    
    report_steps = [
        "点击【复制】按钮，将报告以Markdown格式复制到剪贴板",
        "点击【导出PDF】按钮，生成PDF格式的分析报告",
        "报告包含完整的分析过程、结论和建议",
    ]
    for i, step in enumerate(report_steps, 1):
        elements.append(Paragraph(f"{i}. {step}", styles['ListItem']))
    
    elements.extend(create_placeholder_image(
        caption="图 4-3 分析报告界面"
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter5(styles) -> list:
    """第5章 案件分析"""
    elements = []
    
    elements.append(Paragraph("第5章 案件分析", styles['Heading1Custom']))
    
    elements.append(Paragraph("5.1 分析流程", styles['Heading2Custom']))
    elements.append(Paragraph(
        "案件分析的完整流程如下：",
        styles['BodyTextCustom']
    ))
    
    flow_steps = [
        ("输入案件文本", "通过手动输入、文档上传或Demo案例方式提供案件事实"),
        ("复杂度判断", "系统自动判断案件复杂度，选择单次推理或两阶段推理"),
        ("AI分析", "调用大语言模型进行三维度分析"),
        ("结果生成", "生成包含评分、依据、结论的完整分析报告"),
        ("缓存存储", "分析结果存入缓存，相同案件再次分析可直接返回"),
    ]
    
    for i, (title, desc) in enumerate(flow_steps, 1):
        elements.append(Paragraph(f"<b>步骤{i}：{title}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        height=8 * cm,
        caption="图 5-1 案件分析流程图"
    ))
    
    elements.append(Paragraph("5.2 三维度分析", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统从以下三个维度对案件进行综合分析：",
        styles['BodyTextCustom']
    ))
    
    # 维度表格
    dim_data = [
        ["分析维度", "评估内容", "评分范围"],
        ["客观行为异常度", "评估行为是否偏离正常交易/通讯模式", "0-10分"],
        ["认知能力匹配度", "评估行为人认知水平与犯罪模式的匹配程度", "0-10分"],
        ["辩解合理性", "评估嫌疑人辩解的逻辑合理性和可信度", "0-10分"],
    ]
    
    dim_table = Table(dim_data, colWidths=[4 * cm, 8 * cm, 3 * cm])
    dim_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
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
        "综合评分（knowledge_score）范围为0-10分：",
        styles['BodyTextCustom']
    ))
    
    score_items = [
        "0-3分：确实不明知",
        "4-6分：可能不明知或可能明知（边缘情况）",
        "7-10分：明显明知",
    ]
    for item in score_items:
        elements.append(Paragraph(f"• {item}", styles['ListItem']))
    
    elements.extend(create_placeholder_image(
        caption="图 5-2 三维度分析结果展示"
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter6(styles) -> list:
    """第6章 报告管理"""
    elements = []
    
    elements.append(Paragraph("第6章 报告管理", styles['Heading1Custom']))
    
    elements.append(Paragraph("6.1 报告查看", styles['Heading2Custom']))
    elements.append(Paragraph(
        "分析报告页面展示AI分析的完整结果，包括：",
        styles['BodyTextCustom']
    ))
    
    report_sections = [
        ("综合结论", "显示结论类型（明显明知/边缘情况/确实不明知）、总体描述和置信度"),
        ("维度分析", "每个维度的评分、推理依据、引用证据和相关法条"),
        ("推理链条", "从证据到规则的完整逻辑路径，支持多链条展示"),
    ]
    
    for name, desc in report_sections:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        caption="图 6-1 分析报告查看界面"
    ))
    
    elements.append(Paragraph("6.2 报告下载", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统提供两种报告导出方式：",
        styles['BodyTextCustom']
    ))
    
    export_methods = [
        ("复制为Markdown", "点击【复制】按钮，将报告以Markdown格式复制到剪贴板，可粘贴到文档编辑器"),
        ("导出PDF", "点击【导出PDF】按钮，使用html2canvas和jsPDF生成本地PDF文件"),
    ]
    
    for name, desc in export_methods:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.append(Paragraph("6.3 报告审查", styles['Heading2Custom']))
    elements.append(Paragraph(
        "用户可以对分析报告进行审查和批注：",
        styles['BodyTextCustom']
    ))
    
    review_items = [
        "查看分析依据是否充分",
        "评估推理逻辑是否合理",
        "检查引用法条是否准确",
        "判断结论是否可接受",
        "必要时可重新调整案件文本进行分析",
    ]
    for item in review_items:
        elements.append(Paragraph(f"• {item}", styles['ListItem']))
    
    elements.extend(create_placeholder_image(
        caption="图 6-2 报告审查流程"
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter7(styles) -> list:
    """第7章 知识库"""
    elements = []
    
    elements.append(Paragraph("第7章 知识库", styles['Heading1Custom']))
    
    elements.append(Paragraph("7.1 规则查看", styles['Heading2Custom']))
    elements.append(Paragraph(
        "知识库包含帮信罪相关的法律推定规则，用户可在系统管理页面查看：",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph(
        "规则内容包括：规则ID、规则名称、描述、来源法律、条款、适用条件、结论、证据类型和权重。"
        "这些规则基于《帮信解释》第十一条制定，用于指导AI分析。",
        styles['BodyTextCustom']
    ))
    
    elements.extend(create_placeholder_image(
        caption="图 7-1 法律规则查看界面"
    ))
    
    elements.append(Paragraph("7.2 标签查看", styles['Heading2Custom']))
    elements.append(Paragraph(
        "标签体系用于对案件特征进行分类标记，包括：",
        styles['BodyTextCustom']
    ))
    
    tag_types = [
        "行为特征标签：如【异常高额报酬】、【资金快进快出】等",
        "认知能力标签：如【长期从事相关工作】、【具备专业知识】等",
        "辩解类型标签：如【不知情辩解】、【被蒙骗辩解】等",
    ]
    for tag in tag_types:
        elements.append(Paragraph(f"• {tag}", styles['ListItem']))
    
    elements.append(Paragraph("7.3 冲突查看", styles['Heading2Custom']))
    elements.append(Paragraph(
        "冲突检测功能用于发现规则之间或规则与案例之间的矛盾关系。"
        "系统会自动识别潜在的冲突，并提示管理员进行处理。",
        styles['BodyTextCustom']
    ))
    
    elements.append(Paragraph(
        "冲突查看页面显示冲突的详细信息，包括冲突类型、涉及的规则或案例、冲突描述等。",
        styles['BodyTextCustom']
    ))
    
    elements.extend(create_placeholder_image(
        caption="图 7-2 知识库管理界面"
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter8(styles) -> list:
    """第8章 系统设置"""
    elements = []
    
    elements.append(Paragraph("第8章 系统设置", styles['Heading1Custom']))
    
    elements.append(Paragraph("8.1 配置调整", styles['Heading2Custom']))
    elements.append(Paragraph(
        "系统设置页面提供以下配置功能（仅管理员可用）：",
        styles['BodyTextCustom']
    ))
    
    settings = [
        ("法律规则管理", "新增、编辑、删除法律推定规则，调整规则权重"),
        ("模型版本信息", "查看当前AI模型版本、微调时间、评估指标等"),
        ("系统日志", "查看系统操作日志，支持按级别筛选和关键词搜索"),
        ("用户管理", "新增用户、启用/禁用账户、重置密码"),
    ]
    
    for name, desc in settings:
        elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(desc, styles['BodyTextCustom']))
    
    elements.extend(create_placeholder_image(
        caption="图 8-1 系统设置界面"
    ))
    
    elements.append(Paragraph(
        "系统配置修改后会自动保存，部分配置需要重新登录才能生效。"
        "建议在进行重要配置修改前做好备份。",
        styles['BodyTextCustom']
    ))
    
    elements.append(PageBreak())
    return elements


def build_chapter9(styles) -> list:
    """第9章 常见问题FAQ"""
    elements = []
    
    elements.append(Paragraph("第9章 常见问题FAQ", styles['Heading1Custom']))
    
    faqs = [
        ("Q1：分析结果不准确怎么办？",
         "A：请确认案件文本包含足够的案件事实细节，建议提供交易过程、聊天记录、嫌疑人供述等关键信息。"
         "系统分析结果仅供参考，不构成法律意见。"),
        
        ("Q2：分析速度为什么很慢？",
         "A：首次分析（缓存未命中）需要调用LLM，通常需要30-60秒。复杂案件（文本>2000字或行为人>3）"
         "会触发两阶段推理管线。同类案件再次分析时将命中缓存，响应时间<1秒。"),
        
        ("Q3：文档上传失败怎么办？",
         "A：请确认文件格式为PDF、DOCX或DOC，文件大小不超过20MB，文件未损坏。"
         "如仍无法上传，请检查网络连接或联系管理员。"),
        
        ("Q4：忘记密码如何找回？",
         "A：普通用户请联系管理员重置密码。管理员可在系统管理-用户管理页面进行密码重置操作。"),
        
        ("Q5：系统支持哪些浏览器？",
         "A：推荐使用Chrome 90+、Firefox 88+、Edge 90+等现代浏览器。不支持IE浏览器。"),
        
        ("Q6：分析结果可以修改吗？",
         "A：分析结果由AI自动生成，不支持直接修改。如需调整，可修改案件文本后重新分析。"),
        
        ("Q7：如何导出历史分析报告？",
         "A：进入案件管理页面，找到对应案件，点击【查看详情】进入报告页面，然后使用导出功能。"),
        
        ("Q8：系统数据安全吗？",
         "A：系统默认使用SQLite本地数据库，所有数据存储在本地。敏感案件建议部署在安全环境中，"
         "可配置PostgreSQL并启用SSL加密。"),
    ]
    
    for q, a in faqs:
        elements.append(Paragraph(f"<b>{q}</b>", styles['Heading3Custom']))
        elements.append(Paragraph(a, styles['BodyTextCustom']))
        elements.append(Spacer(1, 0.3 * cm))
    
    elements.append(PageBreak())
    return elements


def build_chapter10(styles) -> list:
    """第10章 错误码表"""
    elements = []
    
    elements.append(Paragraph("第10章 错误码表", styles['Heading1Custom']))
    
    elements.append(Paragraph(
        "系统在运行过程中可能返回以下错误码，请根据错误码进行相应处理：",
        styles['BodyTextCustom']
    ))
    
    # 错误码表格
    error_data = [
        ["错误码", "错误描述", "处理建议"],
        ["AUTH_001", "用户名或密码错误", "检查输入是否正确，注意大小写"],
        ["AUTH_002", "账户已被禁用", "联系管理员启用账户"],
        ["AUTH_003", "Token已过期", "重新登录获取新Token"],
        ["AUTH_004", "权限不足", "联系管理员提升权限"],
        ["CASE_001", "案件文本过短", "输入至少10个字符的案件文本"],
        ["CASE_002", "案件文本过长", "文本长度不超过50000字符"],
        ["CASE_003", "案件不存在", "检查案件ID是否正确"],
        ["CASE_004", "案件已在分析中", "等待分析完成或取消后重试"],
        ["DOC_001", "文件格式不支持", "仅支持PDF、DOCX、DOC格式"],
        ["DOC_002", "文件大小超限", "文件大小不超过20MB"],
        ["DOC_003", "文件内容为空", "检查文件是否损坏"],
        ["DOC_004", "文本提取失败", "检查PDF是否为扫描件"],
        ["AI_001", "AI服务不可用", "检查Ollama服务是否启动"],
        ["AI_002", "模型加载失败", "检查模型文件是否完整"],
        ["AI_003", "推理超时", "简化案件文本或重试"],
        ["AI_004", "分析结果异常", "检查案件文本质量"],
        ["SYS_001", "系统内部错误", "查看日志定位问题"],
        ["SYS_002", "数据库连接失败", "检查数据库服务状态"],
        ["SYS_003", "缓存服务异常", "检查缓存配置"],
    ]
    
    error_table = Table(error_data, colWidths=[2.5 * cm, 4.5 * cm, 8 * cm])
    error_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fdf2f2')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(error_table)
    
    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph(
        "如遇到上述错误码无法解决的问题，请查看系统日志或联系技术支持。",
        styles['BodyTextCustom']
    ))
    
    return elements


def generate_user_manual():
    """生成用户手册PDF"""
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 注册字体
    font_name = register_fonts()
    
    # 创建样式
    styles = create_styles(font_name)
    
    # 创建文档
    doc = SimpleDocTemplate(
        str(OUTPUT_FILE),
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title="帮信罪主观明知分析系统 - 用户手册",
        author="系统开发团队",
    )
    
    # 构建内容
    elements = []
    
    # 封面
    elements.extend(build_cover_page(styles))
    
    # 目录
    elements.extend(build_toc(styles))
    
    # 各章节
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
    
    # 生成PDF
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    
    print(f"[OK] 用户手册已生成: {OUTPUT_FILE}")
    print(f"  文件大小: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")
    
    return OUTPUT_FILE


if __name__ == "__main__":
    try:
        output_file = generate_user_manual()
        print(f"\n生成成功！输出文件: {output_file}")
    except Exception as e:
        print(f"\n生成失败: {e}", file=sys.stderr)
        sys.exit(1)
