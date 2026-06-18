"""knowledge_relation_service - 向后兼容 re-export 层.

本模块已重构至 app.services.knowledge.analyzer，此文件保留用于向后兼容。
请直接从 app.services.knowledge 导入。
"""
from app.services.knowledge.analyzer import (
    auto_link_entries,
    build_knowledge_graph,
    find_related_entries,
    traverse_graph,
)

__all__ = [
    "auto_link_entries",
    "build_knowledge_graph",
    "find_related_entries",
    "traverse_graph",
]
