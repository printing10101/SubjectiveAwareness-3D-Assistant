import pytest
from pydantic import ValidationError

from app.schemas.analysis import AnalyzeRequest
from app.schemas.case import CaseCreate, CaseUpdate
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
from app.schemas.user import UserCreate, UserUpdate


class TestAnalyzeRequest:
    VALID_TEXT = "我是一名法律从业者，正在测试案件分析系统的功能。"

    def test_valid_request(self):
        req = AnalyzeRequest(case_text=self.VALID_TEXT, mode="auto")
        assert req.case_text == self.VALID_TEXT
        assert req.mode == "auto"
        assert req.case_id is None

    def test_valid_with_case_id(self):
        req = AnalyzeRequest(
            case_text=self.VALID_TEXT,
            mode="single",
            case_id=1,
        )
        assert req.case_id == 1

    def test_invalid_short_text(self):
        with pytest.raises(ValidationError) as exc:
            AnalyzeRequest(case_text="短", mode="auto")
        assert "at least" in str(exc.value) or "最少" in str(exc.value)

    def test_invalid_blank_text(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(case_text="   ", mode="auto")

    def test_invalid_mode(self):
        with pytest.raises(ValidationError) as exc:
            AnalyzeRequest(case_text=self.VALID_TEXT, mode="invalid_mode")
        assert "mode" in str(exc.value).lower()

    def test_xss_detection_script(self):
        with pytest.raises(ValidationError) as exc:
            AnalyzeRequest(
                case_text="<script>alert('xss')</script>" + self.VALID_TEXT,
                mode="auto",
            )
        assert "安全风险" in str(exc.value) or "XSS" in str(exc.value)

    def test_xss_detection_onerror(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(
                case_text="<img src=x onerror=alert(1)>" + self.VALID_TEXT,
                mode="auto",
            )

    def test_sql_injection_detection(self):
        with pytest.raises(ValidationError) as exc:
            AnalyzeRequest(
                case_text="' OR '1'='1 " + self.VALID_TEXT,
                mode="auto",
            )
        assert "安全风险" in str(exc.value)

    def test_path_traversal_detection(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(
                case_text="../../../etc/passwd " + self.VALID_TEXT,
                mode="auto",
            )

    def test_default_mode_auto(self):
        req = AnalyzeRequest(case_text=self.VALID_TEXT)
        assert req.mode == "auto"

    def test_sanitize_null_bytes(self):
        req = AnalyzeRequest(
            case_text="这是测试\x00" + self.VALID_TEXT,
            mode="auto",
        )
        assert "\x00" not in req.case_text

    def test_very_long_text(self):
        long_text = "测试" * 10000
        req = AnalyzeRequest(case_text=long_text, mode="auto")
        assert len(req.case_text) >= 10

    def test_negative_case_id(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(
                case_text=self.VALID_TEXT,
                mode="auto",
                case_id=-1,
            )


class TestCaseCreate:
    def test_valid_case(self):
        case = CaseCreate(
            title="测试案件",
            case_text="这是一个测试案件的事实描述文本。",
            status="pending",
        )
        assert case.title == "测试案件"
        assert case.status == "pending"

    def test_empty_title(self):
        with pytest.raises(ValidationError):
            CaseCreate(title="", case_text="事实描述文本。")

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            CaseCreate(title="一" * 51, case_text="事实描述文本。")

    def test_short_case_text(self):
        with pytest.raises(ValidationError):
            CaseCreate(title="案件", case_text="短")

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            CaseCreate(title="案件", case_text="事实描述文本。", status="invalid")

    def test_valid_statuses(self):
        for status in ["pending", "analyzing", "completed"]:
            case = CaseCreate(
                title="案件",
                case_text="这是一个测试案件的事实描述文本内容。",
                status=status,
            )
            assert case.status == status

    def test_default_status(self):
        case = CaseCreate(
            title="案件",
            case_text="这是一个测试案件的事实描述文本内容。",
        )
        assert case.status == "pending"

    def test_default_description(self):
        case = CaseCreate(
            title="案件",
            case_text="这是一个测试案件的事实描述文本内容。",
        )
        assert case.description is None


class TestCaseUpdate:
    def test_partial_update_title(self):
        update = CaseUpdate(title="新标题")
        assert update.title == "新标题"
        assert update.case_text is None

    def test_update_all_fields(self):
        update = CaseUpdate(
            title="新标题",
            case_text="新的事实描述文本内容。",
            status="completed",
        )
        assert update.title == "新标题"
        assert update.case_text == "新的事实描述文本内容。"
        assert update.status == "completed"

    def test_empty_update(self):
        update = CaseUpdate()
        assert update.title is None
        assert update.case_text is None
        assert update.status is None

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            CaseUpdate(status="invalid")


class TestKnowledgeEntryCreate:
    VALID_TITLE = "如何申请法律援助"
    VALID_CONTENT = "申请法律援助需要准备身份证明材料和案件相关证据等文件。"

    def test_valid_entry_with_all_fields(self):
        entry = KnowledgeEntryCreate(
            title=self.VALID_TITLE,
            content=self.VALID_CONTENT,
            category=EntryCategory.law,
            tags=["法律援助", "申请流程"],
            source_type="manual",
        )
        assert entry.title == self.VALID_TITLE
        assert entry.content == self.VALID_CONTENT
        assert entry.category == EntryCategory.law
        assert entry.tags == ["法律援助", "申请流程"]
        assert entry.source_type == "manual"

    def test_valid_entry_defaults(self):
        entry = KnowledgeEntryCreate(
            title=self.VALID_TITLE,
            content=self.VALID_CONTENT,
            category=EntryCategory.law,
        )
        assert entry.tags is None
        assert entry.source_type == "manual"

    def test_empty_title(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                title="",
                content=self.VALID_CONTENT,
                category=EntryCategory.law,
            )

    def test_blank_title(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                title="   ",
                content=self.VALID_CONTENT,
                category=EntryCategory.law,
            )

    def test_title_too_short(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                title="ab",
                content=self.VALID_CONTENT,
                category=EntryCategory.law,
            )

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                title="一" * 256,
                content=self.VALID_CONTENT,
                category=EntryCategory.law,
            )

    def test_title_with_special_chars(self):
        with pytest.raises(ValidationError) as exc:
            KnowledgeEntryCreate(
                title="标题<非法>字符",
                content=self.VALID_CONTENT,
                category=EntryCategory.law,
            )
        assert "特殊字符" in str(exc.value)

    def test_empty_content(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content="",
                category=EntryCategory.law,
            )

    def test_blank_content(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content="      ",
                category=EntryCategory.law,
            )

    def test_content_too_short(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content="短内容",
                category=EntryCategory.law,
            )

    def test_content_xss_script_tag(self):
        with pytest.raises(ValidationError) as exc:
            KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content="<script>alert('xss')</script>" + self.VALID_CONTENT,
                category=EntryCategory.law,
            )
        assert "安全" in str(exc.value)

    def test_content_sql_injection(self):
        with pytest.raises(ValidationError) as exc:
            KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content="SELECT * FROM users; " + self.VALID_CONTENT,
                category=EntryCategory.law,
            )
        assert "安全" in str(exc.value)

    def test_content_path_traversal(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content="../../../etc/passwd " + self.VALID_CONTENT,
                category=EntryCategory.law,
            )

    def test_invalid_category(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content=self.VALID_CONTENT,
                category="invalid_category",
            )

    def test_all_valid_categories(self):
        for cat in EntryCategory:
            entry = KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content=self.VALID_CONTENT,
                category=cat,
            )
            assert entry.category == cat

    def test_tag_too_short(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content=self.VALID_CONTENT,
                category=EntryCategory.law,
                tags=["a"],
            )

    def test_tag_too_long(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content=self.VALID_CONTENT,
                category=EntryCategory.law,
                tags=["a" * 51],
            )

    def test_invalid_source_type(self):
        with pytest.raises(ValidationError) as exc:
            KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content=self.VALID_CONTENT,
                category=EntryCategory.law,
                source_type="invalid_type",
            )
        assert "来源类型" in str(exc.value)

    def test_valid_source_types(self):
        for st in ["manual", "document_import", "case_conversion"]:
            entry = KnowledgeEntryCreate(
                title=self.VALID_TITLE,
                content=self.VALID_CONTENT,
                category=EntryCategory.law,
                source_type=st,
            )
            assert entry.source_type == st


class TestKnowledgeEntryUpdate:
    def test_partial_update_title(self):
        update = KnowledgeEntryUpdate(title="新标题")
        assert update.title == "新标题"
        assert update.content is None
        assert update.category is None

    def test_update_all_fields(self):
        update = KnowledgeEntryUpdate(
            title="更新标题",
            content="更新后的内容文本，需要满足最小长度要求。",
            summary="这是摘要内容",
            category=EntryCategory.methodology,
            status=EntryStatus.active,
            confidence=0.85,
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
        update = KnowledgeEntryUpdate()
        assert update.title is None
        assert update.content is None
        assert update.summary is None
        assert update.category is None
        assert update.status is None
        assert update.confidence is None
        assert update.tags is None

    def test_title_empty_rejected(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(title="")

    def test_title_blank_rejected(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(title="   ")

    def test_content_empty_rejected(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(content="")

    def test_content_blank_rejected(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(content="   ")

    def test_content_too_short(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(content="短")

    def test_summary_too_long(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(summary="一" * 501)

    def test_confidence_below_zero(self):
        with pytest.raises(ValidationError) as exc:
            KnowledgeEntryUpdate(confidence=-0.1)
        assert "0.0" in str(exc.value) or "信心评分" in str(exc.value)

    def test_confidence_above_one(self):
        with pytest.raises(ValidationError) as exc:
            KnowledgeEntryUpdate(confidence=1.1)
        assert "1.0" in str(exc.value) or "信心评分" in str(exc.value)

    def test_confidence_boundary_values(self):
        update_zero = KnowledgeEntryUpdate(confidence=0.0)
        assert update_zero.confidence == 0.0
        update_one = KnowledgeEntryUpdate(confidence=1.0)
        assert update_one.confidence == 1.0

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(status="invalid_status")

    def test_all_valid_statuses(self):
        for s in EntryStatus:
            update = KnowledgeEntryUpdate(status=s)
            assert update.status == s

    def test_update_tags_too_short(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(tags=["x"])

    def test_update_tags_too_long(self):
        with pytest.raises(ValidationError):
            KnowledgeEntryUpdate(tags=["x" * 51])


class TestPaginatedKnowledgeResponse:
    def test_valid_pagination(self):
        resp = PaginatedKnowledgeResponse(
            items=[],
            total=100,
            page=1,
            page_size=10,
        )
        assert resp.total == 100
        assert resp.page == 1
        assert resp.page_size == 10
        assert resp.total_pages == 10
        assert resp.has_next is True
        assert resp.has_prev is False

    def test_last_page_no_next(self):
        resp = PaginatedKnowledgeResponse(
            items=[],
            total=100,
            page=10,
            page_size=10,
        )
        assert resp.total_pages == 10
        assert resp.has_next is False
        assert resp.has_prev is True

    def test_single_page(self):
        resp = PaginatedKnowledgeResponse(
            items=[],
            total=5,
            page=1,
            page_size=10,
        )
        assert resp.total_pages == 1
        assert resp.has_next is False
        assert resp.has_prev is False

    def test_zero_total(self):
        resp = PaginatedKnowledgeResponse(
            items=[],
            total=0,
            page=1,
            page_size=10,
        )
        assert resp.total == 0
        assert resp.total_pages == 0

    def test_middle_page(self):
        resp = PaginatedKnowledgeResponse(
            items=[],
            total=50,
            page=3,
            page_size=10,
        )
        assert resp.total_pages == 5
        assert resp.has_next is True
        assert resp.has_prev is True

    def test_negative_total(self):
        with pytest.raises(ValidationError) as exc:
            PaginatedKnowledgeResponse(
                items=[],
                total=-1,
                page=1,
                page_size=10,
            )
        assert "负数" in str(exc.value)

    def test_page_less_than_one(self):
        with pytest.raises(ValidationError) as exc:
            PaginatedKnowledgeResponse(
                items=[],
                total=10,
                page=0,
                page_size=10,
            )
        assert "1" in str(exc.value)

    def test_page_size_zero(self):
        with pytest.raises(ValidationError) as exc:
            PaginatedKnowledgeResponse(
                items=[],
                total=10,
                page=1,
                page_size=0,
            )
        assert "0" in str(exc.value)

    def test_page_size_negative(self):
        with pytest.raises(ValidationError):
            PaginatedKnowledgeResponse(
                items=[],
                total=10,
                page=1,
                page_size=-5,
            )

    def test_page_size_exceeds_max(self):
        with pytest.raises(ValidationError) as exc:
            PaginatedKnowledgeResponse(
                items=[],
                total=10,
                page=1,
                page_size=101,
            )
        assert "100" in str(exc.value)


class TestEntryRelationCreate:
    def test_valid_relation(self):
        rel = EntryRelationCreate(
            target_entry_id=2,
            relation_type=RelationType.references,
        )
        assert rel.target_entry_id == 2
        assert rel.relation_type == RelationType.references

    def test_all_relation_types(self):
        for rt in RelationType:
            rel = EntryRelationCreate(
                target_entry_id=1,
                relation_type=rt,
            )
            assert rel.relation_type == rt

    def test_target_entry_id_zero(self):
        with pytest.raises(ValidationError) as exc:
            EntryRelationCreate(
                target_entry_id=0,
                relation_type=RelationType.references,
            )
        assert "正整数" in str(exc.value)

    def test_target_entry_id_negative(self):
        with pytest.raises(ValidationError):
            EntryRelationCreate(
                target_entry_id=-1,
                relation_type=RelationType.references,
            )

    def test_invalid_relation_type(self):
        with pytest.raises(ValidationError):
            EntryRelationCreate(
                target_entry_id=1,
                relation_type="invalid_type",
            )


class TestKnowledgeTagCreate:
    def test_valid_tag(self):
        tag = KnowledgeTagCreate(name="法律援助")
        assert tag.name == "法律援助"

    def test_tag_stripped(self):
        tag = KnowledgeTagCreate(name="  法律援助  ")
        assert tag.name == "法律援助"

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            KnowledgeTagCreate(name="")

    def test_blank_name(self):
        with pytest.raises(ValidationError):
            KnowledgeTagCreate(name="   ")

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            KnowledgeTagCreate(name="x")

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            KnowledgeTagCreate(name="x" * 51)

    def test_name_with_special_chars(self):
        with pytest.raises(ValidationError) as exc:
            KnowledgeTagCreate(name="非法<标签>")
        assert "特殊字符" in str(exc.value)

    def test_name_boundary_min(self):
        tag = KnowledgeTagCreate(name="ab")
        assert tag.name == "ab"

    def test_name_boundary_max(self):
        tag = KnowledgeTagCreate(name="a" * 50)
        assert len(tag.name) == 50


class TestUserCreatePassword:
    """UserCreate 模型的密码复杂度验证测试套件."""

    VALID_USERNAME = "test_user_01"

    def test_valid_password_three_categories(self):
        """小写+大写+数字（3类）应通过验证."""
        user = UserCreate(
            username=self.VALID_USERNAME,
            password="Password123",
        )
        assert user.password == "Password123"

    def test_valid_password_four_categories(self):
        """小写+大写+数字+特殊字符（4类）应通过验证."""
        user = UserCreate(
            username=self.VALID_USERNAME,
            password="Password123!",
        )
        assert user.password == "Password123!"

    def test_valid_password_lower_digit_special(self):
        """小写+数字+特殊字符（3类）应通过验证."""
        user = UserCreate(
            username=self.VALID_USERNAME,
            password="password123!",
        )
        assert user.password == "password123!"

    def test_valid_password_upper_digit_special(self):
        """大写+数字+特殊字符（3类）应通过验证."""
        user = UserCreate(
            username=self.VALID_USERNAME,
            password="PASSWORD123!",
        )
        assert user.password == "PASSWORD123!"

    def test_weak_password_digits_only(self):
        """仅数字（1类）应抛出 ValueError 异常."""
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                username=self.VALID_USERNAME,
                password="1234567890",
            )
        assert "至少 3 类" in str(exc.value)
        assert "小写字母" in str(exc.value)
        assert "大写字母" in str(exc.value)
        assert "数字" in str(exc.value)
        assert "特殊字符" in str(exc.value)

    def test_weak_password_letters_only(self):
        """仅字母（大小写2类）应抛出 ValueError 异常."""
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                username=self.VALID_USERNAME,
                password="Abcdefghijk",
            )
        assert "至少 3 类" in str(exc.value)

    def test_password_too_short(self):
        """长度不足 10 个字符应抛出 ValidationError."""
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                username=self.VALID_USERNAME,
                password="Ab1!",
            )
        assert "长度" in str(exc.value)

    def test_password_min_length_boundary(self):
        """恰好 10 个字符的合法密码应通过验证."""
        user = UserCreate(
            username=self.VALID_USERNAME,
            password="Abcd1234!@",
        )
        assert user.password == "Abcd1234!@"

    def test_password_max_length_boundary(self):
        """恰好 128 个字符的合法密码应通过验证."""
        user = UserCreate(
            username=self.VALID_USERNAME,
            password="Aa1!" + "x" * 124,
        )
        assert len(user.password) == 128

    def test_password_too_long(self):
        """超过 128 个字符应抛出 ValidationError."""
        with pytest.raises(ValidationError):
            UserCreate(
                username=self.VALID_USERNAME,
                password="Aa1!" + "x" * 130,
            )

    def test_common_weak_passwords_rejected(self):
        """常见弱密码应全部被拒绝."""
        weak_passwords = [
            "1234567890",
            "passwordABC",
            "PASSWORDabc",
            "abcdefghi1",
            "ABCDEFGHI1",
        ]
        for weak_pw in weak_passwords:
            with pytest.raises(ValidationError):
                UserCreate(
                    username=self.VALID_USERNAME,
                    password=weak_pw,
                )

    def test_all_special_chars_recognized(self):
        """所有声明的特殊字符都应被正确识别."""
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
            "Jj0)",
            "Kk1_",
            "Ll2+",
            "Mm3-",
            "Nn4=",
        ]
        for pw in special_sets:
            full_pw = pw + "123456"
            assert len(full_pw) >= 10
            user = UserCreate(
                username=self.VALID_USERNAME,
                password=full_pw,
            )
            assert user.password == full_pw

    def test_error_message_mentions_current_categories(self):
        """错误消息应提示当前密码包含的字符类数."""
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                username=self.VALID_USERNAME,
                password="Abcdefghij",
            )
        assert "当前密码仅包含 2 类字符" in str(exc.value)


class TestUserUpdatePassword:
    """UserUpdate 模型的密码复杂度验证测试套件（None 跳过验证）."""

    VALID_USERNAME = "test_user_01"

    def test_none_password_skips_validation(self):
        """password 为 None 时应跳过验证（不更新密码）."""
        update = UserUpdate()
        assert update.password is None

    def test_none_password_with_other_fields(self):
        """password 为 None 时可正常设置其他字段."""
        update = UserUpdate(username="new_user_name", role="user")
        assert update.password is None
        assert update.username == "new_user_name"

    def test_valid_password_three_categories(self):
        """3 类字符组合的合法密码应通过验证."""
        update = UserUpdate(password="NewPass123")
        assert update.password == "NewPass123"

    def test_valid_password_with_special(self):
        """含特殊字符的合法密码应通过验证."""
        update = UserUpdate(password="NewPass123$")
        assert update.password == "NewPass123$"

    def test_weak_password_rejected(self):
        """弱密码应在更新场景下同样被拒绝."""
        with pytest.raises(ValidationError) as exc:
            UserUpdate(password="1234567890")
        assert "至少 3 类" in str(exc.value)

    def test_short_password_rejected(self):
        """长度不足的密码应在更新场景下同样被拒绝."""
        with pytest.raises(ValidationError):
            UserUpdate(password="Ab1!")

    def test_two_categories_rejected(self):
        """仅包含 2 类字符的密码应被拒绝."""
        with pytest.raises(ValidationError) as exc:
            UserUpdate(password="ABCDEFGHij")
        assert "至少 3 类" in str(exc.value)
