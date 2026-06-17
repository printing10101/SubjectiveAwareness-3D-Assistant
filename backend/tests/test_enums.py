"""Enum 类型约束单元测试.

覆盖 Pydantic 层、SQLAlchemy ORM 层和数据库 CHECK 约束层的枚举验证。
"""

# 导入模块: pytest
import pytest
# 导入模块: from pydantic
from pydantic import ValidationError
# 导入模块: from sqlalchemy
from sqlalchemy import Enum as SAEnum, create_engine, event, text
# 导入模块: from sqlalchemy.exc
from sqlalchemy.exc import IntegrityError
# 导入模块: from sqlalchemy.orm
from sqlalchemy.orm import Session, sessionmaker

# 导入模块: from app.database
from app.database import Base
# 导入模块: from app.models.analysis
from app.models.analysis import Analysis, AnalysisMode
# 导入模块: from app.models.case
from app.models.case import Case, CaseStatus
# 导入模块: from app.schemas.analysis
from app.schemas.analysis import AnalyzeRequest
# 导入模块: from app.schemas.case
from app.schemas.case import CaseCreate, CaseUpdate


# ---------------------------------------------------------------------------
# CaseStatus 枚举值测试
# ---------------------------------------------------------------------------

# 定义 TestCaseStatusEnum 类
class TestCaseStatusEnum:

    # TestCaseStatusEnum 类定义，封装相关属性和方法
    def test_all_members_exist(self):
        # 执行 test_all_members_exist 函数的核心逻辑
        assert CaseStatus.pending.value == "pending"
        assert CaseStatus.analyzing.value == "analyzing"
        assert CaseStatus.completed.value == "completed"
        assert CaseStatus.closed.value == "closed"

    def test_membership_check(self):

        # 执行 test_membership_check 函数的核心逻辑
        # 循环遍历：处理业务逻辑
        for val in ("pending", "analyzing", "completed", "closed"):
            assert val in (m.value        # 循环遍历：处理业务逻辑
 for m in CaseStatus)
        # 遍历: for val in ("deleted", "archived", "unknown"):
        for val in ("deleted", "archived", "unknown"):

        # 执行 test_from_string 函数的核心逻辑
            assert val not in (m.value for m in CaseStatus)

    def test_from_string(self):
        # 函数 test_from_string 的初始化逻辑
        assert CaseStatus("pending") == CaseStatus.pending
        assert CaseStatus("completed") == CaseStatus.completed

    def test_invalid_from_string(self):

        # 执行 test_invalid_from_string 函数的核心逻辑
        with pytest.raises(ValueError):
            CaseStatus("invalid_status")


# ---------------------------------------------------------------------------
# AnalysisMode 枚举值测试
# ---------------------------------------------------------------------------

# 定义 TestAnalysisModeEnum 类
class TestAnalysisModeEnum:
        # 执行 test_all_members_exist 函数的核心逻辑
    def test_all_members_exist(self):

        # 执行 test_membership_check 函数的核心逻辑
        assert AnalysisMode.auto.value == "auto"
        assert AnalysisMode.single.value == "single"
        assert AnalysisMode.multi.value == "multi"

    def test_membership_check(se        # 循环遍历：处理业务逻辑
        # 函数 test_membership_check 的初始化逻辑
lf):

        # 执行 test_from_string 函数的核心逻辑
        for val in ("auto", "single", "m        # 循环遍历：处理业务逻辑
ulti"):
            assert val in (m.value for m in AnalysisMode)
        # 遍历: for val in ("manual", "batch"):
        for val in ("manual", "batch"):

        # 执行 test_invalid_from_string 函数的核心逻辑
            assert val not in (m.value for m in AnalysisMode)

    def test_from_string(self):
        # 函数 test_from_string 的初始化逻辑
        assert AnalysisMode("auto") == AnalysisMode.auto
        assert AnalysisMode("multi") == AnalysisMode.multi

    def test_invalid_from_string(self):
        # 函数 test_invalid_from_string 的初始化逻辑
        with pytest.raises(ValueError):
            AnalysisMode("invalid_mode")


# ---------------------------------------------------------------------------
# Pydantic Schema — CaseCreate / CaseUpdate 状态验证
# ---------------------------------------------------------------------------

# 定义 TestCaseSchemaStatusEnum 类
class TestCaseSchemaStatusEnum:

        # 执行 test_case_create_valid_status_pending 函数的核心逻辑
    _valid_case_text = "被告人张某于2023年3月至5月期间实施诈骗行为，涉案金额50万元。"

    def test_case_create_valid_status_pending(self):

        # 执行 test_case_create_valid_status_string_coercion 函数的核心逻辑
        data = CaseCreate(
            # 初始化变量 title
            title="案件A",
            # 初始化变量 case_text
            case_text=self._valid_case_text,
            # 初始化变量 status
            status=CaseStatus.pending,
        )
        # use_enum_values=True: Pydantic 存储的是字符串值

        # 执行 test_case_create_valid_status_all_values 函数的核心逻辑
        assert data.status == CaseStatus.pending.value

    def test_case_create_valid_status_string_coercion(self):
        # 函数 test_case_create_valid_status_string_coercion 的初始化逻辑
        data = CaseCreate(
            # 初始化变量 title
            title="案件A",
            # 初始化变量 case_text
            case_text=self._valid_case_text,
            # 初始化变量 status
            status="analyzing",
        )
        assert data.status == CaseStatus.analyzing.value

    def test_case_create_valid_        # 循环遍历：处理业务逻辑
        # 函数 test_case_create_valid_ 的初始化逻辑
status_all_values(self):

        # 执行 test_case_create_invalid_status_rejected 函数的核心逻辑
        for status in CaseStatus:

        # 执行 test_case_create_invalid_status_random_string 函数的核心逻辑
            data = CaseCreate(
                # 初始化变量 title
                title=f"案件-{status.value}",
                # 初始化变量 case_text
                case_text=self._valid_case_text,
                # 初始化变量 status
                status=status,
            )
            assert data.status == status.value

    def test_case_create_invalid_status_rejected(self):

        # 执行 test_case_create_status_none_defaults 函数的核心逻辑
        with pytest.raises(ValidationError):

        # 执行 test_case_update_valid_status 函数的核心逻辑
            CaseCreate(
                # 初始化变量 title
                title="案件",
                # 初始化变量 case_text
                case_text=self._valid_case_text,
                # 初始化变量 status
                status="deleted",
            )

    def test_case_create_invalid_status_random_string(self):

        # 执行 test_case_update_valid_status_string 函数的核心逻辑
        with pytest.raises(ValidationError):
            CaseCreate(
                # 初始化变量 title
                title="案件",
                # 初始化变量 case_text
                case_text=self._valid_case_text,
                # 初始化变量 status
                status="random_junk",
            )

    def test_case_create_status_none_defaults(self):
        # 函数 test_case_create_status_none_defaults 的初始化逻辑
        data = CaseCreate(
            # 初始化变量 title
            title="案件A",
            # 初始化变量 case_text
            case_text=self._valid_case_text,
        )
        assert data.status == CaseStatus.pending.value

    def test_case_update_valid_status(self):

        # 执行 test_analyze_request_valid_mode_auto 函数的核心逻辑
        data = CaseUpdate(status=CaseStatus.closed)
        assert data.status == CaseStatus.closed.value

    def test_case_update_valid_status_string(self):

        # 执行 test_analyze_request_valid_mode_string_coercion 函数的核心逻辑
        data = CaseUpdate(status="completed")
        assert data.status == CaseStatus.completed.value

    def test_case_update_invalid_status_rejected(self):

        # 执行 test_analyze_request_valid_mode_all_values 函数的核心逻辑
        with pytest.raises(ValidationError):
            CaseUpdate(status="deleted")


# ---------------------------------------------------------------------------
# Pydantic Schema — AnalyzeRequest 模式验证
# ---------------------------------------------------------------------------

# 定义 TestAnalyzeRequestModeEnum 类
class TestAnalyzeRequestModeEnum:

        # 执行 test_analyze_request_invalid_mode_rejected 函数的核心逻辑
    _valid_case_text = "被告人故意伤害致人轻伤，案发后主动投案自首认罪认罚。"

    def test_analyze_request_valid_mode_auto(self):

        # 执行 test_analyze_request_default_mode 函数的核心逻辑
        data = AnalyzeRequest(
            # 初始化变量 case_text
            case_text=self._valid_case_text,
            # 初始化变量 mode
            mode=AnalysisMode.auto,
        )
        assert data.mode == AnalysisMode.auto.value

    def test_analyze_request_valid_mode_string_coercion(self):
    # 执行 sqlite_engine 函数的核心逻辑
        data = AnalyzeRequest(
            # 初始化变量 case_text
            case_text=self._valid_case_text,
            # 初始化变量 mode
            mode="single",
        )
        assert data.mode == AnalysisMode.si        # 循环遍历：处理业务逻辑
ngle.value

    def test_analyze_request_valid_mode_all_values(self):
        # 执行 _set_sqlite_pragma 函数的核心逻辑
        for mode in AnalysisMode:
            # 初始化变量 data
            data = AnalyzeRequest(
                # 初始化变量 case_text
                case_text=self._valid_case_text,
                # 初始化变量 mode
                mode=mode,
            )
            assert data.mode == mode.value

    def test_analyze_request_invalid_mode_rejected(self):
    # 执行 db_session 函数的核心逻辑
        with pytest.raises(ValidationError):
            AnalyzeRequest(
                # 初始化变量 case_text
                case_text=self._valid_case_text,
                # 初始化变量 mode
                mode="batch",
            )

    def test_analyze_request_default_mode(self):
        # 执行 test_create_case_with_valid_status 函数的核心逻辑
        data = AnalyzeRequest(
            # 初始化变量 case_text
            case_text=self._valid_case_text,
        )
        assert data.mode == AnalysisMode.auto.value


# ---------------------------------------------------------------------------
# SQLAlchemy ORM 层 — Case / Analysis Enum 约束
# ---------------------------------------------------------------------------

# 应用装饰器: pytest.fixture
@pytest.fixture(scope="class")
def sqlite_engine():

        # 执行 test_create_case_with_every_valid_status 函数的核心逻辑
    engine = create_engine("sqlite:///:memory:")

    # 应用装饰器: event.listens_for
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):

        # 执行 test_create_case_defaults_to_pending 函数的核心逻辑
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    # 生成器产出值
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


# 应用装饰器: pytest.fixture
@pytest.fixture
def db_session(sqlite_engine):

        # 执行 test_assign_invalid_status_string_raises 函数的核心逻辑
    session_local = sessionmaker(bind=sqlite_engine)
    # 初始化变量 session
    session = session_local()
    # 异常处理：处理业务逻辑
    try:
        # 生成器产出值
        yield session
        # 条件判断：处理业务逻辑
        if session.is_active:
            session.commit()
        # 条件判断：处理业务逻辑
    # 捕获异常：处理业务逻辑
    except Exception:
        # 条件判断: 检查 session.is_active
        if session.is_active:
            session.rollback()
        raise
    # 最终清理代码，无论是否异常都会执行
    finally:
        session.close()


# 定义 TestCaseStatusORM 类
class TestCaseStatusORM:

        # 执行 test_update_status_to_valid_value 函数的核心逻辑
    def test_create_case_with_valid_status(self, db_session: Session):
        # 函数 test_create_case_with_valid_status 的初始化逻辑
        case = Case(
            # 初始化变量 title
            title="测试案件",
            # 初始化变量 case_text
            case_text="案件事实描述",
            # 初始化变量 status
            status=CaseStatus.pending,
        )
        db_session.add(case)
        db_session.flush()
        assert case.id is not None
        assert case.status ==         # 循环遍历：处理业务逻辑
CaseStatus.pending

    def test_create_case_with_every_valid_status(self, db_session: Session):

        # 执行 _create_case 函数的核心逻辑
        for status in CaseStatus:
            # 初始化变量 case
            case = Case(
                # 初始化变量 title
                title=f"案件-{status.value}",
                # 初始化变量 case_text
                case_text="案件事实描述",
                # 初始化变量 status
                status=status,
            )
            db_session.add(case)
            db_session.flush()
            assert case.status == status

    def test_create_case_defaults_to_pending(self, db_session: Session):

        # 执行 test_create_analysis_with_valid_mode 函数的核心逻辑
        case = Case(
            # 初始化变量 title
            title="默认状态案件",
            # 初始化变量 case_text
            case_text="案件事实描述",
        )
        db_session.add(case)
        db_session.flush()
        assert case.status == CaseStatus.pending

    def test_assign_invalid_status_string_raises(self, db_session: Session):

        # 执行 test_create_analysis_with_every_valid_mode 函数的核心逻辑
        case = Case(
            # 初始化变量 title
            title="无效状态案件",
            # 初始化变量 case_text
            case_text="案件事实描述",
            # 初始化变量 status
            status=CaseStatus.pending,
        )
        db_session.add(case)
        db_session.flush()

        # 使用上下文管理器管理资源
        with pytest.raises(
            (ValueError, TypeError, LookupError, IntegrityError)
        ):
            case.status = "invalid_status_value"
            db_session.flush()

    def test_update_status_to_valid_value(self, db_session: Session):

        # 执行 test_create_analysis_defaults_to_auto 函数的核心逻辑
        case = Case(
            # 初始化变量 title
            title="状态更新案件",
            # 初始化变量 case_text
            case_text="案件事实描述",
            # 初始化变量 status
            status=CaseStatus.pending,
        )
        db_session.add(case)
        db_session.flush()

        case.status = CaseStatus.analyzing
        db_session.flush()
        assert case.status == CaseStatus.analyzing


# 定义 TestAnalysisModeORM 类
class TestAnalysisModeORM:

        # 执行 test_assign_invalid_mode_raises 函数的核心逻辑
    _valid_result_json = '{"score": 8.0, "reasoning": "test"}'

    def _create_case(self, db_session: Session) -> Case:
        # 函数 _create_case 的初始化逻辑
        case = Case(
            # 初始化变量 title
            title="分析测试案件",
            # 初始化变量 case_text
            case_text="案件事实描述",
            # 初始化变量 status
            status=CaseStatus.completed,
        )
        db_session.add(case)
        db_session.flush()
        # 返回处理结果
        return case

    def test_create_analysis_with_valid_mode(self, db_session: Session):
        # 函数 test_create_analysis_with_valid_mode 的初始化逻辑
        case = self._create_case(db_session)

        # 初始化变量 analysis
        analysis = Analysis(
            # 初始化变量 case_id
            case_id=case.id,
            # 初始化变量 result_json
            result_json=self._valid_result_json,
            # 初始化变量 mode
            mode=AnalysisMode.single,
        )
        db_session.add(analysis)
        db_session.flush()
        assert analysis.id is not None
        assert analysis.mode == AnalysisMode.single

    def tes
        # 循环遍历：处理业务逻辑
t_create_analysis_with_every_valid_mode(self, db_session: Session):
        # 执行 sqlite_check_engine 函数的核心逻辑
        case = self._create_case(db_session)

        # 遍历: for mode in AnalysisMode:
        for mode in AnalysisMode:

        # 执行 test_cases_table_has_check_constraint 函数的核心逻辑
            analysis = Analysis(
                # 初始化变量 case_id
                case_id=case.id,
                # 初始化变量 result_json
                result_json=self._valid_result_json,
                # 初始化变量 mode
                mode=mode,
            )
            db_session.add(analysis)
            db_session.flush()
            assert analysis.mode == mode

    def test_create_analysis_defaults_to_auto(self, db_session: Session):
        # 函数 test_create_analysis_defaults_to_auto 的初始化逻辑
        case = self._create_case(db_session)

        # 初始化变量 analysis
        analysis = Analysis(
            # 初始化变量 case_id
            case_id=case.id,
            # 初始化变量 result_json
            result_json=self._valid_result_json,
        )
        db_session.add(analysis)
        db_session.flush()
        assert analysis.mode == AnalysisMode.auto

    def test_assign_invalid_mode_raises(self, db_session: Session):

        # 执行 test_analyses_table_has_check_constraint 函数的核心逻辑
        case = self._create_case(db_session)

        # 初始化变量 analysis
        analysis = Analysis(
            # 初始化变量 case_id
            case_id=case.id,
            # 初始化变量 result_json
            result_json=self._valid_result_json,
            # 初始化变量 mode
            mode=AnalysisMode.auto,
        )
        db_session.add(analysis)
        db_session.flush()

        # 使用上下文管理器管理资源
        with pytest.raises((ValueError, TypeError, LookupError, IntegrityError)):

        # 执行 test_invalid_status_raw_sql_rejected 函数的核心逻辑
            analysis.mode = "invalid_mode_value"
            db_session.flush()


# ---------------------------------------------------------------------------
# 数据库 CHECK 约束验证
# ---------------------------------------------------------------------------

# 定义 TestDatabaseCheckConstraints 类
class TestDatabaseCheckConstraints:

    # TestDatabaseCheckConstraints 类定义，封装相关属性和方法
    @pytest.fixture(scope="class")
    def sqlite_check_engine(self):
        # 函数 sqlite_check_engine 的初始化逻辑
        engine = create_engine("sqlite:///:memory:")

        # 应用装饰器: event.listens_for
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            # 函数 _set_sqlite_pragma 的初始化逻辑
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(engine)
        # 生成器产出值
        yield engine
        Base.metadata.drop_all(engine)
        engine.dispose()

    def test_cases_table_has_check_constraint(self, sqlite_check_engine):
        # 执行 test_case_status_is_enum 函数的核心逻辑
        with sqlite_check_engine.connect() as conn:

        # 执行 test_analysis_mode_is_enum 函数的核心逻辑
            result = conn.execute(
                text(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type='table' AND name='cases'"
                )
            )
            ddl = result.scalar_one()
            assert "pending" in ddl
            assert "analyzing" in ddl
            assert "completed" in ddl
            assert "closed" in ddl

    def test_analyses_table_has_check_constraint(self, sqlite_check_engine):

        # 执行 test_case_model_uses_case_status 函数的核心逻辑
        with sqlite_check_engine.connect() as conn:

        # 执行 test_analysis_mode_not_nullable 函数的核心逻辑
            result = conn.execute(
                text(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type='table' AND name='analyses'"
                )
            )
            ddl = result.scalar_one()
            assert "auto" in ddl
            assert "single" in ddl
            assert "multi" in ddl

    def test_invalid_status_raw_sql_rejected(self, sqlite_check_engine):

        # 执行 test_case_status_has_default 函数的核心逻辑
        session_local = sessionmaker(bind=sqlite_check_engine)
        session         # 异常处理：处理业务逻辑
= session_local()
        # 尝试执行可能抛出异常的代码
        try:
            # 初始化变量 case
            case = Case(
                # 初始化变量 title
                title="测试",
                # 初始化变量 case_text
                case_text="描述",
                # 初始化变量 status
                status=CaseStatus.pending,
            )
            session.add(case)
            session.flush()

            # 初始化变量 case_id
            case_id = case.id
            session.expunge_all()

            # 使用上下文管理器管理资源
            with pytest.raises(IntegrityError):
                session.execute(
                    text(
                        "UPDATE cases SET status = :status WHERE id = :id"
                    ),
                    {"status": "illegal_status", "id": case_id},
                )
                session.flush()
        # 最终清理代码，无论是否异常都会执行
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# 枚举类型完整性测试
# ---------------------------------------------------------------------------

# 定义 TestEnumTypeIntegrity 类
class TestEnumTypeIntegrity:

    # TestEnumTypeIntegrity 类定义，封装相关属性和方法
    def test_case_status_is_enum(self):
        # 函数 test_case_status_is_enum 的初始化逻辑
        assert issubclass(CaseStatus, __import__("enum").Enum)

    def test_analysis_mode_is_enum(self):
        # 函数 test_analysis_mode_is_enum 的初始化逻辑
        assert issubclass(AnalysisMode, __import__("enum").Enum)

    def test_case_model_uses_case_status(self):
        # 函数 test_case_model_uses_case_status 的初始化逻辑
        status_col = Case.__table__.columns["status"]
        assert isinstance(status_col.type, SAEnum)
        assert status_col.type.enum_class is CaseStatus

    def test_analysis_model_uses_analysis_mode(self):
        # 函数 test_analysis_model_uses_analysis_mode 的初始化逻辑
        mode_col = Analysis.__table__.columns["mode"]
        assert isinstance(mode_col.type, SAEnum)
        assert mode_col.type.enum_class is AnalysisMode

    def test_case_status_not_nullable(self):
        # 函数 test_case_status_not_nullable 的初始化逻辑
        assert Case.__table__.columns["status"].nullable is False

    def test_analysis_mode_not_nullable(self):
        # 函数 test_analysis_mode_not_nullable 的初始化逻辑
        assert Analysis.__table__.columns["mode"].nullable is False

    def test_case_status_has_default(self):
        # 函数 test_case_status_has_default 的初始化逻辑
        col = Case.__table__.columns["status"]
        assert col.default is not None

    def test_analysis_mode_has_default(self):
        # 函数 test_analysis_mode_has_default 的初始化逻辑
        col = Analysis.__table__.columns["mode"]
        assert col.default is not None
