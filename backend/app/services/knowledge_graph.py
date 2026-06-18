"""knowledge_graph - 向后兼容 re-export 层.

本模块已重构至 app.services.knowledge.analyzer，此文件保留用于向后兼容。
请直接从 app.services.knowledge 导入。
"""
from app.services.knowledge.analyzer import (
    ALLOWED_RULE_FIELDS,
    _sanitize_rule,
    create_legal_rule,
    delete_legal_rule,
    get_legal_rule,
    get_legal_rules,
    update_legal_rule,
)

# 向后兼容别名：原模块使用 _sanitize_rule_data，新模块使用 _sanitize_rule
_sanitize_rule_data = _sanitize_rule

__all__ = [
    "ALLOWED_RULE_FIELDS",
    "_sanitize_rule_data",
    "create_legal_rule",
    "delete_legal_rule",
    "get_legal_rule",
    "get_legal_rules",
    "update_legal_rule",
]
