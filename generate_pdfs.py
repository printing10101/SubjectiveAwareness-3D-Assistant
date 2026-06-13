#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成软著申请所需的三个PDF文档
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# 尝试注册中文字体
def register_chinese_font():
    """注册中文字体"""
    font_paths = [
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                return 'ChineseFont'
            except:
                continue
    
    # 如果找不到中文字体，使用默认字体
    return 'Helvetica'

# 注册字体
CHINESE_FONT = register_chinese_font()

def create_software_introduction():
    """创建软件功能简介PDF"""
    doc = SimpleDocTemplate(
        "05_其他说明/软件功能简介.pdf",
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # 自定义样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=1,  # 居中
        fontName=CHINESE_FONT
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName=CHINESE_FONT
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=18,
        fontName=CHINESE_FONT
    )
    
    # 标题
    story.append(Paragraph("帮信罪主观明知智能分析系统", title_style))
    story.append(Paragraph("软件功能简介", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 一、产品定位
    story.append(Paragraph("一、产品定位", heading_style))
    story.append(Paragraph(
        '帮信罪主观明知智能分析系统是专为司法领域设计的AI辅助分析工具，致力于解决帮助信息网络犯罪活动罪案件中"主观明知"要素认定难、标准不统一、效率低下等痛点问题。',
        body_style
    ))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>核心价值主张：</b>", body_style))
    story.append(Paragraph("• 标准化分析框架：将司法实践中的审查逻辑固化为三维度分析模型，确保分析过程可追溯、可复现", body_style))
    story.append(Paragraph("• 自动化审查辅助：AI自动提取案件关键事实、比对行为模式、评估辩解合理性，大幅缩短人工审查时间", body_style))
    story.append(Paragraph("• 智能类案参考：基于知识图谱技术，自动检索相似案例及量刑建议，为检察官提供决策参考", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>差异化优势：</b>", body_style))
    story.append(Paragraph("• 本地化部署：基于Ollama + DeepSeek-R1开源模型，数据不出本机，满足司法数据安全要求", body_style))
    story.append(Paragraph('• 可解释输出：每个维度的评分均附带推理过程和关键依据，非"黑箱"判断', body_style))
    story.append(Paragraph("• RESTful API：前后端完全解耦，提供标准化API接口，易于集成至现有检察业务系统", body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 二、核心功能
    story.append(Paragraph("二、核心功能", heading_style))
    
    # 功能表格
    function_data = [
        ['功能模块', '功能说明'],
        ['三维度智能分析', '基于行为评估、认知匹配、辩解合理性三个维度，对案件"主观明知"要素进行结构化分析'],
        ['可视化分析报告', '自动生成包含评分、推理过程、关键指标的结构化分析报告'],
        ['Demo案例体验', '内置三类典型案例（明显明知/边缘情况/确实不明知），支持一键体验完整分析流程'],
        ['案件管理', '支持案件的创建、查询、更新与删除，提供持久化存储'],
        ['知识图谱检索', '基于Neo4j图数据库，实现相似案例检索与法律知识图谱展示'],
        ['文档解析', '支持PDF/Word案件材料自动解析，提取文本内容进行分析'],
        ['实验对比', '支持不同模型版本的分析结果对比，辅助模型评估与选型']
    ]
    
    function_table = Table(function_data, colWidths=[4*cm, 12*cm])
    function_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 1), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    
    story.append(function_table)
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("<b>使用流程：</b>", body_style))
    story.append(Paragraph("1. 用户登录系统，进入案件分析界面", body_style))
    story.append(Paragraph("2. 输入案件事实文本或上传PDF/Word文档", body_style))
    story.append(Paragraph("3. 系统自动调用AI模型进行三维度分析", body_style))
    story.append(Paragraph("4. 生成结构化分析报告，包含评分、推理过程、关键指标", body_style))
    story.append(Paragraph("5. 用户可查看报告、导出PDF或进行类案检索", body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 三、目标用户
    story.append(Paragraph("三、目标用户", heading_style))
    story.append(Paragraph("<b>主要用户群体：</b>", body_style))
    story.append(Paragraph("• 检察官：负责帮信罪案件审查起诉的司法人员", body_style))
    story.append(Paragraph("• 检察官助理：协助检察官进行案件分析的辅助人员", body_style))
    story.append(Paragraph("• 司法研究人员：研究帮信罪认定标准的学者和实务工作者", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>使用场景：</b>", body_style))
    story.append(Paragraph('• 日常办案：快速分析帮信罪案件，辅助"主观明知"要素认定', body_style))
    story.append(Paragraph("• 案件研讨：为案件讨论会提供AI分析参考意见", body_style))
    story.append(Paragraph("• 培训教学：用于新人培训，展示标准化分析流程", body_style))
    story.append(Paragraph("• 研究分析：批量分析案例，总结认定规律和裁判趋势", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>用户需求：</b>", body_style))
    story.append(Paragraph("• 提高办案效率，减少重复性劳动", body_style))
    story.append(Paragraph("• 统一认定标准，降低主观判断差异", body_style))
    story.append(Paragraph("• 获取类案参考，辅助决策判断", body_style))
    story.append(Paragraph("• 确保数据安全，符合司法保密要求", body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 四、技术亮点
    story.append(Paragraph("四、技术亮点", heading_style))
    
    story.append(Paragraph("<b>1. 两阶段推理管线</b>", body_style))
    story.append(Paragraph("针对法律文本分析的特殊需求，系统实现了分级推理策略：简单案件单次推理，复杂案件两阶段推理（事实提取+维度分析），显著提升分析准确率。", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>2. 三层知识图谱架构</b>", body_style))
    story.append(Paragraph("知识图谱采用分层设计，包含要素图谱层（12个特征节点）、推理图谱层（6条推定规则）、案例图谱层（25个贵州帮信罪案例），对应法律推理的不同抽象层次。", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>3. 智能缓存机制</b>", body_style))
    story.append(Paragraph("基于MD5摘要的文件缓存系统，7天有效期，支持统计追踪和手动清理，避免重复分析相同案件。", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>4. 安全性设计</b>", body_style))
    story.append(Paragraph("JWT双Token认证机制、密码bcrypt哈希存储、管理员/普通用户两级权限、CORS白名单配置、请求日志审计，全方位保障系统安全。", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>5. 技术架构优势</b>", body_style))
    story.append(Paragraph("• 前端：Vue 3 + Vite + Pinia，响应式单页应用", body_style))
    story.append(Paragraph("• 后端：FastAPI + SQLAlchemy + Pydantic，高性能异步框架", body_style))
    story.append(Paragraph("• AI模型：Ollama + DeepSeek-R1，本地部署开源大语言模型", body_style))
    story.append(Paragraph("• 数据库：SQLite/PostgreSQL + Neo4j，关系型+图数据库混合存储", body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 五、性能指标
    story.append(Paragraph("五、性能指标", heading_style))
    
    performance_data = [
        ['指标', '标准值', '说明'],
        ['响应时间', '≤ 1分钟', '从提交案件事实到输出完整分析报告'],
        ['分析准确率', '≥ 70%', '三维度分析结论与专业检察官判断的一致性'],
        ['稳定性', '连续10个测试案例无崩溃', '系统在处理批量案件时不应出现崩溃']
    ]
    
    performance_table = Table(performance_data, colWidths=[4*cm, 4*cm, 8*cm])
    performance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 1), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    
    story.append(performance_table)
    story.append(Spacer(1, 0.5*cm))
    
    # 页脚说明
    story.append(Spacer(1, 1*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=1,
        fontName=CHINESE_FONT
    )
    story.append(Paragraph("本系统仅为辅助分析工具，其输出结果不具有法律效力，不能替代专业法律判断。", footer_style))
    story.append(Paragraph("司法案件的分析与定罪量刑必须由具有法定资质的司法人员依据法定程序独立完成。", footer_style))
    
    # 生成PDF
    doc.build(story)
    print("[OK] 已生成：05_其他说明/软件功能简介.pdf")


def create_environment_spec():
    """创建运行环境说明PDF"""
    doc = SimpleDocTemplate(
        "05_其他说明/运行环境说明.pdf",
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # 自定义样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=1,
        fontName=CHINESE_FONT
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName=CHINESE_FONT
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=18,
        fontName=CHINESE_FONT
    )
    
    # 标题
    story.append(Paragraph("帮信罪主观明知智能分析系统", title_style))
    story.append(Paragraph("运行环境说明", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 一、操作系统兼容性
    story.append(Paragraph("一、操作系统兼容性", heading_style))
    
    os_data = [
        ['操作系统', '支持版本', '备注'],
        ['Windows', 'Windows 10 (64位) / Windows 11', '推荐Windows 11，需启用WSL2（如需GPU加速）'],
        ['macOS', 'macOS 12 (Monterey)及以上', 'Apple Silicon (M1/M2/M3)或Intel芯片均可'],
        ['Linux', 'Ubuntu 20.04+ / CentOS 8+ / Debian 11+', '内核版本 >= 5.4']
    ]
    
    os_table = Table(os_data, colWidths=[3.5*cm, 6*cm, 6.5*cm])
    os_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 1), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    
    story.append(os_table)
    story.append(Spacer(1, 0.5*cm))
    
    # 二、硬件配置要求
    story.append(Paragraph("二、硬件配置要求", heading_style))
    
    story.append(Paragraph("<b>1. 内存（RAM）</b>", body_style))
    memory_data = [
        ['配置级别', '容量', '说明'],
        ['最低配置', '8 GB', '仅运行后端服务，不推荐同时运行AI模型'],
        ['推荐配置', '16 GB及以上', '可同时运行Ollama模型+后端+前端']
    ]
    
    memory_table = Table(memory_data, colWidths=[3.5*cm, 3.5*cm, 9*cm])
    memory_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 1), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    
    story.append(memory_table)
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>2. 硬盘空间</b>", body_style))
    disk_data = [
        ['项目', '占用空间（GB）', '说明'],
        ['Ollama程序', '~0.5 GB', 'Ollama本体'],
        ['AI模型（deepseek-r1:7b）', '~4.5 GB', '模型文件占用'],
        ['Python虚拟环境', '~1 GB', '后端依赖包'],
        ['Node.js依赖', '~0.3 GB', '前端node_modules'],
        ['数据库及日志', '~0.5 GB', 'SQLite数据库+运行日志'],
        ['其他项目文件', '~0.2 GB', '项目代码、配置等'],
        ['总计（推荐预留）', '至少10 GB', '建议预留20 GB以保证运行流畅']
    ]
    
    disk_table = Table(disk_data, colWidths=[5*cm, 3.5*cm, 7.5*cm])
    disk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 1), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    
    story.append(disk_table)
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>3. GPU要求（可选）</b>", body_style))
    gpu_data = [
        ['配置', '说明'],
        ['最低显卡要求', 'NVIDIA GTX 1060 6GB / AMD RX 580 8GB及以上'],
        ['推荐显卡', 'NVIDIA RTX 3060 12GB及以上'],
        ['显存', '最低6GB，推荐8GB及以上'],
        ['无独显', '可使用CPU运行模型，但推理速度会显著降低（建议16GB以上内存）']
    ]
    
    gpu_table = Table(gpu_data, colWidths=[4*cm, 12*cm])
    gpu_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 1), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    
    story.append(gpu_table)
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>4. 其他硬件要求</b>", body_style))
    story.append(Paragraph("• 网络：稳定互联网连接，用于下载依赖包及AI模型（首次安装需要）", body_style))
    story.append(Paragraph("• 端口：确保以下端口可用：11434（Ollama）、8000（后端）、3000（前端）", body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 三、软件依赖项
    story.append(Paragraph("三、软件依赖项", heading_style))
    
    software_data = [
        ['软件', '最低版本', '用途', '下载地址'],
        ['Python', '3.11及以上', '后端运行环境', 'https://www.python.org/downloads/'],
        ['Node.js', '18及以上', '前端构建环境', 'https://nodejs.org/'],
        ['npm', '9及以上', '前端包管理器', '随Node.js自动安装'],
        ['Ollama', '最新版', '本地LLM服务', 'https://ollama.com/'],
        ['Neo4j', '可选', '知识图谱数据库', 'https://neo4j.com/']
    ]
    
    software_table = Table(software_data, colWidths=[2.5*cm, 2.5*cm, 4*cm, 7*cm])
    software_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 1), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    
    story.append(software_table)
    story.append(Spacer(1, 0.5*cm))
    
    # 四、环境配置步骤
    story.append(Paragraph("四、环境配置步骤", heading_style))
    
    story.append(Paragraph("<b>步骤1：安装Ollama及AI模型</b>", body_style))
    story.append(Paragraph("1. 访问Ollama官网下载安装包", body_style))
    story.append(Paragraph("2. 启动Ollama服务：ollama serve", body_style))
    story.append(Paragraph("3. 下载AI模型：ollama pull deepseek-r1:7b", body_style))
    story.append(Paragraph("4. 验证安装：ollama list", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>步骤2：配置后端环境</b>", body_style))
    story.append(Paragraph("1. 进入backend目录：cd backend", body_style))
    story.append(Paragraph("2. 创建虚拟环境：python -m venv venv", body_style))
    story.append(Paragraph("3. 激活虚拟环境：.\\venv\\Scripts\\Activate.ps1", body_style))
    story.append(Paragraph("4. 安装依赖：pip install -r requirements.txt", body_style))
    story.append(Paragraph("5. 配置环境变量：复制.env.example为.env并修改配置", body_style))
    story.append(Paragraph("6. 初始化数据库：alembic upgrade head", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>步骤3：配置前端环境</b>", body_style))
    story.append(Paragraph("1. 进入frontend目录：cd frontend", body_style))
    story.append(Paragraph("2. 安装依赖：npm install", body_style))
    story.append(Paragraph("3. 验证安装：npm run lint", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>步骤4：启动服务</b>", body_style))
    story.append(Paragraph("1. 启动Ollama服务：ollama serve", body_style))
    story.append(Paragraph("2. 启动后端服务：python run.py", body_style))
    story.append(Paragraph("3. 启动前端服务：npm run dev", body_style))
    story.append(Paragraph("4. 访问系统：http://localhost:5173", body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 五、版本兼容性说明
    story.append(Paragraph("五、版本兼容性说明", heading_style))
    
    story.append(Paragraph("<b>Python版本兼容性</b>", body_style))
    story.append(Paragraph("• Python 3.11：推荐版本，完整支持所有特性", body_style))
    story.append(Paragraph("• Python 3.10：可用，但部分新特性可能受限", body_style))
    story.append(Paragraph("• Python 3.9及以下：不推荐使用", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>Node.js版本兼容性</b>", body_style))
    story.append(Paragraph("• Node.js 18.x：推荐版本，LTS长期支持", body_style))
    story.append(Paragraph("• Node.js 20.x：可用，最新LTS版本", body_style))
    story.append(Paragraph("• Node.js 16.x及以下：不推荐使用", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>Ollama版本兼容性</b>", body_style))
    story.append(Paragraph("• 建议使用最新版本的Ollama，以获得最佳性能和兼容性", body_style))
    story.append(Paragraph("• 定期更新Ollama可以获取新功能和bug修复", body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 六、常见问题解决方案
    story.append(Paragraph("六、常见问题解决方案", heading_style))
    
    story.append(Paragraph("<b>问题1：端口被占用</b>", body_style))
    story.append(Paragraph("解决方案：修改.env文件中的端口配置，或停止占用端口的进程", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>问题2：依赖安装失败</b>", body_style))
    story.append(Paragraph("解决方案：升级pip到最新版本，使用--no-cache-dir参数重新安装", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>问题3：模型下载失败</b>", body_style))
    story.append(Paragraph("解决方案：检查网络连接，配置代理后重试，或手动下载模型文件", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>问题4：服务启动失败</b>", body_style))
    story.append(Paragraph("解决方案：检查日志文件（backend/logs/app_YYYY-MM-DD.log），排查错误原因", body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph("<b>问题5：GPU加速未生效</b>", body_style))
    story.append(Paragraph("解决方案：检查NVIDIA驱动是否安装，设置OLLAMA_NUM_GPU_LAYERS环境变量", body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 页脚说明
    story.append(Spacer(1, 1*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=1,
        fontName=CHINESE_FONT
    )
    story.append(Paragraph("如有其他问题，请查看项目文档或联系技术支持。", footer_style))
    
    # 生成PDF
    doc.build(story)
    print("[OK] 已生成：05_其他说明/运行环境说明.pdf")


def create_material_checklist():
    """创建软著申请材料清单PDF"""
    doc = SimpleDocTemplate(
        "05_其他说明/软著申请材料清单.pdf",
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # 自定义样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=1,
        fontName=CHINESE_FONT
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName=CHINESE_FONT
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=16,
        fontName=CHINESE_FONT
    )
    
    # 标题
    story.append(Paragraph("帮信罪主观明知智能分析系统V1.0", title_style))
    story.append(Paragraph("软著申请材料清单", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 说明文字
    story.append(Paragraph(
        "本清单列出了申请计算机软件著作权登记所需的全部材料，请按照清单准备并提交相关文件。",
        body_style
    ))
    story.append(Spacer(1, 0.5*cm))
    
    # 材料清单表格
    checklist_data = [
        ['序号', '文件名称', '文件类型', '版本号', '存储路径', '用途说明'],
        ['1', '软件著作权申请表', 'DOCX', 'V1.0', '01_软件著作权申请表/', '软著申请的核心表格，包含软件基本信息、著作权人信息、权利范围等'],
        ['2', '软件说明书（用户手册）', 'PDF', 'V1.0', '03_软件文档/', '详细描述软件的功能、使用方法、操作流程，面向最终用户'],
        ['3', '软件设计说明书', 'PDF', 'V1.0', '03_软件文档/', '详细描述软件的架构设计、模块划分、技术实现、数据库设计等'],
        ['4', '源代码（前30页）', 'PDF', 'V1.0', '02_源代码/', '软件源代码的前30页，每页不少于50行，用于证明软件的原创性'],
        ['5', '源代码（后30页）', 'PDF', 'V1.0', '02_源代码/', '软件源代码的后30页，每页不少于50行，用于证明软件的原创性'],
        ['6', '源代码（完整）', 'ZIP', 'V1.0', '02_源代码/', '软件的完整源代码压缩包，包含所有源文件'],
        ['7', '原创性声明', 'PDF', 'V1.0', '04_证明材料/', '声明软件为独立开发，未侵犯他人著作权的书面承诺'],
        ['8', '权利归属声明', 'PDF', 'V1.0', '04_证明材料/', '声明软件著作权归属的书面文件，明确著作权人'],
        ['9', '软件功能简介', 'PDF', 'V1.0', '05_其他说明/', '简要介绍软件的功能特点、技术亮点、应用场景等'],
        ['10', '运行环境说明', 'PDF', 'V1.0', '05_其他说明/', '详细说明软件运行所需的硬件、软件环境配置要求'],
        ['11', '软件界面截图', 'PNG/JPG', 'V1.0', '06_界面截图/', '软件主要功能界面的截图，展示软件的交互设计'],
        ['12', '测试报告', 'PDF', 'V1.0', '07_测试文档/', '软件的功能测试、性能测试报告，证明软件的稳定性和可靠性'],
        ['13', '著作权人身份证明', 'PDF', '-', '08_身份证明/', '著作权人的身份证复印件或营业执照复印件'],
        ['14', '代理人委托书（如适用）', 'PDF', '-', '09_委托文件/', '如委托代理机构申请，需提供授权委托书']
    ]
    
    checklist_table = Table(checklist_data, colWidths=[1*cm, 4*cm, 1.5*cm, 1.5*cm, 3.5*cm, 5*cm])
    checklist_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 1), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        # 交替行背景色
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ecf0f1'), colors.white]),
    ]))
    
    story.append(checklist_table)
    story.append(Spacer(1, 0.5*cm))
    
    # 补充说明
    story.append(Paragraph("补充说明：", heading_style))
    story.append(Paragraph("1. 所有PDF文档需使用标准A4纸张，页边距适中，排版清晰", body_style))
    story.append(Paragraph("2. 源代码需使用等宽字体（如Courier New），确保代码可读性", body_style))
    story.append(Paragraph("3. 软件说明书和设计说明书需包含目录、章节编号、图表编号", body_style))
    story.append(Paragraph("4. 界面截图需清晰可见，能够展示软件的主要功能模块", body_style))
    story.append(Paragraph("5. 所有文档需保持一致的版本号和日期", body_style))
    story.append(Paragraph("6. 著作权人身份证明需在有效期内", body_style))
    story.append(Paragraph("7. 如委托代理机构，需提供正式的授权委托书", body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 提交流程
    story.append(Paragraph("提交流程：", heading_style))
    story.append(Paragraph("1. 准备材料：按照本清单准备所有必需文件", body_style))
    story.append(Paragraph("2. 在线填报：登录中国版权保护中心网站，填写软著申请表", body_style))
    story.append(Paragraph("3. 打印签章：打印申请表，著作权人签字或盖章", body_style))
    story.append(Paragraph("4. 提交材料：将所有材料装订成册，提交至版权保护中心或代理机构", body_style))
    story.append(Paragraph("5. 缴纳费用：按照规定缴纳登记费用", body_style))
    story.append(Paragraph("6. 等待审核：版权保护中心进行形式审查和实质审查", body_style))
    story.append(Paragraph("7. 领取证书：审核通过后，领取计算机软件著作权登记证书", body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 注意事项
    story.append(Paragraph("注意事项：", heading_style))
    story.append(Paragraph("• 软件名称需与申请表中的名称完全一致", body_style))
    story.append(Paragraph("• 版本号需统一，建议采用V1.0格式", body_style))
    story.append(Paragraph("• 源代码中不得包含敏感信息（如密码、密钥等）", body_style))
    story.append(Paragraph("• 软件说明书需与实际软件功能一致", body_style))
    story.append(Paragraph("• 所有材料需真实、准确、完整", body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 页脚说明
    story.append(Spacer(1, 1*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=1,
        fontName=CHINESE_FONT
    )
    story.append(Paragraph("本清单仅供参考，具体要求以中国版权保护中心最新规定为准。", footer_style))
    story.append(Paragraph("如有疑问，请咨询版权保护中心或专业代理机构。", footer_style))
    
    # 生成PDF
    doc.build(story)
    print("[OK] 已生成：05_其他说明/软著申请材料清单.pdf")


if __name__ == "__main__":
    print("开始生成PDF文档...")
    print("-" * 50)
    
    try:
        create_software_introduction()
        create_environment_spec()
        create_material_checklist()
        
        print("-" * 50)
        print("[OK] 所有PDF文档生成成功！")
        print("\n生成的文件：")
        print("  1. 05_其他说明/软件功能简介.pdf")
        print("  2. 05_其他说明/运行环境说明.pdf")
        print("  3. 05_其他说明/软著申请材料清单.pdf")
    except Exception as e:
        print(f"✗ 生成PDF文档时出错：{e}")
        import traceback
        traceback.print_exc()
