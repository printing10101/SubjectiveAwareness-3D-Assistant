# Trae Solo 完整优化提示词

> 直接复制以下内容到Trae Solo模式中使用

---

## 系统提示词（复制到Trae设置）

```markdown
你是代码优化专家，负责对【帮信罪主观明知智能分析系统】执行代码库优化。

【项目信息】
- 项目路径: c:\Users\Lenovo\Desktop\微信程序开发
- 技术栈: Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Vue 3 / Pinia
- 数据库: SQLite (开发) / Neo4j (知识图谱)
- AI模型: Ollama + DeepSeek-R1

【执行原则】
1. 每步修改必须有对应的验证检测
2. 所有测试必须通过才能提交
3. 保持现有功能不变，只做优化
4. 遵循项目代码规范（见CODING_STANDARDS.md）

【验证标准】
- Python: ruff check . 无错误 + pytest tests/ 全部通过
- 前端: npm run lint 无错误 + npm run build 成功
- 功能: 手动测试核心分析流程正常

【提交格式】
<type>(<scope>): <描述>

- 具体修改内容
- 所有测试通过
```

---

## 任务1: 后端日志规范化

**直接复制以下提示词开始执行：**

```markdown
【任务】修复后端代码中的日志f-string问题

【扫描命令】
cd backend && grep -rn "logger\.\(info\|debug\|warning\|error\).*f\"" --include="*.py" app/

【修复规则】
将所有f-string日志改为结构化参数格式：
- logger.info(f"分析完成，耗时 {elapsed}ms") → logger.info("分析完成，耗时 {}ms", elapsed)
- logger.debug(f"处理案件 ID={case_id}") → logger.debug("处理案件 ID={}", case_id)
- logger.error("失败: {}".format(err)) → logger.error("失败: {}", err)

【需要修复的文件】
1. app/routers/analysis.py 第62行: logger.info(f"收到分析请求 (文本长度: {len(case_text)})")
2. app/services/analysis_service.py 第79行: logger.info("分析完成: fallback={}, time={}ms", ...)
3. 扫描发现的其他位置

【验证命令】
grep -rn "logger\.\(info\|debug\|warning\|error\).*f\"" --include="*.py" app/ || echo "✓ 无f-string日志"
ruff check app/ --select G004 || echo "✓ Ruff检查通过"
pytest tests/ -v --tb=short

【完成标准】
- grep返回空（无f-string日志）
- ruff check无G004错误
- pytest全部通过
- git commit提交完成

请立即开始执行：先扫描，再修复，最后验证并提交。
```

---

## 任务2: 数据库连接池配置

**直接复制以下提示词开始执行：**

```markdown
【任务】为数据库添加连接池配置

【修改文件】backend/app/database.py

【修改内容】
将engine创建代码修改为：

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

【验证命令】
cd backend && python -c "from app.database import engine; print(f'Pool size: {engine.pool.size()}')"
pytest tests/ -v -k "db" --tb=short

【完成标准】
- engine包含pool_size等参数
- 服务启动无错误
- pytest通过
- git commit提交完成

请立即修改database.py并验证。
```

---

## 任务3: 前端API层封装

**直接复制以下提示词开始执行：**

```markdown
【任务】创建前端API封装层

【创建目录】frontend/src/api/ 和 frontend/src/api/modules/

【创建文件1】frontend/src/api/config.js
内容：
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const TIMEOUT = 120000
export const apiConfig = {
  baseURL: BASE_URL,
  timeout: TIMEOUT,
  headers: { 'Content-Type': 'application/json' },
}
export const responseHandlers = {
  200: (data) => data,
  400: (error) => { throw new Error(error.detail || '请求参数错误') },
  404: (error) => { throw new Error(error.detail || '资源不存在') },
  500: (error) => { throw new Error('服务器内部错误') },
  502: (error) => { throw new Error('分析服务暂时不可用') },
}

【创建文件2】frontend/src/api/instance.js
内容：
import axios from 'axios'
import { apiConfig, responseHandlers } from './config'
const apiInstance = axios.create(apiConfig)
apiInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
apiInstance.interceptors.response.use(
  (response) => responseHandlers[response.status]?.(response.data) ?? response.data,
  (error) => {
    if (error.response) responseHandlers[error.response.status]?.(error.response.data)
    return Promise.reject(error)
  }
)
export default apiInstance

【创建文件3】frontend/src/api/modules/analysis.js
内容：
import api from '../instance'
export const analyzeCase = (params) => api.post('/api/analyze', params)
export const getAnalysisHistory = (caseId) => api.get(`/api/cases/${caseId}/analyses`)
export default { analyzeCase, getAnalysisHistory }

【创建文件4】frontend/src/api/modules/cases.js
内容：
import api from '../instance'
export const getCases = (params = {}) => api.get('/api/cases', { params })
export const getCaseById = (caseId) => api.get(`/api/cases/${caseId}`)
export const createCase = (data) => api.post('/api/cases', data)
export const updateCase = (caseId, data) => api.put(`/api/cases/${caseId}`, data)
export const deleteCase = (caseId) => api.delete(`/api/cases/${caseId}`)
export default { getCases, getCaseById, createCase, updateCase, deleteCase }

【创建文件5】frontend/src/api/index.js
内容：
import analysisApi from './modules/analysis'
import casesApi from './modules/cases'
export const analysis = analysisApi
export const cases = casesApi
export default { analysis: analysisApi, cases: casesApi }

【验证命令】
cd frontend && npm run lint && npm run build

【完成标准】
- src/api/目录结构完整
- npm run lint无错误
- npm run build成功
- git commit提交完成

请立即创建所有文件并验证。
```

---

## 任务4: 安全配置加固

**直接复制以下提示词开始执行：**

```markdown
【任务】强制环境变量读取敏感配置

【修改文件】backend/app/config.py

【修改内容】
将JWT_SECRET_KEY改为必填字段：

class Settings(BaseSettings):
    # JWT配置（敏感，必须设置）
    JWT_SECRET_KEY: str = Field(
        ...,  # 无默认值，必须设置
        min_length=32,
        description="JWT签名密钥，至少32字符",
    )
    
    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY必须至少32字符")
        return v

【创建文件】backend/scripts/verify_config.py
内容：
import sys
from app.config import settings

def verify_security_config():
    errors = []
    if settings.JWT_SECRET_KEY == "your-secret-key-here":
        errors.append("JWT_SECRET_KEY使用了默认占位符")
    elif len(settings.JWT_SECRET_KEY) < 32:
        errors.append(f"JWT_SECRET_KEY长度不足({len(settings.JWT_SECRET_KEY)}字符)")
    if errors:
        print("❌ 配置错误:")
        for e in errors: print(f"  • {e}")
        return False
    print("✅ 配置验证通过")
    return True

if __name__ == "__main__":
    if not verify_security_config(): sys.exit(1)

【更新.env.example】
添加注释：
# JWT配置（必须设置！）
# 生成命令: openssl rand -hex 32
JWT_SECRET_KEY=your-secret-key-here-change-this-in-production

【验证命令】
cd backend && python scripts/verify_config.py

【完成标准】
- JWT_SECRET_KEY无默认值
- verify_config.py可运行
- 配置验证通过
- git commit提交完成

请立即修改config.py并创建验证脚本。
```

---

## 任务5: API请求限流

**直接复制以下提示词开始执行：**

```markdown
【任务】添加API请求限流

【安装依赖】pip install slowapi

【创建文件】backend/app/middleware/rate_limit.py
内容：
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

【修改文件】backend/app/main.py
添加：
from slowapi.errors import RateLimitExceeded
from app.middleware.rate_limit import limiter, rate_limit_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

【为关键路由添加限流】
在analysis.py的analyze_case函数添加：
from app.middleware.rate_limit import limiter

@router.post("/analyze")
@limiter.limit("10/minute")
async def analyze_case(request: Request, ...):

【验证命令】
cd backend && python run.py &
for i in {1..12}; do curl -s -o /dev/null -w "%{http_code} " -X POST http://localhost:8000/api/analyze -H "Content-Type: application/json" -d '{"case_text":"测试","mode":"auto"}'; done
echo ""
# 预期: 200重复10次后出现429

【完成标准】
- slowapi已安装
- 限流中间件已配置
- 超限返回429
- git commit提交完成

请立即安装依赖并添加限流配置。
```

---

## 任务6: 单元测试补全

**直接复制以下提示词开始执行：**

```markdown
【任务】补全核心业务单元测试

【创建文件】backend/tests/conftest.py
内容：
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try: yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try: yield db
        finally: pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client: yield test_client
    app.dependency_overrides.clear()

【创建文件】backend/tests/test_analysis_service.py
内容：
import pytest
from app.services.analysis_service import _compute_knowledge_score

class TestComputeKnowledgeScore:
    def test_valid_result(self):
        result = {"ground_truth_analysis": {"dimension1": {"score": 8.5}, "dimension2": {"score": 7.0}, "dimension3": {"score": 3.0}}}
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(6.17)
    
    def test_missing_analysis(self):
        result = {}
        score = _compute_knowledge_score(result)
        assert score is None
    
    def test_partial_scores(self):
        result = {"ground_truth_analysis": {"dimension1": {"score": 8.5}, "dimension3": {"score": 3.0}}}
        score = _compute_knowledge_score(result)
        assert score == pytest.approx(5.75)

【创建文件】backend/tests/test_case_service.py
内容：
import pytest
from app.schemas.case import CaseCreate
from app.services.case_service import create_case, get_case

class TestCreateCase:
    def test_create_success(self, db):
        case_data = CaseCreate(title="测试案件", case_text="案件事实...")
        case = create_case(db, case_data)
        assert case.title == "测试案件"
        assert case.status == "pending"

class TestGetCase:
    def test_get_existing(self, db):
        from app.models.case import Case
        case = Case(title="测试", case_text="文本")
        db.add(case); db.commit(); db.refresh(case)
        result = get_case(db, case.id)
        assert result is not None
    
    def test_get_nonexistent(self, db):
        result = get_case(db, 999)
        assert result is None

【验证命令】
cd backend && pytest tests/ -v --tb=short --cov=app --cov-report=term

【完成标准】
- conftest.py包含测试固件
- pytest全部通过
- 覆盖率>=80%
- git commit提交完成

请立即创建测试文件并运行验证。
```

---

## 执行顺序建议

```
立即执行（今天）:
1. 任务1: 后端日志规范化 → 30分钟
2. 任务2: 数据库连接池 → 20分钟
3. 任务4: 安全配置加固 → 30分钟

明天执行:
4. 任务3: 前端API层 → 1小时
5. 任务5: 请求限流 → 30分钟
6. 任务6: 单元测试 → 1小时
```

---

## 快速启动提示词

如果你想**一次性执行所有任务**，使用这个提示词：

```markdown
【任务】执行代码库全面优化

【项目】帮信罪主观明知智能分析系统
【路径】c:\Users\Lenovo\Desktop\微信程序开发

【执行顺序】
1. 后端日志规范化（修复f-string）
2. 数据库连接池配置
3. 安全配置加固（强制环境变量）
4. 前端API层封装
5. API请求限流
6. 单元测试补全

【每步验证】
- Python: ruff check + pytest
- 前端: npm run lint + build
- 功能: 核心流程测试

【开始执行】请按顺序完成所有任务，每完成一个任务提交代码后再继续下一个。
```