"""knowledge_import_service - 向后兼容 re-export 层.

本模块已重构至 app.services.knowledge.manager，此文件保留用于向后兼容。
请直接从 app.services.knowledge 导入。
"""
from app.services.document_processor import process_document
from app.services.ollama_client import get_client
from app.services.knowledge.manager import (
    BatchImportResult,
    ImportResult,
    _ImportFileWrapper,
    _associate_tags,
    _get_or_create_tag,
    _resolve_category,
    _validate_metadata,
    batch_import_from_cases,
    extract_metadata_with_llm,
    import_from_case,
    import_from_document,
)

__all__ = [
    "BatchImportResult",
    "ImportResult",
    "batch_import_from_cases",
    "extract_metadata_with_llm",
    "get_client",
    "import_from_case",
    "import_from_document",
    "process_document",
]
