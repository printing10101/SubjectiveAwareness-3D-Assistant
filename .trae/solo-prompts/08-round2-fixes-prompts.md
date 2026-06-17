# 第二轮修复提示词集合（深度扫描）

本文档包含第二轮深度扫描发现的 43 个优化问题的修复提示词，按优先级和领域分组。
每个提示词均包含：问题描述、具体代码位置、修复方案、检验方法。

---

## 提示词 1：P0 安全 — is_active 检查缺失 + 解密失败返回密文

**优先级**：🔴 P0 严重
**涉及文件**：`backend/app/utils/auth.py`、`backend/app/utils/encryption.py`

**提示词内容**：

```
你是安全工程师，精通 Python Web 应用安全。

【任务】
修复两个 P0 级安全漏洞。

【问题 1：get_current_user 数据库查询路径未检查 is_active】

文件：backend/app/utils/auth.py

当前代码（约第 522-530 行）：
```python
async with get_async_db_session() as db:
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    await cache_user(username, user)
    return user  # <-- 缺少 is_active 检查！
```

缓存命中路径（第 514-520 行）有 is_active 检查，但数据库查询路径没有。
当缓存过期后，已禁用用户可通过旧 token 认证成功。

修复方案：在第 529 行 `return user` 之前增加 is_active 检查：
```python
async with get_async_db_session() as db:
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )
    await cache_user(username, user)
    return user
```

同时修复 get_optional_current_user（约第 576-583 行），同样缺少 is_active 检查：
```python
async with get_async_db_session() as db:
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if user is not None:
        if not user.is_active:
            return None
        await cache_user(username, user)
    return user
```

【问题 2：解密失败时返回原始密文】

文件：backend/app/utils/encryption.py，第 79-86 行：

```python
def process_result_value(self, value: Any, dialect: Any) -> Any:
    if value is not None:
        try:
            return cipher_suite.decrypt(value.encode()).decode()
        except (InvalidToken, ValueError, Exception):
            return value  # <-- 返回密文原文！
    return value
```

解密失败时返回原始密文，可能导致敏感数据以加密形式泄露给前端或日志。

修复方案：
1. 缩小异常捕获范围
2. 解密失败时记录错误日志并返回 None
```python
def process_result_value(self, value: Any, dialect: Any) -> Any:
    """将数据库中的密文解密为明文."""
    if value is not None:
        try:
            return cipher_suite.decrypt(value.encode()).decode()
        except InvalidToken:
            logger.error("解密失败: token 无效或密钥已更换")
            return None
        except Exception:
            logger.exception("解密过程中发生未预期错误")
            return None
    return value
```

注意：需要在文件顶部添加 `from loguru import logger`。

【问题 3：移除 ENCRYPTION_KEY_FALLBACK 硬编码值】

文件：backend/app/config.py，第 67 行：
```python
ENCRYPTION_KEY_FALLBACK: str = "legal-judgment-analysis-encryption-v1"
```
删除此字段。如果代码中有引用它的地方，一并删除引用。

【检验方法】

1. 语法检查：
   ```bash
   cd backend
   python -m py_compile app/utils/auth.py
   python -m py_compile app/utils/encryption.py
   python -m py_compile app/config.py
   ```

2. 搜索 ENCRYPTION_KEY_FALLBACK 的所有引用，确认已全部清理：
   ```bash
   grep -rn "ENCRYPTION_KEY_FALLBACK" backend/app/
   ```
   预期结果：无匹配

3. 验证 is_active 检查逻辑：
   ```bash
   grep -n "is_active" backend/app/utils/auth.py
   ```
   预期结果：至少在 get_current_user 和 get_optional_current_user 两个函数的数据库查询路径中都出现

4. 验证解密失败不再返回密文：
   ```bash
   grep -n "return value" backend/app/utils/encryption.py
   ```
   预期结果：process_result_value 中的 except 块不再有 `return value`

5. 运行相关测试：
   ```bash
   pytest tests/test_auth.py tests/test_encryption.py -v
   ```
   预期结果：所有测试通过
```

---

## 提示词 2：P0 安全 — 登录暴力破解防护

**优先级**：🔴 P0 严重
**涉及文件**：`backend/app/utils/auth.py`、`backend/app/models/user.py`、`backend/app/schemas/user.py`

**提示词内容**：

```
你是安全工程师，精通认证系统设计。

【任务】
为登录端点实现暴力破解防护机制。

【当前问题】
文件：backend/app/utils/auth.py，约第 591-635 行的 login 端点
仅依赖 slowapi 的 RATE_LIMIT_AUTH = "20/minute" 限流，没有：
- 登录失败计数和账户锁定
- 验证码集成
- 登录失败告警

攻击者可以在 20 次/分钟的限额内持续尝试不同密码。

【修复方案】

步骤 1：扩展 User 模型，添加安全字段

文件：backend/app/models/user.py

在 User 模型中添加以下字段：
```python
login_failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

步骤 2：在 login 端点中实现账户锁定检查

文件：backend/app/utils/auth.py，修改 login 函数（约第 591 行开始）

在验证密码之前，先检查账户是否被锁定：
```python
@auth_router.post("/login", response_model=TokenPair)
@limiter.limit(AnalysisConfig.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = form_dep,
) -> TokenPair:
    """用户登录端点."""
    async with get_async_db_session() as db:
        result = await db.execute(
            select(User).where(User.username == form_data.username)
        )
        user = result.scalar_one_or_none()

        # 检查账户是否被锁定
        if user and user.locked_until and user.locked_until > datetime.now(UTC):
            remaining_seconds = int(
                (user.locked_until - datetime.now(UTC)).total_seconds()
            )
            logger.warning(
                "登录被拒绝: 账户已锁定, username={}, remaining={}s",
                user.username, remaining_seconds,
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"账户已锁定，请 {remaining_seconds} 秒后重试",
            )

        if (
            not user
            or not verify_password(form_data.password, user.hashed_password)
        ):
            # 登录失败，增加计数
            if user:
                user.login_failed_count = (user.login_failed_count or 0) + 1
                # 连续失败 5 次，锁定 15 分钟
                if user.login_failed_count >= 5:
                    user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
                    logger.warning(
                        "账户已锁定: username={}, failed_count={}",
                        user.username, user.login_failed_count,
                    )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用",
            )

        # 登录成功，重置计数
        user.login_failed_count = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)

        # ... 后续 token 生成逻辑保持不变 ...
```

注意：需要在文件顶部添加 `from datetime import UTC, datetime, timedelta`（timedelta 可能需要新增导入）。

步骤 3：提高密码复杂度要求

文件：backend/app/schemas/user.py，第 35 行

将密码最小长度从 6 提高到 10，并添加复杂度验证器：
```python
password: str = Field(..., min_length=10, max_length=128)

@field_validator("password")
@classmethod
def validate_password(cls, v: str) -> str:
    """验证密码复杂度.

    要求至少包含以下三类中的两类：大写字母、小写字母、数字、特殊字符。
    """
    if len(v) < 10:
        msg = "密码长度至少为 10 个字符"
        raise ValueError(msg)
    categories = 0
    if re.search(r"[a-z]", v):
        categories += 1
    if re.search(r"[A-Z]", v):
        categories += 1
    if re.search(r"\d", v):
        categories += 1
    if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
        categories += 1
    if categories < 2:
        msg = "密码必须包含大写字母、小写字母、数字、特殊字符中的至少两类"
        raise ValueError(msg)
    return v
```

同样修改 UserUpdate 中的 password 验证（第 68 行），保持一致。

步骤 4：为 /refresh 端点添加独立限流

在 login 函数的 @limiter.limit 装饰器之后，找到 refresh 端点（搜索 "refresh"），为其添加更严格的限流：
```python
@auth_router.post("/refresh")
@limiter.limit("5/minute")  # 独立限流，比 login 更严格
async def refresh_token(...):
```

【检验方法】

1. 语法检查：
   ```bash
   cd backend
   python -m py_compile app/utils/auth.py
   python -m py_compile app/models/user.py
   python -m py_compile app/schemas/user.py
   ```

2. 验证 User 模型新增字段：
   ```bash
   grep -n "login_failed_count\|locked_until\|last_login_at" backend/app/models/user.py
   ```
   预期结果：三个字段都存在

3. 验证密码复杂度验证器：
   ```bash
   grep -n "validate_password\|categories" backend/app/schemas/user.py
   ```
   预期结果：UserCreate 和 UserUpdate 中都有密码验证

4. 验证 refresh 端点限流：
   ```bash
   grep -n "5/minute" backend/app/utils/auth.py
   ```
   预期结果：refresh 端点有独立的 5/minute 限流

5. 运行测试：
   ```bash
   pytest tests/test_auth.py -v
   ```
   预期结果：所有测试通过（可能需要更新测试中的 mock 以适配新字段）

6. 手动测试密码验证：
   ```python
   from app.schemas.user import UserCreate
   # 弱密码应被拒绝
   try:
       UserCreate(username="testuser", password="123456")
       print("FAIL: 弱密码被接受")
   except ValueError:
       print("PASS: 弱密码被拒绝")
   # 强密码应通过
   try:
       UserCreate(username="testuser", password="SecurePass123")
       print("PASS: 强密码被接受")
   except ValueError:
       print("FAIL: 强密码被拒绝")
   ```
```

---

## 提示词 3：P0 数据完整性 — Schema 与 Model 枚举不一致

**优先级**：🔴 P0 严重
**涉及文件**：`backend/app/schemas/knowledge.py`、`backend/app/models/knowledge_entry.py`、`backend/app/models/entry_relation.py`

**提示词内容**：

```
你是 Python 后端架构师，精通 SQLAlchemy + Pydantic 数据建模。

【任务】
修复 Schema 层与 Model 层枚举定义完全不一致的严重问题。

【问题描述】

知识库相关的枚举在三个地方分别定义，且值不一致：

1. 分类枚举：
   - Model (knowledge_entry.py): EntryCategory = {law, methodology, case, other}
   - Schema (knowledge.py): CategoryEnum = {faq, document, tutorial}
   → 完全不同！API 接收的值无法存入数据库

2. 状态枚举：
   - Model (knowledge_entry.py): EntryStatus = {draft, active, stale, archived}
   - Schema (knowledge.py): StatusEnum = {draft, published, archived}
   → 不同！Schema 缺少 stale，多了 published

3. 关系类型枚举：
   - Model (entry_relation.py): RelationType = {references, contradicts, supersedes, extends, depends_on}
   - Schema (knowledge.py): RelationTypeEnum = {references, similar_to, parent_of, child_of}
   → 完全不同！

【修复方案】

核心原则：Schema 应直接引用 Model 中的枚举，而不是重新定义。

步骤 1：修改 backend/app/schemas/knowledge.py

删除文件中独立定义的 CategoryEnum、StatusEnum、RelationTypeEnum 三个枚举类（约第 31-66 行）。

替换为从 Model 导入：
```python
from app.models.knowledge_entry import EntryCategory, EntryStatus, SourceType
from app.models.entry_relation import RelationType
```

然后将所有引用 CategoryEnum 的地方改为 EntryCategory，
StatusEnum 改为 EntryStatus，
RelationTypeEnum 改为 RelationType。

具体修改点（需要逐一搜索替换）：
- KnowledgeEntryCreate 中的 category 字段类型：CategoryEnum → EntryCategory
- KnowledgeEntryUpdate 中的 category/status 字段类型
- KnowledgeEntryResponse 中的 category/status/source_type 字段类型
- EntryRelationCreate 中的 relation_type 字段类型：RelationTypeEnum → RelationType
- 所有 field_validator 中引用这些枚举的地方

步骤 2：修改 KnowledgeEntryResponse 中的枚举类型

将 `category: str`、`status: str`、`source_type: str` 改为使用枚举类型：
```python
class KnowledgeEntryResponse(BaseModel):
    category: EntryCategory
    status: EntryStatus
    source_type: SourceType | str = "manual"
```

Pydantic v2 会自动将枚举序列化为其值字符串。

步骤 3：检查并修复 validate_source_type 验证器

如果 Schema 中有自定义的 source_type 验证器允许值 {manual, scraped, imported}，
需要修改为与 Model 的 SourceType {manual, document_import, case_conversion} 一致。

步骤 4：检查路由层和服务层是否有硬编码的枚举值

搜索以下硬编码值并替换为正确的枚举值：
```bash
grep -rn "faq\|document\|tutorial\|published\|similar_to\|parent_of\|child_of\|scraped\|imported" backend/app/ --include="*.py"
```

排除注释和文档字符串中的引用，只修改代码逻辑中的值。

【检验方法】

1. 语法检查：
   ```bash
   cd backend
   python -m py_compile app/schemas/knowledge.py
   ```

2. 验证 Schema 中不再有独立定义的枚举：
   ```bash
   grep -n "class CategoryEnum\|class StatusEnum\|class RelationTypeEnum" backend/app/schemas/knowledge.py
   ```
   预期结果：无匹配

3. 验证 Schema 正确引用了 Model 枚举：
   ```bash
   grep -n "EntryCategory\|EntryStatus\|SourceType\|RelationType" backend/app/schemas/knowledge.py
   ```
   预期结果：从 app.models 导入并使用

4. 搜索代码中残留的错误枚举值：
   ```bash
   grep -rn '"faq"\|"published"\|"similar_to"\|"parent_of"\|"child_of"\|"scraped"' backend/app/ --include="*.py"
   ```
   预期结果：仅在注释中出现，代码逻辑中无引用

5. 运行知识库相关测试：
   ```bash
   pytest tests/test_knowledge*.py -v
   ```

6. 验证 API Schema 文档：
   启动应用后访问 http://localhost:8000/docs，检查知识库相关接口的 schema 枚举值是否与数据库一致。
```

---

## 提示词 4：P0 数据完整性 — Alembic 迁移遗漏模型

**优先级**：🔴 P0 严重
**涉及文件**：`backend/alembic/env.py`

**提示词内容**：

```
你是数据库工程师，精通 Alembic 迁移工具。

【任务】
修复 Alembic 迁移配置中遗漏知识库模型导入的问题。

【问题描述】

文件：backend/alembic/env.py，第 19-28 行

当前导入列表：
```python
from app.models import (  # noqa: E402, F401
    Analysis,
    Case,
    LegalRule,
    ModelVersion,
    RefreshToken,
    SystemLog,
    TokenBlacklist,
    User,
)
```

缺少以下模型：
- KnowledgeEntry
- KnowledgeTag
- EntryTag
- EntryRelation

这意味着对知识库相关表的 schema 变更不会被 Alembic 自动检测到，生成的迁移脚本将缺少这些表的变更。

【修复方案】

方案 A（推荐）：直接导入整个 models 包，触发所有模型注册
```python
from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401 -- 触发所有模型注册到 Base.metadata
```

方案 B：显式添加遗漏的模型
```python
from app.models import (  # noqa: E402, F401
    Analysis,
    Case,
    EntryRelation,
    EntryTag,
    KnowledgeEntry,
    KnowledgeTag,
    LegalRule,
    ModelVersion,
    RefreshToken,
    SystemLog,
    TokenBlacklist,
    User,
)
```

推荐方案 A，因为它自动包含未来新增的模型，不会再次遗漏。

【检验方法】

1. 语法检查：
   ```bash
   cd backend
   python -m py_compile alembic/env.py
   ```

2. 验证所有模型都被注册到 Base.metadata：
   ```bash
   python -c "
   import sys; sys.path.insert(0, '.')
   from app.database import Base
   import app.models
   tables = sorted(Base.metadata.tables.keys())
   print('已注册的表:', tables)
   expected = ['knowledge_entries', 'knowledge_tags', 'entry_tags', 'entry_relations']
   for t in expected:
       print(f'  {t}: {\"✓\" if t in tables else \"✗ 缺失\"}')" 
   ```
   预期结果：所有 4 个知识库表都显示 ✓

3. 验证 Alembic 能检测到所有表：
   ```bash
   alembic check
   ```
   预期结果：无错误（需要先配置好数据库连接）

4. 生成空迁移验证：
   ```bash
   alembic revision --autogenerate -m "verify_all_tables_detected"
   ```
   检查生成的迁移脚本是否为空（或仅包含检测到的真实变更）
```

---

## 提示词 5：P0 性能 — reports.py 全量加载无分页

**优先级**：🔴 P0 严重
**涉及文件**：`backend/app/routers/reports.py`

**提示词内容**：

```
你是 Python 后端工程师，精通 FastAPI 性能优化。

【任务】
修复 reports.py 中全量加载分析记录导致内存溢出的问题，同时将业务逻辑下沉到 service 层。

【问题描述】

文件：backend/app/routers/reports.py

当前代码直接在路由层执行 `select(Analysis)` 加载全部数据，无分页：
```python
@router.get("/")
async def list_reports() -> ReportList:
    async with get_async_db_session() as db:
        result = await db.execute(select(Analysis))
        analyses: list[Analysis] = list(result.scalars().all())
        return {
            "total": len(analyses),
            "analyses": [_format_analysis(a) for a in analyses],
        }
```

【修复方案】

步骤 1：创建 backend/app/services/report_service.py

```python
"""报告服务模块.

提供分析报告的查询和格式化功能。
"""

from math import ceil

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.types.analysis import AnalysisReport


async def list_reports(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询分析报告列表.

    Args:
        db: 异步数据库会话
        page: 页码（从 1 开始）
        page_size: 每页条数

    Returns:
        dict: 包含 total、page、page_size、total_pages、reports 的字典
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    # 查询总数
    count_result = await db.execute(select(func.count(Analysis.id)))
    total: int = count_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Analysis)
        .order_by(Analysis.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    analyses = list(result.scalars().all())

    reports = [_format_analysis(a) for a in analyses]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)) if total > 0 else 0,
        "reports": reports,
    }


def _format_analysis(a: Analysis) -> AnalysisReport:
    """格式化单条分析记录.

    Args:
        a: 分析记录实例

    Returns:
        AnalysisReport: 格式化后的字典
    """
    return {
        "id": a.id if a.id is not None else 0,
        "case_id": int(a.case_id) if a.case_id is not None else None,
        "knowledge_score": (
            float(a.knowledge_score) if a.knowledge_score is not None else None
        ),
        "mode": str(a.mode),
        "result": str(a.result_json),
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
```

步骤 2：修改 backend/app/routers/reports.py

```python
"""报告路由模块.

提供分析报告列表查询的 API 端点。
"""

from fastapi import APIRouter, Query

from app.database import get_async_db_session
from app.services.report_service import list_reports


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/")
async def get_reports(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
) -> dict:
    """分页获取分析报告列表.

    Args:
        page: 页码（从 1 开始，默认 1）
        page_size: 每页条数（默认 20，最大 100）

    Returns:
        dict: 包含 total、page、page_size、total_pages、reports
    """
    async with get_async_db_session() as db:
        return await list_reports(db, page=page, page_size=page_size)
```

【检验方法】

1. 语法检查：
   ```bash
   cd backend
   python -m py_compile app/services/report_service.py
   python -m py_compile app/routers/reports.py
   ```

2. 验证路由不再直接导入 SQLAlchemy 模型：
   ```bash
   grep -n "from sqlalchemy\|from app.models" backend/app/routers/reports.py
   ```
   预期结果：无匹配（业务逻辑已下沉到 service 层）

3. 验证分页参数：
   ```bash
   grep -n "page\|page_size\|offset\|limit" backend/app/services/report_service.py
   ```
   预期结果：有 offset/limit 分页查询逻辑

4. 运行测试：
   ```bash
   pytest tests/ -v -k "report"
   ```

5. API 测试（启动应用后）：
   ```bash
   # 无分页参数，默认第一页
   curl http://localhost:8000/api/reports/
   # 指定分页
   curl "http://localhost:8000/api/reports/?page=2&page_size=5"
   ```
   预期结果：返回包含 total、page、page_size、total_pages、reports 的 JSON
```

---

## 提示词 6：P1 数据库 — 外键级联删除 + 缺失索引 + ORM relationship

**优先级**：🟠 P1 高
**涉及文件**：`backend/app/models/case.py`、`backend/app/models/knowledge_entry.py`、`backend/app/models/analysis.py`、`backend/app/models/legal_rule.py`、`backend/app/models/model_version.py`、`backend/app/models/system_log.py`

**提示词内容**：

```
你是数据库工程师，精通 SQLAlchemy ORM 模型设计。

【任务】
修复多个数据库模型中缺失的外键策略、索引和 ORM 关系。

【修复清单】

1. backend/app/models/case.py — Case.created_by 外键添加级联策略

找到 created_by 字段定义，修改为：
```python
created_by = Column(
    Integer,
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
)
```

2. backend/app/models/knowledge_entry.py — 外键级联策略

找到 created_by 和 verified_by 字段（约第 118-123 行），修改为：
```python
created_by: Mapped[int] = mapped_column(
    Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
)
verified_by: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
)
```
注意：created_by 使用 RESTRICT 是因为知识条目必须有创建者，不允许删除有知识条目的用户。
如果业务上允许，也可以改为 SET NULL（需同时将 nullable 改为 True）。

3. backend/app/models/analysis.py — 添加 ORM relationship

在 Analysis 模型中添加与 Case 的关系：
```python
from sqlalchemy.orm import relationship

# 在类定义内添加：
case: Mapped["Case"] = relationship("Case", backref="analyses")
```
注意：需要处理循环导入。使用字符串引用 "Case" 即可，SQLAlchemy 会在运行时解析。

4. backend/app/models/legal_rule.py — 添加缺失索引

在 LegalRule 类中添加 __table_args__：
```python
from sqlalchemy import Index, UniqueConstraint

__table_args__ = (
    Index("ix_lr_model_version", "model_name", "version", unique=True),
    Index("ix_lr_source_law", "source_law"),
    Index("ix_lr_created_at", "created_at"),
)
```

5. backend/app/models/model_version.py — 添加联合唯一约束和索引

在 ModelVersion 类中添加 __table_args__：
```python
from sqlalchemy import UniqueConstraint

__table_args__ = (
    UniqueConstraint("model_name", "version", name="uq_mv_name_version"),
    Index("ix_mv_created_at", "created_at"),
)
```

6. backend/app/models/system_log.py — 添加查询索引

在 SystemLog 类中添加 __table_args__（或修改现有的）：
```python
Index("ix_system_logs_username", "username"),
Index("ix_system_logs_action", "action"),
```

7. backend/app/models/user.py — is_active 添加 nullable=False

找到 is_active 字段，确保有 nullable=False：
```python
is_active = Column(Boolean, default=True, nullable=False)
```

【检验方法】

1. 语法检查所有修改的模型文件：
   ```bash
   cd backend
   python -m py_compile app/models/case.py
   python -m py_compile app/models/knowledge_entry.py
   python -m py_compile app/models/analysis.py
   python -m py_compile app/models/legal_rule.py
   python -m py_compile app/models/model_version.py
   python -m py_compile app/models/system_log.py
   python -m py_compile app/models/user.py
   ```

2. 验证外键策略：
   ```bash
   grep -n "ondelete" backend/app/models/case.py backend/app/models/knowledge_entry.py
   ```
   预期结果：所有外键都有 ondelete 策略

3. 验证新增索引：
   ```bash
   grep -n "Index\|UniqueConstraint" backend/app/models/legal_rule.py backend/app/models/model_version.py backend/app/models/system_log.py
   ```
   预期结果：每个文件都有索引定义

4. 验证 Analysis relationship：
   ```bash
   grep -n "relationship" backend/app/models/analysis.py
   ```
   预期结果：有 case relationship 定义

5. 运行数据库相关测试：
   ```bash
   pytest tests/test_database.py tests/test_cases.py -v
   ```

6. 生成 Alembic 迁移验证：
   ```bash
   alembic revision --autogenerate -m "add_indexes_and_cascades"
   ```
   检查生成的迁移脚本是否包含预期的 ALTER TABLE 语句
```

---

## 提示词 7：P1 架构 — 事务双重提交 + Ollama 双重重试 + 监控指标

**优先级**：🟠 P1 高
**涉及文件**：`backend/app/database.py`、`backend/app/services/case_service.py`、`backend/app/services/ollama_client.py`、`backend/app/utils/monitoring.py`

**提示词内容**：

```
你是 Python 后端架构师，精通 FastAPI + SQLAlchemy 事务管理和系统可观测性。

【任务】
修复三个架构层面的问题：事务双重提交、Ollama 双重重试、监控指标不足。

【问题 1：事务双重提交】

当前 get_async_db_session() 上下文管理器退出时自动 commit，
但 case_service.py、knowledge_service.py 等服务层也手动调用 db.commit()，
导致双重提交。

修复方案：统一事务管理策略。

选择策略 B（推荐）：上下文管理器负责 commit，service 层只做 flush。

修改 backend/app/database.py 中的 get_async_db_session()：
保持不变（它已经自动 commit）。

修改以下 service 文件，将所有 `await db.commit()` 替换为 `await db.flush()`，
删除所有 `await db.rollback()`（由上下文管理器统一处理）：

- backend/app/services/case_service.py
  搜索 `await db.commit()` 和 `await db.rollback()`，替换为 flush

- backend/app/services/knowledge_service.py
  同上

- backend/app/services/knowledge_graph.py（如果存在手动 commit）
  同上

注意：analysis_service.py 已经正确使用了 flush 策略（见其文档注释），可以作为参考。

【问题 2：Ollama 双重重试】

文件：backend/app/services/ollama_client.py

generate() 内部有手动 for 循环重试（约第 102-135 行），
call_ollama_with_retry() 使用 tenacity 装饰器（约第 403-449 行）。
如果调用链为 call_ollama_with_retry → call_ollama → client.generate，
总重试次数为 N×M，远超预期。

修复方案：移除 generate() 内部的手动重试循环。

将 generate() 方法简化为单次调用：
```python
async def generate(self, prompt: str, system_prompt: str = "") -> str:
    """调用 Ollama 生成文本（单次调用，不内部重试）.

    重试由外层 call_ollama_with_retry 统一管理。
    """
    payload = {"prompt": prompt, "model": settings.OLLAMA_MODEL}
    if system_prompt:
        payload["system"] = system_prompt

    try:
        response = await self._client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=settings.OLLAMA_TIMEOUT_BASE,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
    except Exception as e:
        logger.error(f"Ollama 生成失败: {e}")
        raise
```

同时更新 call_ollama_with_retry 的 tenacity 配置，确保重试参数合理：
```python
@retry(
    stop=stop_after_attempt(AnalysisConfig.RETRY_MAX_ATTEMPTS),
    wait=wait_exponential(
        multiplier=AnalysisConfig.RETRY_WAIT_MULTIPLIER,
        min=AnalysisConfig.RETRY_WAIT_MIN,
        max=AnalysisConfig.RETRY_WAIT_MAX,
    ),
    retry=(httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout),
)
```

【问题 3：监控指标严重不足】

文件：backend/app/utils/monitoring.py

当前仅有 analysis_total 和 analysis_duration_seconds 两个指标。

添加以下关键指标：
```python
"""Prometheus 监控指标模块.

定义系统各关键路径的监控指标。
"""

from prometheus_client import Counter, Histogram


# ---- 分析操作 ----
ANALYSIS_COUNTER = Counter(
    "analysis_total",
    "Total number of analysis operations performed",
    ["mode", "status"],
)
ANALYSIS_DURATION = Histogram(
    "analysis_duration_seconds",
    "Duration of analysis operations in seconds",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)

# ---- HTTP 请求 ----
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)

# ---- LLM 调用 ----
LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total LLM (Ollama) requests",
    ["model", "status"],
)
LLM_REQUEST_DURATION = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["model"],
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60, 120],
)

# ---- 缓存 ----
CACHE_OPERATIONS_TOTAL = Counter(
    "cache_operations_total",
    "Cache operations",
    ["backend", "operation"],  # operation: hit/miss/error
)

# ---- 认证 ----
AUTH_OPERATIONS_TOTAL = Counter(
    "auth_operations_total",
    "Authentication operations",
    ["operation", "status"],  # operation: login/refresh/logout, status: success/failure
)
```

然后在 main.py 的 request_context_middleware 中接入 HTTP 指标：
```python
from app.utils.monitoring import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION

# 在 middleware 中添加：
HTTP_REQUESTS_TOTAL.labels(
    method=request.method,
    endpoint=request.url.path,
    status_code=str(response.status_code),
).inc()
HTTP_REQUEST_DURATION.labels(
    method=request.method,
    endpoint=request.url.path,
).observe(response_time / 1000)
```

【检验方法】

1. 语法检查：
   ```bash
   cd backend
   python -m py_compile app/database.py
   python -m py_compile app/services/ollama_client.py
   python -m py_compile app/utils/monitoring.py
   python -m py_compile app/main.py
   ```

2. 验证 service 层不再手动 commit：
   ```bash
   grep -rn "await db.commit()" backend/app/services/case_service.py backend/app/services/knowledge_service.py
   ```
   预期结果：无匹配（或仅在注释中）

3. 验证 Ollama generate 不再有内部重试：
   ```bash
   grep -n "for attempt\|OLLAMA_RETRY_MAX_ATTEMPTS" backend/app/services/ollama_client.py
   ```
   预期结果：generate() 方法内无重试循环

4. 验证监控指标：
   ```bash
   grep -c "Counter\|Histogram" backend/app/utils/monitoring.py
   ```
   预期结果：至少 10 个（原有 2 个 + 新增 8 个）

5. 验证 /metrics 端点：
   启动应用后：
   ```bash
   curl http://localhost:8000/metrics | grep -E "^(http_|llm_|cache_|auth_)"
   ```
   预期结果：显示新增的监控指标

6. 运行测试：
   ```bash
   pytest tests/test_ollama_client.py tests/test_database.py -v
   ```
```

---

## 提示词 8：P2 — N+1 查询 + 分页统一 + 日志优化 + CI 安全扫描

**优先级**：🟡 P2 中
**涉及文件**：多个 service 文件、`backend/app/utils/logger.py`、`.github/workflows/ci.yml`

**提示词内容**：

```
你是 Python 后端工程师，精通性能优化和 DevOps。

【任务】
修复 4 个 P2 级问题。

【问题 1：knowledge_graph_service.py N+1 查询】

文件：backend/app/services/knowledge_graph_service.py

1a. get_node_neighbors（约第 280-287 行）BFS 循环中逐节点查关系。

修复：批量查询当前层所有节点的关系：
```python
# 将逐节点查询替换为批量查询
if current_layer:
    batch_result = await db.execute(
        select(EntryRelation).where(
            (EntryRelation.source_entry_id.in_(current_layer))
            | (EntryRelation.target_entry_id.in_(current_layer))
        )
    )
    all_relations = list(batch_result.scalars().all())
```

1b. get_shortest_path（约第 372-375 行）全表加载所有关系。

修复：添加最大搜索深度限制，避免全表加载：
```python
# 限制最大搜索深度
MAX_SEARCH_DEPTH = 5

async def get_shortest_path(db, start_id, end_id, max_depth=MAX_SEARCH_DEPTH):
    if start_id == end_id:
        return [start_id]
    
    # 只查询与起始节点直接或间接相关的子图，而非全表
    visited = {start_id}
    queue = [(start_id, [start_id])]
    
    while queue:
        current, path = queue.pop(0)
        if len(path) > max_depth:
            continue
        # 只查询当前节点的直接关系
        relations = await db.execute(
            select(EntryRelation).where(
                (EntryRelation.source_entry_id == current)
                | (EntryRelation.target_entry_id == current)
            )
        )
        for rel in relations.scalars().all():
            neighbor = (
                rel.target_entry_id if rel.source_entry_id == current
                else rel.source_entry_id
            )
            if neighbor == end_id:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return []
```

【问题 2：分页工具函数重复】

backend/app/services/case_service.py 和 knowledge_service.py 中有几乎相同的
_validate_pagination_params 和 _build_sort_column 函数。

修复：创建 backend/app/utils/pagination.py，提取通用分页工具：
```python
"""通用分页工具模块."""

from math import ceil

from sqlalchemy import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select


async def paginate(
    db: AsyncSession,
    query,
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100,
) -> dict:
    """通用分页查询.

    Args:
        db: 数据库会话
        query: 基础查询（不含 offset/limit）
        page: 页码
        page_size: 每页条数
        max_page_size: 最大每页条数

    Returns:
        dict: {total, page, page_size, total_pages, items}
    """
    page = max(1, page)
    page_size = min(max(1, page_size), max_page_size)

    # 查询总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    items = list((await db.execute(
        query.offset(offset).limit(page_size)
    )).scalars().all())

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)) if total > 0 else 0,
        "items": items,
    }


def validate_pagination_params(page: int, page_size: int) -> tuple[int, int]:
    """验证并规范化分页参数."""
    return max(1, page), min(max(1, page_size), 100)
```

然后在 case_service.py 和 knowledge_service.py 中导入使用，删除重复代码。

【问题 3：日志缺少压缩和错误级别分离】

文件：backend/app/utils/logger.py

3a. 添加日志压缩：
找到 `compression=None`，改为 `compression="gz"`

3b. 添加错误级别单独的日志文件：
在 setup_logging 函数中，在 JSON sink 配置之后添加：
```python
# 错误级别单独日志文件
error_log_path = os.path.join(log_dir, "error_{time:YYYY-MM-DD}.json")
logger.add(
    sink=error_log_path,
    format="{message}",
    level="ERROR",
    serialize=True,
    rotation=json_rotation,
    retention=json_retention,
    compression="gz",
    filter=request_id_filter,
)
```

【问题 4：CI 添加安全扫描】

文件：.github/workflows/ci.yml

在 pytest 步骤之后添加：
```yaml
- name: Security scan (bandit)
  run: |
    pip install bandit
    bandit -r backend/app/ -x backend/tests/ -ll

- name: Dependency vulnerability check
  run: |
    pip install pip-audit
    pip-audit --requirement backend/requirements.txt
```

同时升级 actions 版本：
```yaml
- uses: actions/checkout@v4   # 从 v3 升级
- uses: actions/setup-python@v5  # 从 v4 升级
```

【检验方法】

1. 语法检查：
   ```bash
   cd backend
   python -m py_compile app/services/knowledge_graph_service.py
   python -m py_compile app/utils/pagination.py
   python -m py_compile app/utils/logger.py
   ```

2. 验证 N+1 修复：
   ```bash
   grep -n "\.in_(current_layer)" backend/app/services/knowledge_graph_service.py
   ```
   预期结果：有批量查询逻辑

3. 验证分页工具提取：
   ```bash
   ls backend/app/utils/pagination.py
   grep -n "from app.utils.pagination import" backend/app/services/case_service.py backend/app/services/knowledge_service.py
   ```
   预期结果：文件存在且被引用

4. 验证日志压缩：
   ```bash
   grep -n 'compression="gz"' backend/app/utils/logger.py
   ```
   预期结果：至少出现 2 次（主日志 + 错误日志）

5. 验证 CI 配置：
   ```bash
   grep -n "bandit\|pip-audit\|checkout@v4\|setup-python@v5" .github/workflows/ci.yml
   ```
   预期结果：都有匹配

6. 运行测试：
   ```bash
   pytest tests/test_knowledge_graph.py tests/test_database.py -v
   ```
```

---

## 提示词 9：P2 — 内存黑名单 TTL 清理 + 加密密钥派生 + PDF 资源泄露

**优先级**：🟡 P2 中
**涉及文件**：`backend/app/utils/auth.py`、`backend/app/utils/encryption.py`、`backend/app/services/document_processor.py`

**提示词内容**：

```
你是 Python 后端工程师。

【任务】
修复 3 个 P2 级问题。

【问题 1：内存黑名单无 TTL 过期清理】

文件：backend/app/utils/auth.py

_TokenBlacklistSet 类（约第 94-126 行）只是一个简单的 set，
没有过期清理逻辑，已过期的 token JTI 永久积累在内存中。

修复方案：添加基于时间的过期清理。

```python
import time
from dataclasses import dataclass, field

@dataclass
class _TokenBlacklistSet:
    """内存令牌黑名单集合，支持自动过期清理."""

    _set: set[str] = field(default_factory=set)
    _expires: dict[str, float] = field(default_factory=dict)
    _max_size: int = 10000
    _last_cleanup: float = field(default_factory=time.time)

    def add(self, jti: str, expires_at: float | None = None) -> None:
        """添加 JTI 到黑名单."""
        self._set.add(jti)
        if expires_at is not None:
            self._expires[jti] = expires_at
        self._maybe_cleanup()

    def __contains__(self, jti: str) -> bool:
        """检查 JTI 是否在黑名单中（自动清除过期条目）."""
        if jti in self._expires:
            if time.time() > self._expires[jti]:
                self._set.discard(jti)
                del self._expires[jti]
                return False
        return jti in self._set

    def _maybe_cleanup(self) -> None:
        """定期清理过期条目."""
        now = time.time()
        if now - self._last_cleanup < 300:  # 每 5 分钟清理一次
            return
        self._last_cleanup = now
        expired = [
            jti for jti, exp in self._expires.items()
            if now > exp
        ]
        for jti in expired:
            self._set.discard(jti)
            del self._expires[jti]
```

同时修改 add_to_blacklist 函数，传入 expires_at：
```python
async def add_to_blacklist(jti: str, expires_at: datetime | None = None) -> None:
    """将 JTI 添加到内存和数据库黑名单."""
    _blacklist.add(jti, expires_at.timestamp() if expires_at else None)
    # ... 数据库写入逻辑保持不变 ...
```

【问题 2：加密密钥派生缺少盐值和迭代】

文件：backend/app/utils/encryption.py，_get_cipher 函数（第 40-42 行）

当前直接 SHA-256 哈希密钥，没有盐值和迭代。

修复方案：使用 PBKDF2 进行密钥派生：
```python
import base64
import hashlib
import os
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# 固定盐值（存在代码中是可接受的，因为 Fernet 本身使用随机 nonce）
_KDF_SALT = b"legal-analysis-kdf-salt-v1"
_KDF_ITERATIONS = 480000  # OWASP 推荐最小值


def _derive_key(encryption_key: str) -> bytes:
    """使用 PBKDF2-HMAC-SHA256 从密码派生 Fernet 兼容密钥."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_KDF_SALT,
        iterations=_KDF_ITERATIONS,
    )
    key_bytes = kdf.derive(encryption_key.encode())
    return base64.urlsafe_b64encode(key_bytes)


def _get_cipher() -> Fernet:
    """获取 Fernet 加密套件实例."""
    encryption_key = getattr(settings, "ENCRYPTION_KEY", None)

    if encryption_key:
        try:
            # 先尝试直接作为 Fernet key（兼容已有加密数据）
            return Fernet(
                encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
            )
        except (ValueError, TypeError):
            # 回退到 PBKDF2 派生
            return Fernet(_derive_key(encryption_key))

    derive_from = getattr(settings, "ENCRYPTION_KEY_DERIVE", None)
    if derive_from:
        return Fernet(_derive_key(derive_from))

    msg = "无法获取加密密钥：请配置 ENCRYPTION_KEY 环境变量"
    raise RuntimeError(msg)
```

注意：保留直接 Fernet 解密的兼容路径，确保已加密的旧数据仍可解密。

【问题 3：PDF 文档对象未安全关闭】

文件：backend/app/services/document_processor.py（约第 92-96 行）

修复方案：使用 try/finally 确保文档对象被关闭：
```python
doc = fitz.open(stream=content, filetype="pdf")
try:
    text: str = ""
    for page in doc:
        text += page.get_text()
finally:
    doc.close()
```

【检验方法】

1. 语法检查：
   ```bash
   cd backend
   python -m py_compile app/utils/auth.py
   python -m py_compile app/utils/encryption.py
   python -m py_compile app/services/document_processor.py
   ```

2. 验证黑名单有过期清理：
   ```bash
   grep -n "_maybe_cleanup\|_expires\|expires_at" backend/app/utils/auth.py
   ```
   预期结果：_TokenBlacklistSet 中有相关逻辑

3. 验证 PBKDF2 派生：
   ```bash
   grep -n "PBKDF2\|_derive_key\|_KDF" backend/app/utils/encryption.py
   ```
   预期结果：有 PBKDF2 相关代码

4. 验证 PDF 安全关闭：
   ```bash
   grep -A2 "fitz.open" backend/app/services/document_processor.py
   ```
   预期结果：有 try/finally 包裹

5. 运行测试：
   ```bash
   pytest tests/test_auth.py tests/test_encryption.py tests/test_document_processor.py -v
   ```
```

---

## 提示词 10：P3 — 代码质量优化合集

**优先级**：🟢 P3 低
**涉及文件**：多个文件

**提示词内容**：

```
你是 Python 后端工程师。

【任务】
修复 10 个 P3 级代码质量问题。

【1. 错误信息中英文统一】

搜索所有英文错误信息，统一为中文：
```bash
grep -rn 'detail="' backend/app/ --include="*.py" | grep -v "中文"
```

需要修改的已知位置：
- backend/app/services/knowledge_graph.py 中 "Rule not found" → "法律规则不存在"
- backend/app/utils/auth.py 中 "Could not validate credentials" → "认证凭据无效"

【2. experiment.py 添加 Pydantic 请求体 schema】

文件：backend/app/routers/experiment.py

将 `experiment_data: dict[str, Any]` 替换为 Pydantic model：
```python
class ExperimentRequest(BaseModel):
    """实验请求模型."""
    experiment_type: str = Field(..., min_length=1, description="实验类型")
    params: dict[str, Any] = Field(default_factory=dict, description="实验参数")
```

然后在路由函数中使用：
```python
async def run_new_experiment(
    experiment_request: ExperimentRequest,
    ...
```

【3. admin_required lambda 改为 proper dependency】

文件：backend/app/routers/knowledge.py（约第 60-64 行）

将 lambda 替换为正式的依赖函数：
```python
async def admin_required(
    current_user: User | None = Depends(get_current_user),
) -> User:
    """管理员权限依赖."""
    if current_user is None or current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user
```

【4. PaginatedResponse 统一】

文件：backend/app/schemas/knowledge.py

删除 PaginatedKnowledgeResponse，统一使用 PaginatedResponse[KnowledgeEntryResponse]。

找到所有使用 PaginatedKnowledgeResponse 的地方，替换为 PaginatedResponse。

确保 total_pages 计算逻辑一致：使用 `max(1, ceil(...))` 而非 `max(0, ...)`。

【5. _resolve_category 改为同步函数】

文件：backend/app/services/knowledge_import_service.py

找到 `async def _resolve_category`，去掉 `async` 关键字（内部无 await）。

同时更新所有调用处，去掉 `await`。

【6. 响应 Schema 枚举类型恢复】

文件：backend/app/schemas/case.py
将 `status: str` 改为 `status: CaseStatus`

文件：backend/app/schemas/knowledge.py
将 `category: str` 改为 `category: EntryCategory`
将 `source_type: str` 改为 `source_type: SourceType`

（注意：此修复依赖于提示词 3 中枚举统一后的结果）

【7. pwd_context 传入 bcrypt rounds】

文件：backend/app/utils/auth.py（约第 35 行）

```python
from app.config import AnalysisConfig

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=AnalysisConfig.BCRYPT_ROUNDS,
)
```

【8. 用户名长度限制缩减】

文件：backend/app/models/user.py
将 `String(100)` 改为 `String(50)`

文件：backend/app/schemas/user.py
将 _USERNAME_PATTERN 和验证器中的 100 改为 50

【9. CI 添加 artifact 上传】

文件：.github/workflows/ci.yml

在 pytest 步骤之后添加：
```yaml
- name: Upload coverage report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: coverage-report
    path: coverage.xml
    retention-days: 7
```

【10. sanitize_json_string 多 JSON 对象处理改进】

文件：backend/app/utils/common.py

在 sanitize_json_string 函数的文档字符串中明确说明：
"当文本中包含多个 JSON 对象时，提取第一个 { 到最后一个 } 之间的内容，
可能包含中间的非 JSON 文本导致解析失败。此为已知行为，调用方应处理解析失败的情况。"

【检验方法】

1. 全局语法检查：
   ```bash
   cd backend
   python -m py_compile app/routers/experiment.py
   python -m py_compile app/routers/knowledge.py
   python -m py_compile app/schemas/case.py
   python -m py_compile app/schemas/knowledge.py
   python -m py_compile app/utils/auth.py
   python -m py_compile app/utils/common.py
   ```

2. 验证英文错误信息已清理：
   ```bash
   grep -rn 'detail="Rule not found\|detail="Could not validate' backend/app/ --include="*.py"
   ```
   预期结果：无匹配

3. 验证 experiment.py 使用 Pydantic schema：
   ```bash
   grep -n "ExperimentRequest\|dict\[str, Any\]" backend/app/routers/experiment.py
   ```
   预期结果：使用 ExperimentRequest，无 dict[str, Any]

4. 验证 admin_required 是正式函数：
   ```bash
   grep -n "async def admin_required" backend/app/routers/knowledge.py
   ```
   预期结果：有正式函数定义

5. 运行全量测试：
   ```bash
   pytest tests/ -v --tb=short
   ```
   预期结果：所有测试通过
```

---

## 综合检验清单

完成所有修复后，按顺序执行以下验证：

```bash
# ===== 第一阶段：语法和静态检查 =====
cd backend
python -m py_compile app/utils/auth.py
python -m py_compile app/utils/encryption.py
python -m py_compile app/utils/monitoring.py
python -m py_compile app/utils/logger.py
python -m py_compile app/utils/pagination.py
python -m py_compile app/utils/common.py
python -m py_compile app/config.py
python -m py_compile app/database.py
python -m py_compile app/models/user.py
python -m py_compile app/models/case.py
python -m py_compile app/models/analysis.py
python -m py_compile app/models/knowledge_entry.py
python -m py_compile app/models/legal_rule.py
python -m py_compile app/models/model_version.py
python -m py_compile app/models/system_log.py
python -m py_compile app/schemas/user.py
python -m py_compile app/schemas/knowledge.py
python -m py_compile app/schemas/case.py
python -m py_compile app/routers/reports.py
python -m py_compile app/routers/experiment.py
python -m py_compile app/routers/knowledge.py
python -m py_compile app/services/ollama_client.py
python -m py_compile app/services/document_processor.py
python -m py_compile app/services/knowledge_graph_service.py
python -m py_compile app/services/report_service.py
python -m py_compile alembic/env.py

# ===== 第二阶段：代码质量 =====
ruff check app/ --select ALL --ignore D
mypy app/ --ignore-missing-imports

# ===== 第三阶段：测试 =====
pytest tests/ -v --tb=short

# ===== 第四阶段：安全扫描 =====
pip install bandit
bandit -r app/ -x tests/ -ll

# ===== 第五阶段：Alembic 迁移验证 =====
alembic check
```

全部通过即表示第二轮修复完成。
