"""知识导入服务单元测试.

覆盖知识导入服务的所有核心功能，包括文档导入、案件导入、
批量导入和LLM元数据提取等模块。
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: json
import json
# 导入模块: tempfile
import tempfile
# 导入模块: from unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch

# 导入模块: pytest
import pytest
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# 导入模块: from app.models.case
from app.models.case import Case, CaseStatus
# 导入模块: from app.models.entry_tag
from app.models.entry_tag import EntryTag
# 导入模块: from app.models.knowledge_entry
from app.models.knowledge_entry import EntryCategory, KnowledgeEntry, SourceType
# 导入模块: from app.models.knowledge_tag
from app.models.knowledge_tag import KnowledgeTag
# 导入模块: from app.services.knowledge_
from app.services.knowledge_import_service import (
    BatchImportResult,
    ImportResult,
    _associate_tags,
    _get_or_create_tag,
    _ImportFileWrapper,
    _resolve_category,
    _validate_metadata,
    batch_import_from_cases,
    extract_metadata_with_llm,
    import_from_case,
    import_from_document,
)


SAMPLE_METADATA: dict = {
    "title": "测试知识条目",
    "summary": "这是一个测试摘要",
    "key_concepts": ["概念A", "概念B", "概念C"],
    "suggested_tags": ["标签1", "标签2", "刑法"],
    "suggested_category": "law",
}

SAMPLE_CASE_TEXT: str = (
    "被告人李某某，2024年1月至3月间，利用职务便利，"
    "非法占有单位财物价值人民币20万元。案发后主动退还全部赃款。"
)


# 定义 TestImportFileWrapper 类
class TestImportFileWrapper:


    # TestImportFileWrapper 类定义，封装相关属性和方法
    def test_init_with_default_filename(self):
        # 执行 test_init_with_default_filename 函数的核心逻辑
        wrapper = _ImportFileWrapper(b"test content")
        assert wrapper.filename == "document.txt"

    def test_init_with_custom_filename(self):

        # 执行 test_init_with_custom_filename 函数的核心逻辑
        wrapper = _ImportFileWrapper(b"test content", "myfile.pdf")
        assert wrapper.filename == "myfile.pdf"

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_read_returns_content(self):
        # 函数 test_read_returns_content 的初始化逻辑
        wrapper = _ImportFileWrapper(b"hello world")
        # 初始化变量 result
        result = await wrapper.read()
        assert result == b"hello world"


# 定义 TestImportResult 类
class TestImportResult:
        # 执行 test_to_dict_success 函数的核心逻辑
    def test_to_dict_success(self):
        # 函数 test_to_dict_success 的初始化逻辑
        result = ImportResult(
            # 初始化变量 success
            success=True,
            # 初始化变量 entry_id
            entry_id=1,
            # 初始化变量 extracted_metadata
            extracted_metadata={"title": "test"},
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["entry_id"] == 1
        assert d["extracted_metadata"] == {"title": "test"}

        # 执行 test_to_dict_with_error 函数的核心逻辑
        assert "error" not in d

    def test_to_dict_with_error(self):
        # 函数 test_to_dict_with_error 的初始化逻辑
        result = ImportResult(
            # 初始化变量 success
            success=False,
            # 初始化变量 error
            error="something went wrong",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["entry_id"] is None
        assert d["error"] == "something went wrong"


# 定义 TestBatchImportResult 类
class TestBatchImportResult:
        # 执行 test_default_values 函数的核心逻辑
    def test_default_values(self):
        # 函数 test_default_values 的初始化逻辑
        result = BatchImportResult()
        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.skip_count == 0
        assert result.success_case_ids == []
        assert result.failure_case_ids == []
        assert result.skip_case_ids == []
        assert result.errors == []

    def test_to_dict(self):

        # 执行 test_to_dict 函数的核心逻辑
        result = BatchImportResult(
            # 初始化变量 success_count
            success_count=3,
            # 初始化变量 failure_count
            failure_count=1,
            # 初始化变量 skip_count
            skip_count=2,
            # 初始化变量 success_case_ids
            success_case_ids=[1, 2, 3],
            # 初始化变量 failure_case_ids
            failure_case_ids=[4],
            # 初始化变量 skip_case_ids
            skip_case_ids=[5, 6],
            # 初始化变量 errors
            errors=[{"case_id": 4, "error": "test error"}],
        )
        d = result.to_dict()
        assert d["success_count"] == 3
        assert d["failure_count"] == 1
        assert d["skip_count"] == 2
        assert d["success_case_ids"] == [1, 2, 3]
        assert d["failure_case_ids"] == [4]
        assert d["skip_case_ids"] == [5, 6]
        assert len(d["errors"]) == 1


# 定义 TestValidateMetadata 类
class TestValidateMetadata:
        # 执行 test_valid_metadata 函数的核心逻辑
    def test_valid_metadata(self):
        # 函数 test_valid_metadata 的初始化逻辑
        result = _validate_metadata(dict(SAMPLE_METADATA))
        assert result["title"] == "测试知识条目"
        assert result["summary"] == "这是一个测试摘要"
        assert result["key_concepts"] == ["概念A", "概念B", "概念C"]
        assert result["suggested_tags"] == ["标签1", "标签2", "刑法"]
        assert result["suggested_category"] == "law"

    def test_missing_required_field(self):

        # 执行 test_missing_required_field 函数的核心逻辑
        data = {"title": "test", "summary": "summary"}
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="缺少必需字段"):
            _validate_metadata(data)

    def test_missing_title_field(self):

        # 执行 test_empty_title 函数的核心逻辑
        data = {
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "law",
        }
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="缺少必需字段"):

        # 执行 test_whitespace_title 函数的核心逻辑
            _validate_metadata(data)

    def test_empty_title(self):
        # 函数 test_empty_title 的初始化逻辑
        data = {
            "title": "",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "law",
        }
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="title必须是非空字符串"):

        # 执行 test_empty_summary 函数的核心逻辑
            _validate_metadata(data)

    def test_whitespace_title(self):
        # 函数 test_whitespace_title 的初始化逻辑
        data = {
            "title": "   ",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "law",
        }
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="title必须是非空字符串"):

        # 执行 test_non_list_key_concepts_gets_converted 函数的核心逻辑
            _validate_metadata(data)

    def test_empty_summary(self):
        # 函数 test_empty_summary 的初始化逻辑
        data = {
            "title": "test",
            "summary": "",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "law",

        # 执行 test_key_concepts_with_non_strings_filtered 函数的核心逻辑
        }
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="summary必须是非空字符串"):
            _validate_metadata(data)

    def test_non_list_key_concepts_gets_converted(self):
        # 函数 test_non_list_key_concepts_gets_converted 的初始化逻辑
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": "not a list",
            "suggested_tags": [],

        # 执行 test_non_list_suggested_tags_gets_converted 函数的核心逻辑
            "suggested_category": "law",
        }
        # 初始化变量 result
        result = _validate_metadata(data)
        assert result["key_concepts"] == []

    def test_key_concepts_with_non_strings_filtered(self):
        # 函数 test_key_concepts_with_non_strings_filtered 的初始化逻辑
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": ["valid", 123, "", "  ", None, "another"],

        # 执行 test_suggested_tags_with_non_strings_filtered 函数的核心逻辑
            "suggested_tags": [],
            "suggested_category": "law",
        }
        # 初始化变量 result
        result = _validate_metadata(data)
        assert result["key_concepts"] == ["valid", "another"]

    def test_non_list_suggested_tags_gets_converted(self):

        # 执行 test_invalid_category_defaults_to_other 函数的核心逻辑
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": "not a list",
            "suggested_category": "law",
        }
        # 初始化变量 result
        result = _validate_metadata(data)
        assert result["suggested_tags"] == []

    def test_suggested_tags_with_non_strings_filtered(self):

        # 执行 test_missing_category_raises_error 函数的核心逻辑
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": ["tag1", 456, "  ", "tag2"],
            "suggested_category": "law",

        # 执行 test_category_case_insensitive 函数的核心逻辑
        }
        # 初始化变量 result
        result = _validate_metadata(data)
        assert result["suggested_tags"] == ["tag1", "tag2"]

    def test_invalid_category_defaults_to_other(self):
        # 函数 test_invalid_category_defaults_to_other 的初始化逻辑
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "invalid_category",
        }
        # 初始化变量 result
        result = _validate_metadata(data)
        assert result["suggested_category"] == "other"

    def test_missing_category_raises_error(self):
        # 函数 test_missing_category_raises_error 的初始化逻辑
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
        }
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="缺少必需字段"):
            _validate_metadata(data)

    def test_category_case_insensitive(self):
        # 函数 test_category_case_insensitive 的初始化逻辑
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "CASE",
        }
        # 初始化变量 result
        result = _validate_metadata(data)
        assert result["suggested_category"] == "case"


# 定义 TestResolveCategory 类
class TestResolveCategory:


    # TestResolveCategory 类定义，封装相关属性和方法
    @pytest.mark.asyncio
    async def test_law_category(self):
        # 函数 test_law_category 的初始化逻辑
        result = await _resolve_category("law")
        assert result == EntryCategory.law

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_methodology_category(self):
        # 函数 test_methodology_category 的初始化逻辑
        result = await _resolve_category("methodology")
        assert result == EntryCategory.methodology

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_case_category(self):
        # 函数 test_case_category 的初始化逻辑
        result = await _resolve_category("case")
        assert result == EntryCategory.case

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_other_category(self):
        # 函数 test_other_category 的初始化逻辑
        result = await _resolve_category("other")
        assert result == EntryCategory.other

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_unknown_category_defaults_to_other(self):
        # 函数 test_unknown_category_defaults_to_other 的初始化逻辑
        result = await _resolve_category("unknown")
        assert result == EntryCategory.other


# 定义 TestGetOrCreateTag 类
class TestGetOrCreateTag:


    # TestGetOrCreateTag 类定义，封装相关属性和方法
    @pytest.mark.asyncio
    async def test_create_new_tag(self, test_db_session: AsyncSession):
        # 函数 test_create_new_tag 的初始化逻辑
        tag = await _get_or_create_tag(test_db_session, "新标签")
        assert tag.id is not None
        assert tag.name == "新标签"
        assert tag.description == "自动创建的标签: 新标签"

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_existing_tag(self, test_db_session: AsyncSession):
        # 函数 test_get_existing_tag 的初始化逻辑
        first_tag = await _get_or_create_tag(test_db_session, "重复标签")
        # 初始化变量 first_id
        first_id = first_tag.id

        # 初始化变量 second_tag
        second_tag = await _get_or_create_tag(test_db_session, "重复标签")
        assert second_tag.id == first_id
        assert second_tag.name == "重复标签"


# 定义 TestAssociateTags 类
class TestAssociateTags:


    # TestAssociateTags 类定义，封装相关属性和方法
    @pytest.mark.asyncio
    async def test_empty_tag_list(self, test_db_session: AsyncSession):
        # 函数 test_empty_tag_list 的初始化逻辑
        result = await _associate_tags(test_db_session, 1, [])
        assert result == []

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_associate_multiple_tags(self, test_db_session: AsyncSession):
        # 函数 test_associate_multiple_tags 的初始化逻辑
        entry_id = 999
        # 初始化变量 tag_names
        tag_names = ["刑法", "盗窃罪", "自首"]

        # 初始化变量 result
        result = await _associate_tags(test_db_session, entry_id, tag_names)
        assert len(result) == 3
        assert all(tag.id is not None for tag in result)

        # 遍历: for tag in result:
        for tag in result:
            assert tag.name in tag_names

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_duplicate_tags_not_duplicated(self, test_db_session: AsyncSession):
        # 函数 test_duplicate_tags_not_duplicated 的初始化逻辑
        entry_id = 1000
        # 初始化变量 tag_names
        tag_names = ["刑法"]

        # 异步等待操作完成
        await _associate_tags(test_db_session, entry_id, tag_names)
        # 初始化变量 result
        result = await _associate_tags(test_db_session, entry_id, tag_names)
        assert len(result) == 1


# 定义 TestExtractMetadataWithLLM 类
class TestExtractMetadataWithLLM:


    # TestExtractMetadataWithLLM 类定义，封装相关属性和方法
    @pytest.mark.asyncio
    async def test_successful_extraction(self):
        # 函数 test_successful_extraction 的初始化逻辑
        with patch(
            "app.services.knowledge_import_service.get_client"
        ) as mock_get_client:
            # 初始化变量 mock_client
            mock_client = MagicMock()
            mock_client.generate_json = AsyncMock(
                return_value=dict(SAMPLE_METADATA)
            )
            mock_get_client.return_value = mock_client

            # 初始化变量 result
            result = await extract_metadata_with_llm("刑事案件文本内容...")
            assert result["title"] == "测试知识条目"
            assert result["summary"] == "这是一个测试摘要"
            assert result["suggested_category"] == "law"

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_success_after_one_retry(self):
        # 函数 test_success_after_one_retry 的初始化逻辑
        with patch(
            "app.services.knowledge_import_service.get_client"
        ) as mock_get_client:
            # 初始化变量 mock_client
            mock_client = MagicMock()
            mock_client.generate_json = AsyncMock(
                # 初始化变量 side_effect
                side_effect=[
                    {},  # 第一次返回空字典，验证失败
                    dict(SAMPLE_METADATA),  # 第二次成功
                ]
            )
            mock_get_client.return_value = mock_client

            # 初始化变量 result
            result = await extract_metadata_with_llm("案件文本")
            assert result["title"] == "测试知识条目"

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_llm_returns_list_then_dict(self):
        # 函数 test_llm_returns_list_then_dict 的初始化逻辑
        with patch(
            "app.services.knowledge_import_service.get_client"
        ) as mock_get_client:
            # 初始化变量 mock_client
            mock_client = MagicMock()
            mock_client.generate_json = AsyncMock(
                # 初始化变量 side_effect
                side_effect=[
                    [{"title": "test"}],  # 第一次返回列表
                    dict(SAMPLE_METADATA),  # 第二次返回字典
                ]
            )
            mock_get_client.return_value = mock_client

            # 初始化变量 result
            result = await extract_metadata_with_llm("案件文本")
            assert result["title"] == "测试知识条目"

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_exhausted_retries_raises_error(self):
        # 函数 test_exhausted_retries_raises_error 的初始化逻辑
        with patch(
            "app.services.knowledge_import_service.get_client"
        ) as mock_get_client:
            # 初始化变量 mock_client
            mock_client = MagicMock()
            mock_client.generate_json = AsyncMock(return_value={})
            mock_get_client.return_value = mock_client

            # 使用上下文管理器管理资源
            with pytest.raises(ValueError, match="元数据提取失败"):
                # 异步等待操作完成
                await extract_metadata_with_llm("案件文本")

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_llm_raises_exception(self):
        # 函数 test_llm_raises_exception 的初始化逻辑
        with patch(
            "app.services.knowledge_import_service.get_client"
        ) as mock_get_client:
            # 初始化变量 mock_client
            mock_client = MagicMock()
            mock_client.generate_json = AsyncMock(
                # 初始化变量 side_effect
                side_effect=RuntimeError("LLM崩溃")
            )
            mock_get_client.return_value = mock_client

            # 使用上下文管理器管理资源
            with pytest.raises(ValueError, match="元数据提取失败"):


    # TestImportFromDocument 类定义，封装相关属性和方法
                await extract_metadata_with_llm("案件文本")


# 定义 TestImportFromDocument 类
class TestImportFromDocument:
    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_success_with_file_content(self, test_db_session: AsyncSession):
        # 函数 test_success_with_file_content 的初始化逻辑
        file_bytes = "合同纠纷案件事实：甲方未按约定支付货款...".encode()

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            # 初始化变量 result
            result = await import_from_document(
                test_db_session,
                # 初始化变量 file_content
                file_content=file_bytes,
            )

        assert "entry_id" in result
        assert result["entry_id"] is not None
        assert result["extracted_metadata"]["title"] == "测试知识条目"
        assert result["extracted_metadata"]["suggested_category"] == "law"

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_success_with_file_path(self, test_db_session: AsyncSession):
        # 函数 test_success_with_file_path 的初始化逻辑
        with tempfile.NamedTemporaryFile(
            # 初始化变量 suffix
            suffix=".txt", delete=False, mode="wb"
        ) as tmp:
            tmp.write("民事纠纷案件内容...".encode())
            # 初始化变量 tmp_path
            tmp_path = tmp.name

        # 尝试执行可能抛出异常的代码
        try:
            # 使用上下文管理器管理资源
            with patch(
                "app.services.knowledge_import_service.extract_metadata_with_llm",
                # 初始化变量 new_callable
                new_callable=AsyncMock,
            ) as mock_extract:
                mock_extract.return_value = dict(SAMPLE_METADATA)

                # 初始化变量 result
                result = await import_from_document(
                    test_db_session,
                    # 初始化变量 file_path
                    file_path=tmp_path,
                )

            assert "entry_id" in result
            assert result["entry_id"] is not None
        # 最终清理代码，无论是否异常都会执行
        finally:
            # 导入模块: os  # noqa: PLC0415
            import os  # noqa: PLC0415

            os.unlink(tmp_path)

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_no_content_or_path_raises_error(
        # 函数 test_no_content_or_path_raises_error 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="必须提供 file_content 或 file_path"):
            # 异步等待操作完成
            await import_from_document(test_db_session)

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_file_not_found(self, test_db_session: AsyncSession):
        # 函数 test_file_not_found 的初始化逻辑
        with pytest.raises(FileNotFoundError, match="文件不存在"):
            # 异步等待操作完成
            await import_from_document(
                test_db_session,
                # 初始化变量 file_path
                file_path="/nonexistent/path/file.txt",
            )

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_empty_content(self, test_db_session: AsyncSession):
        # 函数 test_empty_content 的初始化逻辑
        with pytest.raises(ValueError, match="文档内容为空"):
            # 异步等待操作完成
            await import_from_document(
                test_db_session,
                # 初始化变量 file_content
                file_content=b"",
            )

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_whitespace_only_content(self, test_db_session: AsyncSession):
        # 函数 test_whitespace_only_content 的初始化逻辑
        with pytest.raises(ValueError, match="文档内容为空"):
            # 异步等待操作完成
            await import_from_document(
                test_db_session,
                # 初始化变量 file_content
                file_content=b"   \n  \t  ",
            )

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_llm_fallback_on_extraction_error(
        # 函数 test_llm_fallback_on_extraction_error 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 初始化变量 file_bytes
        file_bytes = "一些法律文本内容，涉及合同纠纷...".encode()

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.side_effect = RuntimeError("LLM不可用")

            # 初始化变量 result
            result = await import_from_document(
                test_db_session,
                # 初始化变量 file_content
                file_content=file_bytes,
            )

        assert "entry_id" in result
        assert result["entry_id"] is not None
        assert result["extracted_metadata"]["suggested_category"] == "other"

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_with_user_metadata_override(
        # 函数 test_with_user_metadata_override 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 初始化变量 file_bytes
        file_bytes = "案件内容...".encode()
        # 初始化变量 user_metadata
        user_metadata = {"title": "用户自定义标题", "key_concepts": ["自定义概念"]}

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            # 初始化变量 result
            result = await import_from_document(
                test_db_session,
                # 初始化变量 file_content
                file_content=file_bytes,
                # 初始化变量 metadata
                metadata=user_metadata,
            )

        assert result["extracted_metadata"]["title"] == "用户自定义标题"
        assert "自定义概念" in result["extracted_metadata"]["key_concepts"]

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_document_processing_error(
        # 函数 test_document_processing_error 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.process_document",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_process:
            mock_process.side_effect = Exception("文档解析失败")

            # 使用上下文管理器管理资源
            with pytest.raises(Exception, match="文档解析失败"):
                # 异步等待操作完成
                await import_from_document(
                    test_db_session,
                    # 初始化变量 file_content
                    file_content=b"corrupted content",
                )

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_tags_created_and_associated(
        # 函数 test_tags_created_and_associated 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 初始化变量 file_bytes
        file_bytes = "知识产权案件文本...".encode()

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            # 初始化变量 result
            result = await import_from_document(
                test_db_session,
                # 初始化变量 file_content
                file_content=file_bytes,
            )

        # 异步等待操作完成
        await test_db_session.flush()

        # 导入模块: from sqlalchemy
        from sqlalchemy import select  # noqa: PLC0415

        # 初始化变量 tag_result
        tag_result = await test_db_session.execute(
            select(KnowledgeTag).where(KnowledgeTag.name.in_(["标签1", "标签2", "刑法"]))
        )
        # 初始化变量 tags
        tags = tag_result.scalars().all()
        assert len(tags) == 3

        # 初始化变量 entry_tag_result
        entry_tag_result = await test_db_session.execute(
            select(EntryTag).where(EntryTag.entry_id == result["entry_id"])
        )
        # 初始化变量 entry_tags
        entry_tags = entry_tag_result.scalars().all()
        assert len(entry_tags) == 3

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_file_content_prioritized_over_file_path(
        # 函数 test_file_content_prioritized_over_file_path 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 初始化变量 file_content_bytes
        file_content_bytes = "文件内容优先...".encode()

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            # 初始化变量 result
            result = await import_from_document(
                test_db_session,
                # 初始化变量 file_content
                file_content=file_content_bytes,
                # 初始化变量 file_path
                file_path="/some/path.txt",
            )

        assert result["entry_id"] is not None


# 定义 TestImportFromCase 类
class TestImportFromCase:


    # TestImportFromCase 类定义，封装相关属性和方法
    @pytest.mark.asyncio
    async def _create_test_case(self, db: AsyncSession) -> Case:
        # 函数 _create_test_case 的初始化逻辑
        case = Case(
            # 初始化变量 title
            title="测试刑事案件",
            # 初始化变量 description
            description="这是一起盗窃案件",
            # 初始化变量 case_text
            case_text=SAMPLE_CASE_TEXT,
            # 初始化变量 status
            status=CaseStatus.completed,
            # 初始化变量 created_by
            created_by=1,
        )
        db.add(case)
        # 异步等待操作完成
        await db.flush()
        # 返回处理结果
        return case

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_successful_import(self, test_db_session: AsyncSession):
        # 函数 test_successful_import 的初始化逻辑
        case = await self._create_test_case(test_db_session)

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            # 初始化变量 result
            result = await import_from_case(
                test_db_session,
                # 初始化变量 case_id
                case_id=case.id,
            )

        assert "entry_id" in result
        assert result["entry_id"] is not None
        assert result["extracted_metadata"]["suggested_category"] == "case"

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_case_not_found(self, test_db_session: AsyncSession):
        # 函数 test_case_not_found 的初始化逻辑
        with pytest.raises(ValueError, match="案件不存在"):
            # 异步等待操作完成
            await import_from_case(test_db_session, case_id=99999)

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_empty_title(self, test_db_session: AsyncSession):
        # 函数 test_empty_title 的初始化逻辑
        case = Case(
            # 初始化变量 title
            title="",
            # 初始化变量 case_text
            case_text=SAMPLE_CASE_TEXT,
            # 初始化变量 status
            status=CaseStatus.completed,
        )
        test_db_session.add(case)
        # 异步等待操作完成
        await test_db_session.flush()

        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="案件标题为空"):
            # 异步等待操作完成
            await import_from_case(test_db_session, case_id=case.id)

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_empty_case_text(self, test_db_session: AsyncSession):
        # 函数 test_empty_case_text 的初始化逻辑
        case = Case(
            # 初始化变量 title
            title="测试案件",
            # 初始化变量 case_text
            case_text="",
            # 初始化变量 status
            status=CaseStatus.completed,
        )
        test_db_session.add(case)
        # 异步等待操作完成
        await test_db_session.flush()

        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="案件文本内容为空"):
            # 异步等待操作完成
            await import_from_case(test_db_session, case_id=case.id)

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_llm_fallback(self, test_db_session: AsyncSession):
        # 函数 test_llm_fallback 的初始化逻辑
        case = await self._create_test_case(test_db_session)

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.side_effect = RuntimeError("LLM调用失败")

            # 初始化变量 result
            result = await import_from_case(
                test_db_session,
                # 初始化变量 case_id
                case_id=case.id,
            )

        assert "entry_id" in result
        assert result["entry_id"] is not None
        assert result["extracted_metadata"]["suggested_category"] == "case"

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_entry_has_correct_category_and_source_type(
        # 函数 test_entry_has_correct_category_and_source_type 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 初始化变量 case
        case = await self._create_test_case(test_db_session)

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            # 初始化变量 result
            result = await import_from_case(
                test_db_session,
                # 初始化变量 case_id
                case_id=case.id,
            )

        # 导入模块: from sqlalchemy
        from sqlalchemy import select  # noqa: PLC0415

        # 初始化变量 entry_result
        entry_result = await test_db_session.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.id == result["entry_id"]
            )
        )
        # 初始化变量 entry
        entry = entry_result.scalar_one()
        assert entry.category == EntryCategory.case
        assert entry.source_type == SourceType.case_conversion
        assert entry.source_id == case.id

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_default_tag_added(self, test_db_session: AsyncSession):
        # 函数 test_default_tag_added 的初始化逻辑
        case = await self._create_test_case(test_db_session)

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = {
                "title": "test",
                "summary": "test summary",
                "key_concepts": [],
                "suggested_tags": [],
                "suggested_category": "case",
            }

            # 初始化变量 result
            result = await import_from_case(
                test_db_session,
                # 初始化变量 case_id
                case_id=case.id,
            )

        # 初始化变量 tag_names
        tag_names = result["extracted_metadata"]["suggested_tags"]
        assert "案件" in tag_names

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_with_analysis_result(self, test_db_session: AsyncSession):
        # 函数 test_with_analysis_result 的初始化逻辑
        from app.models.analysis import Analysis, AnalysisMode  # noqa: PLC0415

        # 初始化变量 case
        case = await self._create_test_case(test_db_session)

        # 初始化变量 analysis
        analysis = Analysis(
            # 初始化变量 case_id
            case_id=case.id,
            # 初始化变量 result_json
            result_json=json.dumps(
                {"verdict": "有罪", "sentence": "有期徒刑两年"}
            ),
            # 初始化变量 knowledge_score
            knowledge_score=0.75,  # CHECK constraint: 0.0 <= score <= 1.0
            mode=AnalysisMode.single,
        )
        test_db_session.add(analysis)
        # 异步等待操作完成
        await test_db_session.flush()

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            # 初始化变量 result
            result = await import_from_case(
                test_db_session,
                # 初始化变量 case_id
                case_id=case.id,
            )

        # 导入模块: from sqlalchemy
        from sqlalchemy import select  # noqa: PLC0415

        # 初始化变量 entry_result
        entry_result = await test_db_session.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.id == result["entry_id"]
            )
        )
        # 初始化变量 entry
        entry = entry_result.scalar_one()
        assert "案件分析结果" in entry.content
        assert "有期徒刑两年" in entry.content


# 定义 TestBatchImportFromCases 类
class TestBatchImportFromCases:


    # TestBatchImportFromCases 类定义，封装相关属性和方法
    @pytest.mark.asyncio
    async def _create_cases(self, db: AsyncSession, count: int) -> list[Case]:
        # 函数 _create_cases 的初始化逻辑
        cases = []
        # 循环遍历：处理业务逻辑
        for i in range(count):
            # 初始化变量 case
            case = Case(
                # 初始化变量 title
                title=f"批量案件{i + 1}",
                # 初始化变量 case_text
                case_text=f"案件事实内容{i + 1}...".encode().decode("utf-8"),
                # 初始化变量 status
                status=CaseStatus.completed,
                # 初始化变量 created_by
                created_by=1,
            )
            db.add(case)
            cases.append(case)
        # 异步等待操作完成
        await db.flush()
        # 返回处理结果
        return cases

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_empty_when_no_matching_cases(
        # 函数 test_empty_when_no_matching_cases 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 初始化变量 result
        result = await batch_import_from_cases(test_db_session, status="completed")
        assert result["success_count"] == 0
        assert result["failure_count"] == 0
        assert result["skip_count"] == 0

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_successful_batch_import(
        # 函数 test_successful_batch_import 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 初始化变量 cases
        cases = await self._create_cases(test_db_session, 3)

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            # 初始化变量 result
            result = await batch_import_from_cases(
                test_db_session, status="completed"
            )

        assert result["success_count"] == 3
        assert result["failure_count"] == 0
        assert len(result["suc        # 循环遍历：处理业务逻辑
cess_case_ids"]) == 3
        # 遍历: for case in cases:
        for case in cases:
            assert case.id in result["success_case_ids"]

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(
        # 函数 test_mixed_success_and_failure 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 初始化变量 good_cases
        good_cases = await self._create_cases(test_db_session, 2)

        # 初始化变量 bad_case
        bad_case = Case(
            # 初始化变量 title
            title="",
            # 初始化变量 case_text
            case_text="",
            # 初始化变量 status
            status=CaseStatus.completed,
        )
        test_db_session.add(bad_case)
        # 异步等待操作完成
        await test_db_session.flush()

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.import_from_case",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_import:
            async def mock_import_side_effect(db, case_id):  # noqa: ARG001
                # 条件判断：处理业务逻辑
                if case_id == good_cases[0].id:
                    msg = "模拟导入失败"
                    # 抛出异常，处理错误情况
                    raise Exception(msg)
                # 返回处理结果
                return {"entry_id": case_id, "extracted_metadata": {}}

            mock_import.side_effect = mock_import_side_effect

            # 初始化变量 result
            result = await batch_import_from_cases(
                test_db_session, status="completed"
            )

        assert result["success_count"] == 1
        assert result["failure_count"] == 1
        assert result["skip_count"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["case_id"] == good_cases[0].id

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_invalid_status_parameter(
        # 函数 test_invalid_status_parameter 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="无效的案件状态"):
            # 异步等待操作完成
            await batch_import_from_cases(
                test_db_session, status="invalid_status"
            )

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_status_pending_cases_not_imported(
        # 函数 test_status_pending_cases_not_imported 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 初始化变量 case
        case = Case(
            # 初始化变量 title
            title="待处理案件",
            # 初始化变量 case_text
            case_text="案件文本...",
            # 初始化变量 status
            status=CaseStatus.pending,
        )
        test_db_session.add(case)
        # 异步等待操作完成
        await test_db_session.flush()

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.extract_metadata_with_llm",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            # 初始化变量 result
            result = await batch_import_from_cases(
                test_db_session, status="completed"
            )

        assert result["success_count"] == 0

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_skip_incomplete_case_data(
        # 函数 test_skip_incomplete_case_data 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 初始化变量 incomplete_case
        incomplete_case = Case(
            # 初始化变量 title
            title="",  # 空标题
            case_text="",  # 空文本
            status=CaseStatus.completed,
        )
        test_db_session.add(incomplete_case)
        # 异步等待操作完成
        await test_db_session.flush()

        # 初始化变量 result
        result = await batch_import_from_cases(
            test_db_session, status="completed"
        )

        assert result["skip_count"] == 1
        assert result["skip_case_ids"] == [incomplete_case.id]
        assert result["success_count"] == 0

    # 应用装饰器: pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_error_isolation_continues_on_failure(
        # 函数 test_error_isolation_continues_on_failure 的初始化逻辑
        self, test_db_session: AsyncSession
    ):
        # 异步等待操作完成
        await self._create_cases(test_db_session, 3)

        # 初始化变量 call_count
        call_count = 0

        # 使用上下文管理器管理资源
        with patch(
            "app.services.knowledge_import_service.import_from_case",
            # 初始化变量 new_callable
            new_callable=AsyncMock,
        ) as mock_import:
            async def side_effect(db, case_id):  # noqa: ARG001
                # 函数 side_effect 的初始化逻辑
                nonlocal call_count
                  # 条件判断：处理业务逻辑
              call_count += 1
                # 条件判断: 检查 call_count == 2
                if call_count == 2:
                    msg = "中间案件导入失败"
                    # 抛出异常，处理错误情况
                    raise Exception(msg)
                # 返回处理结果
                return {"entry_id": case_id, "extracted_metadata": {}}

            mock_import.side_effect = side_effect

            # 初始化变量 result
            result = await batch_import_from_cases(
                test_db_session, status="completed"
            )

        assert result["success_count"] == 2
        assert result["failure_count"] == 1
        assert call_count == 3
