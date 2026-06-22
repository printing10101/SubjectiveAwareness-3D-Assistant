"""知识图谱分析服务."""
from __future__ import annotations
import hashlib, json, re, time
from collections import deque
from typing import Any
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_async_db_session
from app.models.entry_relation import EntryRelation, RelationType
from app.models.knowledge_entry import EntryCategory, EntryStatus, KnowledgeEntry
from app.models.legal_rule import LegalRule
from app.services.ollama_client import OllamaClient, get_client
from app.services.prompt import KNOWLEDGE_QA_PROMPT, SUGGEST_RELATED_ENTRIES_PROMPT
from app.utils.cache import get_unified_cache

ALLOWED_RULE_FIELDS = {"rule_id", "name", "description", "source_law", "article", "conditions", "conclusion", "evidence_types", "weight"}
CATEGORY_COLORS = {"law": "#4F46E5", "methodology": "#059669", "case": "#D97706", "other": "#6B7280"}
RELATION_LINE_STYLES = {"references": "solid", "contradicts": "dashed", "supersedes": "dotted", "extends": "solid", "depends_on": "dashed"}
RELATION_LABELS = {"references": "引用", "contradicts": "矛盾", "supersedes": "取代", "extends": "扩展", "depends_on": "依赖"}
_LLM_REL_MAP = {"references": RelationType.references, "contradicts": RelationType.contradicts, "supersedes": RelationType.supersedes, "extends": RelationType.extends, "depends_on": RelationType.depends_on, "similar": RelationType.references, "supports": RelationType.depends_on}
_STOP_WORDS = frozenset({"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些", "什么", "怎么", "如何", "为什么", "哪", "吗", "呢", "啊", "吧", "哦", "可以", "应该", "需要", "能够", "可能", "已经", "还是", "因为", "所以", "但是", "如果", "虽然", "而且", "或者", "以及", "关于", "对于", "根据", "通过", "经过", "由于", "为了", "除了", "the", "a", "an", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "can", "could", "should", "may", "might", "shall", "must", "of", "in", "to", "for", "with", "on", "at", "from", "by"})
_CACHE_TTL, _MAX_SNIPPET, _MAX_EXISTING = 300, 500, 50
_DEF_SEARCH_LIMIT, _DEF_SNIPPET_MAX, _MAX_PREVIEW, _MIN_VALID = 5, 200, 1500, 0.5

def _sanitize_rule(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if k in ALLOWED_RULE_FIELDS}

def _cache_key(prefix: str, params: dict[str, Any]) -> str:
    return f"kg:{prefix}:{hashlib.sha256(json.dumps(params, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]}"

def _node_size(conf: float | None, rel_cnt: int) -> float:
    return round(min(max(10.0 + (conf or 0.5) * 8.0 + min(rel_cnt * 0.8, 12.0), 8.0), 30.0), 1)

def _entry_to_node(e: KnowledgeEntry) -> dict[str, Any]:
    tags = [t.name for t in e.tags] if e.tags else []
    rel_cnt = len(e.outgoing_relations) + len(e.incoming_relations)
    cat = e.category.value if isinstance(e.category, EntryCategory) else str(e.category)
    return {"id": e.id, "label": e.title, "category": cat, "properties": {"status": e.status.value if e.status else "draft", "confidence": e.confidence, "summary": e.summary, "tags": tags, "relation_count": rel_cnt, "updated_at": e.updated_at.isoformat() if e.updated_at else None}, "color": CATEGORY_COLORS.get(cat, "#6B7280"), "size": _node_size(e.confidence, rel_cnt)}

def _rel_to_edge(r: EntryRelation) -> dict[str, Any]:
    t = r.relation_type.value if isinstance(r.relation_type, RelationType) else str(r.relation_type)
    return {"source": r.source_entry_id, "target": r.target_entry_id, "type": t, "label": RELATION_LABELS.get(t, t), "lineStyle": RELATION_LINE_STYLES.get(t, "solid")}

def _trunc(s: str, mx: int = _MAX_SNIPPET) -> str:
    return s if len(s) <= mx else s[:mx] + "..."

def _map_rel_type(s: str) -> RelationType:
    return _LLM_REL_MAP.get(s, RelationType.references)

async def get_legal_rules(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[LegalRule]:
    return list((await db.execute(select(LegalRule).offset(skip).limit(limit))).scalars().all())

async def get_legal_rule(db: AsyncSession, rule_id: int) -> LegalRule | None:
    return (await db.execute(select(LegalRule).where(LegalRule.id == rule_id))).scalar_one_or_none()

async def create_legal_rule(db: AsyncSession, rule_data: dict[str, Any]) -> LegalRule:
    r = LegalRule(**_sanitize_rule(rule_data))
    try:
        db.add(r); await db.commit(); await db.refresh(r); return r
    except Exception as e:
        await db.rollback(); logger.error(f"创建法律规则失败: {e}"); raise HTTPException(status_code=500, detail="创建法律规则失败") from e

async def update_legal_rule(db: AsyncSession, rule_id: int, rule_data: dict[str, Any]) -> LegalRule:
    r = await get_legal_rule(db, rule_id)
    if not r: raise HTTPException(status_code=404, detail="Rule not found")
    try:
        for k, v in _sanitize_rule(rule_data).items(): setattr(r, k, v)
        await db.commit(); await db.refresh(r); return r
    except Exception as e:
        await db.rollback(); logger.error(f"更新法律规则失败: rule_id={rule_id}, error={e}"); raise HTTPException(status_code=500, detail="更新法律规则失败") from e

async def delete_legal_rule(db: AsyncSession, rule_id: int) -> bool:
    r = await get_legal_rule(db, rule_id)
    if not r: raise HTTPException(status_code=404, detail="Rule not found")
    try:
        await db.delete(r); await db.commit(); return True
    except Exception as e:
        await db.rollback(); logger.error(f"删除法律规则失败: rule_id={rule_id}, error={e}"); raise HTTPException(status_code=500, detail="删除法律规则失败") from e

async def get_graph_data(db: AsyncSession, category_filters: list[str] | None = None, tag_filters: list[str] | None = None, relation_type_filters: list[str] | None = None, search_query: str | None = None, entry_ids: list[int] | None = None) -> dict[str, Any]:
    cp = {"category_filters": sorted(category_filters) if category_filters else None, "tag_filters": sorted(tag_filters) if tag_filters else None, "relation_type_filters": sorted(relation_type_filters) if relation_type_filters else None, "search_query": search_query, "entry_ids": sorted(entry_ids) if entry_ids else None}
    ck = _cache_key("graph_data", cp); cache = get_unified_cache()
    if (c := await cache.get(ck)) is not None: return c
    stmt = select(KnowledgeEntry).options(selectinload(KnowledgeEntry.tags), selectinload(KnowledgeEntry.outgoing_relations).selectinload(EntryRelation.target_entry), selectinload(KnowledgeEntry.incoming_relations).selectinload(EntryRelation.source_entry))
    if entry_ids: stmt = stmt.where(KnowledgeEntry.id.in_(entry_ids))
    if category_filters: stmt = stmt.where(KnowledgeEntry.category.in_(category_filters))
    if search_query: stmt = stmt.where(KnowledgeEntry.title.ilike(f"%{search_query}%"))
    entries = list((await db.execute(stmt)).scalars().all())
    if tag_filters: entries = [e for e in entries if any(t.name in tag_filters for t in e.tags)]
    eids = {e.id for e in entries}; nodes = [_entry_to_node(e) for e in entries]
    rstmt = select(EntryRelation).options(selectinload(EntryRelation.source_entry), selectinload(EntryRelation.target_entry))
    if relation_type_filters: rstmt = rstmt.where(EntryRelation.relation_type.in_(relation_type_filters))
    rels = list((await db.execute(rstmt)).scalars().all())
    edges, seen = [], set()
    for r in rels:
        if r.source_entry_id in eids and r.target_entry_id in eids:
            ek = (r.source_entry_id, r.target_entry_id, r.relation_type.value)
            if ek not in seen: seen.add(ek); edges.append(_rel_to_edge(r))
    gd = {"nodes": nodes, "edges": edges}; await cache.set(ck, gd, _CACHE_TTL); return gd

async def get_node_neighbors(db: AsyncSession, entry_id: int, depth: int = 1) -> dict[str, Any]:
    ck = _cache_key("neighbors", {"entry_id": entry_id, "depth": depth}); cache = get_unified_cache()
    if (c := await cache.get(ck)) is not None: return c
    center = (await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id).options(selectinload(KnowledgeEntry.tags), selectinload(KnowledgeEntry.outgoing_relations), selectinload(KnowledgeEntry.incoming_relations)))).scalar_one_or_none()
    if not center: return {"nodes": [], "edges": []}
    visited, cur, all_e, all_r = {entry_id}, {entry_id}, {entry_id: center}, []
    for _ in range(depth):
        nxt, lr = set(), []
        for nid in cur:
            for r in (await db.execute(select(EntryRelation).where((EntryRelation.source_entry_id == nid) | (EntryRelation.target_entry_id == nid)))).scalars().all():
                nb = r.target_entry_id if r.source_entry_id == nid else r.source_entry_id
                if nb not in visited:
                    visited.add(nb); nxt.add(nb)
                    et = (r.source_entry_id, r.target_entry_id, str(r.relation_type.value))
                    if et not in {(x.source_entry_id, x.target_entry_id, str(x.relation_type.value)) for x in lr}: lr.append(r)
        if nxt:
            for e in (await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id.in_(list(nxt))).options(selectinload(KnowledgeEntry.tags)))).scalars().all(): all_e[e.id] = e
        all_r.extend(lr); cur = nxt
    res = {"nodes": [_entry_to_node(e) for e in all_e.values()], "edges": [_rel_to_edge(r) for r in all_r]}
    await cache.set(ck, res, _CACHE_TTL); return res

async def get_shortest_path(db: AsyncSession, source_id: int, target_id: int) -> dict[str, Any]:
    ck = _cache_key("shortest_path", {"source_id": source_id, "target_id": target_id}); cache = get_unified_cache()
    if (c := await cache.get(ck)) is not None: return c
    if source_id == target_id:
        e = (await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == source_id).options(selectinload(KnowledgeEntry.tags)))).scalar_one_or_none()
        return {"path_nodes": [_entry_to_node(e)] if e else [], "path_edges": [], "path_length": 0}
    adj = {}
    for r in (await db.execute(select(EntryRelation))).scalars().all():
        adj.setdefault(r.source_entry_id, []).append((r.target_entry_id, r)); adj.setdefault(r.target_entry_id, []).append((r.source_entry_id, r))
    if source_id not in adj or target_id not in adj: return {"path_nodes": [], "path_edges": [], "path_length": -1}
    q, vis, par = deque([source_id]), {source_id}, {source_id: None}
    while q:
        cur = q.popleft()
        if cur == target_id: break
        for nb, r in adj.get(cur, []):
            if nb not in vis: vis.add(nb); par[nb] = (cur, r); q.append(nb)
    if target_id not in par: return {"path_nodes": [], "path_edges": [], "path_length": -1}
    pids, pedges, cur = [], [], target_id
    while cur is not None and cur in par:
        pids.append(cur); pi = par[cur]
        if pi is not None: pedges.append(_rel_to_edge(pi[1]))
        cur = pi[0] if pi else (None if cur == source_id else par.get(cur, (None,))[0])
    pids.reverse(); emap = {e.id: e for e in (await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id.in_(pids)).options(selectinload(KnowledgeEntry.tags)))).scalars().all()}
    pedges.reverse(); res = {"path_nodes": [_entry_to_node(emap[n]) for n in pids if n in emap], "path_edges": pedges, "path_length": len(pids) - 1}
    await cache.set(ck, res, _CACHE_TTL); return res

async def get_graph_data_public(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    p = filters or {}
    async with get_async_db_session() as db: return await get_graph_data(db, **{k: p.get(k) for k in ["category_filters", "tag_filters", "relation_type_filters", "search_query", "entry_ids"]})

async def get_node_neighbors_public(entry_id: int, depth: int = 1) -> dict[str, Any]:
    async with get_async_db_session() as db: return await get_node_neighbors(db, entry_id, depth)

async def get_shortest_path_public(source_id: int, target_id: int) -> dict[str, Any]:
    async with get_async_db_session() as db: return await get_shortest_path(db, source_id, target_id)

async def find_related_entries(db: AsyncSession, entry_id: int, top_k: int = 5) -> list[dict[str, Any]]:
    if not isinstance(entry_id, int) or entry_id <= 0: raise ValueError(f"无效的条目ID: {entry_id}")
    tgt = (await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))).scalar_one_or_none()
    if not tgt: raise LookupError(f"知识条目不存在: entry_id={entry_id}")
    existing = list((await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id != entry_id).limit(_MAX_EXISTING))).scalars().all())
    if not existing: return []
    estr = "\n".join(f"- ID: {e.id}, 标题: {e.title}, 分类: {e.category.value if e.category else 'unknown'}, 摘要: {e.summary or '无摘要'}" for e in existing)
    prompt = SUGGEST_RELATED_ENTRIES_PROMPT.format(entry_title=tgt.title, entry_category=tgt.category.value if tgt.category else "unknown", entry_summary=tgt.summary or "无摘要", entry_content_snippet=_trunc(tgt.content), existing_entries=estr, top_k=top_k)
    try:
        data = await get_client().generate_json(prompt, field="related_entries")
        raw = data if isinstance(data, list) else data.get("related_entries", []) if isinstance(data, dict) else []
    except Exception as e:
        logger.error(f"LLM推荐相关知识条目失败: entry_id={entry_id}, error={e}"); return []
    if not raw: return []
    valid = {e.id for e in existing}; res = []
    for it in raw:
        if not isinstance(it, dict): continue
        rid = it.get("entry_id")
        if not isinstance(rid, int) or rid <= 0 or rid not in valid: continue
        sim = it.get("similarity", 0.0)
        if not isinstance(sim, (int, float)) or sim < 0 or sim > 1: sim = 0.0
        re_ = next((e for e in existing if e.id == rid), None)
        res.append({"entry_id": rid, "title": re_.title if re_ else "", "relation_type": it.get("relation_type", "similar"), "similarity": round(float(sim), 4), "reason": it.get("reason", "")})
    res.sort(key=lambda x: x["similarity"], reverse=True); return res[:top_k]

async def auto_link_entries(db: AsyncSession, entry_id: int) -> int:
    if not isinstance(entry_id, int) or entry_id <= 0: raise ValueError(f"无效的条目ID: {entry_id}")
    if not (await db.execute(select(KnowledgeEntry.id).where(KnowledgeEntry.id == entry_id))).scalar_one_or_none(): raise LookupError(f"知识条目不存在: entry_id={entry_id}")
    recs = await find_related_entries(db, entry_id, top_k=5)
    if not recs: return 0
    cnt = 0
    for r in recs:
        tid, rts = r["entry_id"], r["relation_type"]; rt = _map_rel_type(rts)
        if await db.execute(select(EntryRelation).where(EntryRelation.source_entry_id == entry_id, EntryRelation.target_entry_id == tid)).scalar_one_or_none(): continue
        try: db.add(EntryRelation(source_entry_id=entry_id, target_entry_id=tid, relation_type=rt)); cnt += 1
        except Exception as e: logger.error(f"创建关联关系失败: source={entry_id}, target={tid}, error={e}")
    try: await db.commit()
    except Exception as e: await db.rollback(); logger.error(f"提交关联关系事务失败: entry_id={entry_id}, error={e}"); raise
    return cnt

async def build_knowledge_graph(db: AsyncSession) -> dict[str, list[dict[str, Any]]]:
    entries = list((await db.execute(select(KnowledgeEntry))).scalars().all())
    rels = list((await db.execute(select(EntryRelation))).scalars().all())
    return {"nodes": [{"id": e.id, "title": e.title, "category": e.category.value if e.category else "unknown"} for e in entries], "edges": [{"source": r.source_entry_id, "target": r.target_entry_id, "type": r.relation_type.value} for r in rels]}

async def traverse_graph(db: AsyncSession, start_entry_id: int, relation_types: list[str] | None = None, max_depth: int = 3) -> list[dict[str, Any]]:
    if not isinstance(start_entry_id, int) or start_entry_id <= 0: raise ValueError(f"无效的起始条目ID: {start_entry_id}")
    if max_depth <= 0: raise ValueError(f"遍历深度必须大于0: max_depth={max_depth}")
    start = (await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == start_entry_id))).scalar_one_or_none()
    if not start: raise LookupError(f"起始知识条目不存在: start_entry_id={start_entry_id}")
    vt = set(relation_types) if relation_types else None; adj = {}
    for r in (await db.execute(select(EntryRelation))).scalars().all():
        rt = r.relation_type.value
        if vt and rt not in vt: continue
        adj.setdefault(r.source_entry_id, []).append((r.target_entry_id, rt)); adj.setdefault(r.target_entry_id, []).append((r.source_entry_id, rt))
    emap = {e.id: e for e in (await db.execute(select(KnowledgeEntry))).scalars().all()}
    vis, q, res = {start_entry_id}, deque([(start_entry_id, 0, [])]), []
    if e := emap.get(start_entry_id): res.append({"entry_id": start_entry_id, "title": e.title, "category": e.category.value if e.category else "unknown", "depth": 0, "path": []})
    while q:
        cid, d, p = q.popleft()
        if d >= max_depth: continue
        for nb, rt in adj.get(cid, []):
            if nb in vis: continue
            vis.add(nb); np = list(p) + [(cid, rt)]
            if ne := emap.get(nb): res.append({"entry_id": nb, "title": ne.title, "category": ne.category.value if ne.category else "unknown", "depth": d + 1, "path": np})
            q.append((nb, d + 1, np))
    return res

class KnowledgeQAService:
    def __init__(self, db: AsyncSession, ollama_client: OllamaClient | None = None) -> None:
        self.db, self._ollama = db, ollama_client

    @property
    def ollama(self) -> OllamaClient:
        if self._ollama is None: self._ollama = get_client()
        return self._ollama

    def _extract_keywords(self, q: str) -> list[str]:
        segs = re.split(r'[，。！？、；：""''（）【】《》\s,.!?;:()\[\]{}]+', q); kws = []
        for s in segs:
            s = s.strip()
            if not s: continue
            for w in re.findall(r"[\u4e00-\u9fff]{2,}", s):
                if w not in _STOP_WORDS: kws.append(w)
            for w in re.findall(r"[a-zA-Z]{2,}", s):
                if w.lower() not in _STOP_WORDS: kws.append(w)
        seen = set(); return [k for k in kws if not (k in seen or seen.add(k))]

    def _build_search_query(self, kws: list[str]) -> str:
        if not kws: raise ValueError("无法从问题中提取有效关键词")
        return " ".join(kws[:3])

    def _compute_relevance(self, fts: float, conf: float | None, kwc: int) -> float:
        return fts * (2.0 - conf if conf is not None else 1.0) * (1.0 / max(kwc, 1))

    def _extract_snippet(self, content: str, q: str) -> str:
        kws = self._extract_keywords(q); cl, bp = content.lower(), -1
        for kw in kws:
            if (p := cl.find(kw.lower())) != -1: bp = max(p - 50, 0); break
        s, e = max(bp, 0), min(max(bp, 0) + _DEF_SNIPPET_MAX, len(content)); sn = content[s:e].strip()
        if s > 0: sn = "..." + sn
        if e < len(content): sn = sn + "..."
        return sn

    async def search_for_context(self, q: str) -> list[dict[str, Any]]:
        from app.services.knowledge.repository import ensure_fts_table, search_entries, get_entry
        await ensure_fts_table(self.db); kws = self._extract_keywords(q)
        if not kws: raise ValueError("无法从问题中提取有效关键词，请提供更具体的问题")
        sq = self._build_search_query(kws)
        try: fts = await search_entries(self.db, sq, status=EntryStatus.active, limit=_DEF_SEARCH_LIMIT)
        except Exception as e: logger.error("知识库搜索异常: question={}, error={}", q, e); raise RuntimeError(f"知识库搜索服务暂时不可用: {e}") from e
        if not fts: return []
        ctx = []
        for r in fts:
            eid = r["entry_id"]
            try: e = await get_entry(self.db, eid)
            except Exception as ex: logger.warning("获取知识条目失败: entry_id={}, error={}", eid, ex); continue
            if e is None or not e.content: continue
            ct, sn = e.content, self._extract_snippet(e.content, q); kwc = sum(1 for kw in kws if kw.lower() in ct.lower())
            ctx.append({"entry_id": eid, "title": e.title, "content": ct, "relevance_score": round(self._compute_relevance(float(r.get("score", 1.0)), e.confidence, kwc), 4), "snippet": sn})
        ctx.sort(key=lambda x: x["relevance_score"]); return ctx

    def _format_entries(self, entries: list[dict[str, Any]]) -> str:
        if not entries: return "（未找到相关知识点）"
        parts = []
        for i, e in enumerate(entries, 1):
            t, c = e.get("title", "未知标题"), e.get("content", "")
            if len(c) > _MAX_PREVIEW: c = c[:_MAX_PREVIEW] + "..."
            parts.append(f"【条目{i} - {t}】\n{c}")
        return "\n\n---\n\n".join(parts)

    def _compute_confidence(self, sources: list[dict[str, Any]], fts: list[dict[str, Any]]) -> float:
        if not sources: return 0.0
        base = min(len(sources) / _DEF_SEARCH_LIMIT, 1.0); fm = {r["entry_id"]: float(r.get("score", 1.0)) for r in fts}
        avg = sum(1.0 / max(fm.get(s.get("entry_id", -1), 1.0), 0.01) for s in sources); avg = min(avg / len(sources), 1.0) if sources else 0.0
        return max(0.0, min(round(base * 0.4 + avg * 0.6, 4), 1.0))

    async def answer_question(self, q: str, context_entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        from app.services.knowledge.repository import search_entries
        if not q or not q.strip(): raise ValueError("问题不能为空")
        q, st = q.strip(), time.perf_counter()
        if context_entries is not None:
            for e in context_entries:
                if not all(k in e for k in ("entry_id", "title", "content")): raise ValueError("context_entries 每项必须包含 entry_id、title 和 content 字段")
            sc = context_entries
        else:
            try: sc = await self.search_for_context(q)
            except (ValueError, RuntimeError): raise
            except Exception as e: logger.error("搜索上下文失败: question={}, error={}", q, e); raise RuntimeError(f"知识库搜索失败: {e}") from e
        try: fts = await search_entries(self.db, self._build_search_query(self._extract_keywords(q) or [q]), status=EntryStatus.active, limit=_DEF_SEARCH_LIMIT)
        except Exception as e: logger.warning("FTS搜索异常，继续使用上下文结果: error={}", e); fts = [{"entry_id": e["entry_id"], "score": 1.0, "title": e["title"]} for e in sc]
        fe = self._format_entries(sc); prompt = KNOWLEDGE_QA_PROMPT.format(user_question=q, relevant_entries=fe)
        try: ans = await self.ollama.generate(prompt=prompt, temperature=0.3, dynamic_timeout=True)
        except Exception as e: logger.error("LLM调用失败: question={}, error={}", q, e); raise RuntimeError(f"AI模型调用失败，请稍后重试: {e}") from e
        src = [{"entry_id": e["entry_id"], "title": e["title"], "snippet": e.get("snippet", self._extract_snippet(e.get("content", ""), q))} for e in sc]
        conf = self._compute_confidence(src, fts); em = (time.perf_counter() - st) * 1000
        logger.info("问答处理完成: question={}, sources={}, confidence={}, elapsed={:.1f}ms", q[:50], len(src), conf, em)
        if em > 3000.0: logger.warning("问答处理耗时超标: {:.1f}ms > {:.0f}ms", em, 3000.0)
        return {"answer": ans, "sources": src, "confidence": conf}

    async def validate_answer_with_sources(self, answer: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
        from app.services.knowledge.repository import get_entry
        if not answer or not answer.strip(): raise ValueError("回答不能为空")
        if not sources: raise ValueError("来源列表不能为空")
        vd, sc, ts, fs, rs = [], [], len(sources), 0, 0
        for s in sources:
            eid, st, ex, ec = s.get("entry_id", -1), s.get("title", "未知"), False, ""
            try:
                e = await get_entry(self.db, eid)
                if e is not None: ex, ec = True, e.content or ""; sc.append({"entry_id": eid, "exists": True, "relevant": False, "title": e.title})
                else: sc.append({"entry_id": eid, "exists": False, "relevant": False, "title": st}); vd.append(f"来源条目 (id={eid}, title={st}) 在知识库中不存在")
            except Exception as ex_: logger.error("验证来源条目失败: entry_id={}, error={}", eid, ex_); sc.append({"entry_id": eid, "exists": False, "relevant": False, "title": st}); vd.append(f"无法验证来源条目 (id={eid}): {ex_}")
            if ex:
                fs += 1; kws, mc = self._extract_keywords(answer), sum(1 for kw in kws if kw.lower() in ec.lower())
                if mc > 0: rs += 1; sc[-1]["relevant"] = True
        ser = fs / ts if ts else 0.0; crr = rs / max(fs, 1)
        if fs == 0: vd.append("所有引用的来源条目在知识库中均不存在")
        elif rs == 0: vd.append("回答内容与引用的来源条目之间未检测到明显关联")
        iv = ser >= _MIN_VALID
        if not vd: vd.append(f"验证通过：{fs}/{ts} 个来源存在于知识库中，{rs}/{fs} 个与回答内容相关")
        cc = round(ser * 0.5 + crr * 0.5, 4); logger.info("答案验证完成: is_valid={}, source_ratio={:.2f}, relevance_ratio={:.2f}, coverage={:.2f}", iv, ser, crr, cc)
        return {"is_valid": iv, "validation_details": "; ".join(vd), "source_check": sc, "content_coverage": cc}
