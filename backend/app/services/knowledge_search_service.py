"""knowledge_search_service - 向后兼容 re-export 层.

本模块已重构至 app.services.knowledge.repository，此文件保留用于向后兼容。
请直接从 app.services.knowledge 导入。
"""
from app.services.knowledge.repository import (
    ensure_fts_table,
    get_fts_count,
    remove_entry_from_fts,
    search_entries,
    sync_entry,
)

__all__ = [
    "ensure_fts_table",
    "get_fts_count",
    "remove_entry_from_fts",
    "search_entries",
    "sync_entry",
]
