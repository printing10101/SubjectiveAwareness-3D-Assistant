"""knowledge_service - 向后兼容 re-export 层.

本模块已重构至 app.services.knowledge.repository，此文件保留用于向后兼容。
请直接从 app.services.knowledge 导入。
"""
from app.services.knowledge.repository import (
    add_entry_relation,
    add_entry_tag,
    create_entry,
    create_tag,
    delete_entry,
    get_all_tags,
    get_entries_paginated,
    get_entry,
    get_entry_relations,
    get_entry_tags,
    remove_entry_tag,
    update_entry,
)

__all__ = [
    "add_entry_relation",
    "add_entry_tag",
    "create_entry",
    "create_tag",
    "delete_entry",
    "get_all_tags",
    "get_entries_paginated",
    "get_entry",
    "get_entry_relations",
    "get_entry_tags",
    "remove_entry_tag",
    "update_entry",
]
