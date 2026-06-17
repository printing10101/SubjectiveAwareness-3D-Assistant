"""法律知识体系初始化脚本.

系统性地导入和结构化基础法律知识体系，支持全量初始化和增量更新两种模式。
可重复执行，多次运行不会产生数据重复或冲突。

运行方式:
    python scripts/init_legal_knowledge.py                     # 全量初始化
    python scripts/init_legal_knowledge.py --mode incremental   # 增量更新
    python scripts/init_legal_knowledge.py --dry-run            # 预览模式
    python scripts/init_legal_knowledge.py --log-level DEBUG    # 调试模式
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_BACKEND_DIR = str(Path(__file__).resolve().parent.parent / "backend")
sys.path.insert(0, _BACKEND_DIR)

_old_cwd = os.getcwd()
os.chdir(_BACKEND_DIR)

from loguru import logger  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.config import AnalysisConfig, settings  # noqa: E402
from app.database import AsyncSessionLocal, async_engine  # noqa: E402
from app.models.knowledge_entry import (  # noqa: E402
    EntryCategory, EntryStatus, KnowledgeEntry, SourceType,
)
from app.models.knowledge_tag import KnowledgeTag  # noqa: E402
from app.models.entry_tag import EntryTag  # noqa: E402
from app.models.entry_relation import EntryRelation, RelationType  # noqa: E402
from app.services.ollama_client import get_client  # noqa: E402
from app.utils.logger import setup_logging  # noqa: E402


_LLM_RETRY_MAX_ATTEMPTS: int = 2
_LLM_RETRY_DELAY_BASE: float = 1.0
_CONTENT_PREVIEW_CHARS: int = 8000
_SYSTEM_USER_ID: int = 1
_DEFAULT_TAG_COLOR: str = "#3B82F6"


@dataclass
class InitRecord:
    """单条初始化记录."""
    item_id: str
    title: str
    status: str
    entry_id: int | None = None
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class InitReport:
    """初始化报告."""
    mode: str = "full"
    dry_run: bool = False
    total: int = 0
    created_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    tag_count: int = 0
    relation_count: int = 0
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    records: list[InitRecord] = field(default_factory=list)

    def generate_text_report(self) -> str:
        lines: list[str] = [
            "=" * 70,
            "          法律知识体系初始化报告",
            "=" * 70,
            f"  运行模式: {'预览模式 (DRY-RUN)' if self.dry_run else '正式执行'}",
            f"  初始化模式: {'全量初始化' if self.mode == 'full' else '增量更新'}",
            f"  开始时间: {self.start_time}",
            f"  结束时间: {self.end_time}",
            f"  总耗时: {self.duration_seconds:.2f} 秒",
            "",
            "-" * 70,
            "  总体统计",
            "-" * 70,
            f"  总条目数: {self.total}",
            f"  [成功] 新增: {self.created_count}",
            f"  [跳过] 已存在: {self.skipped_count}",
            f"  [失败] 失败: {self.failed_count}",
            f"  标签总数: {self.tag_count}",
            f"  关联关系: {self.relation_count}",
            f"  成功率: "
            f"{self.created_count / max(self.total, 1) * 100:.1f}%",
            "",
        ]

        if self.failed_count > 0:
            lines.extend(["-" * 70, "  失败详情", "-" * 70])
            for r in self.records:
                if r.status == "failed":
                    lines.append(f"  [{r.item_id}] {r.title}")
                    lines.append(f"     原因: {r.error}")
                    lines.append("")

        lines.extend(["-" * 70, "  详细初始化日志", "-" * 70])
        for r in self.records:
            icon = (
                "[OK]" if r.status == "created"
                else ("[SKIP]" if r.status == "skipped" else "[FAIL]")
            )
            entry_info = f", 条目ID: {r.entry_id}" if r.entry_id else ""
            lines.append(f"  {icon} [{r.item_id}]{entry_info}")
            lines.append(f"     标题: {r.title}")
            lines.append(f"     耗时: {r.duration_seconds:.2f}s")
            if r.error:
                lines.append(f"     状态: {r.status}, 错误: {r.error}")
            lines.append("")

        lines.append("=" * 70)
        lines.append("报告结束")
        lines.append("=" * 70)
        return "\n".join(lines)

    def generate_json_report(self) -> dict[str, Any]:
        return {
            "report_metadata": {
                "mode": self.mode,
                "dry_run": self.dry_run,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": round(self.duration_seconds, 2),
            },
            "statistics": {
                "total": self.total,
                "created": self.created_count,
                "skipped": self.skipped_count,
                "failed": self.failed_count,
                "tags": self.tag_count,
                "relations": self.relation_count,
                "success_rate": round(
                    self.created_count / max(self.total, 1) * 100, 1
                ),
            },
            "records": [
                {
                    "item_id": r.item_id,
                    "title": r.title,
                    "status": r.status,
                    "entry_id": r.entry_id,
                    "error": r.error,
                    "duration_seconds": round(r.duration_seconds, 2),
                }
                for r in self.records
            ],
        }


_METADATA_EXTRACTION_PROMPT: str = """请从以下法律文本中提取结构化元数据，以JSON格式返回。
必须包含以下字段：
- title: 简洁准确的标题（不超过50字，反映法律知识核心内容）
- summary: 内容摘要（100-300字之间，准确概括法律要点）
- suggested_tags: 建议标签列表（3-5个法律专业标签）
- suggested_category: 建议分类，必须是以下之一：
  law（法律法规）、methodology（方法论）、case（案例）、other（其他）

质量要求：
- summary 必须控制在100-300字之间
- suggested_tags 必须包含3-5个法律专业标签

只返回JSON，不要包含任何其他文字：

文本内容：
{text}"""


_LLM_EXTRACTION_SYSTEM_PROMPT: str = "你是一个专业的法律知识管理助手，擅长从法律文本中提取结构化元数据。"

# ============================================================================
# 内置法律知识数据
# ============================================================================

_STANDARD_TAGS: list[dict[str, str]] = [
    {"name": "帮信罪", "description": "帮助信息网络犯罪活动罪相关法律知识", "color": "#EF4444"},
    {"name": "主观明知", "description": "帮信罪主观构成要件中'明知'的认定标准", "color": "#F59E0B"},
    {"name": "量刑建议", "description": "帮信罪量刑标准、量刑情节及建议", "color": "#10B981"},
    {"name": "证据审查", "description": "帮信罪证据收集、审查和认定规则", "color": "#3B82F6"},
    {"name": "犯罪模式", "description": "帮信罪常见犯罪模式和行为特征", "color": "#8B5CF6"},
]

_TAG_RELATIONS: list[tuple[str, str, RelationType]] = [
    ("帮信罪", "主观明知", RelationType.references),
    ("帮信罪", "量刑建议", RelationType.references),
    ("帮信罪", "证据审查", RelationType.references),
    ("帮信罪", "犯罪模式", RelationType.references),
    ("犯罪模式", "主观明知", RelationType.references),
    ("犯罪模式", "证据审查", RelationType.references),
]


_EXTRA_STANDARD_TAGS: list[dict[str, str]] = [
    {
        "name": "司法解释",
        "description": "最高人民法院、最高人民检察院发布的司法解释文件",
        "color": "#EC4899",
    },
    {"name": "立案标准", "description": "帮信罪立案追诉标准和数额门槛", "color": "#14B8A6"},
    {"name": "分析框架", "description": "帮信罪三维度分析模型和评估方法", "color": "#6366F1"},
    {"name": "收购银行卡", "description": "收购、出租、出售银行卡的犯罪行为模式", "color": "#F97316"},
    {"name": "代购争议", "description": "代购行为与帮信罪的法律边界和争议焦点", "color": "#84CC16"},
    {"name": "技术支持", "description": "技术开发、运维支持相关帮信罪行为类型", "color": "#06B6D4"},
]


def _build_legal_knowledge_entries() -> list[dict[str, Any]]:
    """构建内置法律知识条目数据."""
    return [
        {
            "item_id": "criminal_law_287_2",
            "title": "《刑法》第287条之二（帮信罪）全文及官方释义",
            "category": "law",
            "tags": ["帮信罪", "司法解释"],
            "summary": (
                "《中华人民共和国刑法》第二百八十七条之二规定的"
                "帮助信息网络犯罪活动罪的完整法条内容、"
                "构成要件分析及最高法、最高检官方释义。"
            ),
            "content": _BUILTIN_CRIMINAL_LAW_287_2,
        },
        {
            "item_id": "judicial_interpretation",
            "title": "帮信罪相关司法解释文件汇编",
            "category": "law",
            "tags": ["帮信罪", "司法解释", "证据审查"],
            "summary": (
                "最高人民法院、最高人民检察院关于办理"
                "帮助信息网络犯罪活动罪相关司法解释的完整汇编，"
                "包括发布机关、文号、生效日期及核心条款。"
            ),
            "content": _BUILTIN_JUDICIAL_INTERPRETATION,
        },
        {
            "item_id": "filing_standard",
            "title": "帮信罪最新立案追诉标准",
            "category": "law",
            "tags": ["帮信罪", "立案标准", "量刑建议"],
            "summary": (
                "帮信罪立案追诉的数额标准、情节严重认定情形"
                "及证据要求的完整整理，包括支付结算金额、"
                "违法所得数额、关联犯罪后果等量化标准。"
            ),
            "content": _BUILTIN_FILING_STANDARD,
        },
        {
            "item_id": "three_dimension_analysis",
            "title": "帮信罪三维度分析模型",
            "category": "methodology",
            "tags": ["帮信罪", "分析框架", "主观明知"],
            "summary": (
                "帮信罪三维度分析模型的完整说明文档，"
                "包括主观明知维度、客观行为维度、"
                "危害后果维度的定义、分析流程和综合评判方法。"
            ),
            "content": _BUILTIN_THREE_DIMENSION_ANALYSIS,
        },
        {
            "item_id": "scoring_standard",
            "title": "各维度量化评分标准",
            "category": "methodology",
            "tags": ["帮信罪", "分析框架", "量刑建议"],
            "summary": (
                "帮信罪三维度分析框架中各维度的量化评分标准，"
                "包括评分规则、分值范围、评判依据"
                "和综合评分计算方法，确保评分可执行、可解释。"
            ),
            "content": _BUILTIN_SCORING_STANDARD,
        },
        {
            "item_id": "prompt_templates",
            "title": "帮信罪分析Prompt模板库",
            "category": "methodology",
            "tags": ["帮信罪", "分析框架"],
            "summary": "用于帮信罪案件分析的LLM Prompt模板集合，包括模板用途说明、变量定义、使用示例及输出格式要求。",
            "content": _BUILTIN_PROMPT_TEMPLATES,
        },
        {
            "item_id": "crime_pattern_card",
            "title": "收购银行卡犯罪模式详解",
            "category": "case",
            "tags": ["帮信罪", "犯罪模式", "收购银行卡", "证据审查"],
            "summary": "收购、出租、出售银行卡类型的帮信罪行为特征、常见作案手段、证据要点及司法认定标准的详细分析。",
            "content": _BUILTIN_CRIME_PATTERN_CARD,
        },
        {
            "item_id": "crime_pattern_purchase",
            "title": "代购争议犯罪模式分析",
            "category": "case",
            "tags": ["帮信罪", "犯罪模式", "代购争议"],
            "summary": "以代购为名实施帮信罪的法律边界分析，包括代购行为的合法与非法界限、争议焦点、司法认定标准及典型案例分析。",
            "content": _BUILTIN_CRIME_PATTERN_PURCHASE,
        },
        {
            "item_id": "crime_pattern_tech",
            "title": "技术支持犯罪模式梳理",
            "category": "case",
            "tags": ["帮信罪", "犯罪模式", "技术支持"],
            "summary": (
                "技术开发、运维支持、软件服务等技术支持型帮信罪"
                "的行为类型梳理，包括主观明知认定规则、"
                "情节严重情形判定及典型案例。"
            ),
            "content": _BUILTIN_CRIME_PATTERN_TECH,
        },
    ]


# ============================================================================
# 内置法律知识内容
# ============================================================================

_BUILTIN_CRIMINAL_LAW_287_2: str = """# 《中华人民共和国刑法》第二百八十七条之二

## 法条原文

第二百八十七条之二 明知他人利用信息网络实施犯罪，为其犯罪提供互联网接入、服务器托管、网络存储、
通讯传输等技术支持，或者提供广告推广、支付结算等帮助，情节严重的，处三年以下有期徒刑或者拘役，
并处或者单处罚金。

单位犯前款罪的，对单位判处罚金，并对其直接负责的主管人员和其他直接责任人员，依照第一款的规定处罚。

有前两款行为，同时构成其他犯罪的，依照处罚较重的规定定罪处罚。

## 构成要件

### 犯罪主体
本罪的主体为一般主体，即年满十六周岁、具有刑事责任能力的自然人和单位。

### 主观方面
本罪在主观方面表现为故意，即明知他人利用信息网络实施犯罪，仍为其提供技术支持或帮助。关于"明知"的认定，包括"确知"和"应知"两种情形：
- 确知：有直接证据证明行为人明确知道他人利用信息网络实施犯罪
- 应知：根据行为人的认知能力、从业经历、交易对象、获利情况等综合判断，应当知道他人利用信息网络实施犯罪

### 客观方面
本罪在客观方面表现为为他人利用信息网络实施犯罪提供下列帮助行为之一：
1. 技术支持类：互联网接入、服务器托管、网络存储、通讯传输等
2. 广告推广类：为犯罪活动提供广告宣传、推广服务
3. 支付结算类：提供资金支付、结算账户、转账等帮助

### 犯罪客体
本罪侵犯的客体是国家对信息网络的管理秩序。

## 官方释义要点

根据最高人民法院、最高人民检察院《关于办理非法利用信息网络、帮助信息网络犯罪活动等刑事案件适用法律若干问题的解释》：

1. 本罪中的"犯罪"是指刑法分则规定的具体犯罪，包括但不限于电信网络诈骗、开设赌场、非法经营、传播淫秽物品等利用信息网络实施的犯罪。

2. "明知"的认定应当综合考量以下因素：
   - 行为人的认知能力和从业经历
   - 提供服务的技术类型和正常用途
   - 交易价格是否明显偏离市场正常水平
   - 服务提供方式是否异常
   - 是否存在逃避监管或调查的行为
   - 是否曾因类似行为受过行政处罚或刑事处罚

3. "情节严重"的认定标准包括：
   - 为三个以上对象提供帮助
   - 支付结算金额二十万元以上
   - 以投放广告等方式提供资金五万元以上
   - 违法所得一万元以上
   - 二年内曾因非法利用信息网络、帮助信息网络犯罪活动、危害计算机信息系统安全受过行政处罚，又帮助信息网络犯罪活动
   - 被帮助对象实施的犯罪造成严重后果
"""

_BUILTIN_JUDICIAL_INTERPRETATION: str = """# 帮信罪相关司法解释文件汇编

## 一、核心司法解释

### 1. 《关于办理非法利用信息网络、帮助信息网络犯罪活动等刑事案件适用法律若干问题的解释》
- **发布机关**：最高人民法院、最高人民检察院
- **文号**：法释〔2019〕15号
- **发布日期**：2019年10月21日
- **生效日期**：2019年11月1日
- **核心内容**：
  - 明确了《刑法》第287条之二中"明知"的认定标准
  - 细化了"情节严重"的具体情形
  - 规定了单位犯罪的处罚标准
  - 明确了与其他犯罪的竞合处理规则

### 2. 《关于办理电信网络诈骗等刑事案件适用法律若干问题的意见》
- **发布机关**：最高人民法院、最高人民检察院、公安部
- **文号**：法发〔2016〕32号
- **发布日期**：2016年12月19日
- **生效日期**：2016年12月19日
- **核心内容**：
  - 规定了电信网络诈骗犯罪中帮助行为的认定
  - 明确了上下游犯罪的衔接处理

### 3. 《关于办理电信网络诈骗等刑事案件适用法律若干问题的意见（二）》
- **发布机关**：最高人民法院、最高人民检察院、公安部
- **文号**：法发〔2021〕22号
- **发布日期**：2021年6月17日
- **生效日期**：2021年6月17日
- **核心内容**：
  - 进一步明确了涉"两卡"犯罪的认定标准
  - 细化了收购、出售、出租信用卡、手机卡等行为的刑事责任

## 二、重要规范性文件

### 4. 《关于深入推进"断卡"行动有关问题的会议纪要》
- **发布机关**：最高人民法院、最高人民检察院、公安部
- **发布日期**：2020年12月
- **核心内容**：
  - 明确了"两卡"犯罪的证据标准
  - 规定了主观明知认定的参考因素

### 5. 最高人民法院刑事审判庭《关于帮助信息网络犯罪活动罪司法实务问题的解答》
- **发布机关**：最高人民法院刑事审判庭
- **发布日期**：2022年
- **核心内容**：
  - 对帮信罪适用中的疑难问题进行了系统性解答
  - 明确了"明知"的推定规则和反证规则
"""

_BUILTIN_FILING_STANDARD: str = """# 帮信罪最新立案追诉标准

## 一、数额标准

根据《最高人民法院、最高人民检察院关于办理非法利用信息网络、帮助信息网络犯罪活动等刑事案件适用法律若干问题的解释》（法释〔2019〕15号）第十二条：

### （一）支付结算金额标准
- **基本标准**：支付结算金额达到 **20万元** 以上
- **特殊情形**：虽然未达到20万元，但具有其他严重情节的，仍可认定

### （二）违法所得标准
- **基本标准**：违法所得达到 **1万元** 以上
- 包括通过提供帮助行为获取的所有非法收益

### （三）投放广告资金标准
- **基本标准**：以投放广告等方式提供资金达到 **5万元** 以上

## 二、情节严重认定情形

具有下列情形之一的，应当认定为《刑法》第二百八十七条之二规定的"情节严重"：

1. **对象数量标准**：为三个以上对象提供帮助的
2. **支付结算标准**：支付结算金额二十万元以上的
3. **广告资金标准**：以投放广告等方式提供资金五万元以上的
4. **违法所得标准**：违法所得一万元以上的
5. **行政处罚前置标准**：二年内曾因非法利用信息网络、帮助信息网络犯罪活动、危害计算机信息系统安全受过行政处罚，又帮助信息网络犯罪活动的
6. **后果严重标准**：被帮助对象实施的犯罪造成严重后果的
7. **数量+金额综合标准**：虽未达到上述数额标准，但数量或数额接近上述标准且具有其他严重情节的

## 三、特别认定规则

### （一）涉"两卡"犯罪立案标准
根据法发〔2021〕22号意见：
- **银行卡（包括对公账户、结算卡、非银行支付账户）**：
  - 出租、出售、收购信用卡5张以上
  - 出租、出售、收购银行对公账户3个以上
  - 出租、出售、收购非银行支付账户10个以上

- **手机卡（包括虚拟运营商、物联网卡）**：
  - 出租、出售、收购手机卡20张以上


- **综合标准**：同时涉及银行卡和手机卡，按照相应比例折算

### （二）为上游犯罪提供帮助的认定
- 被帮助对象实施的犯罪行为可以确认，但尚未到案、尚未依法裁判或者因未达到刑事责任年龄等原因依法未予追究刑事责任的，不影响帮信罪的认定
- 实施帮信行为，同时构成其他犯罪的，依照处罚较重的规定定罪处罚

## 四、证据要求

### （一）主观明知证据
- 行为人供述和辩解
- 交易记录、聊天记录、通讯记录
- 行为人的认知能力、从业经历等背景证据
- 交易价格明显偏离市场合理水平的证据
- 异常服务方式的证据（如使用加密通信、频繁更换账户等）
- 是否曾因类似行为受过行政处罚或刑事处罚的记录

### （二）客观行为证据
- 技术服务合同、服务器租用记录、网络托管协议
- 广告推广合同、推广记录、推广费用支付凭证
- 支付结算记录、银行流水、第三方支付平台交易记录
- 涉案账户的开户信息、交易明细、资金流向图

### （三）危害后果证据
- 被帮助对象实施犯罪的证据
- 被害人陈述、报案记录
- 涉案金额的审计报告或专项鉴定意见
- 电子数据提取、固定、检验报告
"""

_BUILTIN_THREE_DIMENSION_ANALYSIS: str = """# 帮信罪三维度分析模型

## 一、模型概述

三维度分析模型是对帮信罪案件进行系统性分析的方法论工具，从主观明知、客观行为、危害后果三个核心维度对案件进行全面评估，帮助法律从业者准确判断罪与非罪、此罪与彼罪的界限。

## 二、维度定义

### 维度一：主观明知（Subjective Knowledge）
**定义**：评估行为人在实施帮助行为时，对他人利用信息网络实施犯罪的认知程度和主观心态。

**分析要点**：
1. 明知的程度：确定明知 → 概括明知 → 推定明知 → 应当知道
2. 明知的来源：直接证据证明 → 间接证据推断 → 综合情状推定
3. 明知的时点：行为前明知 → 行为中明知 → 事后明知
4. 反证因素：是否存在被欺骗、被胁迫等阻却事由

### 维度二：客观行为（Objective Conduct）
**定义**：评估行为人实施的具体帮助行为的性质、方式、规模及在社会生活中的通常用途。

**分析要点**：
1. 行为类型：技术支持类、广告推广类、支付结算类
2. 行为方式：主动提供型、被动配合型、默许放任型
3. 行为规模：涉及对象数量、交易金额、持续时间
4. 行为异常性：是否符合行业惯例、是否偏离正常商业逻辑
5. 行为必要性：是否为正常经营活动所必需

### 维度三：危害后果（Harmful Consequences）
**定义**：评估帮助行为对法益造成的实际侵害或现实威胁的程度。

**分析要点**：
1. 直接后果：帮助行为与上游犯罪结果之间的因果关系
2. 间接后果：上游犯罪造成的实际损失和社会影响
3. 可归责性：危害后果在多大程度上可归因于帮助行为
4. 预防与补救：是否存在有效的风险防控措施和补救行为

## 三、分析流程

### Step 1：事实梳理
- 全面收集案件事实信息
- 整理行为人的供述、证人证言、书证、电子数据等
- 形成完整的时间线和行为链条

### Step 2：维度分析
- 对主观明知维度进行独立评估
- 对客观行为维度进行独立评估
- 对危害后果维度进行独立评估

### Step 3：综合评判
- 将三个维度的分析结果进行综合
- 考虑各维度的关联性和相互印证关系
- 得出初步分析结论

### Step 4：验证与调整
- 检验分析结论是否与案件整体事实一致
- 考虑反证因素和辩解理由
- 必要时调整各维度评分

## 四、适用场景

1. **立案审查**：判断案件是否符合帮信罪的立案标准
2. **审查批捕**：评估是否有逮捕必要
3. **审查起诉**：判断是否符合起诉条件
4. **审判参考**：为定罪量刑提供分析支持
5. **二审复查**：验证原审判决的准确性
"""

_BUILTIN_SCORING_STANDARD: str = """# 各维度量化评分标准

## 评分规则总览

每个维度的评分为 1-10 分制，分值含义：
- 1-3分：程度低（有利于被告人）
- 4-6分：程度中等（中性）
- 7-10分：程度高（不利于被告人）

综合评分 = 主观明知分值 × 0.4 + 客观行为分值 × 0.3 + 危害后果分值 × 0.3

## 维度一：主观明知评分标准

### 1-3分（明知程度低）
- 有证据证明行为人被欺骗、被蒙蔽
- 行为人尽到了合理的注意义务和审查义务
- 行为人按要求进行了实名认证、留存了服务记录
- 交易价格符合市场正常水平
- 行为人主动咨询、核实过对方身份和用途

### 4-6分（明知程度中等）
- 行为人应当知道但无法确知对方利用信息网络实施犯罪
- 行为人未尽到合理的注意义务
- 交易价格略高于市场正常水平
- 行为人未对异常情况进行核实

### 7-10分（明知程度高）
- 行为人明确知道或应当知道对方利用信息网络实施犯罪
- 交易价格明显偏离市场正常水平（如远高于正常服务费）
- 行为人使用异常方式提供服务（如加密通信、隐藏身份、频繁更换账户）
- 行为人曾因类似行为受过行政处罚或刑事处罚
- 行为人采取了明显的规避监管措施

## 维度二：客观行为评分标准

### 1-3分（行为危害性低）
- 提供的是正常的技术服务，属于行业惯例
- 服务行为本身具有合法用途
- 行为规模较小，涉及对象较少
- 行为持续时间短
- 行为人主动设置了风险防控措施

### 4-6分（行为危害性中等）
- 提供的服务具有一定特殊性，易被用于犯罪
- 行为规模中等，涉及一定数量的对象
- 行为持续一段时间
- 部分行为不符合行业惯例

### 7-10分（行为危害性高）
- 提供的服务明显异常，缺乏合法用途
- 行为规模大，涉及大量对象
- 行为持续时间长
- 行为明显违反行业规范和法律法规
- 行为人专门为犯罪活动定制技术方案

## 维度三：危害后果评分标准

### 1-3分（后果轻微）
- 被帮助对象未实际实施犯罪或犯罪未遂
- 未造成实际经济损失或损失已全部追回
- 社会影响小，未引发群体性事件或其他严重后果

### 4-6分（后果中等）
- 被帮助对象实施了犯罪但后果不严重
- 造成了一定经济损失（如1万-10万元）
- 有一定社会影响但可控

### 7-10分（后果严重）
- 被帮助对象实施了严重犯罪
- 造成重大经济损失（10万元以上）
- 造成严重后果或恶劣社会影响
- 涉及被害人众多，引发群体性事件
- 严重干扰了信息网络管理秩序

## 评分解读

| 综合评分范围 | 评估结论 | 建议处理方式 |
|------------|---------|------------|
| 1-3分 | 不构成犯罪或情节显著轻微 | 不起诉/无罪/免予刑事处罚 |
| 4-5分 | 构成犯罪但情节较轻 | 可考虑不起诉或判处缓刑 |
| 6-7分 | 构成犯罪，情节一般 | 建议起诉，判处轻刑 |
| 8-10分 | 构成犯罪，情节严重 | 依法追究刑事责任 |
"""

_BUILTIN_PROMPT_TEMPLATES: str = """# 帮信罪分析Prompt模板库

## 模板一：案件事实分析

**用途**：对帮信罪案件事实进行全面分析和结构化提取。

**变量说明**：
- `{case_text}`：案件事实描述文本
- `{analysis_scope}`：分析范围指定（可选：全面分析 / 仅主观明知 / 仅客观行为 / 仅危害后果）

**模板内容**：
```
你是一名资深的刑事法律专家，请对以下帮信罪案件事实进行全面分析。

案件事实：
{case_text}

分析范围：{analysis_scope}

请从以下方面进行分析：
1. 行为人提供了何种类型的帮助（技术支持/广告推广/支付结算）
2. 行为人的主观明知程度（确定明知/概括明知/推定明知/应当知道）
3. 帮助行为的规模和持续时间
4. 上游犯罪的性质和危害后果
5. 案件中的关键证据和待证事实

请以结构化格式输出分析结果。
```

---

## 模板二：主观明知论证

**用途**：专门用于分析和论证帮信罪案件中的主观明知要件。

**变量说明**：
- `{case_text}`：案件事实描述文本
- `{defense_position}`：辩护立场（支持认定明知 / 反对认定明知）

**模板内容**：
```
你是一名刑事法律专家，请对以下案件中行为人的主观明知进行专业分析。

案件事实：
{case_text}

辩护立场：{defense_position}

请从以下维度进行分析：
1. 行为人的认知能力和从业经历
2. 行为人的从业经历和教育背景
3. 交易价格是否偏离市场正常水平
4. 服务方式是否存在异常
5. 是否存在逃避监管行为
6. 是否曾因类似行为受过处罚
7. 反证因素（如被欺骗、被胁迫等）

请以结构化格式输出分析结论，并附上论证理由。
```

---

## 模板三：量刑建议生成

**用途**：根据案件事实和分析结果生成量刑建议。

**变量说明**：
- `{case_facts}`：案件核心事实
- `{aggravating_factors}`：从重处罚情节
- `{mitigating_factors}`：从轻处罚情节

**模板内容**：
```
你是一名刑事法律专家，请根据以下信息生成帮信罪的量刑建议。

案件核心事实：
{case_facts}

从重处罚情节：
{aggravating_factors}

从轻处罚情节：
{mitigating_factors}

请考虑以下因素：
1. 支付结算金额和违法所得数额
2. 行为人在共同犯罪中的地位和作用
3. 是否存在自首、立功、认罪认罚等情节
4. 退赃退赔和被害人谅解情况
5. 前科劣迹情况
6. 当地司法实践的量刑基准

请给出具体的量刑幅度建议，并说明理由。
```
"""

_BUILTIN_CRIME_PATTERN_CARD: str = """# 收购银行卡犯罪模式详解

## 一、行为特征

收购银行卡模式是指行为人通过收购、租用、借用等方式获取他人的银行卡（含对公账户、结算卡、非银行支付账户）及配套信息（U盾、密码、绑定手机卡等），提供给他人用于信息网络犯罪活动的行为模式。

### 典型行为链条
1. **收卡环节**：通过社交平台、校园代理、网络广告等方式发布收购银行卡信息
2. **中介环节**：存在专门的银行卡收购中介，负责联系卖卡人和买卡人
3. **转售环节**：将收集的银行卡加价转售给上游犯罪团伙
4. **使用环节**：上游犯罪团伙利用所购银行卡进行资金转移、洗钱等活动

## 二、常见手段

### （一）线上收购
- 通过微信群、QQ群、贴吧、论坛等社交平台发布收卡信息
- 利用兼职招聘、贷款广告等名义变相收购
- 通过游戏代练、虚拟货币交易等渠道接触潜在卖卡人

### （二）线下收购
- 在学校、工厂、工地等人员密集场所发展下线代理
- 利用熟人关系、老乡关系等社会关系网络进行收购
- 以"办理贷款需要刷流水"等理由欺骗他人提供银行卡

### （三）组织分工
- **招募者**：负责发布信息和招募卖卡人
- **收购者**：负责接洽、验卡、支付报酬
- **运输者**：负责将银行卡及配套物品送至指定地点
- **验收者**：负责测试银行卡能否正常使用

## 三、证据要点

### （一）主观明知证据
- 收购价格明显高于正常水平的证据（如一张银行卡数百至上千元）
- 要求卖卡人配合办理大额转账、开通高额转账权限的记录
- 使用加密通讯工具、隐蔽交易方式的证据
- 对卖卡人的指导话术（如"问就说自己用"）
- 交易对手涉诈涉赌的相关信息

### （二）客观行为证据
- 银行卡交易记录、资金归集和分散转移记录
- 通讯记录、聊天记录、邮件等电子数据
- 转账记录、收款记录等资金往来凭证
- 银行卡的开户信息、挂失记录、补办记录

### （三）数量认定证据
- 涉案银行卡的完整清单
- 银行卡与上游犯罪案件的关联性证据
- 涉案资金的来源和去向分析报告

## 四、司法认定要点

### （一）构成帮信罪的情形
- 明知他人利用信息网络实施犯罪，仍收购、提供银行卡
- 提供的银行卡被用于接收、转移犯罪资金
- 达到"情节严重"标准（如为3个以上对象提供、支付结算20万元以上等）

### （二）不构成犯罪的情形
- 行为人确实不知道所提供银行卡被用于犯罪
- 行为人尽到了合理注意和审查义务
- 提供的银行卡数量少、金额小，达不到立案标准

### （三）与其他罪名的区分
- **掩饰、隐瞒犯罪所得罪**：若行为人在上游犯罪既遂后，专门为转移、隐匿犯罪所得提供银行卡
- **帮助信息网络犯罪活动罪**：若行为人在上游犯罪实施过程中，为犯罪提供支付结算帮助
- **妨害信用卡管理罪**：非法持有他人信用卡数量较大（5张以上）且不能说明合法来源
"""

_BUILTIN_CRIME_PATTERN_PURCHASE: str = """# 代购争议犯罪模式分析

## 一、行为特征

代购争议模式是指行为人通过代购形式，为他人购买特定商品或服务，实质上为信息网络犯罪活动提供帮助的行为模式。此类行为游走在合法代购与刑事犯罪之间的灰色地带。

### 典型情形
1. **代购虚拟商品**：代购游戏点卡、虚拟货币、软件激活码等
2. **代购实物商品**：代购手机、电脑、黄金等易于变现的商品
3. **代购服务**：代购酒店住宿、机票、火车票等
4. **资金代付**：代他人支付各类费用，实为资金转移

## 二、法律边界

### 合法代购的界限
- 代购行为本身不违法，属于正常的民事代理行为
- 代购方不知道且不应当知道所代购商品/服务被用于犯罪
- 代购方尽到了合理的审查义务
- 代购价格符合市场正常水平
- 代购物品有合法用途

### 构成帮信罪的情形
- 行为人明知或应当知道他人在利用信息网络实施犯罪
- 通过代购方式为犯罪活动提供资金转移、洗钱等帮助
- 代购行为异常：如频繁代购、大额代购、代购价格明显偏离市场
- 代购方从中获取明显不合理的高额报酬

## 三、争议焦点

### 焦点一：主观明知认定
- 代购方是否知道代购款项来源于犯罪活动
- 代购方是否知道所购物品被用于犯罪
- "应当知道"的推定标准应如何把握

### 焦点二：帮助行为的性质
- 代购行为是正常的商业行为还是实质上的帮助行为
- 代购方收取的服务费是否属于"违法所得"
- 如何区分共同犯罪与帮信罪

### 焦点三：情节严重认定
- 代购金额是否达到立案标准
- 代购次数和频率是否达到"情节严重"
- 代购行为的持续时间和稳定性

## 四、司法认定标准

### 有利于认定犯罪的因素
1. 代购方明知资金来源可疑仍继续代购
2. 代购方为同一对象多次代购，且金额较大
3. 代购方获取了明显超出合理水平的报酬
4. 代购方使用虚拟身份、加密通讯等隐蔽方式
5. 代购方有能力审查但故意不审查

### 不利于认定犯罪的因素
1. 代购方是正常经营的商家
2. 代购价格符合市场行情
3. 代购方尽到了审查义务
4. 代购方不知道也不可能知道资金来源于犯罪
5. 代购方在发现异常后主动停止代购并报案
"""

_BUILTIN_CRIME_PATTERN_TECH: str = """# 技术支持犯罪模式梳理

## 一、行为类型

### （一）网站/App开发类
- 为诈骗团伙开发虚假投资平台、赌博网站、色情平台
- 开发具有规避监管功能的应用程序（如隐藏IP、加密通讯）
- 开发自动收款、自动转账等资金处理系统

### （二）服务器运维类
- 为犯罪活动提供服务器托管、租赁服务
- 提供域名解析、CDN加速、云存储等技术服务
- 提供DDoS防护、数据加密等安全服务

### （三）软件工具类
- 开发群发软件（短信、微信、邮件群发）
- 开发批量注册软件（批量注册账号、批量验证）
- 开发改号软件、伪基站控制软件
- 开发爬虫、数据采集工具

### （四）通讯传输类
- 搭建VOIP电话系统，提供改号服务
- 提供"多卡宝""络漫宝"等通讯设备和技术支持
- 搭建即时通讯服务器，提供加密聊天服务

## 二、主观明知认定

### 有利于认定明知的因素
1. **技术特殊性**：开发的技术明显缺乏合法用途，如专门用于群发诈骗信息的软件
2. **服务对象异常**：服务对象无法提供合法的业务资质和经营许可证
3. **交易价格异常**：技术服务费远高于市场正常水平
4. **服务方式异常**：要求使用加密通讯、匿名支付、境外服务器等
5. **规避监管**：协助客户规避监管审查、删除服务器日志等
6. **从业经验**：作为技术人员，应知相关技术可能被用于犯罪
7. **历史记录**：曾因类似行为被警告、处罚或被投诉

### 不利于认定明知的因素
1. **技术中立性**：提供的技术具有合法用途，是通用技术
2. **尽到审查义务**：按法律法规要求进行了实名认证、内容审核
3. **合规经营**：有合法的经营资质，正常纳税
4. **异常发现后处理**：发现异常后及时停止服务并报告
5. **技术方案常规**：提供的技术方案完全按照行业标准实施

## 三、情节严重情形

### （一）对象数量
- 为三个以上不同的犯罪团伙或个人提供技术支持
- 技术被多个独立的上游犯罪活动使用

### （二）技术规模
- 开发的技术平台注册用户量大
- 服务器处理的数据量巨大
- 技术支持覆盖的地域范围广

### （三）持续时间
- 长时间持续提供技术支持服务
- 在被告知或发现异常后仍继续提供服务

### （四）违法所得
- 通过提供技术支持获得巨额收益
- 收益明显与正常技术服务不匹配

### （五）造成后果
- 技术支持直接导致重大犯罪结果发生
- 没有技术支持，上游犯罪无法实施或难以实施

## 四、典型案例

### 案例类型一：开发虚假投资平台
- 技术人员为诈骗团伙开发虚假股票、期货、虚拟货币交易平台
- 平台具有后台操控功能，可控制涨跌、限制出金
- 技术人员收取高额开发费和运维费

### 案例类型二：搭建GOIP设备
- 为电信诈骗团伙搭建、维护GOIP（多卡宝）设备
- 实现远程操控手机卡拨打电话
- 帮助诈骗团伙隐藏真实位置和身份

### 案例类型三：提供支付接口
- 为赌博网站、诈骗平台提供第四方支付接口
- 搭建资金归集和分流通道
- 提供虚假商户信息规避监管
"""


def _format_timestamp(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(UTC)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="法律知识体系初始化脚本 — 导入基础法律知识至知识库",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="full",
        choices=["full", "incremental"],
        help="初始化模式: full（全量初始化）/ incremental（增量更新，默认: full）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：仅查询和统计，不实际写入数据库",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别（默认: INFO）",
    )
    return parser.parse_args()


async def _entry_exists(db: AsyncSession, title: str) -> bool:
    result = await db.execute(
        select(KnowledgeEntry.id).where(KnowledgeEntry.title == title)
    )
    return result.scalar_one_or_none() is not None


async def _get_tag_by_name(db: AsyncSession, name: str) -> KnowledgeTag | None:
    result = await db.execute(
        select(KnowledgeTag).where(KnowledgeTag.name == name)
    )
    return result.scalar_one_or_none()


async def _get_or_create_tag(
    db: AsyncSession, tag_def: dict[str, str]
) -> KnowledgeTag:
    tag = await _get_tag_by_name(db, tag_def["name"])
    if tag:
        return tag
    tag = KnowledgeTag(
        name=tag_def["name"],
        description=tag_def.get("description", ""),
        color=tag_def.get("color", _DEFAULT_TAG_COLOR),
    )
    db.add(tag)
    await db.flush()
    logger.debug(f"创建标签: name={tag.name}, id={tag.id}")
    return tag


async def _associate_tags(
    db: AsyncSession,
    entry_id: int,
    tag_names: list[str],
) -> None:
    for tag_name in tag_names:
        tag = await _get_tag_by_name(db, tag_name)
        if not tag:
            logger.warning(f"标签不存在，跳过关联: {tag_name}")
            continue
        existing = await db.execute(
            select(EntryTag).where(
                EntryTag.entry_id == entry_id,
                EntryTag.tag_id == tag.id,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(EntryTag(entry_id=entry_id, tag_id=tag.id))


async def _create_relation_if_not_exists(
    db: AsyncSession,
    source_id: int,
    target_id: int,
    relation_type: RelationType,
) -> bool:
    if source_id == target_id:
        return False
    existing = await db.execute(
        select(EntryRelation).where(
            EntryRelation.source_entry_id == source_id,
            EntryRelation.target_entry_id == target_id,
            EntryRelation.relation_type == relation_type,
        )
    )
    if existing.scalar_one_or_none():
        return False
    rel = EntryRelation(
        source_entry_id=source_id,
        target_entry_id=target_id,
        relation_type=relation_type,
    )
    db.add(rel)
    return True


async def _read_document_file(file_path: str) -> str | None:
    """读取文档文件内容，支持 .txt、.pdf、.docx 格式."""
    ext = Path(file_path).suffix.lower()
    try:
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".pdf":
            import fitz
            doc = fitz.open(file_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text if text.strip() else None
        elif ext == ".docx":
            from docx import Document
            doc = Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs)
            return text if text.strip() else None
        else:
            logger.warning(f"不支持的文档格式: {ext}, 文件: {file_path}")
            return None
    except Exception as e:
        logger.warning(f"读取文档失败: {file_path}, 错误: {e}")
        return None


async def _scan_docs_directory() -> list[dict[str, str]]:
    """扫描 docs/ 目录，读取所有支持的文档文件."""
    docs_root = Path(__file__).resolve().parent.parent / "docs"
    if not docs_root.is_dir():
        logger.info(f"docs 目录不存在: {docs_root}")
        return []

    supported_exts = {".txt", ".pdf", ".docx"}
    documents: list[dict[str, str]] = []

    for file_path in docs_root.rglob("*"):
        if file_path.suffix.lower() in supported_exts and file_path.is_file():
            content = await _read_document_file(str(file_path))
            if content:
                documents.append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "content": content[:50000],
                })
                logger.info(f"读取文档成功: {file_path.name} ({len(content)} 字符)")

    return documents


def _validate_entry_data(data: dict[str, Any]) -> list[str]:
    """验证知识条目数据完整性."""
    errors: list[str] = []
    required = ["item_id", "title", "category", "tags", "content"]
    for required_field in required:
        if required_field not in data:
            errors.append(f"缺少必需字段: {required_field}")
    if "title" in data:
        title = data["title"]
        if not title or not title.strip():
            errors.append("标题不能为空")
        elif len(title.strip()) < 3:
            errors.append(f"标题长度不足: {len(title.strip())} < 3")
        elif len(title.strip()) > AnalysisConfig.MAX_ENTRY_TITLE_LENGTH:
            errors.append(
                f"标题过长: {len(title.strip())} > "
                f"{AnalysisConfig.MAX_ENTRY_TITLE_LENGTH}"
            )
    if "content" in data:
        content = data["content"]
        if not content or not content.strip():
            errors.append("内容不能为空")
    if "tags" in data and isinstance(data["tags"], list):
        if len(data["tags"]) > AnalysisConfig.MAX_TAGS_PER_ENTRY:
            errors.append(
                f"标签数量超过限制: {len(data['tags'])} > "
                f"{AnalysisConfig.MAX_TAGS_PER_ENTRY}"
            )
    valid_categories = {"law", "methodology", "case", "other"}
    if "category" in data and data["category"] not in valid_categories:
        errors.append(f"无效的分类: {data['category']}")
    return errors


async def _extract_metadata_with_llm(content: str) -> dict[str, Any]:
    """调用 LLM 从文档内容中提取元数据."""
    client = get_client()
    prompt = _METADATA_EXTRACTION_PROMPT.format(
        text=content[:_CONTENT_PREVIEW_CHARS]
    )

    for attempt in range(_LLM_RETRY_MAX_ATTEMPTS + 1):
        try:
            raw_result: dict[str, Any] | list[Any] = (
                await client.generate_json(
                    prompt=prompt,
                    system_prompt=_LLM_EXTRACTION_SYSTEM_PROMPT,
                    temperature=0.2,
                )
            )
            if isinstance(raw_result, list):
                if attempt < _LLM_RETRY_MAX_ATTEMPTS:
                    await asyncio.sleep(_LLM_RETRY_DELAY_BASE * (attempt + 1))
                continue
            return _validate_llm_metadata(raw_result, content)
        except (ValueError, json.JSONDecodeError):
            if attempt < _LLM_RETRY_MAX_ATTEMPTS:
                await asyncio.sleep(_LLM_RETRY_DELAY_BASE * (attempt + 1))
        except Exception:
            if attempt < _LLM_RETRY_MAX_ATTEMPTS:
                await asyncio.sleep(_LLM_RETRY_DELAY_BASE * (attempt + 1))

    filename_hint = content[:100].strip()[:30]
    return {
        "title": f"文档导入: {filename_hint}",
        "summary": content[:200].strip(),
        "suggested_tags": [],
        "suggested_category": "other",
    }


def _validate_llm_metadata(
    data: dict[str, Any], original_content: str
) -> dict[str, Any]:
    title = data.get("title", "")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title 必须是非空字符串")

    result: dict[str, Any] = {
        "title": title.strip()[:AnalysisConfig.MAX_ENTRY_TITLE_LENGTH],
        "summary": "",
        "suggested_tags": [],
        "suggested_category": "other",
    }

    summary = data.get("summary", "")
    if isinstance(summary, str) and summary.strip():
        result["summary"] = summary[:500]

    tags = data.get("suggested_tags", [])
    if isinstance(tags, list):
        clean_tags = [
            str(t).strip() for t in tags
            if isinstance(t, (str, int, float)) and str(t).strip()
        ]
        if clean_tags:
            result["suggested_tags"] = clean_tags[:10]

    category = str(data.get("suggested_category", "other")).strip().lower()
    valid = {"law", "methodology", "case", "other"}
    if category not in valid:
        category = "other"
    result["suggested_category"] = category

    return result


async def _process_document_entry(
    db: AsyncSession,
    doc: dict[str, str],
    mode: str,
    dry_run: bool,
) -> InitRecord:
    """处理从 docs/ 目录读取的文档."""
    item_id = f"doc_{Path(doc['filename']).stem}"
    start_ts = time.monotonic()

    record = InitRecord(
        item_id=item_id,
        title=doc["filename"],
        status="pending",
    )

    try:
        metadata = await _extract_metadata_with_llm(doc["content"])

        if mode == "incremental":
            exists = await _entry_exists(db, metadata["title"])
            if exists:
                record.status = "skipped"
                record.error = "条目已存在"
                record.duration_seconds = time.monotonic() - start_ts
                return record

        if dry_run:
            record.status = "created"
            record.entry_id = -1
            record.duration_seconds = time.monotonic() - start_ts
            return record

        db_entry = KnowledgeEntry(
            title=metadata["title"],
            content=doc["content"],
            summary=metadata.get("summary", ""),
            category=EntryCategory(
                metadata.get("suggested_category", "other")
            ),
            status=EntryStatus.active,
            source_type=SourceType.document_import,
            created_by=_SYSTEM_USER_ID,
        )
        db.add(db_entry)
        await db.flush()

        tag_names = metadata.get("suggested_tags", [])
        await _associate_tags(db, db_entry.id, tag_names)

        record.status = "created"
        record.entry_id = db_entry.id
        record.duration_seconds = time.monotonic() - start_ts
        return record

    except Exception as e:
        record.status = "failed"
        record.error = f"{type(e).__name__}: {e!s}"
        record.duration_seconds = time.monotonic() - start_ts
        return record


async def _process_builtin_entry(
    db: AsyncSession,
    entry: dict[str, Any],
    mode: str,
    dry_run: bool,
) -> InitRecord:
    """处理内置知识条目."""
    start_ts = time.monotonic()
    record = InitRecord(
        item_id=entry["item_id"],
        title=entry["title"],
        status="pending",
    )

    try:
        validation_errors = _validate_entry_data(entry)
        if validation_errors:
            record.status = "failed"
            record.error = f"数据校验失败: {'; '.join(validation_errors)}"
            record.duration_seconds = time.monotonic() - start_ts
            return record

        if mode == "incremental":
            exists = await _entry_exists(db, entry["title"])
            if exists:
                record.status = "skipped"
                record.error = "条目已存在"
                record.duration_seconds = time.monotonic() - start_ts
                return record

        if dry_run:
            record.status = "created"
            record.entry_id = -1
            record.duration_seconds = time.monotonic() - start_ts
            return record

        category_map = {
            "law": EntryCategory.law,
            "methodology": EntryCategory.methodology,
            "case": EntryCategory.case,
            "other": EntryCategory.other,
        }

        db_entry = KnowledgeEntry(
            title=entry["title"],
            content=entry["content"],
            summary=entry.get("summary", ""),
            category=category_map.get(entry["category"], EntryCategory.other),
            status=EntryStatus.active,
            source_type=SourceType.manual,
            created_by=_SYSTEM_USER_ID,
            confidence=0.9,
        )
        db.add(db_entry)
        await db.flush()

        await _associate_tags(db, db_entry.id, entry.get("tags", []))

        record.status = "created"
        record.entry_id = db_entry.id
        record.duration_seconds = time.monotonic() - start_ts
        logger.info(f"知识条目创建成功: id={db_entry.id}, title={entry['title'][:50]}")
        return record

    except Exception as e:
        record.status = "failed"
        record.error = f"{type(e).__name__}: {e!s}"
        record.duration_seconds = time.monotonic() - start_ts
        logger.error(f"知识条目创建失败 [{entry['item_id']}]: {e}")
        return record


async def run_init(
    mode: str,
    dry_run: bool,
) -> InitReport:
    """执行初始化主流程."""
    report = InitReport(
        mode=mode,
        dry_run=dry_run,
        start_time=_format_timestamp(),
    )

    async with AsyncSessionLocal() as db:
        try:
            all_tags = _STANDARD_TAGS + _EXTRA_STANDARD_TAGS

            if not dry_run:
                for tag_def in all_tags:
                    await _get_or_create_tag(db, tag_def)
                await db.flush()
                logger.info(f"标签创建/确认完成: {len(all_tags)} 个")

            report.tag_count = len(all_tags)

            builtin_entries = _build_legal_knowledge_entries()
            report.total = len(builtin_entries)

            doc_entries: list[dict[str, str]] = []
            try:
                doc_entries = await _scan_docs_directory()
                if doc_entries:
                    logger.info(f"从 docs/ 目录读取到 {len(doc_entries)} 个文档文件")
                    report.total += len(doc_entries)
            except Exception as e:
                logger.warning(f"扫描 docs/ 目录失败: {e}")

            if dry_run:
                logger.info("=" * 50)
                logger.info(f"预览模式 (DRY-RUN): 将处理 {report.total} 个条目")
                logger.info("=" * 50)

            for entry in builtin_entries:
                record = await _process_builtin_entry(db, entry, mode, dry_run)
                report.records.append(record)
                if record.status == "created":
                    report.created_count += 1
                elif record.status == "skipped":
                    report.skipped_count += 1
                else:
                    report.failed_count += 1

            for doc in doc_entries:
                record = await _process_document_entry(db, doc, mode, dry_run)
                report.records.append(record)
                if record.status == "created":
                    report.created_count += 1
                elif record.status == "skipped":
                    report.skipped_count += 1
                else:
                    report.failed_count += 1

            await _build_tag_relations(db, dry_run, report)

        except Exception as e:
            logger.critical(f"初始化过程发生严重错误: {e}")
            raise
        finally:
            report.end_time = _format_timestamp()

    duration = 0.0
    if report.start_time and report.end_time:
        try:
            start_dt = datetime.strptime(
                report.start_time.replace(" UTC", ""),
                "%Y-%m-%d %H:%M:%S",
            )
            end_dt = datetime.strptime(
                report.end_time.replace(" UTC", ""),
                "%Y-%m-%d %H:%M:%S",
            )
            duration = (end_dt - start_dt).total_seconds()
        except (ValueError, AttributeError):
            pass
    report.duration_seconds = duration
    return report


async def _build_tag_relations(
    db: AsyncSession,
    dry_run: bool,
    report: InitReport,
) -> None:
    """构建标签之间和条目之间的关联关系."""
    relation_count = 0

    if dry_run:
        report.relation_count = len(_TAG_RELATIONS) + 1
        return

    for source_name, target_name, rel_type in _TAG_RELATIONS:
        source_entries = await db.execute(
            select(KnowledgeEntry).join(EntryTag).join(KnowledgeTag).where(
                KnowledgeTag.name == source_name,
            )
        )
        target_entries = await db.execute(
            select(KnowledgeEntry).join(EntryTag).join(KnowledgeTag).where(
                KnowledgeTag.name == target_name,
            )
        )
        source_list = list(source_entries.scalars().all())
        target_list = list(target_entries.scalars().all())

        for s_entry in source_list:
            for t_entry in target_list:
                if await _create_relation_if_not_exists(
                    db, s_entry.id, t_entry.id, rel_type
                ):
                    relation_count += 1

    analysis_entry_result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.title.ilike("%三维度分析模型%"))
    )
    scoring_entry_result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.title.ilike("%量化评分标准%"))
    )

    analysis_entry = analysis_entry_result.scalar_one_or_none()
    scoring_entry = scoring_entry_result.scalar_one_or_none()

    if analysis_entry and scoring_entry:
        if await _create_relation_if_not_exists(
            db, analysis_entry.id, scoring_entry.id, RelationType.references
        ):
            relation_count += 1

    if relation_count > 0:
        await db.flush()

    report.relation_count = relation_count
    logger.info(f"关联关系创建完成: {relation_count} 条")


async def main() -> int:
    args = parse_args()

    setup_logging(log_level=args.log_level, log_dir=settings.LOG_DIR)

    logger.info("=" * 50)
    logger.info("法律知识体系初始化脚本启动")
    logger.info(f"  初始化模式: {'全量初始化' if args.mode == 'full' else '增量更新'}")
    logger.info(f"  运行模式: {'预览 (DRY-RUN)' if args.dry_run else '正式执行'}")
    logger.info(f"  日志级别: {args.log_level}")
    logger.info("=" * 50)

    try:
        report = await run_init(
            mode=args.mode,
            dry_run=args.dry_run,
        )
    except Exception as e:
        logger.critical(f"初始化失败: {e}")
        return 1
    finally:
        await async_engine.dispose()
        os.chdir(_old_cwd)
        logger.info("数据库引擎资源已释放")

    report_text = report.generate_text_report()
    print("\n" + report_text)

    logger.info("初始化报告生成完成")
    logger.info(
        f"总计: {report.total}, "
        f"新增: {report.created_count}, "
        f"跳过: {report.skipped_count}, "
        f"失败: {report.failed_count}, "
        f"标签: {report.tag_count}, "
        f"关联: {report.relation_count}"
    )

    report_dir = Path(settings.LOG_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    mode_suffix = f"_{args.mode}"
    dryrun_suffix = "_dryrun" if args.dry_run else ""
    txt_path = (
        report_dir
        / f"legal_init_report_{timestamp}{mode_suffix}{dryrun_suffix}.txt"
    )
    txt_path.write_text(report_text, encoding="utf-8")
    logger.info(f"文本报告已保存: {txt_path}")

    json_report = report.generate_json_report()
    json_path = (
        report_dir
        / f"legal_init_report_{timestamp}{mode_suffix}{dryrun_suffix}.json"
    )
    json_path.write_text(
        json.dumps(json_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"JSON 报告已保存: {json_path}")

    if args.dry_run:
        logger.info("预览模式完成，未写入任何数据。移除 --dry-run 参数执行正式初始化。")
    else:
        logger.info("法律知识体系初始化完成！")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
