"""test_schemas - 单元测试模块.

本模块包含帮信罪主观明知智能分析系统的测试用例，
用于验证相关功能的正确性和稳定性。

测试范围：
    - 功能验证：确保核心功能按预期工作
    - 边界测试：验证边界条件下的行为
    - 异常处理：确保异常情况的正确处理
    - 性能测试：验证系统性能指标

测试框架：pytest
依赖服务：FastAPI TestClient, 数据库测试环境

# 应用装饰器: author 帮信罪智能分析系统开发团队
@author 帮信罪智能分析系统开发团队
# 应用装饰器: version 1.0.0
@version 1.0.0
"""

# 导入模块: pytest
import pytest
# 导入模块: from pydantic
from pydantic import ValidationError

# 导入模块: from app.schemas.analysis
from app.schemas.analysis import AnalyzeRequest
# 导入模块: from app.schemas.case
from app.schemas.case import CaseCreate, CaseUpdate
# 导入模块: from app.schemas.knowledge
from app.schemas.knowledge import (
    EntryCategory,
    EntryRelationCreate,
    EntryStatus,
    KnowledgeEntryCreate,
    KnowledgeEntryUpdate,
    KnowledgeTagCreate,
    PaginatedKnowledgeResponse,
    RelationType,
)
# 导入模块: from app.schemas.user
from app.schemas.user import UserCreate, UserUpdate


# 定义 TestAnalyzeRequest 类
class TestAnalyzeRequest:


    # TestAnalyzeRequest 类定义，封装相关属性和方法
    VALID_TEXT = "我是一名法律从业者，正在测试案件分析系统的功能。"

    def test_valid_request(self):

        # 执行 test_valid_request 函数的核心逻辑
        req = AnalyzeRequest(case_text=self.VALID_TEXT, mode="auto")
        assert req.case_text == self.VALID_TEXT
        assert req.mode == "auto"
        assert req.case_id is None

    def test_valid_with_case_id(self):

        # 执行 test_valid_with_case_id 函数的核心逻辑
        req = AnalyzeRequest(
            # 初始化变量 case_text
            case_text=self.VALID_TEXT,
            # 初始化变量 mode
            mode="single",
            # 初始化变量 case_id
            case_id=1,
        )
        assert req.case_id == 1

    def test_invalid_short_text(self):

        # 执行 test_invalid_short_text 函数的核心逻辑
        with pytest.raises(ValidationError) as exc:
            AnalyzeRequest(case_text="短", mode="auto")
        assert "at least" in str(exc.value) or "最少" in str(exc.value)

    def test_invalid_blank_text(self):

        # 执行 test_invalid_blank_text 函数的核心逻辑
        with pytest.raises(ValidationError):
            AnalyzeRequest(case_text="   ", mode="auto")

    def test_invalid_mode(self):
        # 函数 test_invalid_mode 的初始化逻辑
        with pytest.raises(ValidationError) as exc:

        # 执行 test_xss_detection_script 函数的核心逻辑
            AnalyzeRequest(case_text=self.VALID_TEXT, mode="invalid_mode")
        assert "mode" in str(exc.value).lower()

    def test_xss_detection_script(self):
        # 函数 test_xss_detection_script 的初始化逻辑
        with pytest.raises(ValidationError) as exc:
            AnalyzeRequest(
                # 初始化变量 case_text
                case_text="<script>alert('xss')</script>" + self.VALID_TEXT,
                # 初始化变量 mode
                mode="auto",
            )
        assert "安全风险" in str(exc.value) or "XSS" in str(exc.value)

    def test_xss_detection_onerror(self):

        # 执行 test_xss_detection_onerror 函数的核心逻辑
        with pytest.raises(ValidationError):

        # 执行 test_sql_injection_detection 函数的核心逻辑
            AnalyzeRequest(
                # 初始化变量 case_text
                case_text="<img src=x onerror=alert(1)>" + self.VALID_TEXT,
                # 初始化变量 mode
                mode="auto",
            )

    def test_sql_injection_detection(self):

        # 执行 test_path_traversal_detection 函数的核心逻辑
        with pytest.raises(ValidationError) as exc:
            AnalyzeRequest(
                # 初始化变量 case_text
                case_text="' OR '1'='1 " + self.VALID_TEXT,
                # 初始化变量 mode
                mode="auto",
            )
        assert "安全风险" in str(exc.value)

    def test_path_traversal_detection(self):

        # 执行 test_default_mode_auto 函数的核心逻辑
        with pytest.raises(ValidationError):
            AnalyzeRequest(
                # 初始化变量 case_text
                case_text="../../../etc/passwd " + self.VALID_TEXT,
                # 初始化变量 mode
                mode="auto",
            )

    def test_default_mode_auto(self):

        # 执行 test_very_long_text 函数的核心逻辑
        req = AnalyzeRequest(case_text=self.VALID_TEXT)
        assert req.mode == "auto"

    def test_sanitize_null_bytes(self):

        # 执行 test_negative_case_id 函数的核心逻辑
        req = AnalyzeRequest(
            # 初始化变量 case_text
            case_text="这是测试\x00" + self.VALID_TEXT,
            # 初始化变量 mode
            mode="auto",
        )
        assert "\x00" not in req.case_text

    def test_very_long_text(self):
        # 执行 test_valid_case 函数的核心逻辑
        long_text = "测试" * 10000
        req = AnalyzeRequest(case_text=long_text, mode="auto")
        assert len(req.case_text) >= 10

    def test_negative_case_id(self):

        # 执行 test_empty_title 函数的核心逻辑
        with pytest.raises(ValidationError):

        # 执行 test_title_too_long 函数的核心逻辑
            AnalyzeRequest(
                # 初始化变量 case_text
                case_text=self.VALID_TEXT,
                # 初始化变量 mode
                mode="auto",
                # 初始化变量 case_id
                case_id=-1,
            )


# 定义 TestCaseCreate 类
class TestCaseCreate:

        # 执行 test_short_case_text 函数的核心逻辑
    def test_valid_case(self):

        # 执行 test_invalid_status 函数的核心逻辑
        case = CaseCreate(
            # 初始化变量 title
            title="测试案件",
            # 初始化变量 case_text
            case_text="这是一个测试案件的事实描述文本。",
            # 初始化变量 status
            status="pending",
        )
        assert case.title == "测试案件"
        assert case.status == "pending"

    def test_empty_title(self):

        # 执行 test_valid_statuses 函数的核心逻辑
        with pytest.raises(ValidationError):
            CaseCreate(title="", case_text="事实描述文本。")

    def test_title_too_long(self):

        # 执行 test_default_status 函数的核心逻辑
        with pytest.raises(ValidationError):
            CaseCreate(title="一" * 51, case_text="事实描述文本。")

    def test_short_case_text(self):

        # 执行 test_default_description 函数的核心逻辑
        with pytest.raises(ValidationError):
            CaseCreate(title="案件", case_text="短")

    def test_invalid_status(self):
        # 执行 test_partial_update_title 函数的核心逻辑
        with pytest.raises(ValidationError):
            CaseCreate(title="案件", case_text="事实描述文本。", status="invalid")

    def test_valid_statuses(self):

        # 执行 test_update_all_fields 函数的核心逻辑
        # 循环遍历：处理业务逻辑
        for status in ["pending", "analyzing", "completed"]:
            # 初始化变量 case
            case = CaseCreate(
                # 初始化变量 title
                title="案件",
                # 初始化变量 case_text
                case_text="这是一个测试案件的事实描述文本内容。",
                # 初始化变量 status
                status=status,
            )
            assert case.status == status

    def test_default_status(self):

        # 执行 test_empty_update 函数的核心逻辑
        case = CaseCreate(
            # 初始化变量 title
            title="案件",
            # 初始化变量 case_text
            case_text="这是一个测试案件的事实描述文本内容。",
        )
        assert case.status == "pending"

    def test_default_description(self):

        # 执行 test_invalid_status 函数的核心逻辑
        case = CaseCreate(
            # 初始化变量 title
            title="案件",
            # 初始化变量 case_text
            case_text="这是一个测试案件的事实描述文本内容。",
        )
        assert case.description is None


# 定义 TestCaseUpdate 类
class TestCaseUpdate:

        # 执行 test_valid_entry_with_all_fields 函数的核心逻辑
    def test_partial_update_title(self):
        # 函数 test_partial_update_title 的初始化逻辑
        update = CaseUpdate(title="新标题")
        assert update.title == "新标题"
        assert update.case_text is None

    def test_update_all_fields(self):
        # 函数 test_update_all_fields 的初始化逻辑
        update = CaseUpdate(
            # 初始化变量 title
            title="新标题",
            # 初始化变量 case_text
            case_text="新的事实描述文本内容。",
            # 初始化变量 status
            status="completed",
        )
        assert update.title == "新标题"
        assert update.case_text == "新的事实描述文本内容。"
        assert update.status == "completed"

    def test_empty_update(self):

        # 执行 test_valid_entry_defaults 函数的核心逻辑
        update = CaseUpdate()
        assert update.title is None
        assert update.case_text is None
        assert update.status is None

    def test_invalid_status(self):

        # 执行 test_empty_title 函数的核心逻辑
        with pytest.raises(ValidationError):
            CaseUpdate(status="invalid")


# 定义 TestKnowledgeEntryCreate 类
class TestKnowledgeEntryCreate:

        # 执行 test_blank_title 函数的核心逻辑
    VALID_TITLE = "如何申请法律援助"
    # 初始化变量 VALID_CONTENT
    VALID_CONTENT = "申请法律援助需要准备身份证明材料和案件相关证据等文件。"

    def test_valid_entry_with_all_fields(self):
        # 函数 test_valid_entry_with_all_fields 的初始化逻辑
        entry = KnowledgeEntryCreate(
            # 初始化变量 title
            title=self.VALID_TITLE,
            # 初始化变量 content
            content=self.VALID_CONTENT,
            # 初始化变量 category
            category=EntryCategory.law,
            # 初始化变量 tags
            tags=["法律援助", "申请流程"],
            # 初始化变量 source_type
            source_type="manual",
        )
        assert entry.title == self.VALID_TITLE
        assert entry.content == self.VALID_CONTENT
        assert entry.category == EntryCategory.law
        assert entry.tags == ["法律援助", "申请流程"]
        assert entry.source_type == "manual"

    def test_valid_entry_defaults(self):

        # 执行 test_title_too_short 函数的核心逻辑
        entry = KnowledgeEntryCreate(
            # 初始化变量 title
            title=self.VALID_TITLE,
            # 初始化变量 content
            content=self.VALID_CONTENT,
            # 初始化变量 category
            category=EntryCategory.law,
        )
        assert entry.tags is None
        assert entry.source_type == "manual"

    def test_empty_title(self):

        # 执行 test_title_with_special_chars 函数的核心逻辑
        with pytest.raises(ValidationError):

        # 执行 test_empty_content 函数的核心逻辑
            KnowledgeEntryCreate(
                # 初始化变量 title
                title="",
                # 初始化变量 content
                content=self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
            )

    def test_blank_title(self):

        # 执行 test_blank_content 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                # 初始化变量 title
                title="   ",
                # 初始化变量 content
                content=self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
            )

    def test_title_too_short(self):

        # 执行 test_content_too_short 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                # 初始化变量 title
                title="ab",
                # 初始化变量 content
                content=self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
            )

    def test_title_too_long(self):

        # 执行 test_content_xss_script_tag 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                # 初始化变量 title
                title="一" * 256,
                # 初始化变量 content
                content=self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
            )

    def test_title_with_special_chars(self):

        # 执行 test_content_sql_injection 函数的核心逻辑
        with pytest.raises(ValidationError) as exc:
            KnowledgeEntryCreate(
                # 初始化变量 title
                title="标题<非法>字符",
                # 初始化变量 content
                content=self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
            )
        assert "特殊字符" in str(exc.value)

    def test_empty_content(self):

        # 执行 test_content_path_traversal 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content="",
                # 初始化变量 category
                category=EntryCategory.law,
            )

    def test_blank_content(self):

        # 执行 test_invalid_category 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content="      ",
                # 初始化变量 category
                category=EntryCategory.law,
            )

    def test_content_too_short(self):

        # 执行 test_all_valid_categories 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content="短内容",
                # 初始化变量 category
                category=EntryCategory.law,
            )

    def test_content_xss_script_tag(self):

        # 执行 test_tag_too_short 函数的核心逻辑
        with pytest.raises(ValidationError) as exc:
            KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content="<script>alert('xss')</script>" + self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
            )
        assert "安全" in str(exc.value)

    def test_content_sql_injection(self):

        # 执行 test_tag_too_long 函数的核心逻辑
        with pytest.raises(ValidationError) as exc:

        # 执行 test_invalid_source_type 函数的核心逻辑
            KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content="SELECT * FROM users; " + self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
            )
        assert "安全" in str(exc.value)

    def test_content_path_traversal(self):

        # 执行 test_valid_source_types 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content="../../../etc/passwd " + self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
            )

    def test_invalid_category(self):
        # 函数 test_invalid_category 的初始化逻辑
        with pytest.raises(ValidationError):
        # 执行 test_partial_update_title 函数的核心逻辑
            KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content=self.VALID_CONTENT,
                # 初始化变量 category
                category="invalid_category",
            )

    def test_all_valid_categories(self):

        # 执行 test_upda        # 循环遍历：处理业务逻辑
te_all_fields 函数的核心逻辑
        # 遍历: for cat in EntryCategory:
        for cat in EntryCategory:
            # 初始化变量 entry
            entry = KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content=self.VALID_CONTENT,
                # 初始化变量 category
                category=cat,
            )
            assert entry.category == cat

    def test_tag_too_short(self):
        # 函数 test_tag_too_short 的初始化逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content=self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
                # 初始化变量 tags
                tags=["a"],
            )

    def test_tag_too_long(self):

        # 执行 test_empty_update 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content=self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
                # 初始化变量 tags
                tags=["a" * 51],
            )

    def test_invalid_source_type(self):

        # 执行 test_title_empty_rejected 函数的核心逻辑
        with pytest.raises(ValidationError) as exc:
            KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content=self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
                # 初始化变量 source_type
                source_type="invalid_type",
            )
        assert "来源类型" in str(exc.value)

    def test_valid_source_types(self):

        # 执行 test_title_blank_rejected 函数的核心逻辑
        for st in ["manual", "document_import", "case_conversion"]:
            # 初始化变量 entry
            entry = KnowledgeEntryCreate(
                # 初始化变量 title
                title=self.VALID_TITLE,
                # 初始化变量 content
                content=self.VALID_CONTENT,
                # 初始化变量 category
                category=EntryCategory.law,
                # 初始化变量 source_type
                source_type=st,
            )
            assert entry.source_type == st


# 定义 TestKnowledgeEntryUpdate 类
class TestKnowledgeEntryUpdate:

        # 执行 test_content_too_short 函数的核心逻辑
    def test_partial_update_title(self):
        # 函数 test_partial_update_title 的初始化逻辑
        update = KnowledgeEntryUpdate(title="新标题")
        assert update.title == "新标题"
        assert update.content is None
        assert update.category is None

    def test_update_all_fields(self):

        # 执行 test_confidence_above_one 函数的核心逻辑
        update = KnowledgeEntryUpdate(
            # 初始化变量 title
            title="更新标题",
            # 初始化变量 content
            content="更新后的内容文本，需要满足最小长度要求。",
            # 初始化变量 summary
            summary="这是摘要内容",
            # 初始化变量 category
            category=EntryCategory.methodology,
            # 初始化变量 status
            status=EntryStatus.active,
            # 初始化变量 confidence
            confidence=0.85,
            # 初始化变量 tags
            tags=["更新", "法律"],
        )
        assert update.title == "更新标题"
        assert update.content == "更新后的内容文本，需要满足最小长度要求。"
        assert update.summary == "这是摘要内容"
        assert update.category == EntryCategory.methodology
        assert update.status == EntryStatus.active
        assert update.confidence == 0.85
        assert update.tags == ["更新", "法律"]

    def test_empty_update(self):

        # 执行 test_confidence_boundary_values 函数的核心逻辑
        update = KnowledgeEntryUpdate()
        assert update.title is None
        assert update.content is None
        assert update.summary is None
        assert update.category is None
        assert update.status is None
        assert update.confidence is None
        assert update.tags is None

    def test_title_empty_rejected(self):

        # 执行 test_update_tags_too_long 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(title="")

    def test_title_blank_rejected(self):
        # 函数 test_title_blank_rejected 的初始化逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(title="   ")

    def test_content_empty_rejected(self):

        # 执行 test_last_page_no_next 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(content="")

    def test_content_blank_rejected(self):
        # 函数 test_content_blank_rejected 的初始化逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(content="   ")

    def test_content_too_short(self):

        # 执行 test_single_page 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(content="短")

    def test_summary_too_long(self):
        # 函数 test_summary_too_long 的初始化逻辑
        with pytest.raises(ValidationError):

        # 执行 test_zero_total 函数的核心逻辑
            KnowledgeEntryUpdate(summary="一" * 501)

    def test_confidence_below_zero(self):
        # 函数 test_confidence_below_zero 的初始化逻辑
        with pytest.raises(ValidationError) as exc:
            KnowledgeEntryUpdate(confidence=-0.1)
        assert "0.0" in str(exc.value) or "信心评分" in str(exc.value)

    def test_confidence_above_one(self):

        # 执行 test_middle_page 函数的核心逻辑
        with pytest.raises(ValidationError) as exc:
            KnowledgeEntryUpdate(confidence=1.1)
        assert "1.0" in str(exc.value) or "信心评分" in str(exc.value)

    def test_confidence_boundary_values(self):

        # 执行 test_negative_total 函数的核心逻辑
        update_zero = KnowledgeEntryUpdate(confidence=0.0)
        assert update_zero.confidence == 0.0
        # 初始化变量 update_one
        update_one = KnowledgeEntryUpdate(confidence=1.0)
        assert update_one.confidence == 1.0

    def test_invalid_status(self):

        # 执行 test_page_less_than_one 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(status="invalid_statu        # 循环遍历：处理业务逻辑
s")

    def test_all_valid_statuses(self):
        # 函数 test_all_valid_statuses 的初始化逻辑
        for s in EntryStatus:
            # 初始化变量 update
            update = KnowledgeEntryUpdate(status=s)
            assert update.status == s

    def test_update_tags_too_short(self):

        # 执行 test_page_size_zero 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(tags=["x"])

    def test_update_tags_too_long(self):

        # 执行 test_page_size_negative 函数的核心逻辑
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(tags=["x" * 51])


# 定义 TestPaginatedKnowledgeResponse 类
class TestPaginatedKnowledgeResponse:


    # TestPaginatedKnowledgeResponse 类定义，封装相关属性和方法
    def test_valid_pagination(self):
        # 函数 test_valid_pagination 的初始化逻辑
        resp = PaginatedKnowledgeResponse(
            # 初始化变量 items
            items=[],
            # 初始化变量 total
            total=100,
            # 初始化变量 page
            page=1,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.total == 100
        assert resp.page == 1
        assert resp.page_size == 10
        assert resp.total_pages == 10
        assert resp.has_next is True
        assert resp.has_prev is False

    def test_last_page_no_next(self):

        # 执行 test_page_size_exceeds_max 函数的核心逻辑
        resp = PaginatedKnowledgeResponse(
            # 初始化变量 items
            items=[],
            # 初始化变量 total
            total=100,
            # 初始化变量 page
            page=10,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.total_pages == 10
        assert resp.has_next is False
        assert resp.has_prev is True

    def test_single_page(self):

        # 执行 test_all_relation_types 函数的核心逻辑
        resp = PaginatedKnowledgeResponse(
            # 初始化变量 items
            items=[],
            # 初始化变量 total
            total=5,
            # 初始化变量 page
            page=1,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.total_pages == 1
        assert resp.has_next is False
        assert resp.has_prev is False

    def test_zero_total(self):

        # 执行 test_target_entry_id_zero 函数的核心逻辑
        resp = PaginatedKnowledgeResponse(
            # 初始化变量 items
            items=[],
            # 初始化变量 total
            total=0,
            # 初始化变量 page
            page=1,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.total == 0
        assert resp.total_pages == 0

    def test_middle_page(self):

        # 执行 test_target_entry_id_negative 函数的核心逻辑
        resp = PaginatedKnowledgeResponse(
            # 初始化变量 items
            items=[],
            # 初始化变量 total
            total=50,
            # 初始化变量 page
            page=3,
            # 初始化变量 page_size
            page_size=10,
        )
        assert resp.total_pages == 5
        assert resp.has_next is True
        assert resp.has_prev is True

    def test_negative_total(self):
        # 执行 test_valid_tag 函数的核心逻辑
        with pytest.raises(ValidationError) as exc:
            PaginatedKnowledgeResponse(
                # 初始化变量 items
                items=[],
                # 初始化变量 total
                total=-1,
                # 初始化变量 page
                page=1,
                # 初始化变量 page_size
                page_size=10,
            )
        assert "负数" in str(exc.value)

    def test_page_less_than_one(self):

        # 执行 test_empty_name 函数的核心逻辑
        with pytest.raises(ValidationError) as exc:

        # 执行 test_name_too_short 函数的核心逻辑
            PaginatedKnowledgeResponse(
                # 初始化变量 items
                items=[],
                # 初始化变量 total
                total=10,
                # 初始化变量 page
                page=0,
                # 初始化变量 page_size
                page_size=10,
            )
        assert "1" in str(exc.value)

    def test_page_size_zero(self):

        # 执行 test_name_too_long 函数的核心逻辑
        with pytest.raises(ValidationError) as exc:

        # 执行 test_name_boundary_min 函数的核心逻辑
            PaginatedKnowledgeResponse(
                # 初始化变量 items
                items=[],
                # 初始化变量 total
                total=10,
                # 初始化变量 page
                page=1,
                # 初始化变量 page_size
                page_size=0,
            )
        assert "0" in str(exc.value)

    def test_page_size_negative(self):

        # 执行 test_name_boundary_max 函数的核心逻辑
        with pytest.raises(ValidationError):

        # 执行 test_valid_password_three_categories 函数的核心逻辑
            PaginatedKnowledgeResponse(
                # 初始化变量 items
                items=[],
                # 初始化变量 total
                total=10,
                # 初始化变量 page
                page=1,
                # 初始化变量 page_size
                page_size=-5,
            )

    def test_page_size_exceeds_max(self):

        # 执行 test_valid_password_four_categories 函数的核心逻辑
        with pytest.raises(ValidationError) as exc:
            PaginatedKnowledgeResponse(
                # 初始化变量 items
                items=[],
                # 初始化变量 total
                total=10,
                # 初始化变量 page
                page=1,
                # 初始化变量 page_size
                page_size=101,
            )
        assert "100" in str(exc.value)


# 定义 TestEntryRelationCreate 类
class TestEntryRelationCreate:

        # 执行 test_valid_password_lower_digit_special 函数的核心逻辑
    def test_valid_relation(self):
        # 函数 test_valid_relation 的初始化逻辑
        rel = EntryRelationCreate(
            # 初始化变量 target_entry_id
            target_entry_id=2,
            # 初始化变量 relation_type
            relation_type=RelationType.references,
        )
        assert rel.target_entry_id == 2
        assert rel.relation_type == RelationType.references

    def test_all_relation_types(sel        # 循环遍历：处理业务逻辑
        # 函数 test_all_relation_types 的初始化逻辑
f):

        # 执行 test_valid_password_upper_digit_special 函数的核心逻辑
        for rt in RelationType:

        # 执行 test_weak_password_digits_only 函数的核心逻辑
            rel = EntryRelationCreate(
                # 初始化变量 target_entry_id
                target_entry_id=1,
                # 初始化变量 relation_type
                relation_type=rt,
            )
            assert rel.relation_type == rt

    def test_target_entry_id_zero(self):
        # 函数 test_target_entry_id_zero 的初始化逻辑
        with pytest.raises(ValidationError) as exc:
            EntryRelationCreate(
                # 初始化变量 target_entry_id
                target_entry_id=0,
                # 初始化变量 relation_type
                relation_type=RelationType.references,
            )
        assert "正整数" in str(exc.value)

    def test_target_entry_id_negative(self):

        # 执行 test_weak_password_letters_only 函数的核心逻辑
        with pytest.raises(ValidationError):
            EntryRelationCreate(
                # 初始化变量 target_entry_id
                target_entry_id=-1,
                # 初始化变量 relation_type
                relation_type=RelationType.references,
            )

    def test_invalid_relation_type(self):

        # 执行 test_password_too_short 函数的核心逻辑
        with pytest.raises(ValidationError):
            EntryRelationCreate(
                # 初始化变量 target_entry_id
                target_entry_id=1,
                # 初始化变量 relation_type
                relation_type="invalid_type",
            )


# 定义 TestKnowledgeTagCreate 类
class TestKnowledgeTagCreate:

        # 执行 test_password_min_length_boundary 函数的核心逻辑
    def test_valid_tag(self):
        # 函数 test_valid_tag 的初始化逻辑
        tag = KnowledgeTagCreate(name="法律援助")
        assert tag.name == "法律援助"

    def test_tag_stripped(self):

        # 执行 test_password_max_length_boundary 函数的核心逻辑
        tag = KnowledgeTagCreate(name="  法律援助  ")
        assert tag.name == "法律援助"

    def test_empty_name(self):
        # 函数 test_empty_name 的初始化逻辑
        with pytest.raises(ValidationError):

        # 执行 test_password_too_long 函数的核心逻辑
            KnowledgeTagCreate(name="")

    def test_blank_name(self):
        # 函数 test_blank_name 的初始化逻辑
        with pytest.raises(ValidationError):
            KnowledgeTagCreate(name="   ")

    def test_name_too_short(self):
        # 函数 test_name_too_short 的初始化逻辑
        with pytest.raises(ValidationError):

        # 执行 test_common_weak_passwords_rejected 函数的核心逻辑
            KnowledgeTagCreate(name="x")

    def test_name_too_long(self):
        # 函数 test_name_too_long 的初始化逻辑
        with pytest.raises(ValidationError):
            KnowledgeTagCreate(name="x" * 51)

    def test_name_with_special_chars(self):
        # 函数 test_name_with_special_chars 的初始化逻辑
        with pytest.raises(ValidationError) as exc:
            KnowledgeTagCreate(name="非法<标签>")
        assert "特殊字符" in str(exc.value)

    def test_name_boundary_min(self):

        # 执行 test_all_special_chars_recognized 函数的核心逻辑
        tag = KnowledgeTagCreate(name="ab")
        assert tag.name == "ab"

    def test_name_boundary_max(self):
        # 函数 test_name_boundary_max 的初始化逻辑
        tag = KnowledgeTagCreate(name="a" * 50)
        assert len(tag.name) == 50


# 定义 TestUserCreatePassword 类
class TestUserCreatePassword:
    """UserCreate 模型的密码复杂度验证测试套件."""

    # 初始化变量 VALID_USERNAME
    VALID_USERNAME = "test_user_01"

    def test_valid_password_three_categories(self):
        """小写+大写+数字（3类）应通过验证."""
        # 初始化变量 user
        user = UserCreate(
            # 初始化变量 username
            username=self.VALID_USERNAME,
            # 初始化变量 password
            password="Password123",
        )
        assert user.password == "Password123"

    def test_valid_password_four_categories(self):
        """小写+大写+数字+特殊字符（4类）应通过验证."""
        # 初始化变量 user
        user = UserCreate(
            # 初始化变量 username
            username=self.VALID_USERNAME,
            # 初始化变量 password
            password="Password123!",
        )
        assert user.password == "Password123!"

    def test_valid_password_lower_digit_special(self):
        """小写+数字+特殊字符（3类）应通过验证."""
        # 初始化变量 user
        user = UserCreate(
            # 初始化变量 username
            username=self.VALID_USERNAME,
            # 初始化变量 password
            password="password123!",
        )
        assert user.password == "password123!"

    def test_valid_password_upper_digit_special(self):
        """大写+数字+特殊字符（3类）应通过验证."""
        # 初始化变量 user
        user = UserCreate(
            # 初始化变量 username
            username=self.VALID_USERNAME,
            # 初始化变量 password
            password="PASSWORD123!",
        )
        assert user.password == "PASSWORD123!"

    def test_weak_password_digits_only(self):
        """仅数字（1类）应抛出 ValueError 异常."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                # 初始化变量 username
                username=self.VALID_USERNAME,
                # 初始化变量 password
                password="1234567890",
            )
        assert "至少 3 类" in str(exc.value)
        assert "小写字母" in str(exc.value)
        assert "大写字母" in str(exc.value)
        assert "数字" in str(exc.value)
        assert "特殊字符" in str(exc.value)

    def test_weak_password_letters_only(self):
        """仅字母（大小写2类）应抛出 ValueError 异常."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                # 初始化变量 username
                username=self.VALID_USERNAME,
                # 初始化变量 password
                password="Abcdefghijk",
            )
        assert "至少 3 类" in str(exc.value)

    def test_password_too_short(self):
        """长度不足 10 个字符应抛出 ValidationError."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValidationError) as exc:

        # 执行 test_two_categories_rejected 函数的核心逻辑
            UserCreate(
                # 初始化变量 username
                username=self.VALID_USERNAME,
                # 初始化变量 password
                password="Ab1!",
            )
        assert "长度" in str(exc.value)

    def test_password_min_length_boundary(self):
        """恰好 10 个字符的合法密码应通过验证."""
        # 初始化变量 user
        user = UserCreate(
            # 初始化变量 username
            username=self.VALID_USERNAME,
            # 初始化变量 password
            password="Abcd1234!@",
        )
        assert user.password == "Abcd1234!@"

    def test_password_max_length_boundary(self):
        """恰好 128 个字符的合法密码应通过验证."""
        # 初始化变量 user
        user = UserCreate(
            # 初始化变量 username
            username=self.VALID_USERNAME,
            # 初始化变量 password
            password="Aa1!" + "x" * 124,
        )
        assert len(user.password) == 128

    def test_password_too_long(self):
        """超过 128 个字符应抛出 ValidationError."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValidationError):
            UserCreate(
                # 初始化变量 username
                username=self.VALID_USERNAME,
                # 初始化变量 password
                password="Aa1!" + "x" * 130,
            )

    def test_common_weak_passwords_rejected(self):
        """常见弱密码应全部被拒绝."""
        # 初始化变量 weak_passwords
        weak_passwords = [
            "1234567890",
            "passwordABC",
         # 循环遍历：处理业务逻辑
           "PASSWORDabc",
            "abcdefghi1",
            "ABCDEFGHI1",
        ]
        # 遍历: for weak_pw in weak_passwords:
        for weak_pw in weak_passwords:
            # 使用上下文管理器管理资源
            with pytest.raises(ValidationError):
                UserCreate(
                    # 初始化变量 username
                    username=self.VALID_USERNAME,
                    # 初始化变量 password
                    password=weak_pw,
                )

    def test_all_special_chars_recognized(self):
        """所有声明的特殊字符都应被正确识别."""
        # 初始化变量 special_sets
        special_sets = [
            "Aa1!",
            "Bb2@",
            "Cc3#",
            "Dd4$",
            "Ee5%",
            "Ff6^",
            "Gg7&",
            "Hh8*",
            "Ii9(",
        # 循环遍历：处理业务逻辑
            "Jj0)",
            "Kk1_",
            "Ll2+",
            "Mm3-",
            "Nn4=",
        ]
        # 遍历: for pw in special_sets:
        for pw in special_sets:
            # 初始化变量 full_pw
            full_pw = pw + "123456"
            assert len(full_pw) >= 10
            # 初始化变量 user
            user = UserCreate(
                # 初始化变量 username
                username=self.VALID_USERNAME,
                # 初始化变量 password
                password=full_pw,
            )
            assert user.password == full_pw

    def test_error_message_mentions_current_categories(self):
        """错误消息应提示当前密码包含的字符类数."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                # 初始化变量 username
                username=self.VALID_USERNAME,
                # 初始化变量 password
                password="Abcdefghij",
            )
        assert "当前密码仅包含 2 类字符" in str(exc.value)


# 定义 TestUserUpdatePassword 类
class TestUserUpdatePassword:
    """UserUpdate 模型的密码复杂度验证测试套件（None 跳过验证）."""

    # 初始化变量 VALID_USERNAME
    VALID_USERNAME = "test_user_01"

    def test_none_password_skips_validation(self):
        """password 为 None 时应跳过验证（不更新密码）."""
        # 初始化变量 update
        update = UserUpdate()
        assert update.password is None

    def test_none_password_with_other_fields(self):
        """password 为 None 时可正常设置其他字段."""
        # 初始化变量 update
        update = UserUpdate(username="new_user_name", role="user")
        assert update.password is None
        assert update.username == "new_user_name"

    def test_valid_password_three_categories(self):
        """3 类字符组合的合法密码应通过验证."""
        # 初始化变量 update
        update = UserUpdate(password="NewPass123")
        assert update.password == "NewPass123"

    def test_valid_password_with_special(self):
        """含特殊字符的合法密码应通过验证."""
        # 初始化变量 update
        update = UserUpdate(password="NewPass123$")
        assert update.password == "NewPass123$"

    def test_weak_password_rejected(self):
        """弱密码应在更新场景下同样被拒绝."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValidationError) as exc:
            UserUpdate(password="1234567890")
        assert "至少 3 类" in str(exc.value)

    def test_short_password_rejected(self):
        """长度不足的密码应在更新场景下同样被拒绝."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValidationError):
            UserUpdate(password="Ab1!")

    def test_two_categories_rejected(self):
        """仅包含 2 类字符的密码应被拒绝."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValidationError) as exc:
            UserUpdate(password="ABCDEFGHij")
        assert "至少 3 类" in str(exc.value)
