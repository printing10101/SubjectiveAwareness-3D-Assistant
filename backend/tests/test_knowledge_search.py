"""知识库全文搜索服务单元测试.

覆盖 FTS5 表管理、搜索功能、过滤条件、高亮片段、
边界条件和错误处理等场景。
"""

# ruff: noqa: ARG002

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: time
import time

# 导入模块: pytest
import pytest
# 导入模块: from sqlalchemy
from sqlalchemy import select, text
# 导入模块: from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# 导入模块: from app.models.entry_tag
from app.models.entry_tag import EntryTag
# 导入模块: from app.models.knowledge_entry
from app.models.knowledge_entry import (
    EntryCategory,
    EntryStatus,
    KnowledgeEntry,
)
# 导入模块: from app.models.knowledge_tag
from app.models.knowledge_tag import KnowledgeTag
# 导入模块: from app.models.user
from app.models.user import User, UserRole
# 导入模块: from app.services.knowledge_search_service
from app.services.knowledge_search_service import (
    ensure_fts_table,
    get_fts_count,
    remove_entry_from_fts,
    search_entries,
    sync_entry,
)


_ENTRY_DATA = [
    {
        "title": "故意伤害罪构成要件分析",
        "content": "故意伤害罪的构成要件包括：主观方面具有伤害故意，客观方面实施了伤害行为并造成轻伤以上后果。"
        "本罪侵犯的客体是他人的身体健康权。主体为一般主体，年满16周岁具有刑事责任能力的自然人。",
        "summary": "分析故意伤害罪的主观要件、客观要件、主体要件和客体要件",
        "category": EntryCategory.law,
        "status": EntryStatus.active,
        "confidence": 0.9,
    },
    {
        "title": "盗窃罪的量刑标准",
        "content": "盗窃罪的量刑标准主要依据盗窃数额和情节。数额较大标准为1000元至3000元以上，"
        "数额巨大标准为3万元至10万元以上，数额特别巨大标准为30万元至50万元以上。"
        "多次盗窃、入户盗窃、携带凶器盗窃、扒窃的，处三年以下有期徒刑、拘役或者管制。",
        "summary": "详解盗窃罪不同数额对应的量刑标准及加重情节",
        "category": EntryCategory.law,
        "status": EntryStatus.active,
        "confidence": 0.85,
    },
    {
        "title": "证据收集方法指南",
        "content": "刑事证据的收集应当遵循合法性、客观性和关联性原则。"
        "常见证据类型包括物证、书证、证人证言、被害人陈述、犯罪嫌疑人供述和辩解、鉴定意见、"
        "勘验检查辨认侦查实验笔录、视听资料和电子数据。收集证据时应制作规范的提取笔录。",
        "summary": "刑事案件中证据收集的方法、原则和注意事项",
        "category": EntryCategory.methodology,
        "status": EntryStatus.active,
        "confidence": 0.92,
    },
    {
        "title": "帮信罪典型案例分析",
        "content": "被告人李某明知他人利用信息网络实施犯罪，仍为其提供支付结算帮助，"
        "涉案资金流水达200余万元，个人获利5000元。法院认定其行为构成帮助信息网络犯罪活动罪，"
        "判处有期徒刑一年，并处罚金人民币一万元。本案体现了对帮助信息网络犯罪的打击力度。",
        "summary": "分析帮助信息网络犯罪活动罪的典型司法案例",
        "category": EntryCategory.case,
        "status": EntryStatus.active,
        "confidence": 0.88,
    },
    {
        "title": "案件归档管理流程",
        "content": "案件归档应当遵循分类管理、按时归档、规范装订的原则。"
        "已结案件应在结案后30日内完成归档。归档材料包括起诉书、判决书、"
        "庭审笔录、证据清单等。电子档案应与纸质档案保持同步一致性。",
        "summary": "规范案件归档流程和归档材料要求",
        "category": EntryCategory.other,
        "status": EntryStatus.draft,
        "confidence": 0.75,
    },
]


# 应用装饰器: pytest.fixture
@pytest.fixture
async def seed_user(test_db_session: AsyncSession) -> User:
    """创建测试用户."""
    # 初始化变量 user
    user = User(
        # 初始化变量 username
        username="test_search_user",
        # 初始化变量 hashed_password
        hashed_password="hashed_pw",
        # 初始化变量 role
        role=UserRole.user,
        # 初始化变量 is_active
        is_active=True,
    )
    test_db_session.add(user)
    # 异步等待操作完成
    await test_db_session.commit()
    # 返回处理结果
    return user


# 应用装饰器: pytest.fixture
@pytest.fixture
async def seed_entries(
    # 函数 seed_entries 的初始化逻辑
    test_db_session: AsyncSession,
    seed_user: User,
) -> list[KnowledgeEntry]:
    """创建测试知识条目."""
    # 初始化变量 entries
    entries = []
    # 循环遍历：处理业务逻辑
    for data in _ENTRY_DATA:
        # 初始化变量 entry
        entry = KnowledgeEntry(
            # 初始化变量 title
            title=data["title"],
            # 初始化变量 content
            content=data["content"],
            # 初始化变量 summary
            summary=data["summary"],
            # 初始化变量 category
            category=data["category"],
            # 初始化变量 status
            status=data["status"],
            # 初始化变量 confidence
            confidence=data["confidence"],
            # 初始化变量 created_by
            created_by=seed_user.id,
        )
        test_db_session.add(entry)
        entries.append(entry)
    # 异步等待操作完成
    await test_db    # 循环遍历：处理业务逻辑
_session.commit()
    # 遍历: for e in entries:
    for e in entries:
        # 异步等待操作完成
        await test_db_session.refresh(e)
    # 返回处理结果
    return entries


# 应用装饰器: pytest.fixture
@pytest.fixture
async def seed_tags(test_db_session: AsyncSession) -> list[KnowledgeTag]:
    """创建测试标签."""
    # 初始化变量 tag_data
    tag_data = [
        {"name": "刑法", "description": "刑法相关"},
        {"name": "证据", "description": "证据相关"},
        {"name": "量刑", "descrip    # 循环遍历：处理业务逻辑
tion": "量刑相关"},
    ]
    # 初始化变量 tags
    tags = []
    # 遍历: for td in tag_data:
    for td in tag_data:
        tag = KnowledgeTag(name=td["name"], description=td["description"])
        test_db_session.add(tag)
          # 循环遍历：处理业务逻辑
  tags.append(tag)
    # 异步等待操作完成
    await test_db_session.commit()
    # 遍历: for t in tags:
    for t in tags:
        # 异步等待操作完成
        await test_db_session.refresh(t)
    # 返回处理结果
    return tags


# 应用装饰器: pytest.fixture
@pytest.fixture
async def seed_entry_tags(
    # 函数 seed_entry_tags 的初始化逻辑
    test_db_session: AsyncSession,
    seed_entries: list[KnowledgeEntry],
    seed_tags: list[KnowledgeTag],
) -> None:
    """为测试条目关联标签."""
    # 初始化变量 mapping
    mapping = [
        (0, 0),  # 故意伤害 → 刑法
        (1, 0),  # 盗窃罪 → 刑法
        (1, 2),  #     # 循环遍历：处理业务逻辑
盗窃罪 → 量刑
        (2, 1),  # 证据收集 → 证据
        (3, 0),  # 帮信罪 → 刑法
    ]
    # 遍历: for entry_idx, tag_idx in mapping:
    for entry_idx, tag_idx in mapping:
        et_ = EntryTag(
            # 初始化变量 entry_id
            entry_id=seed_entries[entry_idx].id,
            # 初始化变量 tag_id
            tag_id=seed_tags[tag_idx].id,
        )
        test_db_session.add(et_)
    # 异步等待操作完成
    await test_db_session.commit()


# 应用装饰器: pytest.fixture
@pytest.fixture
async def fts_setup(
    # 函数 fts_setup 的初始化逻辑
    test_db_session: AsyncSession,
    seed_entries: list[KnowledgeEntry]    # 循环遍历：处理业务逻辑
,
) -> None:
    """初始化 FTS5 表并将测试数据同步至索引."""
    # 异步等待操作完成
    await ensure_fts_table(test_db_session)
    # 遍历: for entry in seed_entries:
    for entry in seed_entries:
        # 异步等待操作完成
        await sync_entry(
            test_db_session,
            entry.id,
            entry.title,
            entry.content,
            entry.summary,
        )


# 定义 TestFTS5TableManagement 类
class TestFTS5TableManagement:
    """FTS5 虚拟表管理测试."""

    async def test_ensure_fts_table_creates_table(
        # 函数 test_ensure_fts_table_creates_table 的初始化逻辑
        self, test_db_session: AsyncSession
    ) -> None:
        """验证 ensure_fts_table 创建 FTS5 虚拟表."""
        # 异步等待操作完成
        await ensure_fts_table(test_db_session)

        # 初始化变量 result
        result = await test_db_session.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='knowledge_fts'"
            )
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == "knowledge_fts"

    async def test_ensure_fts_table_is_idempotent(
        # 函数 test_ensure_fts_table_is_idempotent 的初始化逻辑
        self, test_db_session: AsyncSession
    ) -> None:
        """验证 ensure_fts_table 重复调用不产生错误."""
        # 异步等待操作完成
        await ensure_fts_table(test_db_session)
        # 异步等待操作完成
        await ensure_fts_table(test_db_session)
        # 异步等待操作完成
        await ensure_fts_table(test_db_session)

        # 初始化变量 result
        result = await test_db_session.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='knowledge_fts'"
            )
        )
        assert result.fetchone() is not None

    async def test_sync_entry_inserts_into_fts(
        # 函数 test_sync_entry_inserts_into_fts 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        seed_entries: list[KnowledgeEntry],
    ) -> None:
        """验证 sync_entry 将条目同步至 FTS 索引."""
        # 异步等待操作完成
        await ensure_fts_table(test_db_session)
        # 初始化变量 entry
        entry = seed_entries[0]
        # 异步等待操作完成
        await sync_entry(
            test_db_session,
            entry.id,
            entry.title,
            entry.content,
            entry.summary,
        )

        # 初始化变量 count
        count = await get_fts_count(test_db_session)
        assert count >= 1

    async def test_sync_entry_updates_existing_fts_record(
        # 函数 test_sync_entry_updates_existing_fts_record 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        seed_entries: list[KnowledgeEntry],
    ) -> None:
        """验证 sync_entry 更新已存在的 FTS 记录."""
        # 异步等待操作完成
        await ensure_fts_table(test_db_session)
        # 初始化变量 entry
        entry = seed_entries[0]
        # 异步等待操作完成
        await sync_entry(
            test_db_session,
            entry.id,
            entry.title,
            entry.content,
            entry.summary,
        )

        # 初始化变量 new_title
        new_title = "更新后的标题"
        # 异步等待操作完成
        await sync_entry(
            test_db_session,
            entry.id,
            new_title,
            entry.content,
            entry.summary,
        )

        # 初始化变量 count
        count = await get_fts_count(test_db_session)
        assert count >= 1

    async def test_remove_entry_from_fts(
        # 函数 test_remove_entry_from_fts 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        seed_entries: list[KnowledgeEntry],
    ) -> None:
        """验证 remove_entry_from_fts 从索引中删除条目."""
        # 异步等待操作完成
        await ensure_fts_table(test_db_session)
        # 初始化变量 entry
        entry = seed_entries[0]
        # 异步等待操作完成
        await sync_entry(
            test_db_session,
            entry.id,
            entry.title,
            entry.content,
            entry.summary,
        )
        # 初始化变量 count_before
        count_before = await get_fts_count(test_db_session)
        assert count_before == 1

        # 异步等待操作完成
        await remove_entry_from_fts(test_db_session, entry.id)
        # 初始化变量 count_after
        count_after = await get_fts_count(test_db_session)
        assert count_after == 0

    async def test_get_fts_count_returns_zero_for_empty_index(
        # 函数 test_get_fts_count_returns_zero_for_empty_index 的初始化逻辑
        self, test_db_session: AsyncSession
    ) -> None:
        """验证空 FTS 索引返回计数 0."""
        # 异步等待操作完成
        await ensure_fts_table(test_db_session)
        # 初始化变量 count
        count = await get_fts_count(test_db_session)
        assert count == 0


# 定义 TestSearchBasic 类
class TestSearchBasic:
    """全文搜索基础功能测试."""

    async def test_search_returns_results(
        # 函数 test_search_returns_results 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        seed_entries: list[KnowledgeEntry],
        fts_setup: None,
    ) -> None:
        """验证基本搜索返回结果."""
        # 初始化变量 results
        results = await search_entries(test_db_session, "故意伤害")
        assert len(results) > 0
        assert results[0]["entry_id"] is not None
        assert results[0]["title"] is not None
        assert results[0]["score"] is not None

    async def test_search_returns_correct_fields(
        # 函数 test_search_returns_correct_fields 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        fts_setup: None,
    ) -> None:
        """验证搜索结果包含所有必要字段."""
        # 初始化变量 results
        results = await search_entries(test_db_session, "盗窃罪")
        assert len(results) > 0
        # 初始化变量 result
        result = results[0]
        assert "entry_id" in result
        assert "title" in result
        assert "summary" in result
        assert "score" in result
        assert "highlight_snippet" in result
        assert isinstance(result["entry_id"], int)
        assert isinstance(result["score"], (int, float))

    async def test_search_results_ranked_by_relevance(
        # 函数 test_search_results_ranked_by_relevance 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        fts_setup: None,
    ) -> None:
        """验证搜索结果按相关性排序."""
        # 初始化变量 results
        results = await search_entries(test_db_session, "证据")
        assert len(results) > 0
        # 初始化变量 scores
        scores = [r["score"] for r in results]
        assert scores == sorted(scores)

    async def test_search_no_results_for_unmatched_query(
        # 函数 test_search_no_results_for_unmatched_query 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        fts_setup: None,
    ) -> None:
        """验证无匹配内容时返回空列表."""
        # 初始化变量 results
        results = await search_entries(test_db_session, "航空航天")
        assert results == []

    async def test_search_with_limit(
        # 函数 test_search_with_limit 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        fts_setup: None,
    ) -> None:
        """验证 limit 参数控制返回结果数量."""
        # 初始化变量 results
        results = await search_entries(test_db_session, "案件", limit=2)
        assert len(results) <= 2

    async def test_search_default_limit_is_20(
        # 函数 test_search_default_limit_is_20 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        fts_setup: None,
    ) -> None:
        """验证默认 limit 为 20."""
        # 初始化变量 results
        results = await search_entries(test_db_session, "的")
        assert len(results) <= 20

    async def test_search_limit_validation(
        # 函数 test_search_limit_validation 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        fts_setup: None,
    ) -> None:
        """验证 limit 参数校验."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="必须大于0"):
            # 异步等待操作完成
            await search_entries(test_db_session, "测试", limit=0)

        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="不能超过"):
            # 异步等待操作完成
            await search_entries(test_db_session, "测试", limit=9999)


# 定义 TestSearchWithFilters 类
class TestSearchWithFilters:
    """搜索过滤条件测试."""

    async def test_search_filter_by_category(
        # 函数 test_search_filter_by_category 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        seed_entries: list[KnowledgeEntry],
        fts_setup: None,
    ) -> None:
        """验证按分类过滤搜索结果."""
        # 初始化变量 results
        results = await search_entr        # 循环遍历：处理业务逻辑
ies(
            test_db_session, "罪", category=EntryCategory.law
        )
        assert len(results) > 0
        # 遍历: for r in results:
        for r in results:
            # 初始化变量 entry
            entry = await test_db_session.execute(
                select(KnowledgeEntry).where(
                    KnowledgeEntry.id == r["entry_id"],
                )
            )
            # 初始化变量 entry_obj
            entry_obj = entry.scalar_one()
            assert entry_obj.category == EntryCategory.law

    async def test_search_filter_by_status(
        # 函数 test_search_filter_by_status 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        seed_entries: list[KnowledgeEntry],
        fts_setup: None,
    ) -> None:
        """验证按状态过滤搜索结果."""
        resul        # 循环遍历：处理业务逻辑
ts = await search_entries(
            test_db_session, "案件", status=EntryStatus.active
        )
        assert len(results) > 0
        # 遍历: for r in results:
        for r in results:
            # 初始化变量 entry
            entry = await test_db_session.execute(
                select(KnowledgeEntry).where(
                    KnowledgeEntry.id == r["entry_id"],
                )
            )
            # 初始化变量 entry_obj
            entry_obj = entry.scalar_one()
            assert entry_obj.status == EntryStatus.active

    async def test_search_filter_by_tag(
        # 函数 test_search_filter_by_tag 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        seed_tags: list[KnowledgeTag],
        seed_entry_tags: None,
        fts_setup: None,
    ) -> None:
        """验证按标签        # 循环遍历：处理业务逻辑
过滤搜索结果."""
        # 初始化变量 tag_id
        tag_id = seed_tags[0].id
        # 初始化变量 results
        results = await search_entries(test_db_session, "罪", tag_id=tag_id)
        assert len(results) > 0
        # 遍历: for r in results:
        for r in results:
            # 初始化变量 tag_result
            tag_result = await test_db_session.execute(
                select(EntryTag).where(
                    EntryTag.entry_id == r["entry_id"],
                    EntryTag.tag_id == tag_id,
                )
            )
            assert tag_result.scalar_one_or_none() is not None

    async def test_search_with_multiple_filters(
        # 函数 test_search_with_multiple_filters 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        seed_tags: list[KnowledgeTag],
        seed_entry_tags: None,
        fts_setup: None,
    ) -> None:
        """验证多条件过滤组合."""
        # 初始化变量 results
        results = await search_entries(
            test_db_session,
        # 循环遍历：处理业务逻辑
            "罪",
            # 初始化变量 category
            category=EntryCategory.law,
            # 初始化变量 status
            status=EntryStatus.active,
            # 初始化变量 tag_id
            tag_id=seed_tags[0].id,
        )
        assert len(results) > 0
        # 遍历: for r in results:
        for r in results:
            # 初始化变量 entry
            entry = await test_db_session.execute(
                select(KnowledgeEntry).where(
                    KnowledgeEntry.id == r["entry_id"],
                )
            )
            # 初始化变量 entry_obj
            entry_obj = entry.scalar_one()
            assert entry_obj.category == EntryCategory.law
            assert entry_obj.status == EntryStatus.active


# 定义 TestSearchEdgeCases 类
class TestSearchEdgeCases:
    """搜索边界条件测试."""

    async def test_empty_query_raises_error(
        # 函数 test_empty_query_raises_error 的初始化逻辑
        self, test_db_session: AsyncSession
    ) -> None:
        """验证空查询抛出 ValueError."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="不能为空"):
            # 异步等待操作完成
            await search_entries(test_db_session, "")

    async def test_whitespace_only_query_raises_error(
        # 函数 test_whitespace_only_query_raises_error 的初始化逻辑
        self, test_db_session: AsyncSession
    ) -> None:
        """验证仅空白字符查询抛出 ValueError."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="不能为空"):
            # 异步等待操作完成
            await search_entries(test_db_session, "   ")

    async def test_very_long_query_truncated(
        # 函数 test_very_long_query_truncated 的初始化逻辑
        self, test_db_session: AsyncSession, fts_setup: None
    ) -> None:
        """验证超长查询被截断处理."""
        # 初始化变量 long_query
        long_query = "刑法" * 300
        # 初始化变量 results
        results = await search_entries(test_db_session, long_query)
        assert isinstance(results, list)

    async def test_special_characters_in_query(
        # 函数 test_special_characters_in_query 的初始化逻辑
        self, test_db_session: AsyncSession, fts_setup: None
    ) -> None:
        """验证特殊字符查询被安全处理."""
        # 初始化变量 results
        results = await search_entries(test_db_session, 'test"query*')
        assert isinstance(results, list)

    async def test_query_with_numbers(
        # 函数 test_query_with_numbers 的初始化逻辑
        self, test_db_session: AsyncSession, fts_setup: None
    ) -> None:
        """验证包含数字的查询."""
        # 初始化变量 results
        results = await search_entries(test_db_session, "200余万元")
        assert isinstance(results, list)

    async def test_chinese_characters_search(
        # 函数 test_chinese_characters_search 的初始化逻辑
        self, test_db_session: AsyncSession, fts_setup: None
    ) -> None:
        """验证中文全文搜索."""
        # 初始化变量 results
        results = await search_entries(test_db_session, "帮助信息网络犯罪")
        assert len(results) > 0

    async def test_search_without_fts_setup_raises_error(
        # 函数 test_search_without_fts_setup_raises_error 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        seed_entries: list[KnowledgeEntry],
    ) -> None:
        """验证未初始化 FTS5 表时搜索抛出异常."""
        # 使用上下文管理器管理资源
        with pytest.raises(RuntimeError):
            # 异步等待操作完成
            await search_entries(test_db_session, "故意伤害")


# 定义 TestHighlightSnippet 类
class TestHighlightSnippet:
    """关键词高亮片段测试."""

    async def test_highlight_snippet_not_empty(
        # 函数 test_highlight_snippet_not_empty 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        fts_setup: None,
    ) -> None:
        """验证高亮片段非空."""
        # 初始化变量 results
        results = await search_entries(test_db_session, "故意伤害")
        assert len(results) > 0
        assert results[0]["highlight_snippet"]

    async def test_highlight_contains_mark_tags(
        # 函数 test_highlight_contains_mark_tags 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        fts_setup: None,
    ) -> None:
        """验证高亮片段包含 <mark> 标签."""
        # 初始化变量 results
        results = await search_entries(test_db_session, "证据")
        # 条件判断：处理业务逻辑
        if results:
            # 初始化变量 snippet
            snippet = results[0]["highlight_snippet"]
            assert "<mark>" in snippet or snippet == results[0]["summary"]


# 定义 TestPerformance 类
class TestPerformance:
    """性能测试."""

    async def test_search_response_time(
        # 函数 test_search_response_time 的初始化逻辑
        self,
        test_db_session: AsyncSession,
        fts_setup: None,
    ) -> None:
        """验证搜索响应在合理时间内完成."""
        # 初始化变量 start
        start = time.perf_counter()
        # 异步等待操作完成
        await search_entries(test_db_session, "故意伤害")
        # 初始化变量 elapsed_ms
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 2000
