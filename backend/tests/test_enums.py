"""Enum 类型约束单元测试.

覆盖 Pydantic 层、SQLAlchemy ORM 层和数据库 CHECK 约束层的枚举验证。
"""

import pytest
from pydantic import ValidationError
from sqlalchemy import Enum as SAEnum, create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models.analysis import Analysis, AnalysisMode
from app.models.case import Case, CaseStatus
from app.schemas.analysis import AnalyzeRequest
from app.schemas.case import CaseCreate, CaseUpdate


# ---------------------------------------------------------------------------
# CaseStatus 枚举值测试
# ---------------------------------------------------------------------------

class TestCaseStatusEnum:
    def test_all_members_exist(self):
        assert CaseStatus.pending.value == "pending"
        assert CaseStatus.analyzing.value == "analyzing"
        assert CaseStatus.completed.value == "completed"
        assert CaseStatus.closed.value == "closed"

    def test_membership_check(self):
        for val in ("pending", "analyzing", "completed", "closed"):
            assert val in (m.value for m in CaseStatus)
        for val in ("deleted", "archived", "unknown"):
            assert val not in (m.value for m in CaseStatus)

    def test_from_string(self):
        assert CaseStatus("pending") == CaseStatus.pending
        assert CaseStatus("completed") == CaseStatus.completed

    def test_invalid_from_string(self):
        with pytest.raises(ValueError):
            CaseStatus("invalid_status")


# ---------------------------------------------------------------------------
# AnalysisMode 枚举值测试
# ---------------------------------------------------------------------------

class TestAnalysisModeEnum:
    def test_all_members_exist(self):
        assert AnalysisMode.auto.value == "auto"
        assert AnalysisMode.single.value == "single"
        assert AnalysisMode.multi.value == "multi"

    def test_membership_check(self):
        for val in ("auto", "single", "multi"):
            assert val in (m.value for m in AnalysisMode)
        for val in ("manual", "batch"):
            assert val not in (m.value for m in AnalysisMode)

    def test_from_string(self):
        assert AnalysisMode("auto") == AnalysisMode.auto
        assert AnalysisMode("multi") == AnalysisMode.multi

    def test_invalid_from_string(self):
        with pytest.raises(ValueError):
            AnalysisMode("invalid_mode")


# ---------------------------------------------------------------------------
# Pydantic Schema — CaseCreate / CaseUpdate 状态验证
# ---------------------------------------------------------------------------

class TestCaseSchemaStatusEnum:
    _valid_case_text = "被告人张某于2023年3月至5月期间实施诈骗行为，涉案金额50万元。"

    def test_case_create_valid_status_pending(self):
        data = CaseCreate(
            title="案件A",
            case_text=self._valid_case_text,
            status=CaseStatus.pending,
        )
        # use_enum_values=True: Pydantic 存储的是字符串值
        assert data.status == CaseStatus.pending.value

    def test_case_create_valid_status_string_coercion(self):
        data = CaseCreate(
            title="案件A",
            case_text=self._valid_case_text,
            status="analyzing",
        )
        assert data.status == CaseStatus.analyzing.value

    def test_case_create_valid_status_all_values(self):
        for status in CaseStatus:
            data = CaseCreate(
                title=f"案件-{status.value}",
                case_text=self._valid_case_text,
                status=status,
            )
            assert data.status == status.value

    def test_case_create_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            CaseCreate(
                title="案件",
                case_text=self._valid_case_text,
                status="deleted",
            )

    def test_case_create_invalid_status_random_string(self):
        with pytest.raises(ValidationError):
            CaseCreate(
                title="案件",
                case_text=self._valid_case_text,
                status="random_junk",
            )

    def test_case_create_status_none_defaults(self):
        data = CaseCreate(
            title="案件A",
            case_text=self._valid_case_text,
        )
        assert data.status == CaseStatus.pending.value

    def test_case_update_valid_status(self):
        data = CaseUpdate(status=CaseStatus.closed)
        assert data.status == CaseStatus.closed.value

    def test_case_update_valid_status_string(self):
        data = CaseUpdate(status="completed")
        assert data.status == CaseStatus.completed.value

    def test_case_update_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            CaseUpdate(status="deleted")


# ---------------------------------------------------------------------------
# Pydantic Schema — AnalyzeRequest 模式验证
# ---------------------------------------------------------------------------

class TestAnalyzeRequestModeEnum:
    _valid_case_text = "被告人故意伤害致人轻伤，案发后主动投案自首认罪认罚。"

    def test_analyze_request_valid_mode_auto(self):
        data = AnalyzeRequest(
            case_text=self._valid_case_text,
            mode=AnalysisMode.auto,
        )
        assert data.mode == AnalysisMode.auto.value

    def test_analyze_request_valid_mode_string_coercion(self):
        data = AnalyzeRequest(
            case_text=self._valid_case_text,
            mode="single",
        )
        assert data.mode == AnalysisMode.single.value

    def test_analyze_request_valid_mode_all_values(self):
        for mode in AnalysisMode:
            data = AnalyzeRequest(
                case_text=self._valid_case_text,
                mode=mode,
            )
            assert data.mode == mode.value

    def test_analyze_request_invalid_mode_rejected(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(
                case_text=self._valid_case_text,
                mode="batch",
            )

    def test_analyze_request_default_mode(self):
        data = AnalyzeRequest(
            case_text=self._valid_case_text,
        )
        assert data.mode == AnalysisMode.auto.value


# ---------------------------------------------------------------------------
# SQLAlchemy ORM 层 — Case / Analysis Enum 约束
# ---------------------------------------------------------------------------

@pytest.fixture(scope="class")
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    session_local = sessionmaker(bind=sqlite_engine)
    session = session_local()
    try:
        yield session
        if session.is_active:
            session.commit()
    except Exception:
        if session.is_active:
            session.rollback()
        raise
    finally:
        session.close()


class TestCaseStatusORM:
    def test_create_case_with_valid_status(self, db_session: Session):
        case = Case(
            title="测试案件",
            case_text="案件事实描述",
            status=CaseStatus.pending,
        )
        db_session.add(case)
        db_session.flush()
        assert case.id is not None
        assert case.status == CaseStatus.pending

    def test_create_case_with_every_valid_status(self, db_session: Session):
        for status in CaseStatus:
            case = Case(
                title=f"案件-{status.value}",
                case_text="案件事实描述",
                status=status,
            )
            db_session.add(case)
            db_session.flush()
            assert case.status == status

    def test_create_case_defaults_to_pending(self, db_session: Session):
        case = Case(
            title="默认状态案件",
            case_text="案件事实描述",
        )
        db_session.add(case)
        db_session.flush()
        assert case.status == CaseStatus.pending

    def test_assign_invalid_status_string_raises(self, db_session: Session):
        case = Case(
            title="无效状态案件",
            case_text="案件事实描述",
            status=CaseStatus.pending,
        )
        db_session.add(case)
        db_session.flush()

        with pytest.raises(
            (ValueError, TypeError, LookupError, IntegrityError)
        ):
            case.status = "invalid_status_value"
            db_session.flush()

    def test_update_status_to_valid_value(self, db_session: Session):
        case = Case(
            title="状态更新案件",
            case_text="案件事实描述",
            status=CaseStatus.pending,
        )
        db_session.add(case)
        db_session.flush()

        case.status = CaseStatus.analyzing
        db_session.flush()
        assert case.status == CaseStatus.analyzing


class TestAnalysisModeORM:
    _valid_result_json = '{"score": 8.0, "reasoning": "test"}'

    def _create_case(self, db_session: Session) -> Case:
        case = Case(
            title="分析测试案件",
            case_text="案件事实描述",
            status=CaseStatus.completed,
        )
        db_session.add(case)
        db_session.flush()
        return case

    def test_create_analysis_with_valid_mode(self, db_session: Session):
        case = self._create_case(db_session)

        analysis = Analysis(
            case_id=case.id,
            result_json=self._valid_result_json,
            mode=AnalysisMode.single,
        )
        db_session.add(analysis)
        db_session.flush()
        assert analysis.id is not None
        assert analysis.mode == AnalysisMode.single

    def test_create_analysis_with_every_valid_mode(self, db_session: Session):
        case = self._create_case(db_session)

        for mode in AnalysisMode:
            analysis = Analysis(
                case_id=case.id,
                result_json=self._valid_result_json,
                mode=mode,
            )
            db_session.add(analysis)
            db_session.flush()
            assert analysis.mode == mode

    def test_create_analysis_defaults_to_auto(self, db_session: Session):
        case = self._create_case(db_session)

        analysis = Analysis(
            case_id=case.id,
            result_json=self._valid_result_json,
        )
        db_session.add(analysis)
        db_session.flush()
        assert analysis.mode == AnalysisMode.auto

    def test_assign_invalid_mode_raises(self, db_session: Session):
        case = self._create_case(db_session)

        analysis = Analysis(
            case_id=case.id,
            result_json=self._valid_result_json,
            mode=AnalysisMode.auto,
        )
        db_session.add(analysis)
        db_session.flush()

        with pytest.raises((ValueError, TypeError, LookupError, IntegrityError)):
            analysis.mode = "invalid_mode_value"
            db_session.flush()


# ---------------------------------------------------------------------------
# 数据库 CHECK 约束验证
# ---------------------------------------------------------------------------

class TestDatabaseCheckConstraints:
    @pytest.fixture(scope="class")
    def sqlite_check_engine(self):
        engine = create_engine("sqlite:///:memory:")

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(engine)
        yield engine
        Base.metadata.drop_all(engine)
        engine.dispose()

    def test_cases_table_has_check_constraint(self, sqlite_check_engine):
        with sqlite_check_engine.connect() as conn:
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
        with sqlite_check_engine.connect() as conn:
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
        session_local = sessionmaker(bind=sqlite_check_engine)
        session = session_local()
        try:
            case = Case(
                title="测试",
                case_text="描述",
                status=CaseStatus.pending,
            )
            session.add(case)
            session.flush()

            case_id = case.id
            session.expunge_all()

            with pytest.raises(IntegrityError):
                session.execute(
                    text(
                        "UPDATE cases SET status = :status WHERE id = :id"
                    ),
                    {"status": "illegal_status", "id": case_id},
                )
                session.flush()
        finally:
            session.rollback()
            session.close()


# ---------------------------------------------------------------------------
# 枚举类型完整性测试
# ---------------------------------------------------------------------------

class TestEnumTypeIntegrity:
    def test_case_status_is_enum(self):
        assert issubclass(CaseStatus, __import__("enum").Enum)

    def test_analysis_mode_is_enum(self):
        assert issubclass(AnalysisMode, __import__("enum").Enum)

    def test_case_model_uses_case_status(self):
        status_col = Case.__table__.columns["status"]
        assert isinstance(status_col.type, SAEnum)
        assert status_col.type.enum_class is CaseStatus

    def test_analysis_model_uses_analysis_mode(self):
        mode_col = Analysis.__table__.columns["mode"]
        assert isinstance(mode_col.type, SAEnum)
        assert mode_col.type.enum_class is AnalysisMode

    def test_case_status_not_nullable(self):
        assert Case.__table__.columns["status"].nullable is False

    def test_analysis_mode_not_nullable(self):
        assert Analysis.__table__.columns["mode"].nullable is False

    def test_case_status_has_default(self):
        col = Case.__table__.columns["status"]
        assert col.default is not None

    def test_analysis_mode_has_default(self):
        col = Analysis.__table__.columns["mode"]
        assert col.default is not None
