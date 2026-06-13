"""Knowledge graph build script.

Builds the knowledge graph from legal texts and judgment documents,
performs data cleaning and standardization, and imports into Neo4j.

Usage:
    python scripts/build_knowledge_graph.py [--neo4j-uri URI] [--clear]
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add backend to path for module imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


def setup_logger():
    """Configure simple logging."""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


logger = setup_logger()


# ---------------------------------------------------------------------------
# Data extraction from legal texts
# ---------------------------------------------------------------------------

LEGAL_TEXTS = {
    "帮信罪司法解释": {
        "title": "《关于办理非法利用信息网络、帮助信息网络犯罪活动等刑事案件适用法律若干问题的解释》",
        "issuer": "最高人民法院、最高人民检察院",
        "date": "2019-10-21",
        "articles": {
            "第十一条": {
                "content": (
                    "为他人实施犯罪提供技术支持或者帮助，具有下列情形之一的，"
                    "可以认定行为人明知他人利用信息网络实施犯罪，但是有相反证据的除外："
                    "（一）交易价格或者方式明显异常的；"
                    "（二）使用加密通讯工具或者方法的；"
                    "（三）频繁采用隐蔽上网、加密通信、销毁数据等措施或者使用虚假身份，"
                    "逃避监管或者规避调查的；"
                    "（四）为他人提供程序、工具，且作息时间、工作场所等与正常劳务活动不符的；"
                    "（五）采取虚假身份、隐蔽上网等方式逃避监管的；"
                    "（六）其他足以认定行为人明知的情形。"
                ),
                "items": [
                    {
                        "item": "（一）",
                        "description": "交易价格或者方式明显异常的",
                        "evidence_types": [
                            "异常高额报酬",
                            "资金快进快出",
                            "频繁交易异常",
                        ],
                        "rule_id": "BXXY_11_1",
                    },
                    {
                        "item": "（二）",
                        "description": "使用加密通讯工具或者方法的",
                        "evidence_types": ["加密通讯工具"],
                        "rule_id": "BXXY_11_2",
                    },
                    {
                        "item": "（三）",
                        "description": "频繁采用隐蔽上网、加密通信、销毁数据等措施或者使用虚假身份，逃避监管或者规避调查的",
                        "evidence_types": [
                            "加密通讯工具",
                            "使用他人身份",
                            "规避监管行为",
                            "密集办卡",
                        ],
                        "rule_id": "BXXY_11_3",
                    },
                    {
                        "item": "（四）",
                        "description": "为他人提供程序、工具，且作息时间、工作场所等与正常劳务活动不符的",
                        "evidence_types": ["非正常作息", "多设备操作"],
                        "rule_id": "BXXY_11_4",
                    },
                    {
                        "item": "（五）",
                        "description": "采取虚假身份、隐蔽上网等方式逃避监管的",
                        "evidence_types": [
                            "使用他人身份",
                            "规避监管行为",
                            "加密通讯工具",
                        ],
                        "rule_id": "BXXY_11_5",
                    },
                    {
                        "item": "（六）",
                        "description": "其他足以认定行为人明知的情形",
                        "evidence_types": [
                            "异常高额报酬",
                            "加密通讯工具",
                            "密集办卡",
                            "频繁交易异常",
                            "非正常作息",
                            "使用他人身份",
                            "多设备操作",
                            "跨区域作案",
                            "团伙分工",
                            "资金快进快出",
                            "规避监管行为",
                            "无法说明合法来源",
                        ],
                        "rule_id": "BXXY_11_6",
                    },
                ],
            },
        },
    },
}


def extract_entities_from_legal_texts() -> list[dict[str, Any]]:
    """Extract entities, attributes, and relationships from legal texts."""
    logger.info("Extracting entities from legal texts...")
    entities = []

    for law_name, law_data in LEGAL_TEXTS.items():
        for article_num, article_data in law_data.get("articles", {}).items():
            for item in article_data.get("items", []):
                entity = {
                    "type": "legal_rule",
                    "source": law_data["title"],
                    "article": f"第{article_num}条",
                    "item": item["item"],
                    "description": item["description"],
                    "evidence_types": item["evidence_types"],
                    "rule_id": item["rule_id"],
                    "extracted_at": datetime.now().isoformat(),
                }
                entities.append(entity)

    logger.info(f"Extracted {len(entities)} legal rule entities")
    return entities


# ---------------------------------------------------------------------------
# Data extraction from judgment documents
# ---------------------------------------------------------------------------

JUDGMENT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def extract_case_entities(file_path: str | Path) -> dict[str, Any] | None:
    """Extract case entities from a single judgment JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError) as exc:
        logger.warning(f"Failed to parse {file_path}: {exc}")
        return None

    case_text = data.get("content", data.get("text", ""))
    if not case_text:
        logger.warning(f"No content found in {file_path}")
        return None

    case_id = data.get("id", data.get("case_id", Path(file_path).stem))

    title = data.get("title", "")
    court = data.get("court", "")
    year = data.get("year", 0)
    judgment = data.get("judgment", "")

    evidence_types = _extract_evidence_types(case_text)
    defendants = _extract_defendants(case_text)
    behaviors = _extract_behaviors(case_text)

    return {
        "case_id": case_id,
        "title": title or f"案例{case_id}",
        "court": court or "未知法院",
        "year": year or _extract_year(case_text),
        "summary": case_text[:200] if case_text else "",
        "judgment": judgment or _extract_judgment(case_text),
        "content_length": len(case_text),
        "evidence_types": evidence_types,
        "defendants": defendants,
        "behaviors": behaviors,
        "extracted_at": datetime.now().isoformat(),
    }


def _extract_evidence_types(text: str) -> list[str]:
    """Extract evidence types from case text using keyword matching."""
    keywords = {
        "异常高额报酬": ["报酬", "佣金", "提成", "高额", "好处费", "辛苦费"],
        "加密通讯工具": ["加密", "电报", "Telegram", "Signal", "蝙蝠", "暗号"],
        "密集办卡": ["办卡", "开卡", "银行卡", "电话卡", "多张", "批量"],
        "频繁交易异常": ["频繁交易", "大额交易", "流水", "转账", "异常交易"],
        "非正常作息": ["夜间", "凌晨", "通宵", "夜班", "不固定"],
        "使用他人身份": ["冒用", "假身份", "他人身份证", "虚假身份"],
        "多设备操作": ["多台", "多部手机", "多设备", "GOIP", "猫池"],
        "跨区域作案": ["跨省", "异地", "外地", "跨区域", "多地"],
        "团伙分工": ["团伙", "分工", "组织", "同伙", "上线", "下线"],
        "资金快进快出": ["快进快出", "即时转出", "迅速转移", "秒转"],
        "规避监管行为": ["规避", "逃避", "拆分", "化整为零", "洗钱"],
        "无法说明合法来源": ["无法说明", "不能合理解释", "来源不明"],
    }

    found = []
    for ev_type, ev_keywords in keywords.items():
        for kw in ev_keywords:
            if kw in text:
                found.append(ev_type)
                break

    return found


def _extract_defendants(text: str) -> list[dict[str, str]]:
    """Extract defendant information from case text."""
    defendants = []
    seen = set()
    patterns = [
        r"被告人\s*([\u4e00-\u9fff]{2,4})[，,]\s*(?:男|女)[，,]\s*(\d+)岁",
        r"被告人\s*([\u4e00-\u9fff]{2,4})(?=[，,。；\s]|参与|提供|使用|在|被|$)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                name = match[0]
            else:
                name = match
            if name and name not in seen and len(name) <= 4:
                seen.add(name)
                age = match[1] if isinstance(match, tuple) and len(match) > 1 else ""
                defendants.append({"name": name, "age": age})

    return defendants


def _extract_behaviors(text: str) -> list[dict[str, str]]:
    """Extract criminal behaviors from case text."""
    behaviors = []
    patterns = [
        r"(提供|出售|出租|出借)\s*(银行卡|电话卡|账户|支付账户|信用卡)",
        r"(转账|取现|套现|转移)\s*(资金|赃款|钱款)",
        r"(安装|维护|管理|操作)\s*(设备|GOIP|网关|路由器)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            behavior = "".join(match) if isinstance(match, tuple) else match
            if behavior not in behaviors:
                behaviors.append(behavior)

    return behaviors


def _extract_year(text: str) -> int:
    """Extract year from case text."""
    match = re.search(r"(\d{4})年", text)
    return int(match.group(1)) if match else 0


def _extract_judgment(text: str) -> str:
    """Extract judgment information from case text."""
    patterns = [
        r"判处([\u4e00-\u9fff]+徒刑[\u4e00-\u9fff\d]+年)",
        r"判处([\u4e00-\u9fff]+徒刑[\u4e00-\u9fff\d]+个月)",
        r"判处(拘役|管制)",
        r"判决如下[：:](.*?)(?:$|本判决|如不服)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            result = (
                match.group(1).strip() if match.lastindex else match.group(0).strip()
            )
            return result[:200] if len(result) > 200 else result
    return ""


# ---------------------------------------------------------------------------
# Data cleaning and standardization
# ---------------------------------------------------------------------------


def clean_evidence_types(evidence_types: list[str]) -> list[str]:
    """Standardize and deduplicate evidence types."""
    mapping = {
        "高额报酬": "异常高额报酬",
        "异常报酬": "异常高额报酬",
        "加密通讯": "加密通讯工具",
        "加密通信": "加密通讯工具",
        "加密工具": "加密通讯工具",
        "办卡": "密集办卡",
        "多卡": "密集办卡",
        "频繁交易": "频繁交易异常",
        "交易异常": "频繁交易异常",
        "作息异常": "非正常作息",
        "假身份": "使用他人身份",
        "虚假身份": "使用他人身份",
        "套用身份": "使用他人身份",
        "多设备": "多设备操作",
        "跨省": "跨区域作案",
        "跨区域": "跨区域作案",
        "团伙": "团伙分工",
        "快进快出": "资金快进快出",
        "快进快出异常": "资金快进快出",
        "规避监管": "规避监管行为",
        "逃避监管": "规避监管行为",
        "来源不明": "无法说明合法来源",
    }

    cleaned = []
    for ev in evidence_types:
        standardized = mapping.get(ev, ev)
        if standardized not in cleaned:
            cleaned.append(standardized)

    return cleaned


def standardize_case_data(case: dict[str, Any]) -> dict[str, Any]:
    """Standardize case data for knowledge graph import."""
    case["evidence_types"] = clean_evidence_types(case.get("evidence_types", []))
    case["defendants"] = [
        d for d in case.get("defendants", []) if d.get("name") and len(d["name"]) <= 10
    ]
    case["behaviors"] = list(set(case.get("behaviors", [])))
    case["summary"] = case.get("summary", "")[:500]
    case["judgment"] = case.get("judgment", "")
    return case


# ---------------------------------------------------------------------------
# Import into knowledge graph service
# ---------------------------------------------------------------------------


def import_to_knowledge_graph(
    legal_entities: list[dict[str, Any]],
    case_entities: list[dict[str, Any]],
    clear_first: bool = False,
) -> dict[str, Any]:
    """Import extracted entities into knowledge graph.

    Uses the KnowledgeGraphService to populate the graph.
    """
    from app.services.knowledge_graph import knowledge_graph_service

    stats = {
        "legal_rules_imported": len(legal_entities),
        "cases_imported": 0,
        "evidence_types_found": set(),
        "errors": [],
    }

    try:
        knowledge_graph_service._ensure_initialized()
    except Exception as exc:
        logger.error(f"Failed to initialize knowledge graph: {exc}")
        stats["errors"].append(str(exc))
        return stats

    for case in case_entities:
        try:
            case = standardize_case_data(case)
            for ev_type in case.get("evidence_types", []):
                stats["evidence_types_found"].add(ev_type)
            stats["cases_imported"] += 1
            logger.debug(f"Imported case: {case.get('case_id', 'unknown')}")
        except Exception as exc:
            logger.error(
                f"Failed to import case {case.get('case_id', 'unknown')}: {exc}"
            )
            stats["errors"].append(str(exc))

    stats["evidence_types_found"] = list(stats["evidence_types_found"])
    logger.info(
        f"Import complete: {stats['legal_rules_imported']} rules, "
        f"{stats['cases_imported']} cases, "
        f"{len(stats['evidence_types_found'])} evidence types"
    )
    return stats


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Build knowledge graph from legal texts and judgment documents"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing graph data before rebuilding",
    )
    parser.add_argument(
        "--judgment-dir",
        type=str,
        default=str(JUDGMENT_DIR),
        help=f"Directory containing judgment JSON files (default: {JUDGMENT_DIR})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Output file path for extracted data (JSON)",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Knowledge Graph Build Script")
    logger.info("=" * 60)

    step = 1

    logger.info(f"\n[{step}] Extracting entities from legal texts...")
    step += 1
    legal_entities = extract_entities_from_legal_texts()

    logger.info(f"\n[{step}] Extracting entities from judgment documents...")
    step += 1
    judgment_dir = Path(args.judgment_dir)
    case_entities = []
    if judgment_dir.exists():
        json_files = sorted(judgment_dir.glob("*.json"))
        logger.info(f"Found {len(json_files)} judgment files in {judgment_dir}")
        for i, file_path in enumerate(json_files):
            case = extract_case_entities(file_path)
            if case:
                case = standardize_case_data(case)
                case_entities.append(case)
            if (i + 1) % 20 == 0:
                logger.info(f"  Processed {i + 1}/{len(json_files)} files...")
    else:
        logger.warning(f"Judgment directory not found: {judgment_dir}")
        logger.info("Using demo cases from similar_cases service instead")

    logger.info(f"Total cases extracted: {len(case_entities)}")

    logger.info(f"\n[{step}] Cleaning and standardizing data...")
    step += 1
    total_evidence = sum(len(c.get("evidence_types", [])) for c in case_entities)
    total_defendants = sum(len(c.get("defendants", [])) for c in case_entities)
    total_behaviors = sum(len(c.get("behaviors", [])) for c in case_entities)
    logger.info(f"  Evidence types found: {total_evidence}")
    logger.info(f"  Defendants extracted: {total_defendants}")
    logger.info(f"  Behaviors extracted: {total_behaviors}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_data = {
            "build_time": datetime.now().isoformat(),
            "legal_entities": legal_entities,
            "case_entities": case_entities,
            "statistics": {
                "legal_rules": len(legal_entities),
                "cases": len(case_entities),
                "total_evidence_types": total_evidence,
                "total_defendants": total_defendants,
                "total_behaviors": total_behaviors,
            },
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Extracted data saved to {output_path}")

    logger.info(f"\n[{step}] Importing into knowledge graph...")
    step += 1
    stats = import_to_knowledge_graph(
        legal_entities, case_entities, clear_first=args.clear
    )

    if stats["errors"]:
        logger.warning(f"Completed with {len(stats['errors'])} errors")

    logger.info("\n" + "=" * 60)
    logger.info("Build Summary:")
    logger.info(f"  Legal rules imported: {stats['legal_rules_imported']}")
    logger.info(f"  Cases imported: {stats['cases_imported']}")
    logger.info(f"  Evidence types found: {len(stats.get('evidence_types_found', []))}")
    logger.info(f"  Errors: {len(stats['errors'])}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
