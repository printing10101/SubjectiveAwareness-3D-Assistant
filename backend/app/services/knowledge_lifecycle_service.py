"""knowledge_lifecycle_service - 向后兼容 re-export 层.

本模块已重构至 app.services.knowledge.manager，此文件保留用于向后兼容。
请直接从 app.services.knowledge 导入。
"""
from app.services.knowledge.manager import (
    DecayStatistics,
    KnowledgeLifecycleScheduler,
    LintIssue,
    LintReport,
    ScheduleConfig,
    _extract_wikilinks,
    _validate_entry_id,
    _validate_feedback,
    apply_decay,
    lint_knowledge_base,
    run_decay_sync,
    run_lint_sync,
    supersede_entry,
    update_confidence,
)

__all__ = [
    "DecayStatistics",
    "KnowledgeLifecycleScheduler",
    "LintIssue",
    "LintReport",
    "ScheduleConfig",
    "apply_decay",
    "lint_knowledge_base",
    "run_decay_sync",
    "run_lint_sync",
    "supersede_entry",
    "update_confidence",
]
