# 项目修复提示词集合

本文档包含针对项目各类问题的修复提示词，每个提示词都包含具体的检验方法。

---

## 提示词 1：前端项目结构修复

**适用场景**：`frontend/src/` 目录为空，前端代码缺失

**目标**：创建完整的前端项目结构，包括基础组件、路由、状态管理和 API 调用层

**提示词内容**：

```
你是资深前端开发工程师，精通 Vue 3 + Vite + Pinia 技术栈。

【任务】
为法律案件分析系统创建完整的前端项目结构。当前 frontend/src/ 目录为空，需要创建以下模块：

【技术栈要求】
- Vue 3.4+ (Composition API + <script setup>)
- Vue Router 4
- Pinia 状态管理
- Axios HTTP 客户端
- Vite 构建工具

【必须创建的文件结构】

1. 基础配置和入口文件：
   - src/main.js - 应用入口
   - src/App.vue - 根组件
   - src/router/index.js - 路由配置
   - src/stores/index.js - Pinia  store 汇总
   - src/stores/auth.js - 认证状态管理
   - src/stores/case.js - 案件状态管理

2. API 层：
   - src/api/client.js - Axios 实例配置（含拦截器）
   - src/api/auth.js - 认证相关 API
   - src/api/cases.js - 案件相关 API
   - src/api/analysis.js - 分析相关 API

3. 视图组件：
   - src/views/LoginView.vue - 登录页面
   - src/views/DashboardView.vue - 仪表盘首页
   - src/views/CaseListView.vue - 案件列表
   - src/views/CaseDetailView.vue - 案件详情
   - src/views/AnalysisView.vue - 分析页面
   - src/views/KnowledgeView.vue - 知识库页面

4. 通用组件：
   - src/components/common/AppHeader.vue - 顶部导航
   - src/components/common/AppSidebar.vue - 侧边栏
   - src/components/common/LoadingSpinner.vue - 加载动画
   - src/components/cases/CaseCard.vue - 案件卡片
   - src/components/analysis/AnalysisResult.vue - 分析结果展示

5. 工具函数：
   - src/utils/storage.js - localStorage 封装
   - src/utils/formatters.js - 日期/文本格式化
   - src/utils/validators.js - 表单验证

【代码规范要求】
1. 所有组件使用 <script setup> 语法
2. Props 必须定义类型和默认值
3. 事件处理函数使用 handle 前缀（如 handleSubmit）
4. 布尔变量使用 is/has 前缀
5. 组件名使用大驼峰（PascalCase）
6. 组合式函数使用 use 前缀

【API 接口规范】
根据后端 API 设计，前端需要对接以下接口：
- POST /api/auth/login - 登录
- POST /api/auth/logout - 登出
- GET /api/cases - 获取案件列表
- POST /api/cases - 创建案件
- GET /api/cases/{id} - 获取案件详情
- POST /api/analyze - 执行分析
- GET /api/knowledge/entries - 获取知识库条目

【检验方法】
执行以下命令验证前端项目：

1. 依赖安装检查：
   ```bash
   cd frontend
   npm install
   ```
   预期结果：无错误，node_modules 正常创建

2. 开发服务器启动：
   ```bash
   npm run dev
   ```
   预期结果：Vite 启动成功，显示本地访问地址（如 http://localhost:5173）

3. 生产构建检查：
   ```bash
   npm run build
   ```
   预期结果：dist/ 目录生成，无构建错误

4. ESLint 检查：
   ```bash
   npm run lint
   ```
   预期结果：无语法错误

5. 文件结构验证：
   ```bash
   find src -type f -name "*.vue" -o -name "*.js" | wc -l
   ```
   预期结果：至少创建 15 个文件

【输出要求】
- 一次性创建所有文件
- 确保代码符合 Vue 3 最佳实践
- 包含必要的注释说明
- 提供完整的 package.json 依赖配置
```

---

## 提示词 2：缓存目录清理

**适用场景**：缓存目录被提交到版本控制

**目标**：清理已提交的缓存文件，更新 .gitignore 配置

**提示词内容**：

```
你是 DevOps 工程师，精通 Git 版本控制最佳实践。

【任务】
清理项目中已被提交到 Git 的缓存目录，并确保它们不再被跟踪。

【需要处理的缓存目录】
1. .mypy_cache/ - MyPy 类型检查缓存
2. .pytest_cache/ - Pytest 测试缓存
3. .ruff_cache/ - Ruff 代码检查缓存
4. backend/.mypy_cache/ - 后端 MyPy 缓存
5. backend/.pytest_cache/ - 后端 Pytest 缓存
6. backend/.ruff_cache/ - 后端 Ruff 缓存
7. backend/.cache/ - 应用缓存文件

【操作步骤】

1. 更新根目录 .gitignore：
   确保以下条目存在：
   ```
   # Python 缓存
   __pycache__/
   *.py[cod]
   *$py.class
   *.so
   .Python
   
   # 虚拟环境
   .venv/
   venv/
   env/
   
   # 工具缓存
   .mypy_cache/
   .pytest_cache/
   .ruff_cache/
   .cache/
   
   # 日志
   logs/
   *.log
   
   # 数据库
   *.db
   *.sqlite
   *.sqlite3
   
   # IDE
   .vscode/
   .idea/
   *.swp
   *.swo
   
   # 前端
   node_modules/
   dist/
   coverage/
   ```

2. 更新 backend/.gitignore（如果不存在则创建）：
   ```
   # 缓存目录
   .mypy_cache/
   .pytest_cache/
   .ruff_cache/
   .cache/
   
   # 日志
   logs/
   
   # 数据库
   *.db
   *.sqlite
   *.sqlite3
   
   # 环境变量
   .env
   ```

3. 从 Git 历史中移除缓存目录（但不删除本地文件）：
   ```bash
   git rm -r --cached .mypy_cache
   git rm -r --cached .pytest_cache
   git rm -r --cached .ruff_cache
   git rm -r --cached backend/.mypy_cache
   git rm -r --cached backend/.pytest_cache
   git rm -r --cached backend/.ruff_cache
   git rm -r --cached backend/.cache
   ```

【检验方法】

1. 验证 .gitignore 配置：
   ```bash
   git check-ignore -v .mypy_cache/CACHEDIR.TAG
   git check-ignore -v .pytest_cache/README.md
   git check-ignore -v .ruff_cache/.gitignore
   ```
   预期结果：显示匹配的 .gitignore 规则行

2. 验证缓存目录不再被跟踪：
   ```bash
   git status
   ```
   预期结果：显示 "deleted: .mypy_cache/..." 等，表示已从暂存区移除

3. 验证本地文件仍然存在：
   ```bash
   ls -la .mypy_cache/
   ls -la backend/.cache/
   ```
   预期结果：目录和文件仍然存在（仅停止 Git 跟踪）

4. 验证提交状态：
   ```bash
   git diff --cached --name-only | grep -E "(mypy_cache|pytest_cache|ruff_cache|.cache)"
   ```
   预期结果：显示被移除的缓存文件列表

【注意事项】
- 不要删除本地缓存文件，只停止 Git 跟踪
- 如果缓存目录包含重要数据，先备份
- 操作后需要执行 git commit 提交更改
```

---

## 提示词 3：Docker 配置修复

**适用场景**：Dockerfile 路径配置可能不正确

**目标**：验证并修复 Docker 构建配置

**提示词内容**：

```
你是容器化专家，精通 Docker 和 Docker Compose。

【任务】
检查并修复项目 Docker 配置，确保可以正常构建和运行。

【检查项目】

1. Dockerfile 路径检查：
   - 检查 COPY 指令路径是否正确
   - 当前配置：COPY backend/pyproject.toml backend/requirements.txt ./
   - 问题：requirements.txt 可能不存在于 backend/ 目录

2. 构建上下文检查：
   - 确认 docker build 上下文位置
   - 检查 .dockerignore 配置

3. 多阶段构建优化：
   - 检查 builder 和 runtime 阶段配置
   - 优化层缓存

【修复内容】

1. 验证 backend/requirements.txt 是否存在：
   - 如果不存在，需要创建或修改 Dockerfile

2. 修复 Dockerfile：
   ```dockerfile
   # 方案 A：如果 requirements.txt 不存在
   # 仅复制 pyproject.toml，使用 pip install 直接安装
   COPY backend/pyproject.toml ./
   RUN pip install --no-cache-dir -e .
   
   # 方案 B：如果 requirements.txt 存在但位置不同
   # 调整 COPY 路径
   COPY backend/pyproject.toml ./
   COPY requirements.txt ./  # 如果在根目录
   ```

3. 更新 .dockerignore：
   ```
   # Git
   .git
   .gitignore
   
   # Python
   __pycache__
   *.pyc
   *.pyo
   *.pyd
   .Python
   *.so
   .pytest_cache
   .mypy_cache
   .ruff_cache
   .coverage
   htmlcov/
   
   # 虚拟环境
   .venv
   venv
   env
   
   # IDE
   .vscode
   .idea
   
   # 日志和数据
   logs/
   *.log
   *.db
   *.sqlite
   
   # 前端（如果单独构建）
   frontend/node_modules
   
   # 文档和测试
   docs/
   tests/
   reports/
   
   # 其他
   .trae/
   .github/
   ```

4. 验证 docker-compose.yml：
   - 检查服务依赖关系
   - 验证健康检查配置
   - 确认卷挂载路径

【检验方法】

1. 验证 Dockerfile 语法：
   ```bash
   docker build --no-cache -t legal-analysis:test -f Dockerfile .
   ```
   预期结果：构建成功，无错误

2. 验证多阶段构建：
   ```bash
   docker images | grep legal-analysis
   ```
   预期结果：显示构建的镜像，大小合理（< 2GB）

3. 验证容器启动：
   ```bash
   docker run -d --name test-api -p 8000:8000 legal-analysis:test
   sleep 5
   docker ps | grep test-api
   ```
   预期结果：容器状态为 Up

4. 验证健康检查：
   ```bash
   docker inspect --format='{{.State.Health.Status}}' test-api
   ```
   预期结果：显示 "healthy"

5. 验证 API 响应：
   ```bash
   curl http://localhost:8000/health
   ```
   预期结果：返回 JSON 健康状态

6. 清理测试容器：
   ```bash
   docker stop test-api && docker rm test-api
   ```

7. 验证 docker-compose 配置：
   ```bash
   docker-compose config
   ```
   预期结果：显示解析后的配置，无错误

【输出要求】
- 提供修复后的 Dockerfile
- 提供完整的 .dockerignore
- 如有必要，更新 docker-compose.yml
- 提供构建和测试命令
```

---

## 提示词 4：异常处理优化

**适用场景**：代码中存在过于宽泛的异常捕获

**目标**：细化异常处理，提高代码健壮性

**提示词内容**：

```
你是 Python 专家，精通异常处理最佳实践和代码健壮性设计。

【任务】
优化项目中的异常处理，将宽泛的 Exception 捕获替换为具体的异常类型。

【需要优化的文件和位置】

1. backend/app/main.py 第 134 行：
   ```python
   except Exception as e:
       logger.error(f"预缓存示例案件失败: {e}")
   ```

2. backend/app/main.py 第 261-262 行：
   ```python
   except Exception as e:
       logger.error(f"创建默认管理员失败: {e}")
   ```

3. backend/app/main.py 第 318-319 行：
   ```python
   except Exception as e:
       logger.error(f"知识库默认数据初始化失败: {e}")
   ```

【优化要求】

1. 为每个异常捕获块指定具体异常类型：
   - 数据库操作：SQLAlchemyError, IntegrityError, OperationalError
   - HTTP/网络：HTTPException, ConnectionError, TimeoutError
   - 配置错误：ValidationError, ValueError
   - 文件操作：OSError, FileNotFoundError, PermissionError
   - JSON 解析：JSONDecodeError

2. 添加异常分类处理：
   ```python
   from sqlalchemy.exc import SQLAlchemyError, IntegrityError
   from httpx import HTTPError, ConnectError
   import json

   try:
       # 操作代码
   except IntegrityError as e:
       logger.warning(f"数据完整性错误: {e}")
       # 处理重复键等
   except SQLAlchemyError as e:
       logger.error(f"数据库操作失败: {e}")
       # 数据库特定处理
   except HTTPError as e:
       logger.error(f"HTTP 请求失败: {e}")
       # 网络错误处理
   except json.JSONDecodeError as e:
       logger.warning(f"JSON 解析失败: {e}")
       # JSON 错误处理
   except OSError as e:
       logger.error(f"系统错误: {e}")
       # 文件/系统错误
   except Exception as e:
       logger.exception(f"未预期的错误: {e}")
       # 最后的兜底，但记录完整堆栈
       raise
   ```

3. 添加重试机制（适用于临时性错误）：
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential

   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=4, max=10),
       retry=(ConnectError, TimeoutError)
   )
   async def operation_with_retry():
       # 可能失败的网络操作
   ```

4. 完善错误日志：
   - 使用 logger.exception() 替代 logger.error() 以包含堆栈信息
   - 添加上下文信息（如用户ID、操作类型）
   - 对敏感信息进行脱敏

【检验方法】

1. 语法检查：
   ```bash
   cd backend
   python -m py_compile app/main.py
   ```
   预期结果：无语法错误

2. Ruff 检查：
   ```bash
   ruff check app/main.py --select BLE
   ```
   预期结果：无 "blind except" 警告

3. 类型检查：
   ```bash
   mypy app/main.py --ignore-missing-imports
   ```
   预期结果：无类型错误

4. 单元测试：
   ```bash
   pytest tests/test_common.py -v
   ```
   预期结果：所有测试通过

5. 异常处理验证：
   ```python
   # 创建测试脚本 test_exceptions.py
   import asyncio
   from app.main import pre_cache_demo_cases, create_default_admin

   async def test_error_handling():
       try:
           await pre_cache_demo_cases()
           print("✓ 预缓存函数执行完成")
       except Exception as e:
           print(f"✗ 未捕获的异常: {e}")

   asyncio.run(test_error_handling())
   ```
   预期结果：函数正常执行或抛出预期异常

【输出要求】
- 提供优化后的代码片段
- 每个异常捕获块都要有明确的异常类型
- 添加必要的导入语句
- 保持原有功能不变
```

---

## 提示词 5：代码重构 - 重复代码合并

**适用场景**：database.py 中存在功能重复的函数

**目标**：合并重复代码，提高可维护性

**提示词内容**：

```
你是软件架构师，精通代码重构和设计模式。

【任务】
重构 backend/app/database.py，合并功能重复的函数。

【问题分析】

当前代码中有两个几乎相同的函数：
1. `get_async_db_session()` - 通用异步会话上下文管理器
2. `get_async_db()` - FastAPI 依赖注入专用

两个函数的实现完全一致，只是文档字符串不同。

【重构方案】

方案 A：保留一个函数，添加别名（推荐）
```python
@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """异步数据库会话上下文管理器.
    
    适用于：
    - 通用数据库操作
    - FastAPI 依赖注入（通过 get_async_db 别名）
    
    使用异步引擎的连接池获取会话，自动处理事务提交和回滚。
    """
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

# FastAPI 依赖注入别名
get_async_db = get_async_db_session
```

方案 B：提取公共函数
```python
async def _get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """内部数据库会话生成器."""
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """通用异步数据库会话上下文管理器."""
    async for db in _get_db_session():
        yield db

@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入专用异步数据库会话."""
    async for db in _get_db_session():
        yield db
```

【检验方法】

1. 语法检查：
   ```bash
   cd backend
   python -m py_compile app/database.py
   ```
   预期结果：无语法错误

2. 导入测试：
   ```python
   # 测试脚本 test_import.py
   from app.database import get_async_db_session, get_async_db
   
   print(f"get_async_db_session: {get_async_db_session}")
   print(f"get_async_db: {get_async_db}")
   print(f"是否相同: {get_async_db_session is get_async_db}")
   ```
   预期结果：两个函数指向同一对象（方案A）或不同对象（方案B）

3. 功能测试：
   ```python
   # 测试脚本 test_db.py
   import asyncio
   from app.database import get_async_db_session, get_async_db
   from sqlalchemy import text

   async def test_session():
       # 测试 get_async_db_session
       async with get_async_db_session() as db:
           result = await db.execute(text("SELECT 1"))
           print(f"✓ get_async_db_session 工作正常: {result.scalar()}")
       
       # 测试 get_async_db
       async with get_async_db() as db:
           result = await db.execute(text("SELECT 1"))
           print(f"✓ get_async_db 工作正常: {result.scalar()}")

   asyncio.run(test_session())
   ```
   预期结果：两个函数都能正常执行数据库查询

4. 回滚测试：
   ```python
   async def test_rollback():
       from app.models.case import Case
       
       try:
           async with get_async_db_session() as db:
               # 创建一个临时案件
               case = Case(title="测试", case_text="测试内容")
               db.add(case)
               await db.flush()
               # 故意抛出异常触发回滚
               raise ValueError("测试回滚")
       except ValueError:
           pass
       
       # 验证案件未保存
       async with get_async_db_session() as db:
           result = await db.execute(
               text("SELECT COUNT(*) FROM cases WHERE title = '测试'")
           )
           count = result.scalar()
           print(f"✓ 回滚测试通过: 临时数据未保存 (count={count})")
   
   asyncio.run(test_rollback())
   ```
   预期结果：异常后数据正确回滚，count=0

5. 运行现有测试：
   ```bash
   pytest tests/test_database.py -v
   ```
   预期结果：所有数据库相关测试通过

【输出要求】
- 提供重构后的完整 database.py
- 说明选择方案 A 或方案 B 的理由
- 确保所有现有导入仍然有效
- 不破坏任何现有功能
```

---

## 提示词 6：依赖版本锁定

**适用场景**：requirements.txt 使用宽松版本约束

**目标**：创建精确的依赖版本锁定

**提示词内容**：

```
你是 Python 依赖管理专家，精通 pip、pip-tools 和 Poetry。

【任务】
为项目创建精确的依赖版本锁定，确保生产环境可重现。

【当前问题】

backend/requirements.txt 使用 >= 约束：
```
fastapi[all]>=0.100.0
uvicorn[standard]>=0.23.2
...
```

这可能导致不同环境安装不同版本，引发兼容性问题。

【解决方案】

1. 创建 requirements.in（高层依赖）：
   ```
   # 核心框架
   fastapi[all]>=0.100.0
   uvicorn[standard]>=0.23.2
   
   # 数据验证和配置
   pydantic>=2.0.0
   pydantic-settings>=2.0.0
   
   # 数据库
   sqlalchemy[asyncio]>=2.0.0
   alembic>=1.12.0
   asyncpg>=0.29.0
   aiosqlite>=0.20.0
   
   # 安全和认证
   PyJWT>=2.8.0
   passlib[bcrypt]>=1.7.4
   bcrypt>=4.0.0
   cryptography>=41.0.0
   
   # HTTP 客户端
   httpx>=0.24.1
   
   # 文档处理
   PyMuPDF>=1.23.0
   python-docx>=1.1.0
   python-multipart>=0.0.6
   
   # 缓存和队列
   redis>=5.0.0
   
   # 日志
   loguru>=0.7.0
   
   # 工具
   python-dotenv>=1.0.0
   tenacity>=8.2.3
   slowapi>=0.1.9
   prometheus-client>=0.19.0
   neo4j>=5.14.0
   
   # OCR（可选）
   paddlepaddle>=2.6.0
   paddleocr>=2.8.0
   
   # 开发依赖
   pytest>=7.0.0
   pytest-asyncio>=0.21.0
   fakeredis[lua]>=2.20.0
   pytest-mock>=3.12.0
   pytest-benchmark>=4.0.0
   ```

2. 使用 pip-tools 生成锁定文件：
   ```bash
   pip install pip-tools
   pip-compile requirements.in --output-file requirements.lock --generate-hashes
   ```

3. 或使用 pip freeze 创建当前锁定：
   ```bash
   pip freeze > requirements.lock
   ```

4. 创建生产环境专用 requirements：
   ```
   # requirements-prod.txt - 不包含开发依赖
   -c requirements.lock  # 使用锁定文件约束
   -r requirements.in
   ```

【检验方法】

1. 验证锁定文件生成：
   ```bash
   cd backend
   pip install pip-tools
   pip-compile requirements.in --output-file requirements.lock --dry-run
   ```
   预期结果：显示将要生成的依赖列表，无冲突

2. 验证依赖安装：
   ```bash
   python -m venv test_venv
   source test_venv/bin/activate  # Windows: test_venv\Scripts\activate
   pip install -r requirements.lock
   ```
   预期结果：所有依赖安装成功，无版本冲突

3. 验证应用启动：
   ```bash
   cd backend
   python run.py
   ```
   预期结果：应用正常启动，无导入错误

4. 验证依赖树：
   ```bash
   pipdeptree --warn silence
   ```
   预期结果：显示完整的依赖树，无循环依赖

5. 安全检查：
   ```bash
   pip install safety
   safety check -r requirements.lock
   ```
   预期结果：无已知安全漏洞（或已评估风险）

6. 版本一致性检查：
   ```bash
   pip list --format=freeze > installed.txt
   diff requirements.lock installed.txt
   ```
   预期结果：版本一致（可能有些次要差异）

【输出要求】
- 提供 requirements.in（高层依赖）
- 提供生成的 requirements.lock（精确版本）
- 提供生成锁定文件的命令
- 添加依赖更新工作流说明
```

---

## 综合检验清单

执行完所有修复后，运行以下综合检验：

```bash
# 1. 代码质量检查
cd backend
ruff check . --select ALL --ignore D
mypy app --ignore-missing-imports

# 2. 测试套件
pytest tests/ -v --tb=short

# 3. 前端构建
cd ../frontend
npm install
npm run build

# 4. Docker 构建
cd ..
docker build -t legal-analysis:final .

# 5. 集成测试
docker-compose up -d
sleep 10
curl http://localhost:8000/health
docker-compose down
```

所有检查通过即表示修复完成。
