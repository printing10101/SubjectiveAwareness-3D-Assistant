# 项目优化提示词集合（第三轮）

本文档包含针对项目当前状态的优化提示词，每个提示词均包含分步骤的实施指令和对应的检验方法。

---

## 提示词 1：前端 API 层统一 — knowledgeStore 使用 apiClient

**优先级**：🔴 高
**问题**：`knowledgeStore.js` 直接使用 axios，绕过了统一的拦截器（Token自动刷新、错误处理）
**涉及文件**：`frontend/src/stores/knowledgeStore.js`

### 提示词

```
你是前端工程师，精通 Vue 3 + Pinia + Axios。

【任务】
将 knowledgeStore.js 中的直接 axios 调用替换为统一的 apiClient，
确保所有 API 请求都经过统一的请求/响应拦截器。

【当前问题】
文件：frontend/src/stores/knowledgeStore.js

第 3 行直接导入 axios：
```javascript
import axios from 'axios'
```

第 45、64、81、99、121、137 行直接使用 axios.get/post/put/delete：
```javascript
const response = await axios.get('/api/knowledge', { params: queryParams })
const response = await axios.get(`/api/knowledge/${id}`)
const response = await axios.post('/api/knowledge', data)
const response = await axios.put(`/api/knowledge/${id}`, data)
await axios.delete(`/api/knowledge/${id}`)
const response = await axios.get('/api/knowledge/tags')
```

这些调用绕过了 client.js 中配置的：
- Token 自动注入（请求拦截器）
- Token 过期自动刷新（响应拦截器 401 处理）
- 统一错误格式化（extractErrorMessage）

【步骤 1：修改导入语句】

将第 3 行的：
```javascript
import axios from 'axios'
```

替换为：
```javascript
import apiClient from '@/api/client'
```

注意：如果项目未配置 @ 路径别名，使用相对路径：
```javascript
import apiClient from '../api/client'
```

【步骤 2：替换所有 axios 调用】

将所有 `axios.get`、`axios.post`、`axios.put`、`axios.delete` 替换为 `apiClient.get`、`apiClient.post`、`apiClient.put`、`apiClient.delete`。

具体替换位置：
- 第 45 行：`axios.get('/api/knowledge', ...)` → `apiClient.get('/api/knowledge', ...)`
- 第 64 行：`axios.get(`/api/knowledge/${id}`)` → `apiClient.get(`/api/knowledge/${id}`)`
- 第 81 行：`axios.post('/api/knowledge', data)` → `apiClient.post('/api/knowledge', data)`
- 第 99 行：`axios.put(`/api/knowledge/${id}`, data)` → `apiClient.put(`/api/knowledge/${id}`, data)`
- 第 121 行：`axios.delete(`/api/knowledge/${id}`)` → `apiClient.delete(`/api/knowledge/${id}`)`
- 第 137 行：`axios.get('/api/knowledge/tags')` → `apiClient.get('/api/knowledge/tags')`

【步骤 3：验证拦截器生效】

确认替换后：
- 请求时会自动携带 Authorization: Bearer {token}
- 401 响应时会自动尝试刷新 Token
- 错误会被统一格式化为 { message, status, data }

【检验方法】

检验 1.1 — 验证导入语句：
```bash
cd frontend
grep -n "import apiClient" src/stores/knowledgeStore.js
```
预期：第 3 行（或附近）有 `import apiClient from '@/api/client'` 或等效导入

检验 1.2 — 验证无直接 axios 调用：
```bash
grep -n "axios\." src/stores/knowledgeStore.js
```
预期：无匹配（所有 axios.get/post/put/delete 已替换为 apiClient）

检验 1.3 — 验证无 axios 导入：
```bash
grep -n "import axios" src/stores/knowledgeStore.js
```
预期：无匹配（已删除直接 axios 导入）

检验 1.4 — 语法检查：
```bash
npm run lint -- --fix src/stores/knowledgeStore.js
```
预期：无错误

检验 1.5 — 功能测试：
启动前端开发服务器：
```bash
npm run dev
```
在浏览器中测试知识库功能：
1. 打开知识库页面
2. 尝试获取知识条目列表
3. 检查浏览器 Network 面板，确认请求头包含 Authorization: Bearer {token}
4. 如果 Token 过期，确认页面不会直接跳转登录，而是先尝试刷新

检验 1.6 — Token 刷新测试：
手动将 localStorage 中的 auth_token 设为无效值：
```javascript
localStorage.setItem('auth_token', 'invalid_token')
```
然后刷新页面，尝试访问知识库：
- 预期：自动尝试刷新 Token（通过 refresh_token）
- 如果刷新成功：正常显示数据
- 如果刷新失败：跳转登录页，显示"认证已过期"

检验 1.7 — 搜索其他 Store 是否有同样问题：
```bash
grep -rn "import axios" src/stores/
```
预期：无匹配（所有 Store 都应使用 apiClient）
如果有匹配，同样替换为 apiClient
```

---

## 提示词 2：N+1 查询防护 — 案件列表预加载 creator

**优先级**：🔴 高
**问题**：`case_service.py` 的 `get_cases()` 未预加载 `creator` 关系，序列化时可能触发 N+1 查询
**涉及文件**：`backend/app/services/case_service.py`

### 提示词

```
你是 Python 后端工程师，精通 SQLAlchemy ORM 优化。

【任务】
在案件列表查询中预加载 creator 关系，避免 N+1 查询问题。

【当前问题】
文件：backend/app/services/case_service.py，第 117-129 行

```python
base_stmt = select(Case)
if status_filter:
    base_stmt = base_stmt.where(Case.status == status_filter)

count_stmt = select(func.count()).select_from(base_stmt.subquery())
count_result = await db.execute(count_stmt)
total: int = count_result.scalar_one()

sort_expr = _build_sort_column(sort_by, sort_order)
offset = (page - 1) * page_size
items_stmt = base_stmt.order_by(sort_expr).offset(offset).limit(page_size)
items_result = await db.execute(items_stmt)
items: list[Case] = list(items_result.scalars().all())
```

查询只获取了 Case 对象，未预加载关联的 User（creator）。
如果在序列化时访问 case.creator.username，每个案件都会触发一次额外的数据库查询。

假设 page_size=20，则会产生 1（count）+ 1（items）+ 20（creator）= 22 次查询。

【步骤 1：添加 selectinload 导入】

在文件顶部的导入区域（第 11 行附近），添加：
```python
from sqlalchemy.orm import selectinload
```

【步骤 2：修改 get_cases() 查询语句】

在第 117 行的 `base_stmt = select(Case)` 之后，添加 selectinload：
```python
base_stmt = select(Case).options(selectinload(Case.creator))
```

或者在 items_stmt 构建时添加（更精确的控制）：
```python
items_stmt = base_stmt.options(selectinload(Case.creator)).order_by(sort_expr).offset(offset).limit(page_size)
```

推荐在 base_stmt 中添加，这样 count 查询和 items 查询都能复用同一个 base_stmt 定义。

【步骤 3：验证 Case 模型有 creator 关系】

确认 backend/app/models/case.py 中定义了 creator 关系：
```python
creator: Mapped[User] = relationship("User", backref="cases")
```

如果没有，需要先在 Case 模型中添加此关系。

【步骤 4：考虑其他需要预加载的场景】

检查是否有其他地方也需要预加载：
- 案件详情查询（get_case）：如果返回时包含 creator 信息，也应预加载
- 分析结果查询：如果包含 case 关系，应预加载

【检验方法】

检验 2.1 — 验证 selectinload 导入：
```bash
cd backend
grep -n "selectinload" app/services/case_service.py
```
预期：导入区域有 `from sqlalchemy.orm import selectinload`

检验 2.2 — 验证查询使用 selectinload：
```bash
grep -n "selectinload(Case.creator)" app/services/case_service.py
```
预期：get_cases() 函数中有 `.options(selectinload(Case.creator))`

检验 2.3 — 验证 Case 模型有 creator 关系：
```bash
grep -n "creator.*relationship" app/models/case.py
```
预期：有 `creator: Mapped[User] = relationship("User", ...)`

检验 2.4 — 语法检查：
```bash
python -m py_compile app/services/case_service.py
```
预期：无错误

检验 2.5 — SQL 查询数量验证（需要数据库）：
启用 SQL echo 进行验证：
```python
# 在 config.py 中临时设置
DB_ECHO: bool = True
```

然后执行案件列表查询，观察日志中的 SQL 语句数量：
- 优化前：应有 22+ 条 SQL（count + items + N 个 creator）
- 优化后：应有 2 条 SQL（count + items with join/subquery）

检验 2.6 — 运行测试：
```bash
pytest tests/test_cases.py -v
```
预期：所有测试通过

检验 2.7 — 搜索其他潜在的 N+1 问题：
```bash
grep -rn "relationship\|Mapped\[" app/models/ | grep -v "test"
```
检查所有模型关系，确认在列表查询中都使用了 selectinload 或 joinedload
```

---

## 提示词 3：Sentry 错误追踪集成

**优先级**：🔴 高
**问题**：无错误追踪服务，生产环境问题难以定位
**涉及文件**：`backend/app/main.py`、`frontend/src/main.js`（新建配置）

### 提示词

```
你是 DevOps 工程师，精通 Sentry 错误追踪平台集成。

【任务】
为后端和前端集成 Sentry 错误追踪，实现生产环境实时错误告警。

【当前问题】
- 后端：错误只能通过日志文件排查，无实时告警
- 前端：JavaScript 错误无上报机制

【步骤 1：后端 Sentry SDK 安装和配置】

1. 添加依赖到 backend/requirements.txt 或 backend/pyproject.toml：
```python
sentry-sdk[fastapi]>=2.0.0
```

2. 在 backend/app/config.py 中添加 Sentry 配置（约第 50 行后）：
```python
SENTRY_DSN: str | None = None
SENTRY_ENVIRONMENT: str = "development"
SENTRY_TRACES_SAMPLE_RATE: float = 0.1
SENTRY_ATTACH_STACKTRACE: bool = True
```

3. 在 backend/app/main.py 的 lifespan 函数中初始化 Sentry（约第 130 行后）：
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

# 在 lifespan 函数开头，数据库初始化之前
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[FastApiIntegration()],
        attach_stacktrace=settings.SENTRY_ATTACH_STACKTRACE,
    )
    logger.info(f"Sentry initialized: environment={settings.SENTRY_ENVIRONMENT}")
```

4. 在 backend/.env.example 中添加配置说明：
```bash
# Sentry 错误追踪（可选）
# SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
# SENTRY_ENVIRONMENT=production
# SENTRY_TRACES_SAMPLE_RATE=0.1
```

【步骤 2：前端 Sentry SDK 安装和配置】

1. 添加依赖到 frontend/package.json：
```json
"@sentry/vue": "^8.0.0"
```

2. 在 frontend/src/main.js 中初始化 Sentry（在 createApp 之前）：
```javascript
import * as Sentry from '@sentry/vue'

// Sentry 初始化（仅在配置了 DSN 时）
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN
if (SENTRY_DSN) {
  Sentry.init({
    app,
    dsn: SENTRY_DSN,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || 'development',
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration(),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  })
}
```

3. 创建 frontend/.env.example（如果不存在）添加：
```bash
# Sentry 错误追踪（可选）
# VITE_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
# VITE_SENTRY_ENVIRONMENT=production
```

【步骤 3：配置 Sentry 项目】

1. 在 https://sentry.io 创建账号和项目
2. 创建两个项目：
   - legal-analysis-backend（Python/FastAPI）
   - legal-analysis-frontend（Vue）
3. 获取各自的 DSN
4. 配置告警规则：
   - 错误频率阈值：5分钟内超过10次
   - 告警渠道：邮件 + Slack/钉钉

【步骤 4：添加错误上下文信息】

后端：在关键业务逻辑中添加上下文：
```python
import sentry_sdk

# 在分析开始时设置上下文
sentry_sdk.set_context("analysis", {
    "case_id": case_id,
    "mode": mode,
    "user_id": user_id,
})

# 在异常捕获时添加标签
sentry_sdk.set_tag("analysis_mode", mode)
```

前端：在关键操作中添加面包屑：
```javascript
import * as Sentry from '@sentry/vue'

// 在用户操作时添加面包屑
Sentry.addBreadcrumb({
  category: 'user-action',
  message: 'User clicked analyze button',
  level: 'info',
})
```

【检验方法】

检验 3.1 — 验证后端 Sentry 导入：
```bash
cd backend
grep -n "sentry_sdk\|SENTRY_DSN" app/main.py app/config.py
```
预期：main.py 有 sentry_sdk 导入和初始化，config.py 有 SENTRY_DSN 配置

检验 3.2 — 验证前端 Sentry 导入：
```bash
cd frontend
grep -n "@sentry/vue\|Sentry.init" src/main.js
```
预期：main.js 有 Sentry 导入和初始化

检验 3.3 — 验证依赖添加：
```bash
grep -n "sentry-sdk\|@sentry/vue" backend/pyproject.toml frontend/package.json
```
预期：两个文件都有 Sentry 依赖

检验 3.4 — 验证环境变量模板：
```bash
grep -n "SENTRY" backend/.env.example frontend/.env.example
```
预期：两个文件都有 Sentry 配置说明

检验 3.5 — 后端错误上报测试：
临时配置一个有效的 Sentry DSN，然后触发一个测试错误：
```python
# 在某个路由中临时添加
@router.get("/test-sentry")
async def test_sentry():
    raise ValueError("Sentry test error")
```

访问该端点，检查 Sentry 项目中是否收到错误报告。

检验 3.6 — 前端错误上报测试：
在浏览器控制台手动触发错误：
```javascript
Sentry.captureException(new Error('Sentry frontend test'))
```
检查 Sentry 前端项目中是否收到错误报告。

检验 3.7 — 生产环境验证：
部署后检查：
- Sentry 项目中是否收到真实的错误报告
- 错误是否包含完整的上下文信息（用户ID、操作类型等）
- 告警是否按配置规则触发
```

---

## 提示词 4：Makefile 添加

**优先级**：🟠 中
**问题**：无 Makefile，常用命令分散，开发效率低
**涉及文件**：`Makefile`（新建）

### 提示词

```
你是 DevOps 工程师，精通 Makefile 构建。

【任务】
创建 Makefile 封装常用开发命令，提升开发效率。

【当前问题】
常用命令分散在各处，每次执行需要记忆完整命令：
- 后端测试：`cd backend && pytest tests/ -v`
- 后端 lint：`cd backend && ruff check app/`
- 前端构建：`cd frontend && npm run build`
- Docker 构建：`docker-compose up --build`

【步骤 1：创建根目录 Makefile】

在项目根目录创建 Makefile：

```makefile
.PHONY: help install dev test lint format build docker clean

# 默认目标：显示帮助
help:
	@echo "可用命令:"
	@echo "  make install     - 安装所有依赖"
	@echo "  make dev         - 启动开发环境（后端+前端）"
	@echo "  make test        - 运行所有测试"
	@echo "  make lint        - 运行代码检查"
	@echo "  make format      - 格式化代码"
	@echo "  make build       - 构建生产版本"
	@echo "  make docker      - 启动 Docker 容器"
	@echo "  make docker-down - 停止 Docker 容器"
	@echo "  make clean       - 清理临时文件"

# 安装依赖
install:
	cd backend && pip install -e .
	cd frontend && npm install

# 启动开发环境
dev:
	@echo "启动后端..."
	cd backend && python run.py &
	@echo "启动前端..."
	cd frontend && npm run dev &

# 运行测试
test:
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing
	cd frontend && npm run test

# 代码检查
lint:
	cd backend && ruff check app/
	cd backend && mypy app/ --ignore-missing-imports
	cd frontend && npm run lint

# 格式化代码
format:
	cd backend && ruff format app/
	cd frontend && npm run format

# 构建生产版本
build:
	cd backend && pip-compile requirements.in --output-file requirements.lock
	cd frontend && npm run build

# Docker 相关
docker:
	docker-compose up --build -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# 清理临时文件
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	rm -rf backend/.cache backend/logs/*.log frontend/dist

# 数据库相关
db-migrate:
	cd backend && alembic upgrade head

db-reset:
	cd backend && alembic downgrade base && alembic upgrade head

db-seed:
	cd backend && python seed_data.py

# 快速检查（CI 本地模拟）
ci: lint test
	@echo "CI 检查完成"
```

注意：Windows 环境可能需要使用 Make 的 Windows 版本（如 GnuWin32 或 Chocolatey 安装），
或者创建等效的 PowerShell 脚本（scripts/dev.ps1）。

【步骤 2：创建 PowerShell 脚本（Windows 兼容）】

如果团队使用 Windows，创建 scripts/dev.ps1：

```powershell
# scripts/dev.ps1 - Windows 开发脚本

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "可用命令:"
    Write-Host "  .\scripts\dev.ps1 install     - 安装所有依赖"
    Write-Host "  .\scripts\dev.ps1 dev         - 启动开发环境"
    Write-Host "  .\scripts\dev.ps1 test        - 运行所有测试"
    Write-Host "  .\scripts\dev.ps1 lint        - 运行代码检查"
    Write-Host "  .\scripts\dev.ps1 format      - 格式化代码"
    Write-Host "  .\scripts\dev.ps1 build       - 构建生产版本"
    Write-Host "  .\scripts\dev.ps1 docker      - 启动 Docker"
    Write-Host "  .\scripts\dev.ps1 clean       - 清理临时文件"
}

switch ($Command) {
    "help" { Show-Help }
    "install" {
        Set-Location backend; pip install -e .; Set-Location ..
        Set-Location frontend; npm install; Set-Location ..
    }
    "test" {
        Set-Location backend; pytest tests/ -v --cov=app; Set-Location ..
        Set-Location frontend; npm run test; Set-Location ..
    }
    "lint" {
        Set-Location backend; ruff check app/; mypy app/; Set-Location ..
        Set-Location frontend; npm run lint; Set-Location ..
    }
    "format" {
        Set-Location backend; ruff format app/; Set-Location ..
        Set-Location frontend; npm run format; Set-Location ..
    }
    "docker" { docker-compose up --build -d }
    "docker-down" { docker-compose down }
    "clean" {
        Get-ChildItem -Recurse -Directory -Name "__pycache__" | Remove-Item -Recurse -Force
        Get-ChildItem -Recurse -Directory -Name ".pytest_cache" | Remove-Item -Recurse -Force
        Get-ChildItem -Recurse -Directory -Name "node_modules" | Remove-Item -Recurse -Force
    }
    default { Write-Host "未知命令: $Command"; Show-Help }
}
```

【步骤 3：更新 README.md】

在 README.md 的开发指南部分添加 Makefile 使用说明：

```markdown
## 快速开发命令

使用 Makefile 快速执行常用命令：

```bash
make help        # 显示所有可用命令
make install     # 安装依赖
make dev         # 启动开发环境
make test        # 运行测试
make lint        # 代码检查
make ci          # CI 本地模拟（lint + test）
```

Windows 用户可使用 PowerShell 脚本：

```powershell
.\scripts\dev.ps1 help
.\scripts\dev.ps1 test
```
```

【检验方法】

检验 4.1 — 验证 Makefile 存在：
```bash
ls -la Makefile
```
预期：文件存在

检验 4.2 — 验证 Makefile 内容：
```bash
head -20 Makefile
```
预期：显示帮助信息和至少 5 个命令定义

检验 4.3 — 测试 help 命令：
```bash
make help
```
预期：显示可用命令列表

检验 4.4 — 测试 lint 命令：
```bash
make lint
```
预期：执行 ruff check 和 mypy，输出检查结果

检验 4.5 — 测试 test 命令：
```bash
make test
```
预期：执行 pytest 和前端测试，输出测试结果

检验 4.6 — Windows PowerShell 脚本验证：
```powershell
.\scripts\dev.ps1 help
```
预期：显示可用命令列表

检验 4.7 — 验证 README 更新：
```bash
grep -n "make help\|Makefile" README.md
```
预期：README 中有 Makefile 使用说明
```

---

## 提示词 5：密码复杂度检查增强

**优先级**：🟠 中
**问题**：密码仅检查长度，无字符类型要求
**涉及文件**：`backend/app/schemas/user.py`

### 提示词

```
你是安全工程师，精通密码安全策略。

【任务】
增强密码复杂度验证，强制要求大小写字母、数字、特殊字符组合。

【当前问题】
文件：backend/app/schemas/user.py

当前密码验证仅检查长度（第 35 行）：
```python
password: str = Field(..., min_length=6, max_length=128)
```

无字符类型要求，用户可以设置如 "123456" 这样的弱密码。

【步骤 1：修改 UserCreate 的 password 字段】

将 min_length 从 6 提升到 10：
```python
password: str = Field(..., min_length=10, max_length=128)
```

【步骤 2：添加密码复杂度验证器】

在 UserCreate 类中添加 field_validator：

```python
import re

@field_validator("password")
@classmethod
def validate_password_complexity(cls, v: str) -> str:
    """验证密码复杂度.
    
    要求至少包含以下四类中的三类：
    - 小写字母 (a-z)
    - 大写字母 (A-Z)
    - 数字 (0-9)
    - 特殊字符 (!@#$%^&*等)
    
    Args:
        v: 密码字符串
        
    Returns:
        str: 验证通过的密码
        
    Raises:
        ValueError: 密码复杂度不足
    """
    if len(v) < 10:
        raise ValueError("密码长度至少为10个字符")
    
    categories = 0
    if re.search(r"[a-z]", v):
        categories += 1
    if re.search(r"[A-Z]", v):
        categories += 1
    if re.search(r"\d", v):
        categories += 1
    if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
        categories += 1
    
    if categories < 3:
        raise ValueError(
            "密码必须包含大写字母、小写字母、数字、特殊字符中的至少三类"
        )
    
    return v
```

【步骤 3：同样修改 UserUpdate 的 password 字段】

如果 UserUpdate 也有 password 字段（可选更新），添加相同的验证器：

```python
password: str | None = Field(None, min_length=10, max_length=128)

@field_validator("password")
@classmethod
def validate_password_complexity(cls, v: str | None) -> str | None:
    if v is None:
        return v
    # 同上验证逻辑
    ...
```

【步骤 4：更新 config.py 中的密码长度配置】

确保 config.py 中的 _MIN_PASSWORD_LENGTH 与 schema 一致：
```python
_MIN_PASSWORD_LENGTH = 10  # 从 12 改为 10，或保持 12 更严格
```

【步骤 5：更新错误提示信息】

确保错误信息对用户友好，在注册页面显示密码要求：
- 长度至少 10 个字符
- 必须包含大写字母、小写字母、数字、特殊字符中的至少三类

【检验方法】

检验 5.1 — 验证 min_length 提升：
```bash
cd backend
grep -n "min_length.*10" app/schemas/user.py
```
预期：password 字段的 min_length 为 10

检验 5.2 — 验证复杂度验证器：
```bash
grep -n "validate_password_complexity\|categories" app/schemas/user.py
```
预期：有验证器函数，包含四类字符检查

检验 5.3 — 验证 re 模块导入：
```bash
grep -n "import re" app/schemas/user.py
```
预期：有正则表达式模块导入

检验 5.4 — 语法检查：
```bash
python -m py_compile app/schemas/user.py
```
预期：无错误

检验 5.5 — 单元测试验证：
```python
# 测试脚本 test_password.py
from app.schemas.user import UserCreate

# 测试弱密码应被拒绝
weak_passwords = [
    "123456789",      # 纯数字
    "abcdefghij",     # 纯小写
    "ABCDEFGHIJ",     # 纯大写
    "password12",     # 小写+数字（仅2类）
]

for pwd in weak_passwords:
    try:
        UserCreate(username="test", password=pwd)
        print(f"FAIL: {pwd} 被接受")
    except ValueError as e:
        print(f"PASS: {pwd} 被拒绝 - {e}")

# 测试强密码应通过
strong_passwords = [
    "Password123",    # 大写+小写+数字（3类）
    "Pass@word1",     # 大写+小写+数字+特殊（4类）
]

for pwd in strong_passwords:
    try:
        UserCreate(username="test", password=pwd)
        print(f"PASS: {pwd} 被接受")
    except ValueError as e:
        print(f"FAIL: {pwd} 被拒绝 - {e}")
```

预期：
- 所有弱密码被拒绝
- 所有强密码被接受

检验 5.6 — 运行现有测试：
```bash
pytest tests/test_auth.py -v -k "password"
```
预期：所有测试通过（可能需要更新测试中的密码以符合新规则）

检验 5.7 — API 测试：
尝试注册一个弱密码用户：
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "123456789"}'
```
预期：返回 422 错误，提示密码复杂度不足
```

---

## 提示词 6：前端 Docker 化

**优先级**：🟠 中
**问题**：只有后端 Dockerfile，前端未容器化
**涉及文件**：`frontend/Dockerfile`（新建）、`docker-compose.yml`

### 提示词

```
你是 DevOps 工程师，精通前端容器化部署。

【任务】
为前端创建 Dockerfile，并更新 docker-compose.yml 实现完整容器化部署。

【当前问题】
- 只有后端 Dockerfile
- docker-compose.yml 未包含前端服务
- 前端需要单独启动 npm run dev

【步骤 1：创建 frontend/Dockerfile】

```dockerfile
# 阶段1：构建
FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖
COPY package.json package-lock.json* ./
RUN npm ci

# 复制源码并构建
COPY . .
RUN npm run build

# 阶段2：生产运行
FROM nginx:alpine AS runtime

# 复制构建产物到 Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

【步骤 2：创建 frontend/nginx.conf】

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # SPA 路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理到后端
    location /api/ {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;
}
```

【步骤 3：更新 docker-compose.yml】

添加前端服务：

```yaml
services:
  # ... 现有的 postgres, redis, api 服务 ...

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: legal-analysis-frontend
    ports:
      - "80:80"
    depends_on:
      - api
    networks:
      - legal-network
    restart: unless-stopped
```

【步骤 4：更新前端 vite.config.js】

确保构建输出目录为 dist：
```javascript
export default defineConfig({
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
```

【步骤 5：添加 .dockerignore】

创建 frontend/.dockerignore：
```
node_modules
dist
.git
.gitignore
*.md
.env
.env.*
*.log
```

【检验方法】

检验 6.1 — 验证 Dockerfile 存在：
```bash
ls -la frontend/Dockerfile
```
预期：文件存在

检验 6.2 — 验证 nginx.conf 存在：
```bash
ls -la frontend/nginx.conf
```
预期：文件存在

检验 6.3 — 验证 docker-compose.yml 包含 frontend：
```bash
grep -n "frontend:" docker-compose.yml
```
预期：有 frontend 服务定义

检验 6.4 — 构建前端镜像：
```bash
cd frontend
docker build -t legal-analysis-frontend:test .
```
预期：构建成功

检验 6.5 — 运行完整 Docker Compose：
```bash
docker-compose up --build -d
```
预期：所有服务启动成功

检验 6.6 — 验证前端可访问：
```bash
curl http://localhost/
```
预期：返回前端 HTML

检验 6.7 — 验证 API 代理：
```bash
curl http://localhost/api/health
```
预期：返回后端健康状态

检验 6.8 — 验证 SPA 路由：
浏览器访问 http://localhost/login，刷新页面：
预期：不返回 404，正常显示登录页
```

---

## 提示词 7：Redis 缓存切换（生产环境）

**优先级**：🟠 中
**问题**：默认使用文件缓存，生产环境性能受限
**涉及文件**：`backend/.env`、`backend/app/config.py`

### 提示词

```
你是后端工程师，精通缓存架构优化。

【任务】
配置生产环境使用 Redis 缓存，提升缓存性能。

【当前问题】
文件：backend/app/config.py

默认缓存配置：
```python
CACHE_BACKEND: str = "file"
```

文件缓存性能受限，不支持分布式部署。

【步骤 1：确认 Redis 服务可用】

确保 docker-compose.yml 中有 Redis 服务，或生产环境有独立的 Redis。

检查 docker-compose.yml：
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  ...
```

【步骤 2：更新 config.py 缓存配置】

添加 Redis 连接配置：
```python
REDIS_URL: str = "redis://localhost:6379/0"
CACHE_BACKEND: str = "redis"  # 生产环境默认使用 Redis
CACHE_TTL_SECONDS: int = 3600
```

【步骤 3：更新 .env.example】

添加 Redis 配置说明：
```bash
# 缓存配置
CACHE_BACKEND=redis
REDIS_URL=redis://redis:6379/0
CACHE_TTL_SECONDS=3600
```

【步骤 4：验证 cache.py 支持 Redis】

确认 backend/app/utils/cache.py 中有 RedisCache 实现：
```bash
grep -n "RedisCache\|redis" backend/app/utils/cache.py
```

如果没有，需要实现 RedisCache 类。

【步骤 5：生产环境部署验证】

部署后检查：
- Redis 服务正常运行
- 应用启动时连接 Redis 成功
- 缓存读写正常

【检验方法】

检验 7.1 — 验证 Redis 服务运行：
```bash
docker-compose ps redis
```
预期：Redis 服务状态为 Up

检验 7.2 — 验证 Redis 可连接：
```bash
docker-compose exec redis redis-cli ping
```
预期：返回 PONG

检验 7.3 — 验证配置：
```bash
grep -n "CACHE_BACKEND\|REDIS_URL" backend/.env
```
预期：CACHE_BACKEND=redis，REDIS_URL 正确配置

检验 7.4 — 验证应用连接 Redis：
启动应用后，检查日志：
```bash
grep -i "redis\|cache" backend/logs/*.log
```
预期：有 Redis 连接成功的日志

检验 7.5 — 缓存功能测试：
执行一次分析，然后再次执行相同分析：
```bash
# 第一次分析
curl -X POST http://localhost:8000/api/analyze -d '{"case_text": "测试案件"}'

# 第二次分析（应命中缓存）
curl -X POST http://localhost:8000/api/analyze -d '{"case_text": "测试案件"}'
```

检查 Redis 中是否有缓存数据：
```bash
docker-compose exec redis redis-cli keys "*"
```
预期：有缓存键存在

检验 7.6 — 缓存性能对比：
对比文件缓存和 Redis 缓存的响应时间：
- 文件缓存：约 10-50ms
- Redis 缓存：约 1-5ms

检验 7.7 — 分布式部署验证（可选）：
启动多个 API 实例，验证缓存共享：
```bash
docker-compose up --scale api=2
```

两个实例应能共享同一份缓存数据。
```

---

## 综合检验清单

完成所有优化后，执行以下综合验证：

```bash
# ===== 前端验证 =====
cd frontend
npm run lint
npm run build
npm run test

# ===== 后端验证 =====
cd backend
ruff check app/
mypy app/ --ignore-missing-imports
pytest tests/ -v --cov=app

# ===== Docker 验证 =====
docker-compose up --build -d
docker-compose ps

# ===== 功能验证 =====
curl http://localhost/api/health
curl http://localhost/

# ===== Sentry 验证 =====
# 检查 Sentry 项目中是否收到测试错误

# ===== 清理 =====
docker-compose down
make clean  # 或 .\scripts\dev.ps1 clean
```