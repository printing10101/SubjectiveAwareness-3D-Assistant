"""knowledge_qa_service - 向后兼容 re-export 层.

本模块已重构至 app.services.knowledge.analyzer，此文件保留用于向后兼容。
请直接从 app.services.knowledge 导入。
"""
from app.services.knowledge.analyzer import KnowledgeQAService

__all__ = ["KnowledgeQAService"]
