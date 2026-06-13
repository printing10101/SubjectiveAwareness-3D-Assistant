"""知识导入服务模块.

提供从文档和案件导入知识的功能，复用 document_processor 文档处理能力
和 ollama_client LLM 调用能力，支持批量导入、元数据自动提取和错误隔离。
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.case import Case
from app.models.entry_tag import EntryTag
from app.models.knowledge_entry import EntryCategory, EntryStatus, KnowledgeEntry, SourceType
from app.models.knowledge_tag import KnowledgeTag
from app.services.document_processor import process_document
from app.services.ollama_client import get_client


_MAX_METADATA_RETRIES: int = 2
_METADATA_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"title", "summary", "key_concepts", "suggested_tags", "suggested_category"}
)
_VALID_CATEGORIES: frozenset[str] = frozenset(
    {"law", "methodology", "case", "other"}
)
_SYSTEM_USER_ID: int = 1
_DEFAULT_TAG_COLOR: str = "#3B82F6"

_METADATA_EXTRACTION_PROMPT: str = """请从以下文本中提取结构化元数据，以JSON格式返回。
必须包含以下字段：
- title: 简洁的标题（不超过100字）
- summary: 内容摘要（不超过200字）
- key_concepts: 关键概念列表（字符串数组，3-5个）
- suggested_tags: 建议标签列表（字符串数组，3-8个，用于分类和检索）
- suggested_category: 建议分类，必须是以下之一：law（法律）、methodology（方法论）、case（案例）、other（其他）

只返回JSON，不要包含任何其他文字：

文本内容：
{text}"""


class _ImportFileWrapper:
    """将字节内容包装为类 UploadFile 对象，供 process_document 使用."""

    def __init__(self, content: bytes, filename: str = "document.txt") -> None:
        self.filename: str = filename
        self._content: bytes = content

    async def read(self) -> bytes:
        return self._content


@dataclass
class ImportResult:
    """单条导入结果."""

    success: bool
    entry_id: int | None = None
    extracted_metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        result: dict[str, Any] = {
            "success": self.success,
            "entry_id": self.entry_id,
            "extracted_metadata": self.extracted_metadata,
        }
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class BatchImportResult:
    """批量导入结果统计."""

    success_count: int = 0
    failure_count: int = 0
    skip_count: int = 0
    success_case_ids: list[int] = field(default_factory=list)
    failure_case_ids: list[int] = field(default_factory=list)
    skip_case_ids: list[int] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "skip_count": self.skip_count,
            "success_case_ids": self.success_case_ids,
            "failure_case_ids": self.failure_case_ids,
            "skip_case_ids": self.skip_case_ids,
            "errors": self.errors,
        }


def _validate_metadata(data: dict[str, Any]) -> dict[str, Any]:
    """验证并格式化 LLM 返回的元数据.

    Args:
        data: LLM 返回的原始元数据字典

    Returns:
        格式化后的元数据字典

    Raises:
        ValueError: 必需字段缺失或格式不正确
    """
    missing = [f for f in _METADATA_REQUIRED_FIELDS if f not in data]
    if missing:
        msg = f"LLM返回的元数据缺少必需字段: {', '.join(missing)}"
        raise ValueError(msg)

    if not isinstance(data.get("title"), str) or not data["title"].strip():
        msg = "title必须是非空字符串"
        raise ValueError(msg)
    if not isinstance(data.get("summary"), str) or not data["summary"].strip():
        msg = "summary必须是非空字符串"
        raise ValueError(msg)
    if not isinstance(data.get("key_concepts"), list):
        data["key_concepts"] = []

    key_concepts = [
        str(c) for c in data["key_concepts"] if isinstance(c, str) and c.strip()
    ]
    data["key_concepts"] = key_concepts

    if not isinstance(data.get("suggested_tags"), list):
        data["suggested_tags"] = []

    suggested_tags = [
        str(t).strip()
        for t in data["suggested_tags"]
        if isinstance(t, str) and t.strip()
    ]
    data["suggested_tags"] = suggested_tags

    category = str(data.get("suggested_category", "other")).strip().lower()
    if category not in _VALID_CATEGORIES:
        category = "other"
    data["suggested_category"] = category

    return data


async def _resolve_category(category_str: str) -> EntryCategory:
    """将分类字符串映射为 EntryCategory 枚举.

    Args:
        category_str: 分类字符串

    Returns:
        EntryCategory 枚举值
    """
    mapping: dict[str, EntryCategory] = {
        "law": EntryCategory.law,
        "methodology": EntryCategory.methodology,
        "case": EntryCategory.case,
        "other": EntryCategory.other,
    }
    return mapping.get(category_str, EntryCategory.other)


async def _get_or_create_tag(
    db: AsyncSession,
    tag_name: str,
) -> KnowledgeTag:
    """获取或创建知识标签.

    如果标签已存在则直接返回，否则创建新标签。

    Args:
        db: 异步数据库会话
        tag_name: 标签名称

    Returns:
        KnowledgeTag: 已存在或新创建的标签实例
    """
    result = await db.execute(
        select(KnowledgeTag).where(KnowledgeTag.name == tag_name)
    )
    existing_tag = result.scalar_one_or_none()
    if existing_tag:
        return existing_tag

    new_tag = KnowledgeTag(
        name=tag_name,
        description=f"自动创建的标签: {tag_name}",
        color=_DEFAULT_TAG_COLOR,
    )
    db.add(new_tag)
    await db.flush()
    logger.debug(f"自动创建标签: name={tag_name}, id={new_tag.id}")
    return new_tag


async def _associate_tags(
    db: AsyncSession,
    entry_id: int,
    tag_names: list[str],
) -> list[KnowledgeTag]:
    """为知识条目关联标签（自动创建不存在的标签）.

    Args:
        db: 异步数据库会话
        entry_id: 知识条目ID
        tag_names: 标签名称列表

    Returns:
        list[KnowledgeTag]: 关联的标签列表
    """
    if not tag_names:
        return []

    associated_tags: list[KnowledgeTag] = []
    for tag_name in tag_names:
        try:
            tag = await _get_or_create_tag(db, tag_name)

            existing = await db.execute(
                select(EntryTag).where(
                    EntryTag.entry_id == entry_id,
                    EntryTag.tag_id == tag.id,
                )
            )
            if not existing.scalar_one_or_none():
                entry_tag = EntryTag(entry_id=entry_id, tag_id=tag.id)
                db.add(entry_tag)
                logger.debug(f"标签关联成功: entry={entry_id}, tag={tag_name}")

            associated_tags.append(tag)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"标签关联失败: entry={entry_id}, tag={tag_name}, error={e}")

    if associated_tags:
        await db.flush()

    return associated_tags


async def extract_metadata_with_llm(text: str) -> dict[str, Any]:
    """使用 LLM 从文本中提取结构化元数据.

    调用 OllamaClient.generate_json 方法处理输入文本，
    提取 title、summary、key_concepts、suggested_tags 和
    suggested_category 等字段，并对结果进行验证和格式化。

    支持重试机制，在 LLM 返回无效结果时自动重试。

    Args:
        text: 需要提取元数据的文本内容

    Returns:
        结构化的元数据字典，包含以下字段：
        - title: 标题
        - summary: 摘要
        - key_concepts: 关键概念列表
        - suggested_tags: 建议标签列表
        - suggested_category: 建议分类

    Raises:
        ValueError: 重试耗尽后仍未获取有效元数据
        RuntimeError: LLM 调用完全失败
    """
    client = get_client()
    prompt = _METADATA_EXTRACTION_PROMPT.format(text=text[:8000])

    last_error: str | None = None

    for attempt in range(_MAX_METADATA_RETRIES + 1):
        try:
            raw_result: dict[str, Any] | list[Any] = await client.generate_json(
                prompt=prompt,
                system_prompt="你是一个专业的法律知识管理助手，擅长从文本中提取结构化元数据。",
                temperature=0.2,
            )

            if isinstance(raw_result, list):
                logger.warning(f"LLM返回了列表而非字典 (尝试 {attempt + 1})")
                last_error = "LLM返回了列表格式而非字典"
                continue

            validated = _validate_metadata(raw_result)
            logger.info(
                f"元数据提取成功: title={validated['title'][:50]}, "
                f"category={validated['suggested_category']}, "
                f"tags={len(validated['suggested_tags'])}"
            )
            return validated

        except (ValueError, json.JSONDecodeError) as e:
            last_error = str(e)
            logger.warning(
                f"元数据提取验证失败 (尝试 {attempt + 1}/{_MAX_METADATA_RETRIES + 1}): {e}"
            )
            if attempt < _MAX_METADATA_RETRIES:
                await asyncio.sleep(0.5 * (attempt + 1))

        except Exception as e:  # noqa: BLE001
            last_error = str(e)
            logger.error(f"LLM元数据提取异常 (尝试 {attempt + 1}): {e}")
            if attempt < _MAX_METADATA_RETRIES:
                await asyncio.sleep(1.0 * (attempt + 1))

    msg = f"元数据提取失败，已重试{_MAX_METADATA_RETRIES}次: {last_error}"
    raise ValueError(msg)


async def import_from_document(  # noqa: PLR0915
    db: AsyncSession,
    file_content: bytes | None = None,
    file_path: str | None = None,
    metadata: dict[str, Any] | None = None,
    created_by: int = _SYSTEM_USER_ID,
) -> dict[str, Any]:
    """从指定文档导入知识内容并创建知识条目.

    调用 document_processor.process_document 提取文本内容，
    然后使用 LLM 自动提取元数据（标题、摘要、关键概念、
    建议标签、建议分类），最后创建 KnowledgeEntry 记录
    并关联标签。

    file_content 和 file_path 至少需要提供其中之一。
    如果同时提供，优先使用 file_content。

    Args:
        db: 异步数据库会话
        file_content: 文件的原始字节内容
        file_path: 文件的本地路径
        metadata: 额外的用户自定义元数据，用于补充或覆盖 LLM 提取的结果
        created_by: 创建者用户 ID，默认为系统用户(1)

    Returns:
        结构化的导入结果字典：
        - entry_id: 知识条目 ID
        - extracted_metadata: 提取的完整元数据

    Raises:
        ValueError: 未提供文件内容或文件路径、文档内容为空
        FileNotFoundError: 指定的文件路径不存在
        Exception: 文档处理或数据库操作失败
    """
    if file_content is None and file_path is None:
        logger.error("文档导入失败: 未提供 file_content 或 file_path")
        msg = "必须提供 file_content 或 file_path 参数"
        raise ValueError(msg)

    if file_content is not None:
        content_bytes = file_content
        filename = "uploaded_document.txt"
        logger.info(
            f"[文档导入] 使用 file_content: size={len(content_bytes)} bytes, "
            f"source=内存, created_by={created_by}"
        )
    elif file_path is not None:
        if not os.path.isfile(file_path):
            logger.error(f"[文档导入] 文件不存在: path={file_path}")
            msg = f"文件不存在: {file_path}"
            raise FileNotFoundError(msg)
        with open(file_path, "rb") as f:
            content_bytes = f.read()
        filename = os.path.basename(file_path)
        logger.info(
            f"[文档导入] 使用 file_path: path={file_path}, filename={filename}, "
            f"size={len(content_bytes)} bytes, created_by={created_by}"
        )
    else:
        msg = "必须提供 file_content 或 file_path 参数"
        raise ValueError(msg)

    wrapper = _ImportFileWrapper(content_bytes, filename)

    try:
        extracted_text = await process_document(wrapper)
        logger.info(
            f"[文档导入] 文档解析成功: filename={filename}, "
            f"text_length={len(extracted_text)} chars"
        )
    except Exception as e:
        logger.error(
            f"[文档导入] 文档解析失败: filename={filename}, "
            f"error_type={type(e).__name__}, error={e}"
        )
        raise

    if not extracted_text or not extracted_text.strip():
        logger.warning(
            f"[文档导入] 文档内容为空: filename={filename}, "
            f"text_length={len(extracted_text) if extracted_text else 0}"
        )
        msg = f"文档内容为空，无法导入: {filename}"
        raise ValueError(msg)

    logger.info(
        f"[文档导入] 开始LLM元数据提取: filename={filename}, "
        f"input_length={min(len(extracted_text), 8000)} chars"
    )
    try:
        llm_metadata = await extract_metadata_with_llm(extracted_text)
        logger.info(
            f"[文档导入] LLM元数据提取成功: title={llm_metadata['title'][:50]}, "
            f"category={llm_metadata['suggested_category']}, "
            f"tags_count={len(llm_metadata.get('suggested_tags', []))}, "
            f"concepts_count={len(llm_metadata.get('key_concepts', []))}"
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[文档导入] LLM元数据提取失败，使用回退元数据: "
            f"filename={filename}, error_type={type(e).__name__}, error={e}"
        )
        llm_metadata = {
            "title": filename.rsplit(".", 1)[0][:100],
            "summary": extracted_text[:200].strip(),
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "other",
        }
        logger.info(
            f"[文档导入] 回退元数据: title={llm_metadata['title']}, "
            f"summary_length={len(llm_metadata['summary'])} chars, "
            f"category={llm_metadata['suggested_category']}"
        )

    if metadata:
        logger.info(
            f"[文档导入] 应用用户自定义元数据覆盖: override_keys={list(metadata.keys())}"
        )
        llm_metadata.update(metadata)

    category = await _resolve_category(llm_metadata["suggested_category"])
    logger.info(
        f"[文档导入] 分类映射: suggested={llm_metadata['suggested_category']}, "
        f"resolved={category.value}"
    )

    db_entry = KnowledgeEntry(
        title=llm_metadata["title"],
        content=extracted_text,
        summary=llm_metadata["summary"],
        category=category,
        status=EntryStatus.draft,
        source_type=SourceType.document_import,
        created_by=created_by,
    )

    logger.info(
        f"[文档导入] 准备创建知识条目: title={db_entry.title[:50]}, "
        f"content_length={len(db_entry.content)} chars, "
        f"summary_length={len(db_entry.summary or '')} chars, "
        f"category={db_entry.category.value}, "
        f"source_type={db_entry.source_type.value}, "
        f"created_by={created_by}"
    )
    try:
        db.add(db_entry)
        await db.flush()
        logger.info(
            f"[文档导入] 知识条目创建成功: entry_id={db_entry.id}, "
            f"title={db_entry.title}, status={db_entry.status.value}"
        )
    except Exception as e:
        logger.error(
            f"[文档导入] 知识条目创建失败: title={db_entry.title}, "
            f"error_type={type(e).__name__}, error={e}"
        )
        raise

    tag_names = llm_metadata.get("suggested_tags", [])
    logger.info(
        f"[文档导入] 开始关联标签: entry_id={db_entry.id}, "
        f"tag_count={len(tag_names)}, tags={tag_names}"
    )
    await _associate_tags(db, db_entry.id, tag_names)
    logger.info(
        f"[文档导入] 标签关联完成: entry_id={db_entry.id}, "
        f"associated_tags={tag_names}"
    )

    result_metadata = {
        "title": llm_metadata["title"],
        "summary": llm_metadata["summary"],
        "key_concepts": llm_metadata.get("key_concepts", []),
        "suggested_tags": tag_names,
        "suggested_category": llm_metadata["suggested_category"],
    }

    logger.info(
        f"[文档导入] 导入完成: entry_id={db_entry.id}, "
        f"title={result_metadata['title'][:50]}, "
        f"category={result_metadata['suggested_category']}, "
        f"tags={tag_names}, concepts={result_metadata['key_concepts']}"
    )
    return {
        "entry_id": db_entry.id,
        "extracted_metadata": result_metadata,
    }


async def import_from_case(  # noqa: PLR0915
    db: AsyncSession,
    case_id: int,
) -> dict[str, Any]:
    """从指定案件导入数据创建知识条目.

    读取案件的标题、事实文本和分析结果，
    将其转换为 KnowledgeEntry 记录并关联标签。

    Args:
        db: 异步数据库会话
        case_id: 案件 ID

    Returns:
        结构化的导入结果字典：
        - entry_id: 知识条目 ID
        - extracted_metadata: 提取的元数据

    Raises:
        ValueError: 案件不存在或数据不完整
        Exception: 数据库操作失败
    """
    case_result = await db.execute(select(Case).where(Case.id == case_id))
    case = case_result.scalar_one_or_none()

    if not case:
        logger.error(f"[案件导入] 案件不存在: case_id={case_id}")
        msg = f"案件不存在: case_id={case_id}"
        raise ValueError(msg)

    logger.info(
        f"[案件导入] 开始导入: case_id={case_id}, title={case.title}, "
        f"status={case.status.value if case.status else 'N/A'}, "
        f"has_description={bool(case.description and case.description.strip())}"
    )

    if not case.title or not case.title.strip():
        logger.error(f"[案件导入] 案件标题为空: case_id={case_id}")
        msg = f"案件标题为空，无法导入: case_id={case_id}"
        raise ValueError(msg)

    decoded_case_text: str = case.case_text or ""
    if not decoded_case_text or not decoded_case_text.strip():
        logger.error(
            f"[案件导入] 案件文本内容为空: case_id={case_id}, title={case.title}"
        )
        msg = f"案件文本内容为空，无法导入: case_id={case_id}"
        raise ValueError(msg)

    logger.info(
        f"[案件导入] 案件文本解密成功: case_id={case_id}, "
        f"text_length={len(decoded_case_text)} chars"
    )

    analysis_result = await db.execute(
        select(Analysis)
        .where(Analysis.case_id == case_id)
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    latest_analysis = analysis_result.scalar_one_or_none()

    content_parts: list[str] = [decoded_case_text]

    if latest_analysis and latest_analysis.result_json:
        try:
            analysis_data: dict[str, Any] | list[Any] = json.loads(
                latest_analysis.result_json
            )
            analysis_text = json.dumps(analysis_data, ensure_ascii=False, indent=2)
            content_parts.append("\n\n--- 案件分析结果 ---\n")
            content_parts.append(analysis_text)
            logger.info(
                f"[案件导入] 分析结果已附着: case_id={case_id}, "
                f"analysis_id={latest_analysis.id}, "
                f"analysis_mode={latest_analysis.mode.value if latest_analysis.mode else 'N/A'}, "
                f"knowledge_score={latest_analysis.knowledge_score}"
            )
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(
                f"[案件导入] 分析结果JSON解析失败，使用原始文本: "
                f"case_id={case_id}, analysis_id={latest_analysis.id}, error={e}"
            )
            content_parts.append("\n\n--- 案件分析结果 ---\n")
            content_parts.append(str(latest_analysis.result_json))
    else:
        logger.info(
            f"[案件导入] 未找到分析结果: case_id={case_id}, "
            f"content仅包含案件事实文本"
        )

    full_content = "".join(content_parts)
    logger.info(
        f"[案件导入] 内容组装完成: case_id={case_id}, "
        f"total_length={len(full_content)} chars, "
        f"has_analysis={latest_analysis is not None}"
    )

    description = case.description or ""

    logger.info(
        f"[案件导入] 开始LLM元数据提取: case_id={case_id}, "
        f"input_length={min(len(full_content), 8000)} chars"
    )
    try:
        llm_metadata = await extract_metadata_with_llm(full_content[:8000])
        logger.info(
            f"[案件导入] LLM元数据提取成功: case_id={case_id}, "
            f"title={llm_metadata['title'][:50]}, "
            f"tags_count={len(llm_metadata.get('suggested_tags', []))}"
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[案件导入] LLM元数据提取失败，使用回退元数据: "
            f"case_id={case_id}, error_type={type(e).__name__}, error={e}"
        )
        llm_metadata = {
            "title": case.title[:100],
            "summary": (description or decoded_case_text)[:200].strip(),
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "case",
        }
        logger.info(
            f"[案件导入] 回退元数据: case_id={case_id}, "
            f"title={llm_metadata['title']}, "
            f"summary_length={len(llm_metadata['summary'])} chars"
        )

    db_entry = KnowledgeEntry(
        title=llm_metadata["title"],
        content=full_content,
        summary=llm_metadata["summary"],
        category=EntryCategory.case,
        status=EntryStatus.draft,
        source_type=SourceType.case_conversion,
        source_id=case_id,
        created_by=case.created_by or _SYSTEM_USER_ID,
    )

    logger.info(
        f"[案件导入] 准备创建知识条目: case_id={case_id}, "
        f"title={db_entry.title[:50]}, "
        f"content_length={len(db_entry.content)} chars, "
        f"summary_length={len(db_entry.summary or '')} chars, "
        f"category={db_entry.category.value}, "
        f"source_type={db_entry.source_type.value}, "
        f"source_id={db_entry.source_id}, "
        f"created_by={db_entry.created_by}"
    )
    try:
        db.add(db_entry)
        await db.flush()
        logger.info(
            f"[案件导入] 知识条目创建成功: entry_id={db_entry.id}, "
            f"case_id={case_id}, title={db_entry.title}, "
            f"status={db_entry.status.value}"
        )
    except Exception as e:
        logger.error(
            f"[案件导入] 知识条目创建失败: case_id={case_id}, "
            f"title={db_entry.title}, error_type={type(e).__name__}, error={e}"
        )
        raise

    tag_names = llm_metadata.get("suggested_tags", [])
    if "案件" not in tag_names:
        tag_names.append("案件")
        logger.debug(f"[案件导入] 自动追加默认标签 '案件': case_id={case_id}")

    logger.info(
        f"[案件导入] 开始关联标签: entry_id={db_entry.id}, "
        f"tag_count={len(tag_names)}, tags={tag_names}"
    )
    await _associate_tags(db, db_entry.id, tag_names)
    logger.info(
        f"[案件导入] 标签关联完成: entry_id={db_entry.id}, "
        f"associated_tags={tag_names}"
    )

    result_metadata = {
        "title": llm_metadata["title"],
        "summary": llm_metadata["summary"],
        "key_concepts": llm_metadata.get("key_concepts", []),
        "suggested_tags": tag_names,
        "suggested_category": "case",
    }

    logger.info(
        f"[案件导入] 导入完成: entry_id={db_entry.id}, case_id={case_id}, "
        f"title={result_metadata['title'][:50]}, "
        f"tags={tag_names}, concepts={result_metadata['key_concepts']}"
    )
    return {
        "entry_id": db_entry.id,
        "extracted_metadata": result_metadata,
    }


async def batch_import_from_cases(
    db: AsyncSession,
    status: str = "completed",
) -> dict[str, Any]:
    """批量将指定状态的案件转换为知识条目.

    查询所有状态为 status 的案件（默认为 'completed'），
    逐个调用 import_from_case 进行转换，实现错误隔离
    和进度跟踪机制。

    Args:
        db: 异步数据库会话
        status: 案件状态过滤条件，默认为 'completed'

    Returns:
        批量导入统计信息字典：
        - success_count: 成功导入数量
        - failure_count: 失败数量
        - skip_count: 跳过数量
        - success_case_ids: 成功导入的案件 ID 列表
        - failure_case_ids: 失败导入的案件 ID 列表
        - skip_case_ids: 跳过的案件 ID 列表
        - errors: 错误详情列表
    """
    from app.models.case import CaseStatus  # noqa: PLC0415

    try:
        target_status = CaseStatus(status)
    except ValueError:
        valid_statuses = [s.value for s in CaseStatus]
        msg = f"无效的案件状态: '{status}'，有效状态: {valid_statuses}"
        raise ValueError(msg) from None

    cases_result = await db.execute(
        select(Case.id, Case.title, Case.case_text)
        .where(Case.status == target_status)
        .order_by(Case.id)
    )
    cases = cases_result.all()

    if not cases:
        logger.info(f"没有找到状态为 '{status}' 的案件")
        return BatchImportResult().to_dict()

    result = BatchImportResult()
    total = len(cases)
    logger.info(f"开始批量导入案件: total={total}, status={status}")

    for idx, (case_id, case_title, case_text) in enumerate(cases):
        if not case_title or not case_text:
            logger.warning(f"跳过数据不完整的案件: case_id={case_id}")
            result.skip_count += 1
            result.skip_case_ids.append(case_id)
            continue

        try:
            import_result = await import_from_case(db, case_id)
            result.success_count += 1
            result.success_case_ids.append(case_id)
            logger.info(
                f"案件导入成功: case_id={case_id}, "
                f"entry_id={import_result.get('entry_id')}, "
                f"进度={idx + 1}/{total}"
            )
        except Exception as e:  # noqa: BLE001
            result.failure_count += 1
            result.failure_case_ids.append(case_id)
            result.errors.append({
                "case_id": case_id,
                "case_title": case_title,
                "error": str(e),
            })
            logger.error(
                f"案件导入失败: case_id={case_id}, error={e}, "
                f"进度={idx + 1}/{total}"
            )

    logger.info(
        f"批量案件导入完成: success={result.success_count}, "
        f"failure={result.failure_count}, skip={result.skip_count}"
    )
    return result.to_dict()
