# Trae Solo 提示词 - 单元测试补全

## 任务目标
为核心业务逻辑补全单元测试，确保代码质量和可维护性。

## 执行步骤

### 步骤1: 检查现有测试
```bash
cd backend

# 查看现有测试
find tests -name "*.py" -type f

# 运行现有测试
pytest tests/ -v --tb=short

# 查看测试覆盖率
pytest tests/ --cov=app --cov-report=term-missing
```

### 步骤2: 创建测试基类
创建 `backend/tests/conftest.py`：

```python
"""测试配置和固件."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# 测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """创建测试数据库会话."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """创建测试客户端."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

### 步骤3: 测试分析服务
创建 `backend/tests/test_analysis_service.py`：

```python
"""分析服务测试."""

import pytest
from fastapi import HTTPException

from app.models.case import Case
from app.services.analysis_service import (
    run_analysis,
    get_analysis,
    get_analyses_for_case,
    _compute_knowledge_score,
)


class TestComputeKnowledgeScore:
    """测试知识评分计算."""
    
    def test_valid_result(self):
        """测试有效结果."""
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 8.5},
                "dimension2": {"score": 7.0},
                "dimension3": {"score": 3.0},
            }
        }
        score = _compute_knowledge_score(result)
        assert score == 6.166666666666667  # (8.5 + 7.0 + 3.0) / 3
    
    def test_missing_analysis(self):
        """测试缺少分析结果."""
        result = {}
        score = _compute_knowledge_score(result)
        assert score is None
    
    def test_partial_scores(self):
        """测试部分维度有评分."""
        result = {
            "ground_truth_analysis": {
                "dimension1": {"score": 8.5},
                "dimension3": {"score": 3.0},
            }
        }
        score = _compute_knowledge_score(result)
        assert score == 5.75  # (8.5 + 3.0) / 2


class TestRunAnalysis:
    """测试运行分析."""
    
    @pytest.mark.asyncio
    async def test_case_not_found(self, db):
        """测试案件不存在."""
        with pytest.raises(HTTPException) as exc_info:
            await run_analysis(db, case_id=999, mode="auto")
        assert exc_info.value.status_code == 404
        assert "案件不存在" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_successful_analysis(self, db):
        """测试成功分析."""
        # 创建测试案件
        case = Case(
            title="测试案件",
            case_text="这是一起帮信罪案件，嫌疑人出售银行卡...",
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        
        # 运行分析
        analysis = await run_analysis(db, case_id=case.id, mode="auto")
        
        # 验证结果
        assert analysis.case_id == case.id
        assert analysis.mode == "auto"
        assert analysis.result_json is not None
        assert analysis.knowledge_score is not None


class TestGetAnalysis:
    """测试获取分析结果."""
    
    def test_existing_analysis(self, db):
        """测试获取存在的分析."""
        # 创建测试数据
        from app.models.analysis import Analysis
        analysis = Analysis(
            case_id=1,
            result_json='{"test": "data"}',
            mode="auto",
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # 获取
        result = get_analysis(db, analysis.id)
        assert result is not None
        assert result.id == analysis.id
    
    def test_nonexistent_analysis(self, db):
        """测试获取不存在的分析."""
        result = get_analysis(db, 999)
        assert result is None
```

### 步骤4: 测试案件服务
创建 `backend/tests/test_case_service.py`：

```python
"""案件服务测试."""

import pytest
from fastapi import HTTPException

from app.schemas.case import CaseCreate, CaseUpdate
from app.services.case_service import (
    create_case,
    get_case,
    get_cases,
    update_case,
    delete_case,
)


class TestCreateCase:
    """测试创建案件."""
    
    def test_create_success(self, db):
        """测试成功创建."""
        case_data = CaseCreate(
            title="测试案件",
            description="案件描述",
            case_text="案件事实文本...",
        )
        
        case = create_case(db, case_data)
        
        assert case.title == "测试案件"
        assert case.description == "案件描述"
        assert case.case_text == "案件事实文本..."
        assert case.status == "pending"
    
    def test_create_minimal(self, db):
        """测试最小数据创建."""
        case_data = CaseCreate(
            title="最小案件",
            case_text="只有标题和文本",
        )
        
        case = create_case(db, case_data)
        
        assert case.title == "最小案件"
        assert case.description is None


class TestGetCase:
    """测试获取案件."""
    
    def test_get_existing(self, db):
        """测试获取存在的案件."""
        from app.models.case import Case
        case = Case(
            title="测试案件",
            case_text="测试文本",
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        
        result = get_case(db, case.id)
        assert result is not None
        assert result.id == case.id
    
    def test_get_nonexistent(self, db):
        """测试获取不存在的案件."""
        result = get_case(db, 999)
        assert result is None


class TestGetCases:
    """测试获取案件列表."""
    
    def test_pagination(self, db):
        """测试分页."""
        from app.models.case import Case
        # 创建10个案件
        for i in range(10):
            case = Case(title=f"案件{i}", case_text=f"文本{i}")
            db.add(case)
        db.commit()
        
        # 测试分页
        cases = get_cases(db, skip=0, limit=5)
        assert len(cases) == 5
        
        cases = get_cases(db, skip=5, limit=5)
        assert len(cases) == 5
    
    def test_status_filter(self, db):
        """测试状态筛选."""
        from app.models.case import Case
        # 创建不同状态的案件
        case1 = Case(title="案件1", case_text="文本1", status="pending")
        case2 = Case(title="案件2", case_text="文本2", status="completed")
        db.add(case1)
        db.add(case2)
        db.commit()
        
        # 筛选
        pending_cases = get_cases(db, status_filter="pending")
        assert len(pending_cases) == 1
        assert pending_cases[0].status == "pending"


class TestUpdateCase:
    """测试更新案件."""
    
    def test_update_success(self, db):
        """测试成功更新."""
        from app.models.case import Case
        case = Case(title="原标题", case_text="原文本")
        db.add(case)
        db.commit()
        db.refresh(case)
        
        update_data = CaseUpdate(title="新标题")
        updated = update_case(db, case.id, update_data)
        
        assert updated.title == "新标题"
        assert updated.case_text == "原文本"  # 未修改字段保持不变
    
    def test_update_nonexistent(self, db):
        """测试更新不存在的案件."""
        update_data = CaseUpdate(title="新标题")
        
        with pytest.raises(HTTPException) as exc_info:
            update_case(db, 999, update_data)
        assert exc_info.value.status_code == 404


class TestDeleteCase:
    """测试删除案件."""
    
    def test_delete_success(self, db):
        """测试成功删除."""
        from app.models.case import Case
        case = Case(title="待删除", case_text="文本")
        db.add(case)
        db.commit()
        db.refresh(case)
        
        result = delete_case(db, case.id)
        assert result is True
        
        # 验证已删除
        deleted = get_case(db, case.id)
        assert deleted is None
    
    def test_delete_nonexistent(self, db):
        """测试删除不存在的案件."""
        with pytest.raises(HTTPException) as exc_info:
            delete_case(db, 999)
        assert exc_info.value.status_code == 404
```

### 步骤5: 测试工具函数
创建 `backend/tests/test_utils.py`：

```python
"""工具函数测试."""

import pytest

from app.utils.common import generate_cache_key, sanitize_json_string


class TestGenerateCacheKey:
    """测试缓存键生成."""
    
    def test_string_input(self):
        """测试字符串输入."""
        key1 = generate_cache_key("test text", "auto")
        key2 = generate_cache_key("test text", "auto")
        assert key1 == key2  # 相同输入产生相同键
    
    def test_different_inputs(self):
        """测试不同输入."""
        key1 = generate_cache_key("text1", "auto")
        key2 = generate_cache_key("text2", "auto")
        assert key1 != key2
    
    def test_complex_input(self):
        """测试复杂输入."""
        key = generate_cache_key("案件文本", "multi", {"option": "value"})
        assert len(key) == 32  # MD5哈希长度


class TestSanitizeJsonString:
    """测试JSON字符串清理."""
    
    def test_valid_json(self):
        """测试有效JSON."""
        input_str = '{"key": "value"}'
        result = sanitize_json_string(input_str)
        assert result == input_str
    
    def test_with_markdown(self):
        """测试带Markdown标记."""
        input_str = '```json\n{"key": "value"}\n```'
        result = sanitize_json_string(input_str)
        assert result == '{"key": "value"}'
    
    def test_with_comments(self):
        """测试带注释."""
        input_str = '// 注释\n{"key": "value"}'
        result = sanitize_json_string(input_str)
        assert result == '{"key": "value"}'
```

### 步骤6: 运行测试并检查覆盖率
```bash
cd backend

# 运行所有测试
pytest tests/ -v --tb=short

# 检查覆盖率
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=80

# 生成HTML报告
pytest tests/ --cov=app --cov-report=html
```

### 步骤7: 提交代码
```bash
git add -A
git commit -m "test(backend): 补全核心业务单元测试

- 添加conftest.py测试固件配置
- 测试分析服务：评分计算、运行分析、查询
- 测试案件服务：CRUD操作、分页、筛选
- 测试工具函数：缓存键、JSON清理
- 测试覆盖率提升至80%+
- 所有测试通过"
```

## 完成标准
- [ ] `conftest.py` 包含测试固件
- [ ] `test_analysis_service.py` 覆盖分析服务
- [ ] `test_case_service.py` 覆盖案件服务
- [ ] `test_utils.py` 覆盖工具函数
- [ ] `pytest tests/` 全部通过
- [ ] 测试覆盖率 >= 80%
- [ ] 代码已提交

## 验证命令
```bash
cd backend

# 运行测试
pytest tests/ -v

# 检查覆盖率
pytest tests/ --cov=app --cov-report=term

# 查看详细报告
pytest tests/ --cov=app --cov-report=html
# 然后打开 htmlcov/index.html
```
