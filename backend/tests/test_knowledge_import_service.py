"""知识导入服务单元测试.

覆盖知识导入服务的所有核心功能，包括文档导入、案件导入、
批量导入和LLM元数据提取等模块。
"""

from __future__ import annotations

import json
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case, CaseStatus
from app.models.entry_tag import EntryTag
from app.models.knowledge_entry import EntryCategory, KnowledgeEntry, SourceType
from app.models.knowledge_tag import KnowledgeTag
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


class TestImportFileWrapper:
    def test_init_with_default_filename(self):
        wrapper = _ImportFileWrapper(b"test content")
        assert wrapper.filename == "document.txt"

    def test_init_with_custom_filename(self):
        wrapper = _ImportFileWrapper(b"test content", "myfile.pdf")
        assert wrapper.filename == "myfile.pdf"

    @pytest.mark.asyncio
    async def test_read_returns_content(self):
        wrapper = _ImportFileWrapper(b"hello world")
        result = await wrapper.read()
        assert result == b"hello world"


class TestImportResult:
    def test_to_dict_success(self):
        result = ImportResult(
            success=True,
            entry_id=1,
            extracted_metadata={"title": "test"},
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["entry_id"] == 1
        assert d["extracted_metadata"] == {"title": "test"}
        assert "error" not in d

    def test_to_dict_with_error(self):
        result = ImportResult(
            success=False,
            error="something went wrong",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["entry_id"] is None
        assert d["error"] == "something went wrong"


class TestBatchImportResult:
    def test_default_values(self):
        result = BatchImportResult()
        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.skip_count == 0
        assert result.success_case_ids == []
        assert result.failure_case_ids == []
        assert result.skip_case_ids == []
        assert result.errors == []

    def test_to_dict(self):
        result = BatchImportResult(
            success_count=3,
            failure_count=1,
            skip_count=2,
            success_case_ids=[1, 2, 3],
            failure_case_ids=[4],
            skip_case_ids=[5, 6],
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


class TestValidateMetadata:
    def test_valid_metadata(self):
        result = _validate_metadata(dict(SAMPLE_METADATA))
        assert result["title"] == "测试知识条目"
        assert result["summary"] == "这是一个测试摘要"
        assert result["key_concepts"] == ["概念A", "概念B", "概念C"]
        assert result["suggested_tags"] == ["标签1", "标签2", "刑法"]
        assert result["suggested_category"] == "law"

    def test_missing_required_field(self):
        data = {"title": "test", "summary": "summary"}
        with pytest.raises(ValueError, match="缺少必需字段"):
            _validate_metadata(data)

    def test_missing_title_field(self):
        data = {
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "law",
        }
        with pytest.raises(ValueError, match="缺少必需字段"):
            _validate_metadata(data)

    def test_empty_title(self):
        data = {
            "title": "",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "law",
        }
        with pytest.raises(ValueError, match="title必须是非空字符串"):
            _validate_metadata(data)

    def test_whitespace_title(self):
        data = {
            "title": "   ",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "law",
        }
        with pytest.raises(ValueError, match="title必须是非空字符串"):
            _validate_metadata(data)

    def test_empty_summary(self):
        data = {
            "title": "test",
            "summary": "",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "law",
        }
        with pytest.raises(ValueError, match="summary必须是非空字符串"):
            _validate_metadata(data)

    def test_non_list_key_concepts_gets_converted(self):
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": "not a list",
            "suggested_tags": [],
            "suggested_category": "law",
        }
        result = _validate_metadata(data)
        assert result["key_concepts"] == []

    def test_key_concepts_with_non_strings_filtered(self):
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": ["valid", 123, "", "  ", None, "another"],
            "suggested_tags": [],
            "suggested_category": "law",
        }
        result = _validate_metadata(data)
        assert result["key_concepts"] == ["valid", "another"]

    def test_non_list_suggested_tags_gets_converted(self):
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": "not a list",
            "suggested_category": "law",
        }
        result = _validate_metadata(data)
        assert result["suggested_tags"] == []

    def test_suggested_tags_with_non_strings_filtered(self):
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": ["tag1", 456, "  ", "tag2"],
            "suggested_category": "law",
        }
        result = _validate_metadata(data)
        assert result["suggested_tags"] == ["tag1", "tag2"]

    def test_invalid_category_defaults_to_other(self):
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "invalid_category",
        }
        result = _validate_metadata(data)
        assert result["suggested_category"] == "other"

    def test_missing_category_raises_error(self):
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
        }
        with pytest.raises(ValueError, match="缺少必需字段"):
            _validate_metadata(data)

    def test_category_case_insensitive(self):
        data = {
            "title": "test",
            "summary": "summary",
            "key_concepts": [],
            "suggested_tags": [],
            "suggested_category": "CASE",
        }
        result = _validate_metadata(data)
        assert result["suggested_category"] == "case"


class TestResolveCategory:
    @pytest.mark.asyncio
    async def test_law_category(self):
        result = await _resolve_category("law")
        assert result == EntryCategory.law

    @pytest.mark.asyncio
    async def test_methodology_category(self):
        result = await _resolve_category("methodology")
        assert result == EntryCategory.methodology

    @pytest.mark.asyncio
    async def test_case_category(self):
        result = await _resolve_category("case")
        assert result == EntryCategory.case

    @pytest.mark.asyncio
    async def test_other_category(self):
        result = await _resolve_category("other")
        assert result == EntryCategory.other

    @pytest.mark.asyncio
    async def test_unknown_category_defaults_to_other(self):
        result = await _resolve_category("unknown")
        assert result == EntryCategory.other


class TestGetOrCreateTag:
    @pytest.mark.asyncio
    async def test_create_new_tag(self, test_db_session: AsyncSession):
        tag = await _get_or_create_tag(test_db_session, "新标签")
        assert tag.id is not None
        assert tag.name == "新标签"
        assert tag.description == "自动创建的标签: 新标签"

    @pytest.mark.asyncio
    async def test_get_existing_tag(self, test_db_session: AsyncSession):
        first_tag = await _get_or_create_tag(test_db_session, "重复标签")
        first_id = first_tag.id

        second_tag = await _get_or_create_tag(test_db_session, "重复标签")
        assert second_tag.id == first_id
        assert second_tag.name == "重复标签"


class TestAssociateTags:
    @pytest.mark.asyncio
    async def test_empty_tag_list(self, test_db_session: AsyncSession):
        result = await _associate_tags(test_db_session, 1, [])
        assert result == []

    @pytest.mark.asyncio
    async def test_associate_multiple_tags(self, test_db_session: AsyncSession):
        entry_id = 999
        tag_names = ["刑法", "盗窃罪", "自首"]

        result = await _associate_tags(test_db_session, entry_id, tag_names)
        assert len(result) == 3
        assert all(tag.id is not None for tag in result)

        for tag in result:
            assert tag.name in tag_names

    @pytest.mark.asyncio
    async def test_duplicate_tags_not_duplicated(self, test_db_session: AsyncSession):
        entry_id = 1000
        tag_names = ["刑法"]

        await _associate_tags(test_db_session, entry_id, tag_names)
        result = await _associate_tags(test_db_session, entry_id, tag_names)
        assert len(result) == 1


class TestExtractMetadataWithLLM:
    @pytest.mark.asyncio
    async def test_successful_extraction(self):
        with patch(
            "app.services.knowledge.manager.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate_json = AsyncMock(
                return_value=dict(SAMPLE_METADATA)
            )
            mock_get_client.return_value = mock_client

            result = await extract_metadata_with_llm("刑事案件文本内容...")
            assert result["title"] == "测试知识条目"
            assert result["summary"] == "这是一个测试摘要"
            assert result["suggested_category"] == "law"

    @pytest.mark.asyncio
    async def test_success_after_one_retry(self):
        with patch(
            "app.services.knowledge.manager.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate_json = AsyncMock(
                side_effect=[
                    {},  # 第一次返回空字典，验证失败
                    dict(SAMPLE_METADATA),  # 第二次成功
                ]
            )
            mock_get_client.return_value = mock_client

            result = await extract_metadata_with_llm("案件文本")
            assert result["title"] == "测试知识条目"

    @pytest.mark.asyncio
    async def test_llm_returns_list_then_dict(self):
        with patch(
            "app.services.knowledge.manager.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate_json = AsyncMock(
                side_effect=[
                    [{"title": "test"}],  # 第一次返回列表
                    dict(SAMPLE_METADATA),  # 第二次返回字典
                ]
            )
            mock_get_client.return_value = mock_client

            result = await extract_metadata_with_llm("案件文本")
            assert result["title"] == "测试知识条目"

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises_error(self):
        with patch(
            "app.services.knowledge.manager.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate_json = AsyncMock(return_value={})
            mock_get_client.return_value = mock_client

            with pytest.raises(ValueError, match="元数据提取失败"):
                await extract_metadata_with_llm("案件文本")

    @pytest.mark.asyncio
    async def test_llm_raises_exception(self):
        with patch(
            "app.services.knowledge.manager.get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate_json = AsyncMock(
                side_effect=RuntimeError("LLM崩溃")
            )
            mock_get_client.return_value = mock_client

            with pytest.raises(ValueError, match="元数据提取失败"):
                await extract_metadata_with_llm("案件文本")


class TestImportFromDocument:
    @pytest.mark.asyncio
    async def test_success_with_file_content(self, test_db_session: AsyncSession):
        file_bytes = "合同纠纷案件事实：甲方未按约定支付货款...".encode()

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            result = await import_from_document(
                test_db_session,
                file_content=file_bytes,
            )

        assert "entry_id" in result
        assert result["entry_id"] is not None
        assert result["extracted_metadata"]["title"] == "测试知识条目"
        assert result["extracted_metadata"]["suggested_category"] == "law"

    @pytest.mark.asyncio
    async def test_success_with_file_path(self, test_db_session: AsyncSession):
        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False, mode="wb"
        ) as tmp:
            tmp.write("民事纠纷案件内容...".encode())
            tmp_path = tmp.name

        try:
            with patch(
                "app.services.knowledge.manager.extract_metadata_with_llm",
                new_callable=AsyncMock,
            ) as mock_extract:
                mock_extract.return_value = dict(SAMPLE_METADATA)

                result = await import_from_document(
                    test_db_session,
                    file_path=tmp_path,
                )

            assert "entry_id" in result
            assert result["entry_id"] is not None
        finally:
            import os  # noqa: PLC0415

            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_no_content_or_path_raises_error(
        self, test_db_session: AsyncSession
    ):
        with pytest.raises(ValueError, match="必须提供 file_content 或 file_path"):
            await import_from_document(test_db_session)

    @pytest.mark.asyncio
    async def test_file_not_found(self, test_db_session: AsyncSession):
        with pytest.raises(FileNotFoundError, match="文件不存在"):
            await import_from_document(
                test_db_session,
                file_path="/nonexistent/path/file.txt",
            )

    @pytest.mark.asyncio
    async def test_empty_content(self, test_db_session: AsyncSession):
        with pytest.raises(ValueError, match="文档内容为空"):
            await import_from_document(
                test_db_session,
                file_content=b"",
            )

    @pytest.mark.asyncio
    async def test_whitespace_only_content(self, test_db_session: AsyncSession):
        with pytest.raises(ValueError, match="文档内容为空"):
            await import_from_document(
                test_db_session,
                file_content=b"   \n  \t  ",
            )

    @pytest.mark.asyncio
    async def test_llm_fallback_on_extraction_error(
        self, test_db_session: AsyncSession
    ):
        file_bytes = "一些法律文本内容，涉及合同纠纷...".encode()

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.side_effect = RuntimeError("LLM不可用")

            result = await import_from_document(
                test_db_session,
                file_content=file_bytes,
            )

        assert "entry_id" in result
        assert result["entry_id"] is not None
        assert result["extracted_metadata"]["suggested_category"] == "other"

    @pytest.mark.asyncio
    async def test_with_user_metadata_override(
        self, test_db_session: AsyncSession
    ):
        file_bytes = "案件内容...".encode()
        user_metadata = {"title": "用户自定义标题", "key_concepts": ["自定义概念"]}

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            result = await import_from_document(
                test_db_session,
                file_content=file_bytes,
                metadata=user_metadata,
            )

        assert result["extracted_metadata"]["title"] == "用户自定义标题"
        assert "自定义概念" in result["extracted_metadata"]["key_concepts"]

    @pytest.mark.asyncio
    async def test_document_processing_error(
        self, test_db_session: AsyncSession
    ):
        with patch(
            "app.services.knowledge.manager.process_document",
            new_callable=AsyncMock,
        ) as mock_process:
            mock_process.side_effect = Exception("文档解析失败")

            with pytest.raises(Exception, match="文档解析失败"):
                await import_from_document(
                    test_db_session,
                    file_content=b"corrupted content",
                )

    @pytest.mark.asyncio
    async def test_tags_created_and_associated(
        self, test_db_session: AsyncSession
    ):
        file_bytes = "知识产权案件文本...".encode()

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            result = await import_from_document(
                test_db_session,
                file_content=file_bytes,
            )

        await test_db_session.flush()

        from sqlalchemy import select  # noqa: PLC0415

        tag_result = await test_db_session.execute(
            select(KnowledgeTag).where(KnowledgeTag.name.in_(["标签1", "标签2", "刑法"]))
        )
        tags = tag_result.scalars().all()
        assert len(tags) == 3

        entry_tag_result = await test_db_session.execute(
            select(EntryTag).where(EntryTag.entry_id == result["entry_id"])
        )
        entry_tags = entry_tag_result.scalars().all()
        assert len(entry_tags) == 3

    @pytest.mark.asyncio
    async def test_file_content_prioritized_over_file_path(
        self, test_db_session: AsyncSession
    ):
        file_content_bytes = "文件内容优先...".encode()

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            result = await import_from_document(
                test_db_session,
                file_content=file_content_bytes,
                file_path="/some/path.txt",
            )

        assert result["entry_id"] is not None


class TestImportFromCase:
    @pytest.mark.asyncio
    async def _create_test_case(self, db: AsyncSession) -> Case:
        case = Case(
            title="测试刑事案件",
            description="这是一起盗窃案件",
            case_text=SAMPLE_CASE_TEXT,
            status=CaseStatus.completed,
            created_by=1,
        )
        db.add(case)
        await db.flush()
        return case

    @pytest.mark.asyncio
    async def test_successful_import(self, test_db_session: AsyncSession):
        case = await self._create_test_case(test_db_session)

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            result = await import_from_case(
                test_db_session,
                case_id=case.id,
            )

        assert "entry_id" in result
        assert result["entry_id"] is not None
        assert result["extracted_metadata"]["suggested_category"] == "case"

    @pytest.mark.asyncio
    async def test_case_not_found(self, test_db_session: AsyncSession):
        with pytest.raises(ValueError, match="案件不存在"):
            await import_from_case(test_db_session, case_id=99999)

    @pytest.mark.asyncio
    async def test_empty_title(self, test_db_session: AsyncSession):
        case = Case(
            title="",
            case_text=SAMPLE_CASE_TEXT,
            status=CaseStatus.completed,
        )
        test_db_session.add(case)
        await test_db_session.flush()

        with pytest.raises(ValueError, match="案件标题为空"):
            await import_from_case(test_db_session, case_id=case.id)

    @pytest.mark.asyncio
    async def test_empty_case_text(self, test_db_session: AsyncSession):
        case = Case(
            title="测试案件",
            case_text="",
            status=CaseStatus.completed,
        )
        test_db_session.add(case)
        await test_db_session.flush()

        with pytest.raises(ValueError, match="案件文本内容为空"):
            await import_from_case(test_db_session, case_id=case.id)

    @pytest.mark.asyncio
    async def test_llm_fallback(self, test_db_session: AsyncSession):
        case = await self._create_test_case(test_db_session)

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.side_effect = RuntimeError("LLM调用失败")

            result = await import_from_case(
                test_db_session,
                case_id=case.id,
            )

        assert "entry_id" in result
        assert result["entry_id"] is not None
        assert result["extracted_metadata"]["suggested_category"] == "case"

    @pytest.mark.asyncio
    async def test_entry_has_correct_category_and_source_type(
        self, test_db_session: AsyncSession
    ):
        case = await self._create_test_case(test_db_session)

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            result = await import_from_case(
                test_db_session,
                case_id=case.id,
            )

        from sqlalchemy import select  # noqa: PLC0415

        entry_result = await test_db_session.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.id == result["entry_id"]
            )
        )
        entry = entry_result.scalar_one()
        assert entry.category == EntryCategory.case
        assert entry.source_type == SourceType.case_conversion
        assert entry.source_id == case.id

    @pytest.mark.asyncio
    async def test_default_tag_added(self, test_db_session: AsyncSession):
        case = await self._create_test_case(test_db_session)

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = {
                "title": "test",
                "summary": "test summary",
                "key_concepts": [],
                "suggested_tags": [],
                "suggested_category": "case",
            }

            result = await import_from_case(
                test_db_session,
                case_id=case.id,
            )

        tag_names = result["extracted_metadata"]["suggested_tags"]
        assert "案件" in tag_names

    @pytest.mark.asyncio
    async def test_with_analysis_result(self, test_db_session: AsyncSession):
        from app.models.analysis import Analysis, AnalysisMode  # noqa: PLC0415

        case = await self._create_test_case(test_db_session)

        analysis = Analysis(
            case_id=case.id,
            result_json=json.dumps(
                {"verdict": "有罪", "sentence": "有期徒刑两年"}
            ),
            knowledge_score=0.75,  # CHECK constraint: 0.0 <= score <= 1.0
            mode=AnalysisMode.single,
        )
        test_db_session.add(analysis)
        await test_db_session.flush()

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            result = await import_from_case(
                test_db_session,
                case_id=case.id,
            )

        from sqlalchemy import select  # noqa: PLC0415

        entry_result = await test_db_session.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.id == result["entry_id"]
            )
        )
        entry = entry_result.scalar_one()
        assert "案件分析结果" in entry.content
        assert "有期徒刑两年" in entry.content


class TestBatchImportFromCases:
    @pytest.mark.asyncio
    async def _create_cases(self, db: AsyncSession, count: int) -> list[Case]:
        cases = []
        for i in range(count):
            case = Case(
                title=f"批量案件{i + 1}",
                case_text=f"案件事实内容{i + 1}...".encode().decode("utf-8"),
                status=CaseStatus.completed,
                created_by=1,
            )
            db.add(case)
            cases.append(case)
        await db.flush()
        return cases

    @pytest.mark.asyncio
    async def test_empty_when_no_matching_cases(
        self, test_db_session: AsyncSession
    ):
        result = await batch_import_from_cases(test_db_session, status="completed")
        assert result["success_count"] == 0
        assert result["failure_count"] == 0
        assert result["skip_count"] == 0

    @pytest.mark.asyncio
    async def test_successful_batch_import(
        self, test_db_session: AsyncSession
    ):
        cases = await self._create_cases(test_db_session, 3)

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            result = await batch_import_from_cases(
                test_db_session, status="completed"
            )

        assert result["success_count"] == 3
        assert result["failure_count"] == 0
        assert len(result["success_case_ids"]) == 3
        for case in cases:
            assert case.id in result["success_case_ids"]

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(
        self, test_db_session: AsyncSession
    ):
        good_cases = await self._create_cases(test_db_session, 2)

        bad_case = Case(
            title="",
            case_text="",
            status=CaseStatus.completed,
        )
        test_db_session.add(bad_case)
        await test_db_session.flush()

        with patch(
            "app.services.knowledge.manager.import_from_case",
            new_callable=AsyncMock,
        ) as mock_import:
            async def mock_import_side_effect(db, case_id):  # noqa: ARG001
                if case_id == good_cases[0].id:
                    msg = "模拟导入失败"
                    raise Exception(msg)
                return {"entry_id": case_id, "extracted_metadata": {}}

            mock_import.side_effect = mock_import_side_effect

            result = await batch_import_from_cases(
                test_db_session, status="completed"
            )

        assert result["success_count"] == 1
        assert result["failure_count"] == 1
        assert result["skip_count"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["case_id"] == good_cases[0].id

    @pytest.mark.asyncio
    async def test_invalid_status_parameter(
        self, test_db_session: AsyncSession
    ):
        with pytest.raises(ValueError, match="无效的案件状态"):
            await batch_import_from_cases(
                test_db_session, status="invalid_status"
            )

    @pytest.mark.asyncio
    async def test_status_pending_cases_not_imported(
        self, test_db_session: AsyncSession
    ):
        case = Case(
            title="待处理案件",
            case_text="案件文本...",
            status=CaseStatus.pending,
        )
        test_db_session.add(case)
        await test_db_session.flush()

        with patch(
            "app.services.knowledge.manager.extract_metadata_with_llm",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = dict(SAMPLE_METADATA)

            result = await batch_import_from_cases(
                test_db_session, status="completed"
            )

        assert result["success_count"] == 0

    @pytest.mark.asyncio
    async def test_skip_incomplete_case_data(
        self, test_db_session: AsyncSession
    ):
        incomplete_case = Case(
            title="",  # 空标题
            case_text="",  # 空文本
            status=CaseStatus.completed,
        )
        test_db_session.add(incomplete_case)
        await test_db_session.flush()

        result = await batch_import_from_cases(
            test_db_session, status="completed"
        )

        assert result["skip_count"] == 1
        assert result["skip_case_ids"] == [incomplete_case.id]
        assert result["success_count"] == 0

    @pytest.mark.asyncio
    async def test_error_isolation_continues_on_failure(
        self, test_db_session: AsyncSession
    ):
        await self._create_cases(test_db_session, 3)

        call_count = 0

        with patch(
            "app.services.knowledge.manager.import_from_case",
            new_callable=AsyncMock,
        ) as mock_import:
            async def side_effect(db, case_id):  # noqa: ARG001
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    msg = "中间案件导入失败"
                    raise Exception(msg)
                return {"entry_id": case_id, "extracted_metadata": {}}

            mock_import.side_effect = side_effect

            result = await batch_import_from_cases(
                test_db_session, status="completed"
            )

        assert result["success_count"] == 2
        assert result["failure_count"] == 1
        assert call_count == 3
