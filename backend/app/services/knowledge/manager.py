"""知识管理服务层.

整合原 knowledge_import_service.py 和 knowledge_lifecycle_service.py，
提供知识导入处理、生命周期管理、质量扫描和版本更替等功能。
"""
from __future__ import annotations
import asyncio, contextlib, json, os, re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import AnalysisConfig
from app.database import get_async_db_session
from app.models.analysis import Analysis
from app.models.case import Case
from app.models.entry_relation import EntryRelation, RelationType
from app.models.entry_tag import EntryTag
from app.models.knowledge_entry import EntryCategory, EntryStatus, KnowledgeEntry, SourceType
from app.models.knowledge_tag import KnowledgeTag
from app.services.document_processor import process_document
from app.services.ollama_client import get_client

FeedbackType = Literal["positive", "negative"]
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
_MAX_RETRIES, _SYS_UID, _TAG_CLR = 2, 1, "#3B82F6"
_VALID_CAT = frozenset({"law", "methodology", "case", "other"})
_META_FIELDS = frozenset({"title", "summary", "key_concepts", "suggested_tags", "suggested_category"})
_META_PROMPT = """请从以下文本中提取结构化元数据，以JSON格式返回。
必须包含以下字段：
- title: 简洁的标题（不超过100字）
- summary: 内容摘要（不超过200字）
- key_concepts: 关键概念列表（字符串数组，3-5个）
- suggested_tags: 建议标签列表（字符串数组，3-8个，用于分类和检索）
- suggested_category: 建议分类，必须是以下之一：law（法律）、methodology（方法论）、case（案例）、other（其他）

只返回JSON，不要包含任何其他文字：

文本内容：
{text}"""

@dataclass
class ImportResult:
    success: bool
    entry_id: int | None = None
    extracted_metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    def to_dict(self) -> dict[str, Any]:
        r = {"success": self.success, "entry_id": self.entry_id, "extracted_metadata": self.extracted_metadata}
        if self.error: r["error"] = self.error
        return r

@dataclass
class BatchImportResult:
    success_count: int = 0
    failure_count: int = 0
    skip_count: int = 0
    success_case_ids: list[int] = field(default_factory=list)
    failure_case_ids: list[int] = field(default_factory=list)
    skip_case_ids: list[int] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]:
        return {"success_count": self.success_count, "failure_count": self.failure_count, "skip_count": self.skip_count, "success_case_ids": self.success_case_ids, "failure_case_ids": self.failure_case_ids, "skip_case_ids": self.skip_case_ids, "errors": self.errors}

@dataclass
class DecayStatistics:
    total_decayed: int = 0
    newly_stale: int = 0
    avg_decay_magnitude: float = 0.0
    min_decay: float = 0.0
    max_decay: float = 0.0
    def to_dict(self) -> dict[str, Any]:
        return {"total_decayed": self.total_decayed, "newly_stale": self.newly_stale, "avg_decay_magnitude": round(self.avg_decay_magnitude, 6), "min_decay": round(self.min_decay, 6), "max_decay": round(self.max_decay, 6)}

@dataclass
class LintIssue:
    issue_type: str
    affected_entry_ids: list[int]
    description: str
    suggestion: str
    def to_dict(self) -> dict[str, Any]:
        return {"issue_type": self.issue_type, "affected_entry_ids": self.affected_entry_ids, "description": self.description, "suggestion": self.suggestion}

@dataclass
class LintReport:
    total_issues: int = 0
    issues: list[LintIssue] = field(default_factory=list)
    scanned_entries: int = 0
    timestamp: str = ""
    def to_dict(self) -> dict[str, Any]:
        return {"total_issues": self.total_issues, "issues": [i.to_dict() for i in self.issues], "scanned_entries": self.scanned_entries, "timestamp": self.timestamp}

@dataclass
class ScheduleConfig:
    decay_interval: int = AnalysisConfig.KNOWLEDGE_DECAY_SCHEDULE_INTERVAL
    lint_interval: int = AnalysisConfig.KNOWLEDGE_LINT_SCHEDULE_INTERVAL
    decay_enabled: bool = True
    lint_enabled: bool = True

class _FileWrapper:
    def __init__(self, content: bytes, filename: str = "document.txt") -> None:
        self.filename, self._content = filename, content
    async def read(self) -> bytes:
        return self._content

def _validate_meta(d: dict[str, Any]) -> dict[str, Any]:
    miss = [f for f in _META_FIELDS if f not in d]
    if miss: raise ValueError(f"LLM返回的元数据缺少必需字段: {', '.join(miss)}")
    if not isinstance(d.get("title"), str) or not d["title"].strip(): raise ValueError("title必须是非空字符串")
    if not isinstance(d.get("summary"), str) or not d["summary"].strip(): raise ValueError("summary必须是非空字符串")
    if not isinstance(d.get("key_concepts"), list): d["key_concepts"] = []
    d["key_concepts"] = [str(c) for c in d["key_concepts"] if isinstance(c, str) and c.strip()]
    if not isinstance(d.get("suggested_tags"), list): d["suggested_tags"] = []
    d["suggested_tags"] = [str(t).strip() for t in d["suggested_tags"] if isinstance(t, str) and t.strip()]
    cat = str(d.get("suggested_category", "other")).strip().lower()
    d["suggested_category"] = cat if cat in _VALID_CAT else "other"
    return d

def _validate_entry_id(eid: int, name: str = "entry_id") -> None:
    if not isinstance(eid, int) or eid <= 0: raise ValueError(f"无效的参数'{name}': {eid}，必须为正整数")

def _validate_feedback(fb: str) -> FeedbackType:
    if fb not in ("positive", "negative"): raise ValueError(f"无效的反馈类型'{fb}'，仅支持: positive, negative")
    return fb  # type: ignore

def _extract_wikilinks(c: str) -> set[str]:
    return {m.group(1).strip() for m in _WIKILINK_RE.finditer(c)} if c else set()

# 向后兼容别名（供旧 service 文件 re-export 层使用）
_ImportFileWrapper = _FileWrapper
_validate_metadata = _validate_meta

async def _resolve_category(cs: str) -> EntryCategory:
    return {"law": EntryCategory.law, "methodology": EntryCategory.methodology, "case": EntryCategory.case, "other": EntryCategory.other}.get(cs, EntryCategory.other)

async def _get_or_create_tag(db: AsyncSession, name: str) -> KnowledgeTag:
    r = await db.execute(select(KnowledgeTag).where(KnowledgeTag.name == name))
    if (t := r.scalar_one_or_none()): return t
    nt = KnowledgeTag(name=name, description=f"自动创建的标签: {name}", color=_TAG_CLR)
    db.add(nt); await db.flush(); logger.debug(f"自动创建标签: name={name}, id={nt.id}"); return nt

async def _associate_tags(db: AsyncSession, eid: int, names: list[str]) -> list[KnowledgeTag]:
    if not names: return []
    res = []
    for n in names:
        try:
            t = await _get_or_create_tag(db, n)
            ex = await db.execute(select(EntryTag).where(EntryTag.entry_id == eid, EntryTag.tag_id == t.id))
            if not ex.scalar_one_or_none(): db.add(EntryTag(entry_id=eid, tag_id=t.id)); logger.debug(f"标签关联成功: entry={eid}, tag={n}")
            res.append(t)
        except Exception as e: logger.warning(f"标签关联失败: entry={eid}, tag={n}, error={e}")
    if res: await db.flush()
    return res

async def extract_metadata_with_llm(text: str) -> dict[str, Any]:
    client = get_client()
    prompt = _META_PROMPT.format(text=text[:8000])
    last_err: str | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            raw = await client.generate_json(prompt=prompt, system_prompt="你是一个专业的法律知识管理助手，擅长从文本中提取结构化元数据。", temperature=0.2)
            if isinstance(raw, list): logger.warning(f"LLM返回了列表而非字典 (尝试 {attempt + 1})"); last_err = "LLM返回了列表格式而非字典"; continue
            v = _validate_meta(raw)
            logger.info(f"元数据提取成功: title={v['title'][:50]}, category={v['suggested_category']}, tags={len(v['suggested_tags'])}")
            return v
        except (ValueError, json.JSONDecodeError) as e:
            last_err = str(e); logger.warning(f"元数据提取验证失败 (尝试 {attempt + 1}/{_MAX_RETRIES + 1}): {e}")
            if attempt < _MAX_RETRIES: await asyncio.sleep(0.5 * (attempt + 1))
        except Exception as e:
            last_err = str(e); logger.error(f"LLM元数据提取异常 (尝试 {attempt + 1}): {e}")
            if attempt < _MAX_RETRIES: await asyncio.sleep(1.0 * (attempt + 1))
    raise ValueError(f"元数据提取失败，已重试{_MAX_RETRIES}次: {last_err}")

async def import_from_document(db: AsyncSession, file_content: bytes | None = None, file_path: str | None = None, metadata: dict[str, Any] | None = None, created_by: int = _SYS_UID) -> dict[str, Any]:
    if file_content is None and file_path is None: logger.error("文档导入失败: 未提供 file_content 或 file_path"); raise ValueError("必须提供 file_content 或 file_path 参数")
    if file_content is not None: cb, fn = file_content, "uploaded_document.txt"; logger.info(f"[文档导入] 使用 file_content: size={len(cb)} bytes, source=内存, created_by={created_by}")
    elif file_path is not None:
        if not os.path.isfile(file_path): logger.error(f"[文档导入] 文件不存在: path={file_path}"); raise FileNotFoundError(f"文件不存在: {file_path}")
        with open(file_path, "rb") as f: cb = f.read()
        fn = os.path.basename(file_path); logger.info(f"[文档导入] 使用 file_path: path={file_path}, filename={fn}, size={len(cb)} bytes, created_by={created_by}")
    else: raise ValueError("必须提供 file_content 或 file_path 参数")
    w = _FileWrapper(cb, fn)
    try: et = await process_document(w); logger.info(f"[文档导入] 文档解析成功: filename={fn}, text_length={len(et)} chars")
    except Exception as e: logger.error(f"[文档导入] 文档解析失败: filename={fn}, error_type={type(e).__name__}, error={e}"); raise
    if not et or not et.strip(): logger.warning(f"[文档导入] 文档内容为空: filename={fn}, text_length={len(et) if et else 0}"); raise ValueError(f"文档内容为空，无法导入: {fn}")
    logger.info(f"[文档导入] 开始LLM元数据提取: filename={fn}, input_length={min(len(et), 8000)} chars")
    try: lm = await extract_metadata_with_llm(et); logger.info(f"[文档导入] LLM元数据提取成功: title={lm['title'][:50]}, category={lm['suggested_category']}, tags_count={len(lm.get('suggested_tags', []))}, concepts_count={len(lm.get('key_concepts', []))}")
    except Exception as e:
        logger.warning(f"[文档导入] LLM元数据提取失败，使用回退元数据: filename={fn}, error_type={type(e).__name__}, error={e}")
        lm = {"title": fn.rsplit(".", 1)[0][:100], "summary": et[:200].strip(), "key_concepts": [], "suggested_tags": [], "suggested_category": "other"}
        logger.info(f"[文档导入] 回退元数据: title={lm['title']}, summary_length={len(lm['summary'])} chars, category={lm['suggested_category']}")
    if metadata: logger.info(f"[文档导入] 应用用户自定义元数据覆盖: override_keys={list(metadata.keys())}"); lm.update(metadata)
    cat = await _resolve_category(lm["suggested_category"]); logger.info(f"[文档导入] 分类映射: suggested={lm['suggested_category']}, resolved={cat.value}")
    de = KnowledgeEntry(title=lm["title"], content=et, summary=lm["summary"], category=cat, status=EntryStatus.draft, source_type=SourceType.document_import, created_by=created_by)
    logger.info(f"[文档导入] 准备创建知识条目: title={de.title[:50]}, content_length={len(de.content)} chars, summary_length={len(de.summary or '')} chars, category={de.category.value}, source_type={de.source_type.value}, created_by={created_by}")
    try: db.add(de); await db.flush(); logger.info(f"[文档导入] 知识条目创建成功: entry_id={de.id}, title={de.title}, status={de.status.value}")
    except Exception as e: logger.error(f"[文档导入] 知识条目创建失败: title={de.title}, error_type={type(e).__name__}, error={e}"); raise
    tn = lm.get("suggested_tags", []); logger.info(f"[文档导入] 开始关联标签: entry_id={de.id}, tag_count={len(tn)}, tags={tn}")
    await _associate_tags(db, de.id, tn); logger.info(f"[文档导入] 标签关联完成: entry_id={de.id}, associated_tags={tn}")
    rm = {"title": lm["title"], "summary": lm["summary"], "key_concepts": lm.get("key_concepts", []), "suggested_tags": tn, "suggested_category": lm["suggested_category"]}
    logger.info(f"[文档导入] 导入完成: entry_id={de.id}, title={rm['title'][:50]}, category={rm['suggested_category']}, tags={tn}, concepts={rm['key_concepts']}")
    return {"entry_id": de.id, "extracted_metadata": rm}

async def import_from_case(db: AsyncSession, case_id: int) -> dict[str, Any]:
    cr = await db.execute(select(Case).where(Case.id == case_id)); c = cr.scalar_one_or_none()
    if not c: logger.error(f"[案件导入] 案件不存在: case_id={case_id}"); raise ValueError(f"案件不存在: case_id={case_id}")
    logger.info(f"[案件导入] 开始导入: case_id={case_id}, title={c.title}, status={c.status.value if c.status else 'N/A'}, has_description={bool(c.description and c.description.strip())}")
    if not c.title or not c.title.strip(): logger.error(f"[案件导入] 案件标题为空: case_id={case_id}"); raise ValueError(f"案件标题为空，无法导入: case_id={case_id}")
    dct = c.case_text or ""
    if not dct or not dct.strip(): logger.error(f"[案件导入] 案件文本内容为空: case_id={case_id}, title={c.title}"); raise ValueError(f"案件文本内容为空，无法导入: case_id={case_id}")
    logger.info(f"[案件导入] 案件文本解密成功: case_id={case_id}, text_length={len(dct)} chars")
    ar = await db.execute(select(Analysis).where(Analysis.case_id == case_id).order_by(Analysis.created_at.desc()).limit(1)); la = ar.scalar_one_or_none()
    cp = [dct]
    if la and la.result_json:
        try: ad = json.loads(la.result_json); at = json.dumps(ad, ensure_ascii=False, indent=2); cp.append("\n\n--- 案件分析结果 ---\n"); cp.append(at); logger.info(f"[案件导入] 分析结果已附着: case_id={case_id}, analysis_id={la.id}, analysis_mode={la.mode.value if la.mode else 'N/A'}, knowledge_score={la.knowledge_score}")
        except (json.JSONDecodeError, TypeError) as e: logger.warning(f"[案件导入] 分析结果JSON解析失败，使用原始文本: case_id={case_id}, analysis_id={la.id}, error={e}"); cp.append("\n\n--- 案件分析结果 ---\n"); cp.append(str(la.result_json))
    else: logger.info(f"[案件导入] 未找到分析结果: case_id={case_id}, content仅包含案件事实文本")
    fc = "".join(cp); logger.info(f"[案件导入] 内容组装完成: case_id={case_id}, total_length={len(fc)} chars, has_analysis={la is not None}")
    desc = c.description or ""; logger.info(f"[案件导入] 开始LLM元数据提取: case_id={case_id}, input_length={min(len(fc), 8000)} chars")
    try: lm = await extract_metadata_with_llm(fc[:8000]); logger.info(f"[案件导入] LLM元数据提取成功: case_id={case_id}, title={lm['title'][:50]}, tags_count={len(lm.get('suggested_tags', []))}")
    except Exception as e:
        logger.warning(f"[案件导入] LLM元数据提取失败，使用回退元数据: case_id={case_id}, error_type={type(e).__name__}, error={e}")
        lm = {"title": c.title[:100], "summary": (desc or dct)[:200].strip(), "key_concepts": [], "suggested_tags": [], "suggested_category": "case"}
        logger.info(f"[案件导入] 回退元数据: case_id={case_id}, title={lm['title']}, summary_length={len(lm['summary'])} chars")
    de = KnowledgeEntry(title=lm["title"], content=fc, summary=lm["summary"], category=EntryCategory.case, status=EntryStatus.draft, source_type=SourceType.case_conversion, source_id=case_id, created_by=c.created_by or _SYS_UID)
    logger.info(f"[案件导入] 准备创建知识条目: case_id={case_id}, title={de.title[:50]}, content_length={len(de.content)} chars, summary_length={len(de.summary or '')} chars, category={de.category.value}, source_type={de.source_type.value}, source_id={de.source_id}, created_by={de.created_by}")
    try: db.add(de); await db.flush(); logger.info(f"[案件导入] 知识条目创建成功: entry_id={de.id}, case_id={case_id}, title={de.title}, status={de.status.value}")
    except Exception as e: logger.error(f"[案件导入] 知识条目创建失败: case_id={case_id}, title={de.title}, error_type={type(e).__name__}, error={e}"); raise
    tn = lm.get("suggested_tags", [])
    if "案件" not in tn: tn.append("案件"); logger.debug(f"[案件导入] 自动追加默认标签 '案件': case_id={case_id}")
    logger.info(f"[案件导入] 开始关联标签: entry_id={de.id}, tag_count={len(tn)}, tags={tn}")
    await _associate_tags(db, de.id, tn); logger.info(f"[案件导入] 标签关联完成: entry_id={de.id}, associated_tags={tn}")
    rm = {"title": lm["title"], "summary": lm["summary"], "key_concepts": lm.get("key_concepts", []), "suggested_tags": tn, "suggested_category": "case"}
    logger.info(f"[案件导入] 导入完成: entry_id={de.id}, case_id={case_id}, title={rm['title'][:50]}, tags={tn}, concepts={rm['key_concepts']}")
    return {"entry_id": de.id, "extracted_metadata": rm}

async def batch_import_from_cases(db: AsyncSession, status: str = "completed") -> dict[str, Any]:
    from app.models.case import CaseStatus
    try: ts = CaseStatus(status)
    except ValueError: raise ValueError(f"无效的案件状态: '{status}'，有效状态: {[s.value for s in CaseStatus]}") from None
    cr = await db.execute(select(Case.id, Case.title, Case.case_text).where(Case.status == ts).order_by(Case.id)); cases = cr.all()
    if not cases: logger.info(f"没有找到状态为 '{status}' 的案件"); return BatchImportResult().to_dict()
    r = BatchImportResult(); tot = len(cases); logger.info(f"开始批量导入案件: total={tot}, status={status}")
    for idx, (cid, ct, cx) in enumerate(cases):
        if not ct or not cx: logger.warning(f"跳过数据不完整的案件: case_id={cid}"); r.skip_count += 1; r.skip_case_ids.append(cid); continue
        try: ir = await import_from_case(db, cid); r.success_count += 1; r.success_case_ids.append(cid); logger.info(f"案件导入成功: case_id={cid}, entry_id={ir.get('entry_id')}, 进度={idx + 1}/{tot}")
        except Exception as e: r.failure_count += 1; r.failure_case_ids.append(cid); r.errors.append({"case_id": cid, "case_title": ct, "error": str(e)}); logger.error(f"案件导入失败: case_id={cid}, error={e}, 进度={idx + 1}/{tot}")
    logger.info(f"批量案件导入完成: success={r.success_count}, failure={r.failure_count}, skip={r.skip_count}")
    return r.to_dict()

async def update_confidence(db: AsyncSession, entry_id: int, feedback: FeedbackType) -> KnowledgeEntry:
    _validate_entry_id(entry_id, "entry_id"); fb = _validate_feedback(feedback)
    r = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)); e = r.scalar_one_or_none()
    if e is None: raise LookupError(f"知识条目不存在: entry_id={entry_id}")
    step = AnalysisConfig.KNOWLEDGE_POSITIVE_FEEDBACK_STEP if fb == "positive" else -AnalysisConfig.KNOWLEDGE_NEGATIVE_FEEDBACK_STEP
    cc = e.confidence or 0.5; nc = max(0.0, min(1.0, cc + step))
    logger.info("信心评分调整: entry_id={}, feedback={}, old_confidence={:.4f}, new_confidence={:.4f}", entry_id, fb, cc, nc)
    try: e.confidence = nc; await db.flush(); return e
    except Exception as ex: logger.error(f"更新信心评分失败: entry_id={entry_id}, error={ex}"); raise RuntimeError(f"更新信心评分失败: {ex}") from ex

async def apply_decay(db: AsyncSession) -> dict[str, Any]:
    dc, st, bs = AnalysisConfig.KNOWLEDGE_DECAY_COEFFICIENT, AnalysisConfig.KNOWLEDGE_STALE_CONFIDENCE_THRESHOLD, AnalysisConfig.KNOWLEDGE_BATCH_SIZE
    stats = DecayStatistics()
    cr = await db.execute(select(func.count(KnowledgeEntry.id)).where(KnowledgeEntry.confidence.isnot(None), KnowledgeEntry.confidence > 0.0)); te = cr.scalar_one()
    if te == 0: logger.info("apply_decay: 无需衰减的条目（所有条目confidence为空或已为0）"); return stats.to_dict()
    logger.info("开始应用遗忘曲线衰减: 系数={}, 待处理条目={}", dc, te)
    dm: list[float] = []; off = 0
    try:
        while off < te:
            br = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.confidence.isnot(None), KnowledgeEntry.confidence > 0.0).order_by(KnowledgeEntry.id).offset(off).limit(bs)); b = list(br.scalars().all())
            for e in b:
                oc = e.confidence or 0.0; nc = max(0.0, oc * (1.0 - dc)); da = oc - nc; e.confidence = nc; stats.total_decayed += 1; dm.append(da)
                if nc < st:
                    wa = e.status in (EntryStatus.active, EntryStatus.draft)
                    if wa: e.status = EntryStatus.stale; stats.newly_stale += 1; logger.info("条目标记为stale: entry_id={}, confidence={:.4f}", e.id, nc)
            await db.flush(); off += len(b); logger.debug("衰减批次完成: offset={} / total={}", off, te)
        await db.flush()
        if dm: stats.avg_decay_magnitude = sum(dm) / len(dm); stats.min_decay = min(dm); stats.max_decay = max(dm)
        logger.info("遗忘曲线衰减完成: total={}, stale={}, avg={:.6f}, min={:.6f}, max={:.6f}", stats.total_decayed, stats.newly_stale, stats.avg_decay_magnitude, stats.min_decay, stats.max_decay)
        return stats.to_dict()
    except Exception as e: logger.error(f"apply_decay 执行失败: {e}"); raise RuntimeError(f"遗忘曲线衰减执行失败: {e}") from e

async def lint_knowledge_base(db: AsyncSession) -> dict[str, Any]:
    bs, od, cmc = AnalysisConfig.KNOWLEDGE_BATCH_SIZE, AnalysisConfig.KNOWLEDGE_OUTDATED_DAYS_THRESHOLD, AnalysisConfig.KNOWLEDGE_CONTRADICTION_MIN_CONFIDENCE
    rpt = LintReport(); rpt.timestamp = datetime.now(UTC).isoformat()
    cr = await db.execute(select(func.count(KnowledgeEntry.id))); te = cr.scalar_one(); rpt.scanned_entries = te
    logger.info("开始知识库质量扫描: 条目总数={}", te)
    if te == 0: logger.info("知识库为空，扫描完成"); return rpt.to_dict()
    try:
        bwi = await _detect_blank_wikilinks(db, te, bs); rpt.issues.extend(bwi)
        ci = await _detect_contradictions(db, cmc); rpt.issues.extend(ci)
        oi = await _detect_outdated_entries(db, od); rpt.issues.extend(oi)
        opi = await _detect_orphan_entries(db, te, bs); rpt.issues.extend(opi)
        rpt.total_issues = len(rpt.issues)
        logger.info("知识库质量扫描完成: issues={}, blank_wikilinks={}, contradictions={}, outdated={}, orphan={}", rpt.total_issues, len(bwi), len(ci), len(oi), len(opi))
        return rpt.to_dict()
    except Exception as e: logger.error(f"lint_knowledge_base 扫描失败: {e}"); raise RuntimeError(f"知识库质量扫描失败: {e}") from e

async def _detect_blank_wikilinks(db: AsyncSession, te: int, bs: int) -> list[LintIssue]:
    atr = await db.execute(select(KnowledgeEntry.title)); et = {r[0] for r in atr.all() if r[0]}
    iss: list[LintIssue] = []; siwa = set(); off = 0
    while off < te:
        br = await db.execute(select(KnowledgeEntry.id, KnowledgeEntry.content).order_by(KnowledgeEntry.id).offset(off).limit(bs)); b = br.all()
        for r in b:
            eid, c = r[0], r[1] or ""; rt = _extract_wikilinks(c)
            if not rt: continue
            mt = rt - et - {""}
            if mt: siwa.add(eid); iss.append(LintIssue(issue_type="blank_wikilinks", affected_entry_ids=[eid], description=f"知识条目(id={eid})内容中存在指向不存在条目的wikilinks: {', '.join(sorted(mt))}", suggestion="请检查引用的条目标题是否正确拼写，或创建对应的知识条目。"))
        off += len(b)
    if siwa: logger.info("发现 {} 个条目存在 {} 个空白wikilinks问题", len(siwa), len(iss))
    return iss

async def _detect_contradictions(db: AsyncSession, mc: float) -> list[LintIssue]:
    r = await db.execute(select(EntryRelation.source_entry_id, EntryRelation.target_entry_id).where(EntryRelation.relation_type == RelationType.contradicts)); cr = r.all()
    if not cr: return []
    aci = set()
    for rel in cr: aci.add(rel[0]); aci.add(rel[1])
    cfr = await db.execute(select(KnowledgeEntry.id, KnowledgeEntry.confidence).where(KnowledgeEntry.id.in_(list(aci)), KnowledgeEntry.confidence >= mc)); hci = {r[0] for r in cfr.all()}
    iss: list[LintIssue] = []
    for sid, tid in cr:
        if sid in hci and tid in hci: iss.append(LintIssue(issue_type="contradiction", affected_entry_ids=[sid, tid], description=f"知识条目(id={sid})与条目(id={tid})存在矛盾关系(contradicts)，且双方信心评分均 >= {mc}，内容可能存在冲突。", suggestion="请人工审查这两个条目的内容，确认矛盾是否真实存在。若一方正确，请更新错误方的内容并降低其信心评分；若矛盾已解决，请移除contradicts关系。"))
    if iss: logger.info("发现 {} 个高信心矛盾条目组", len(iss))
    return iss

async def _detect_outdated_entries(db: AsyncSession, od: int) -> list[LintIssue]:
    cd = datetime.now(UTC) - timedelta(days=od)
    r = await db.execute(select(KnowledgeEntry.id, KnowledgeEntry.title).where(KnowledgeEntry.last_verified_at.isnot(None), KnowledgeEntry.last_verified_at < cd, KnowledgeEntry.status != EntryStatus.archived)); oe = r.all()
    if not oe: return []
    oi = [r[0] for r in oe]
    iss = [LintIssue(issue_type="outdated_content", affected_entry_ids=oi, description=f"发现 {len(oi)} 个知识条目的最后验证时间超过 {od} 天，内容可能已过时。受影响条目ID: {oi}", suggestion="请逐一审查这些条目的内容是否仍然准确有效，更新内容后设置新的 last_verified_at 时间戳。若确认不再使用，请将其状态设为 archived。")]
    logger.info("发现 {} 个过时条目（>{}天）", len(oi), od)
    return iss

async def _detect_orphan_entries(db: AsyncSession, te: int, bs: int) -> list[LintIssue]:
    or_ = await db.execute(select(EntryRelation.source_entry_id).distinct()); oi = {r[0] for r in or_.all()}
    ir = await db.execute(select(EntryRelation.target_entry_id).distinct()); ii = {r[0] for r in ir.all()}
    ci = oi | ii; opids: list[int] = []; off = 0
    while off < te:
        br = await db.execute(select(KnowledgeEntry.id).where(KnowledgeEntry.status != EntryStatus.archived).order_by(KnowledgeEntry.id).offset(off).limit(bs)); bi = {r[0] for r in br.all()}
        for eid in sorted(bi):
            if eid not in ci: opids.append(eid)
        off += bs
    if not opids: return []
    iss = [LintIssue(issue_type="orphan_entry", affected_entry_ids=opids, description=f"发现 {len(opids)} 个孤立知识条目，它们没有任何入站或出站的关联关系。受影响条目ID: {opids}", suggestion="请审查这些条目是否需要与其他条目建立关联关系。可使用自动关联功能(find_related_entries / auto_link_entries)为孤立条目建立语义关系。如果条目确实独立且不需要关联，可忽略此提示。")]
    logger.info("发现 {} 个孤立条目", len(opids))
    return iss

async def supersede_entry(db: AsyncSession, old_entry_id: int, new_entry_id: int, operated_by: int, reason: str | None = None) -> dict[str, Any]:
    _validate_entry_id(old_entry_id, "old_entry_id"); _validate_entry_id(new_entry_id, "new_entry_id")
    if old_entry_id == new_entry_id: raise ValueError("新旧条目ID不能相同，old_entry_id 与 new_entry_id 必须不同")
    if not isinstance(operated_by, int) or operated_by <= 0: raise ValueError(f"无效的operated_by: {operated_by}，必须为正整数")
    oe = (await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == old_entry_id))).scalar_one_or_none()
    if oe is None: raise LookupError(f"旧知识条目不存在: id={old_entry_id}")
    ne = (await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == new_entry_id))).scalar_one_or_none()
    if ne is None: raise LookupError(f"新知识条目不存在: id={new_entry_id}")
    logger.info("开始版本更替: old_entry_id={}, new_entry_id={}, operated_by={}, reason={}", old_entry_id, new_entry_id, operated_by, reason or "未指定")
    rc = 0; ts = datetime.now(UTC).isoformat()
    try:
        er = (await db.execute(select(EntryRelation).where(EntryRelation.source_entry_id == new_entry_id, EntryRelation.target_entry_id == old_entry_id, EntryRelation.relation_type == RelationType.supersedes))).scalar_one_or_none()
        if er is not None: logger.info("supersedes关系已存在: source={}, target={}", new_entry_id, old_entry_id)
        else: db.add(EntryRelation(source_entry_id=new_entry_id, target_entry_id=old_entry_id, relation_type=RelationType.supersedes)); await db.flush(); logger.info("已创建supersedes关系: source={}, target={}", new_entry_id, old_entry_id)
        oe.status = EntryStatus.archived; await db.flush(); logger.info("旧条目标记为archived: entry_id={}", old_entry_id)
        ir = await db.execute(select(EntryRelation).where(EntryRelation.target_entry_id == old_entry_id, EntryRelation.relation_type != RelationType.supersedes)); irs = list(ir.scalars().all())
        for rel in irs: rel.target_entry_id = new_entry_id; rc += 1
        if rc > 0: await db.flush(); logger.info("已重定向 {} 条关联关系到新条目: new_entry_id={}", rc, new_entry_id)
        lm = f"[版本更替] old_entry_id={old_entry_id} -> new_entry_id={new_entry_id}, operated_by={operated_by}, reason='{reason or '未指定'}', redirected_relations={rc}, timestamp={ts}"
        logger.info(lm)
        return {"old_entry_id": old_entry_id, "new_entry_id": new_entry_id, "old_entry_status": oe.status.value, "redirected_relations": rc, "operated_by": operated_by, "reason": reason or "未指定", "timestamp": ts}
    except Exception as e: logger.error(f"版本更替失败: old={old_entry_id}, new={new_entry_id}, error={e}"); raise RuntimeError(f"知识条目版本更替失败: {e}") from e

class KnowledgeLifecycleScheduler:
    def __init__(self, config: ScheduleConfig | None = None) -> None:
        self._config = config or ScheduleConfig(); self._decay_task: asyncio.Task[Any] | None = None; self._lint_task: asyncio.Task[Any] | None = None; self._running = False; self._last_decay_run: str | None = None; self._last_lint_run: str | None = None
    @property
    def is_running(self) -> bool: return self._running
    @property
    def status(self) -> dict[str, Any]: return {"running": self._running, "decay_enabled": self._config.decay_enabled, "lint_enabled": self._config.lint_enabled, "decay_interval_seconds": self._config.decay_interval, "lint_interval_seconds": self._config.lint_interval, "last_decay_run": self._last_decay_run, "last_lint_run": self._last_lint_run}
    async def start(self) -> None:
        if self._running: logger.warning("调度器已在运行中，忽略重复启动"); return
        self._running = True; logger.info("知识生命周期调度器启动: decay_interval={}s, lint_interval={}s", self._config.decay_interval, self._config.lint_interval)
        if self._config.decay_enabled: self._decay_task = asyncio.create_task(self._decay_loop())
        if self._config.lint_enabled: self._lint_task = asyncio.create_task(self._lint_loop())
    async def stop(self) -> None:
        self._running = False
        for t in (self._decay_task, self._lint_task):
            if t and not t.done(): t.cancel()
            with contextlib.suppress(asyncio.CancelledError): await t
        self._decay_task = None; self._lint_task = None; logger.info("知识生命周期调度器已停止")
    async def trigger_decay(self) -> dict[str, Any]:
        logger.info("手动触发遗忘曲线衰减...")
        try:
            async with get_async_db_session() as db: r = await apply_decay(db)
            self._last_decay_run = datetime.now(UTC).isoformat(); return r  # type: ignore
        except Exception as e: logger.error(f"手动触发decay失败: {e}"); raise
    async def trigger_lint(self) -> dict[str, Any]:
        logger.info("手动触发知识库质量扫描...")
        try:
            async with get_async_db_session() as db: r = await lint_knowledge_base(db)
            self._last_lint_run = datetime.now(UTC).isoformat(); return r  # type: ignore
        except Exception as e: logger.error(f"手动触发lint失败: {e}"); raise
    async def _decay_loop(self) -> None:
        while self._running:
            try:
                logger.info("定时任务: 开始执行遗忘曲线衰减...")
                async with get_async_db_session() as db: r = await apply_decay(db)
                self._last_decay_run = datetime.now(UTC).isoformat(); logger.info("定时decay完成: {}", r)
            except asyncio.CancelledError: logger.info("衰减定时任务被取消"); break
            except Exception as e: logger.error(f"定时decay执行异常: {e}")
            await asyncio.sleep(self._config.decay_interval)
    async def _lint_loop(self) -> None:
        while self._running:
            try:
                logger.info("定时任务: 开始执行知识库质量扫描...")
                async with get_async_db_session() as db: r = await lint_knowledge_base(db)
                self._last_lint_run = datetime.now(UTC).isoformat(); logger.info("定时lint完成: total_issues={}", r.get("total_issues", 0))
            except asyncio.CancelledError: logger.info("扫描定时任务被取消"); break
            except Exception as e: logger.error(f"定时lint执行异常: {e}")
            await asyncio.sleep(self._config.lint_interval)

async def run_decay_sync() -> dict[str, Any]:
    async with get_async_db_session() as db: return await apply_decay(db)  # type: ignore

async def run_lint_sync() -> dict[str, Any]:
    async with get_async_db_session() as db: return await lint_knowledge_base(db)  # type: ignore
