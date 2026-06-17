"""知识导入服务模块.

提供从文档和案件导入知识的功能，复用 document_processor 文档处理能力
和 ollama_client LLM 调用能力，支持批量导入、元数据自动提取和错误隔离。
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: asyncio
import asyncio
# 导入模块: json
import json
# 导入模块: os
import os
# 导入模块: from dataclasses
from dataclasses import dataclass, field
# 导入模块: from typing
from typing import Any

# 导入模块: from loguru
from loguru import logger
# 导入模块: from sqlalchemy
from sqlalchemy import select
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# 导入模块: from app.models.analysis
from app.models.analysis import Analysis
# 导入模块: from app.models.case
from app.models.case import Case
# 导入模块: from app.models.entry_tag
from app.models.entry_tag import EntryTag
# 导入模块: from app.models.knowledge_entry
from app.models.knowledge_entry import EntryCategory, EntryStatus, KnowledgeEntry, SourceType
# 导入模块: from app.models.knowledge_tag
from app.models.knowledge_tag import KnowledgeTag
# 导入模块: from app.services.document_processor
from app.services.document_processor import process_document
# 导入模块: from app.services.ollama_client
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


# 定义 _ImportFileWrapper 类
class _ImportFileWrapper:
    """将字节内容包装为类 UploadFile 对象，供 process_document 使用."""

    def __init__(self, content: bytes, filename: str = "document.txt") -> None:

        # 执行 __init__ 函数的核心逻辑
        self.filename: str = filename
        self._content: bytes = content

    async def read(self) -> bytes:
        # 函数 read 的初始化逻辑
        return self._content


# 应用装饰器: dataclass
@dataclass
# 定义 ImportResult 类
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
        # 条件判断：处理业务逻辑
        if self.error:
            result["error"] = self.error
        # 返回处理结果
        return result


# 应用装饰器: dataclass
@dataclass
# 定义 BatchImportResult 类
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
        # 返回处理结果
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
    # 初始化变量 missing
    missing = [f for f in _METADATA_REQUIRED_FIE    # 条件判断：处理业务逻辑
LDS if f not in data]
    # 条件判断: 检查 missing
    if missing:
        msg = f"LLM返回的元数据缺少必需字段: {', '.join(m
    # 条件判断：处理业务逻辑
issing)}"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    # 条件判断: 检查 not isinstance(data.get("title"), str) o
    if not isinstance(data.get("title"), str) or not data["title"].strip():
     # 条件判断：处理业务逻辑
       msg = "title必须是非空字符串"
        # 抛出异常，处理错误情况
        raise ValueError(msg)
    # 条件判断: 检查 not isinstance(data.get("summary"), str)
    if not isinstance(data.get("summary"), str) or not data["summ    # 条件判断：处理业务逻辑
ary"].strip():
        msg = "summary必须是非空字符串"
        # 抛出异常，处理错误情况
        raise ValueError(msg)
    # 条件判断: 检查 not isinstance(data.get("key_concepts"),
    if not isinstance(data.get("key_concepts"), list):
        data["key_concepts"] = []

    # 初始化变量 key_concepts
    key_concepts = [
        str(c) for c in data["ke
    # 条件判断：处理业务逻辑
y_concepts"] if isinstance(c, str) and c.strip()
    ]
    data["key_concepts"] = key_concepts

    # 条件判断: 检查 not isinstance(data.get("suggested_tags"
    if not isinstance(data.get("suggested_tags"), list):
        d        # 条件判断：处理业务逻辑
ata["suggested_tags"] = []

    # 初始化变量 suggested_tags
    suggested_tags = [
        str(t).strip()
        # 循环遍历：处理业务逻辑
        for t in data["suggested_tags"]
        # 条件判断: 检查 isinstance(t, str) and t    # 条件判断：处理业务逻
        if isinstance(t, str) and t    # 条件判断：处理业务逻辑
.strip()
    ]
    data["suggested_tags"] = suggested_tags

    # 初始化变量 category
    category = str(data.get("suggested_category", "other")).strip().lower()
    # 条件判断: 检查 category not in _VALID_CATEGORIES
    if category not in _VALID_CATEGORIES:
        # 初始化变量 category
        category = "other"
    data["suggested_category"] = category

    # 返回处理结果
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
    # 返回处理结果
    return mapping.get(category_str, EntryCategory.other)


async def _get_or_create_tag(
    # 函数 _get_or_create_tag 的初始化逻辑
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
        # 条件判断：处理业务逻辑
"""
    # 初始化变量 result
    result = await db.execute(
        select(KnowledgeTag).where(KnowledgeTag.name == tag_name)
    )
    # 初始化变量 existing_tag
    existing_tag = result.scalar_one_or_none()
    # 条件判断: 检查 existing_tag
    if existing_tag:
        # 返回处理结果
        return existing_tag

    # 初始化变量 new_tag
    new_tag = KnowledgeTag(
        # 初始化变量 name
        name=tag_name,
        # 初始化变量 description
        description=f"自动创建的标签: {tag_name}",
        # 初始化变量 color
        color=_DEFAULT_TAG_COLOR,
    )
    db.add(new_tag)
    # 异步等待操作完成
    await db.flush()
    # 记录日志信息
    logger.debug(f"自动创建标签: name={tag_name}, id={new_tag.id}")
    # 返回处理结果
    return new_tag


async def _associate_tags(
    # 函数 _associate_tags 的初始化逻辑
    db: AsyncSession,
    entry_id: int,
    tag_names: list[str],
) -> list[KnowledgeTag]    # 条件判断：处理业务逻辑
:
    """为知识条目关联标签（自动创建不存在的标签）.

    Args:
        db: 异步数据库会话
        entry_id: 知识条目ID
        tag_names: 标签名称列表

    Returns:
        list[KnowledgeTag]: 关联的标签列表
    """
    # 条件判断: 检查 not tag_names
    if not tag_names:
        # 返回处理结果
        return []

    associated_tags: li    # 循环遍历：处理业务逻辑
st[KnowledgeTag] = []
    # 遍历: for tag_name in tag_names:
    for tag_name in tag_names:
        # 异常处理：处理业务逻辑
        try:
            tag = await _get_or_create_tag(db, tag_name)

            existing             # 条件判断：处理业务逻辑
= await db.execute(
                select(EntryTag).where(
                    EntryTag.entry_id == entry_id,
                    EntryTag.tag_id == tag.id,
                )
            )
            # 条件判断: 检查 not existing.scalar_one_or_none()
            if not existing.scalar_one_or_none():
                # 初始化变量 entry_tag
                entry_tag = EntryTag(entry_id=entry_id, tag_id=tag.id)
                db.add(entry_tag)
                # 记录日志信息
                logger.debug(
    # 条件判断：处理业务逻辑
f"标签关联成功: entry={entry_id}, tag={tag_name}")

            associated_tags.append(tag)
        # 捕获并处理异常
        except Exception as e:  # noqa: BLE001
            logger.warning(f"标签关联失败: entry={entry_id}, tag={tag_name}, error={e}")

    # 条件判断: 检查 associated_tags
    if associated_tags:
        # 异步等待操作完成
        await db.flush()

    # 返回处理结果
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
    # 初始化变量 client
    client = get_client()
    # 初始化变量 prompt
    prompt = _METADATA_EXTRACTION_PROMPT.format(text=text[:80
    # 循环遍历：处理业务逻辑
00])

    last_error: str | None = None

    # 遍历: for attempt in range(_MAX_METADATA_RETRIES + 1):
    for attempt in range(_MAX_METADATA_RETRIES + 1):
  
            # 条件判断：处理业务逻辑
      try:
            # 异步等待操作完成
            raw_result: dict[str, Any] | list[Any] = await client.generate_json(
                # 初始化变量 prompt
                prompt=prompt,
                # 初始化变量 system_prompt
                system_prompt="你是一个专业的法律知识管理助手，擅长从文本中提取结构化元数据。",
                # 初始化变量 temperature
                temperature=0.2,
            )

            # 条件判断: 检查 isinstance(raw_result, list)
            if isinstance(raw_result, list):
                # 记录日志信息
                logger.warning(f"LLM返回了列表而非字典 (尝试 {attempt + 1})")
                # 初始化变量 last_error
                last_error = "LLM返回了列表格式而非字典"
                continue

            # 初始化变量 validated
            validated = _validate_metadata(raw_result)
            # 记录日志信息
            logger.info(
                f"元数据提取成功: title={validated['title'][:50]}, "
                f"category={validated['suggested_category']}, "
                f"tags={len(validated['suggested_tag            # 条件判断：处理业务逻辑
s'])}"
            )
            # 返回处理结果
            return validated

        # 捕获并处理异常
        except (ValueError, json.JSONDecodeError) as e:
            # 初始化变量 last_error
            last_error = str(e)
            # 记录日志信息
            logger.warning(
                f"元数据提取验证失败 (尝试 {attempt + 1}/{_MAX_META            # 条件判断：处理业务逻辑
DATA_RETRIES + 1}): {e}"
            )
            # 条件判断: 检查 attempt < _MAX_METADATA_RETRIES
            if attempt < _MAX_METADATA_RETRIES:
                # 异步等待操作完成
                await asyncio.sleep(0.5 * (attempt + 1))

        # 捕获并处理异常
        except Exception as e:  # noqa: BLE001
            last_error = str(e)
            # 记录日志信息
            logger.error(f"LLM元数据提取异常 (尝试 {attempt + 1}): {e}")
            # 条件判断: 检查 attempt < _MAX_METADATA_RETRIES
            if attempt < _MAX_METADATA_RETRIES:
                # 异步等待操作完成
                await asyncio.sleep(1.0 * (attempt + 1))

    msg = f"元数据提取失败，已重试{_MAX_METADATA_RETRIES}次: {last_error}"
    # 抛出异常，处理错误情况
    raise ValueError(msg)


async def import_from_document(  # noqa: PLR0915
    # 函数 import_from_document 的初始化逻辑
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
          # 条件判断：处理业务逻辑
  metadata: 额外的用户自定义元数据，用于补充或覆盖 LLM 提取的结果
        created_by: 创建者用户 ID，默认为系统用户(1)

    Returns:
        结构化的导入结果字典：
        - entry_id: 知识条目 ID
        - extracted_metadata:
    # 条件判断：处理业务逻辑
 提取的完整元数据

    Raises:
        ValueError: 未提供文件内容或文件路径、文档内容为空
        FileNotFoundError: 指定的文件路径不存在
        Exception: 文档处理或数据库操作失败
    """
    # 条件判断: 检查 file_content is None and file_path is No
    if file_content is None and file_path is None:
        # 记录日志信息
        logger.error("文档导入失败: 未提供 file_content 或 file_path")
        msg = "必须提供 file_con        # 条件判断：处理业务逻辑
tent 或 file_path 参数"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    # 条件判断: 检查 file_content is not None
    if file_content is not None:
        # 初始化变量 content_bytes
        content_bytes = file_content
        # 初始化变量 filename
        filename = "uploaded_document.txt"
        # 记录日志信息
        logger.info(
            f"[文档导入] 使用 file_content: size={len(content_bytes)} bytes, "
            f"source=内存, created_by={created_by}"
        )
    # 条件判断: 检查 elfile_path is not None
    elif file_path is not None:
        # 条件判断: 检查 not os.path.isfile(file_path)
        if not os.path.isfile(file_path):
            # 记录日志信息
            logger.error(f"[文档导入] 文件不存在: path={file_path}")
            msg = f"文件不存在: {file_path}"
            # 抛出异常，处理错误情况
            raise FileNotFoundError(msg)
        # 使用上下文管理器管理资源
        with open(file_path, "rb") as f:
            # 初始化变量 content_bytes
            content_bytes = f.read()
        # 初始化变量 filename
        filename = os.path.basename(file_path)
        # 记录日志信息
        logger.info(
            f"[文档导入] 使用 file_path: path={file_path}, filename={filename}, "
            f"size={len(content_bytes)} bytes, created_by={created_by}"
        )
    # 其他情况的默认处理
    else:
        msg = "必须提供 file_content 或 file_path 参数"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    # 初始化变量 wrapper
    wrapper = _ImportFileWrapper(con
    # 异常处理：处理业务逻辑
tent_bytes, filename)

    # 尝试执行可能抛出异常的代码
    try:
   
    # 条件判断：处理业务逻辑
     extracted_text = await process_document(wrapper)
        # 记录日志信息
        logger.info(
            f"[文档导入] 文档解析成功: filename={filename}, "
            f"text_length={len(extracted_text)} chars"
        )
    # 捕获异常：处理业务逻辑
    except Exception as e:
        # 记录日志信息
        logger.error(
            f"[文档导入] 文档解析失败: filename={filename}, "
            f"error_type={type(e).__name__}, error={e}"
        )
        raise

    # 条件判断: 检查 not extracted_text or not extracted_text
    if not extracted_text or not extracted_text.strip():
        # 记录日志信息
        logger.warning(
            f"[文档导入] 文档内容为空: filename={filename}, "
            f"text_length={len(extracted_text) if extracted_text else 0}"
        )
        msg = f"文档内容为空，无法导入: {filename}"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    # 记录日志信息
    logger.info(
        f"[文档导入] 开始LLM元数据提取: filename={filename}, "
        f"input_length={min(    # 异常处理：处理业务逻辑
len(extracted_text), 8000)} chars"
    )
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 llm_metadata
        llm_metadata = await extract_metadata_with_llm(extracted_text)
        # 记录日志信息
        logger.info(
            f"[文档导入] LLM元数据提取成功: title={llm_metadata['title'][:50]}, "
            f"category={llm_metadata['suggested_category']}, "
            f"tags_count={len(llm_metadata.get('suggested_tags', []))}, "
            f"concepts_count={len(llm_metadata.get('key_concepts',    # 捕获异常：处理业务逻辑
 []))}"
        )
    # 捕获并处理异常
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[文档导入] LLM元数据提取失败，使用回退元数据: "
            f"filename={filename}, error_type={type(e).__name__}, error={e}"
        )
        # 初始化变量 llm_metadata
        llm_metadata = {
            "title": filename.rsplit(".", 1)[0][:100],
  
    # 条件判断：处理业务逻辑
          "summary": extracted_text[:200].strip(),
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "other",
        }
        # 记录日志信息
        logger.info(
            f"[文档导入] 回退元数据: title={llm_metadata['title']}, "
            f"summary_length={len(llm_metadata['summary'])} chars, "
            f"category={llm_metadata['suggested_category']}"
        )

    # 条件判断: 检查 metadata
    if metadata:
        # 记录日志信息
        logger.info(
            f"[文档导入] 应用用户自定义元数据覆盖: override_keys={list(metadata.keys())}"
        )
        llm_metadata.update(metadata)

    # 初始化变量 category
    category = await _resolve_category(llm_metadata["suggested_category"])
    # 记录日志信息
    logger.info(
        f"[文档导入] 分类映射: suggested={llm_metadata['suggested_category']}, "
        f"resolved={category.value}"
    )

    # 初始化变量 db_entry
    db_entry = KnowledgeEntry(
        # 初始化变量 title
        title=llm_metadata["title"],
        # 初始化变量 content
        content=extracted_text,
        # 初始化变量 summary
        summary=llm_metadata["summary"],
        # 初始化变量 category
        category=category,
        # 初始化变量 status
        status=EntryStatus.draft,
        # 初始化变量 source_type
        source_type=SourceType.document_import,
        # 初始化变量 created_by
        created_by=created_by,
    )

    # 记录日志信息
    logger.info(
        f"[文档导入] 准备创建知识条目: title={db_entry.title[:50]}, "
        f"content_length={len(db_entry.content)} chars, "
        f"summary_length={len(db_entry.summary or '')} chars, "
        f"category={db_entry.category.value}, "
        f"source_type={db_entry.sour    # 异常处理：处理业务逻辑
ce_type.value}, "
        f"created_by={created_by}"
    )
    # 尝试执行可能抛出异常的代码
    try:
        db.add(db_entry)
        # 异步等待操作完成
        await db.flush()
        # 记录日志信息
        logger.info(
            f"[文档导入] 知识条目创建成功: entry_id={db_entry.id}, "
            f"title={db_entry.title}, status    # 捕获异常：处理业务逻辑
={db_entry.status.value}"
        )
    # 捕获并处理异常
    except Exception as e:
        # 记录日志信息
        logger.error(
            f"[文档导入] 知识条目创建失败: title={db_entry.title}, "
            f"error_type={type(e).__name__}, error={e}"
        )
        raise

    # 初始化变量 tag_names
    tag_names = llm_metadata.get("suggested_tags", [])
    # 记录日志信息
    logger.info(
        f"[文档导入] 开始关联标签: entry_id={db_entry.id}, "
        f"tag_count={len(tag_names)}, tags={tag_names}"
    )
    # 异步等待操作完成
    await _associate_tags(db, db_entry.id, tag_names)
    # 记录日志信息
    logger.info(
        f"[文档导入] 标签关联完成: entry_id={db_entry.id}, "
        f"associated_tags={tag_names}"
    )

    # 初始化变量 result_metadata
    result_metadata = {
        "title": llm_metadata["title"],
        "summary": llm_metadata["summary"],
        "key_concepts": llm_metadata.get("key_concepts", []),
        "suggested_tags": tag_names,
        "suggested_category": llm_metadata["suggested_category"],
    }

    # 记录日志信息
    logger.info(
        f"[文档导入] 导入完成: entry_id={db_entry.id}, "
        f"title={result_metadata['title'][:50]}, "
        f"category={result_metadata['suggested_category']}, "
        f"tags={tag_names}, concepts={result_metadata['key_concepts']}"
    )
    # 返回处理结果
    return {
        "entry_id": db_entry.id,
        "extracted_metadata": result_metadata,
    }


async def import_from_case(  # noqa: PLR0915
    # 函数 import_from_case 的初始化逻辑
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
    # 初始化变量 case_result
    case_result = await db.execute(select(Case).where(Case.id == case_id))
    # 初始化变量 case
    case = case
    # 条件判断：处理业务逻辑
_result.scalar_one_or_none()

    # 条件判断: 检查 not case
    if not case:
        # 记录日志信息
        logger.error(f"[案件导入] 案件不存在: case_id={case_id}")
        msg = f"案件不存在: case_id={case_id}"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    # 记录日志信息
    logger.info(
        f"[案件导入] 开始导入: c    # 条件判断：处理业务逻辑
ase_id={case_id}, title={case.title}, "
        f"status={case.status.value if case.status else 'N/A'}, "
        f"has_description={bool(case.description and case.description.strip())}"
    )

    # 条件判断: 检查 not case.title or not case.title.strip()
    if not case.title or not case.title.strip():
        # 记录日志信息
        logger.error(f"[案件导入] 案件标题为空: case_id={case_id}")
        msg = f"案件标题为空，无法导入: case_id={case_id}"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    decoded_case_text: str = case.case_text or ""
    # 条件判断: 检查 not decoded_case_text or not decoded_cas
    if not decoded_case_text or not decoded_case_text.strip():
        # 记录日志信息
        logger.error(
            f"[案件导入] 案件文本内容为空: case_id={case_id}, title={case.title}"
        )
        msg = f"案件文本内容为空，无法导入: case_id={case_id}"
        # 抛出异常，处理错误情况
        raise ValueError(msg)

    # 记录日志信息
    logger.info(
        f"[案件导入] 案件文本解密成功: case_id={case_id}, "
        f"text_length={len(decoded_case_text)} chars"
    )

    # 初始化变量 analysis_result
    analysis_result = await db.execute(
        select(Analysis)
        .where(Analysis.case_id == case_id)
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    # 初始化变量 latest_analysis
    latest_analysis = analysis_result.scalar_one_or_none()

    content_parts: list[str] =         # 异常处理：处理业务逻辑
[decoded_case_text]

    # 条件判断: 检查 latest_analysis and latest_analysis.resu
    if latest_analysis and latest_analysis.result_json:
        # 尝试执行可能抛出异常的代码
        try:
            analysis_data: dict[str, Any] | list[Any] = json.loads(
                latest_analysis.result_json
            )
            # 初始化变量 analysis_text
            analysis_text = json.dumps(analysis_data, ensure_ascii=False, indent=2)
            content_parts.append("\n\n--- 案件分析结果 ---\n")
            content_parts.append(analysis_text)
            # 记录日志信息
            logger.info(
                f"[案件导入] 分析结果已附着: case_id={case_id}, "
                f"analysis_id={latest_analysis.id}, "
                f"analysis_mode={latest_analysis.mode.value if latest_analysis.mode else 'N/A'}, "
                f"knowledge_s        # 捕获异常：处理业务逻辑
core={latest_analysis.knowledge_score}"
            )
        # 捕获并处理异常
        except (json.JSONDecodeError, TypeError) as e:
            # 记录日志信息
            logger.warning(
                f"[案件导入] 分析结果JSON解析失败，使用原始文本: "
                f"case_id={case_id}, analysis_id={latest_analysis.id}, error={e}"
            )
            content_parts.append("\n\n--- 案件分析结果 ---\n")
            content_parts.append(str(latest_analysis.result_json))
    # 其他情况的默认处理
    else:
        # 记录日志信息
        logger.info(
            f"[案件导入] 未找到分析结果: case_id={case_id}, "
            f"content仅包含案件事实文本"
        )

    # 初始化变量 full_content
    full_content = "".join(content_parts)
    # 记录日志信息
    logger.info(
        f"[案件导入] 内容组装完成: case_id={case_id}, "
        f"total_length={len(full_content)} chars, "
        f"has_analysis={latest_analysis is not None}"
    )

    # 初始化变量 description
    description = case.description or ""

    # 记录日志信息
    logger.info(
        f"[案件导入] 开    # 异常处理：处理业务逻辑
始LLM元数据提取: case_id={case_id}, "
        f"input_length={min(len(full_content), 8000)} chars"
    )
    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 llm_metadata
        llm_metadata = await extract_metadata_with_llm(full_content[:8000])
        # 记录日志信息
        logger.info(
            f"[案件导入] LLM元数据提取成功: case_id={case_id}, "
            f"title={llm_metadata['title'][:50]}, "
          # 捕获异常：处理业务逻辑
      f"tags_count={len(llm_metadata.get('suggested_tags', []))}"
        )
    # 捕获并处理异常
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[案件导入] LLM元数据提取失败，使用回退元数据: "
            f"case_id={case_id}, error_type={type(e).__name__}, error={e}"
        )
        # 初始化变量 llm_metadata
        llm_metadata = {
            "title": case.title[:100],
            "summary": (description or decoded_case_text)[:200].strip(),
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "case",
        }
        # 记录日志信息
        logger.info(
            f"[案件导入] 回退元数据: case_id={case_id}, "
            f"title={llm_metadata['title']}, "
            f"summary_length={len(llm_metadata['summary'])} chars"
        )

    # 初始化变量 db_entry
    db_entry = KnowledgeEntry(
        # 初始化变量 title
        title=llm_metadata["title"],
        # 初始化变量 content
        content=full_content,
        # 初始化变量 summary
        summary=llm_metadata["summary"],
        # 初始化变量 category
        category=EntryCategory.case,
        # 初始化变量 status
        status=EntryStatus.draft,
        # 初始化变量 source_type
        source_type=SourceType.case_conversion,
        # 初始化变量 source_id
        source_id=case_id,
        # 初始化变量 created_by
        created_by=case.created_by or _SYSTEM_USER_ID,
    )

    # 记录日志信息
    logger.info(
        f"[案件导入] 准备创建知识条目: case_id={case_id}, "
        f"title={db_entry.title[:50]}, "
        f"content_length={len(db_entry.content)} chars, "
        f"summary_length={len(db_entry.summary or '')} chars, "
        f"category={db_entry.category.value}, "
        f"source_type={db_entry    # 异常处理：处理业务逻辑
.source_type.value}, "
        f"source_id={db_entry.source_id}, "
        f"created_by={db_entry.created_by}"
    )
    # 尝试执行可能抛出异常的代码
    try:
        db.add(db_entry)
        # 异步等待操作完成
        await db.flush()
          # 条件判断：处理业务逻辑
  logger.info(
            f"[案件导入] 知识条目创建成功: entry_id={db_entry.id}, "
            f"case_id    # 捕获异常：处理业务逻辑
={case_id}, title={db_entry.title}, "
            f"status={db_entry.status.value}"
        )
    # 捕获并处理异常
    except Exception as e:
        # 记录日志信息
        logger.error(
            f"[案件导入] 知识条目创建失败: case_id={case_id}, "
            f"title={db_entry.title}, error_type={type(e).__name__}, error={e}"
        )
        raise

    # 初始化变量 tag_names
    tag_names = llm_metadata.get("suggested_tags", [])
    # 条件判断: 检查 "案件" not in tag_names
    if "案件" not in tag_names:
        tag_names.append("案件")
        # 记录日志信息
        logger.debug(f"[案件导入] 自动追加默认标签 '案件': case_id={case_id}")

    # 记录日志信息
    logger.info(
        f"[案件导入] 开始关联标签: entry_id={db_entry.id}, "
        f"tag_count={len(tag_names)}, tags={tag_names}"
    )
    # 异步等待操作完成
    await _associate_tags(db, db_entry.id, tag_names)
    # 记录日志信息
    logger.info(
        f"[案件导入] 标签关联完成: entry_id={db_entry.id}, "
        f"associated_tags={tag_names}"
    )

    # 初始化变量 result_metadata
    result_metadata = {
        "title": llm_metadata["title"],
        "summary": llm_metadata["summary"],
        "key_concepts": llm_metadata.get("key_concepts", []),
        "suggested_tags": tag_names,
        "suggested_category": "case",
    }

    # 记录日志信息
    logger.info(
        f"[案件导入] 导入完成: entry_id={db_entry.id}, case_id={case_id}, "
        f"title={result_metadata['title'][:50]}, "
        f"tags={tag_names}, concepts={result_metadata['key_concepts']}"
    )
    # 返回处理结果
    return {
        "entry_id": db_entry.id,
        "extracted_metadata": result_metadata,
    }


async def batch_import_from_cases(
    # 函数 batch_import_from_cases 的初始化逻辑
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
        - failure_case_ids: 失败导入的案件 I
    # 异常处理：处理业务逻辑
D 列表
        - skip_case_ids: 跳过的案件 ID 列表
        - errors: 错误详情列表
    """
    # 导入模块: from app.models.case
    from app.models.case import CaseStatus  # noqa: PLC0415

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 target_status
        target_status = CaseStatus(status)
    # 捕获并处理异常
    except ValueError:
        # 初始化变量 valid_statuses
        valid_statuses = [s.value for s in CaseStatus]
        msg = f"无效的案件状态: '{status}'，有效状态: {valid_statuses}"
        # 抛出异常，处理错误情况
        raise ValueError(msg) from None

    # 初始化变量 cases_result
    cases_result = await db.e        # 条件判断：处理业务逻辑
xecute(
        select(Case.id, Case.title, Case.case_text)
        .where(Case.status == target_status)
        .order_by(Case.id)
    )
    # 初始化变量 cases
    cases = cases_result.all()

    # 条件判断: 检查 not cases
    if not cases:
        # 记录日志信息
        logger.info(f"没有找到状态为 '{status}' 的案件")
        # 返回处理结果
        return BatchImportResult().to_dict()

    # 初始化变量 result
    result = BatchImportResult()
    # 初始化变量 total
    total = len(cases)
  
    # 循环遍历：处理业务逻辑
  logger.info(f"开始批量导入案件: total={total}, status={status}")

    # 遍历: for idx, (case_id, case_title, case_text) in enume
    for idx, (case_id, case_title, case_text) in enumerate(cases):
        # 条件判断: 检查 not case_title or not case_text
        if not case_title or not case_text:
            
        # 异常处理：处理业务逻辑
logger.warning(f"跳过数据不完整的案件: case_id={case_id}")
            result.skip_count += 1
            result.skip_case_ids.append(case_id)
            continue

        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 import_result
            import_result = await import_from_case(db, case_id)
            result.success_count += 1
            result.success_case_ids.append(case_id)
            # 记录日志信息
            logger.info(
                f"案件导入成功: case_id={case_id}, "
            # 捕获异常：处理业务逻辑
            f"entry_id={import_result.get('entry_id')}, "
                f"进度={idx + 1}/{total}"
            )
        # 捕获并处理异常
        except Exception as e:  # noqa: BLE001
            result.failure_count += 1
            result.failure_case_ids.append(case_id)
            result.errors.append({
                "case_id": case_id,
                "case_title": case_title,
                "error": str(e),
            })
            # 记录日志信息
            logger.error(
                f"案件导入失败: case_id={case_id}, error={e}, "
                f"进度={idx + 1}/{total}"
            )

    # 记录日志信息
    logger.info(
        f"批量案件导入完成: success={result.success_count}, "
        f"failure={result.failure_count}, skip={result.skip_count}"
    )
    # 返回处理结果
    return result.to_dict()
