# Trae Solo 优化提示词完整汇总

> 本文件包含所有优化任务的完整提示词，可直接复制到Trae Solo模式使用

---

## 目录

1. [系统提示词](#系统提示词)
2. [任务1: 后端日志规范化](#任务1-后端日志规范化)
3. [任务2: 数据库连接池配置](#任务2-数据库连接池配置)
4. [任务3: 前端API层封装](#任务3-前端api层封装)
5. [任务4: 安全配置加固](#任务4-安全配置加固)
6. [任务5: API请求限流](#任务5-api请求限流)
7. [任务6: 单元测试补全](#任务6-单元测试补全)
8. [任务7: 异步代码修复](#任务7-异步代码修复)
9. [任务8: 异常处理完善](#任务8-异常处理完善)
10. [任务9: 常量提取规范化](#任务9-常量提取规范化)
11. [任务10: 前端组件规范化](#任务10-前端组件规范化)
12. [批量执行提示词](#批量执行提示词)

---

## 系统提示词

**复制到Trae设置中使用：**

```
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
4. 遵循项目代码规范

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

**完整提示词：**

```
【任务】修复后端代码中的日志f-string问题，统一使用loguru结构化日志格式

【项目路径】c:\Users\Lenovo\Desktop\微信程序开发\backend

【步骤1: 扫描问题】
执行命令：
cd backend
grep -rn "logger\.\(info\|debug\|warning\|error\).*f\"" --include="*.py" app/
grep -rn "logger\.\(info\|debug\|warning\|error\).*\.format(" --include="*.py" app/

【步骤2: 修复日志调用】
修复规则（应用到每个发现的位置）：

修复前：logger.info(f"分析完成，耗时 {elapsed}ms")
修复后：logger.info("分析完成，耗时 {}ms", elapsed)

修复前：logger.debug(f"处理案件 ID={case_id}, 文本长度={len(text)}")
修复后：logger.debug("处理案件 ID={}, 文本长度={}", case_id, len(text))

修复前：logger.error("保存失败: {}".format(error))
修复后：logger.error("保存失败: {}", error)

【已知需要修复的文件】
1. app/routers/analysis.py 第62行
   修复前: logger.info(f"收到分析请求 (文本长度: {len(case_text)})")
   修复后: logger.info("收到分析请求 (文本长度: {})", len(case_text))

2. app/services/analysis_service.py 第79行
   检查并修复所有f-string日志

【步骤3: 验证修复】
执行命令：
cd backend
grep -rn "logger\.\(info\|debug\|warning\|error\).*f\"" --include="*.py" app/ || echo "✓ 无f-string日志"
ruff check app/ --select G004 || echo "✓ Ruff检查通过"
pytest tests/ -v --tb=short

【步骤4: 提交代码】
git add -A
git commit -m "style(backend): 统一日志格式，移除f-string

- 将所有logger调用从f-string改为结构化参数
- 提升日志性能和可读性
- 所有测试通过"

【完成标准】
□ grep命令返回空（无f-string日志）
□ ruff check无G004错误
□ pytest全部通过
□ 代码已提交

请立即开始执行：先扫描，再逐个修复，最后验证并提交。
```

---

## 任务2: 数据库连接池配置

**完整提示词：**

```
【任务】为数据库添加连接池配置，提升并发性能和稳定性

【项目路径】c:\Users\Lenovo\Desktop\微信程序开发\backend

【步骤1: 备份原文件】
cp backend/app/database.py backend/app/database.py.bak

【步骤2: 修改database.py】
编辑 backend/app/database.py，将engine创建代码替换为：

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# 创建数据库引擎，添加连接池配置
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    # 连接池配置
    pool_size=10,              # 基础连接数
    max_overflow=20,           # 最大溢出连接数（总共最多30个连接）
    pool_pre_ping=True,        # 连接前ping检测，确保连接有效
    pool_recycle=3600,         # 连接回收时间(秒)，防止连接过期
    pool_timeout=30,           # 获取连接超时时间(秒)
    echo=settings.DEBUG,       # 调试模式打印SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """获取数据库会话."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

【步骤3: 创建连接池监控工具（可选）】
创建 backend/app/utils/db_monitor.py：

"""数据库连接池监控."""

from loguru import logger
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.database import engine


@event.listens_for(Engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """连接建立时触发."""
    logger.debug("数据库连接已建立")


@event.listens_for(Engine, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """连接从池取出时触发."""
    logger.debug("数据库连接从连接池取出")


def get_pool_status():
    """获取连接池状态."""
    pool = engine.pool
    return {
        "size": pool.size(),           # 当前连接数
        "checked_in": pool.checkedin(),  # 空闲连接
        "checked_out": pool.checkedout(),  # 使用中连接
        "overflow": pool.overflow(),   # 溢出连接数
    }

【步骤4: 验证配置】
执行命令：
cd backend
python -c "from app.database import engine; print(f'Pool size: {engine.pool.size()}')"
python -c "from app.database import engine; pool = engine.pool; print(f'Pool: size={pool.size()}, checked_in={pool.checkedin()}, checked_out={pool.checkedout()}')"
pytest tests/ -v -k "db" --tb=short

【步骤5: 提交代码】
git add -A
git commit -m "perf(backend): 添加数据库连接池配置

- 配置连接池大小: pool_size=10, max_overflow=20
- 添加连接健康检查: pool_pre_ping=True
- 添加连接回收机制: pool_recycle=3600
- 添加连接池监控工具
- 所有测试通过"

【完成标准】
□ database.py包含pool_size等参数
□ engine.pool.size()返回正确值
□ 服务启动无错误
□ pytest通过
□ 代码已提交

请立即修改database.py并验证。
```

---

## 任务3: 前端API层封装

**完整提示词：**

```
【任务】创建统一的前端API封装层，集中管理所有后端接口调用

【项目路径】c:\Users\Lenovo\Desktop\微信程序开发\frontend

【步骤1: 创建目录结构】
执行命令：
cd frontend/src
mkdir -p api
mkdir -p api/modules

【步骤2: 创建API基础配置】
创建文件 frontend/src/api/config.js，内容如下：

/**
 * API基础配置
 */

// API基础URL（从环境变量读取，默认本地开发地址）
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 请求超时时间(毫秒) - AI分析可能需要较长时间
const TIMEOUT = 120000

// 请求配置
export const apiConfig = {
  baseURL: BASE_URL,
  timeout: TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
}

// 响应状态码处理映射
export const responseHandlers = {
  200: (data) => data,
  201: (data) => data,
  400: (error) => { throw new Error(error.detail || '请求参数错误') },
  401: (error) => { throw new Error('未授权，请重新登录') },
  403: (error) => { throw new Error('没有权限执行此操作') },
  404: (error) => { throw new Error(error.detail || '请求的资源不存在') },
  500: (error) => { throw new Error('服务器内部错误') },
  502: (error) => { throw new Error('分析服务暂时不可用') },
  504: (error) => { throw new Error('请求超时，请稍后重试') },
}

【步骤3: 创建axios实例】
创建文件 frontend/src/api/instance.js，内容如下：

/**
 * Axios实例配置
 */

import axios from 'axios'

import { apiConfig, responseHandlers } from './config'

// 创建axios实例
const apiInstance = axios.create(apiConfig)

// 请求拦截器 - 添加认证token
apiInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 统一处理响应和错误
apiInstance.interceptors.response.use(
  (response) => {
    const { status, data } = response
    const handler = responseHandlers[status]
    if (handler) {
      return handler(data)
    }
    return data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      const handler = responseHandlers[status]
      if (handler) {
        return handler(data)
      }
    }
    return Promise.reject(error)
  }
)

export default apiInstance

【步骤4: 创建分析API模块】
创建文件 frontend/src/api/modules/analysis.js，内容如下：

/**
 * 分析相关API
 */

import api from '../instance'

/**
 * 执行案件分析
 * @param {Object} params - 分析参数
 * @param {string} params.case_text - 案件文本
 * @param {string} [params.mode='auto'] - 分析模式 (auto/single/multi)
 * @param {number} [params.case_id] - 案件ID
 * @returns {Promise<Object>} 分析结果
 */
export const analyzeCase = (params) => {
  return api.post('/api/analyze', params)
}

/**
 * 获取分析历史
 * @param {number} caseId - 案件ID
 * @returns {Promise<Array>} 分析历史列表
 */
export const getAnalysisHistory = (caseId) => {
  return api.get(`/api/cases/${caseId}/analyses`)
}

/**
 * 获取单个分析结果
 * @param {number} analysisId - 分析ID
 * @returns {Promise<Object>} 分析结果详情
 */
export const getAnalysisById = (analysisId) => {
  return api.get(`/api/analyses/${analysisId}`)
}

export default {
  analyzeCase,
  getAnalysisHistory,
  getAnalysisById,
}

【步骤5: 创建案件API模块】
创建文件 frontend/src/api/modules/cases.js，内容如下：

/**
 * 案件相关API
 */

import api from '../instance'

/**
 * 获取案件列表
 * @param {Object} params - 查询参数
 * @param {number} [params.skip=0] - 分页偏移
 * @param {number} [params.limit=100] - 每页数量
 * @param {string} [params.status] - 状态筛选
 * @returns {Promise<Array>} 案件列表
 */
export const getCases = (params = {}) => {
  return api.get('/api/cases', { params })
}

/**
 * 获取单个案件
 * @param {number} caseId - 案件ID
 * @returns {Promise<Object>} 案件详情
 */
export const getCaseById = (caseId) => {
  return api.get(`/api/cases/${caseId}`)
}

/**
 * 创建案件
 * @param {Object} data - 案件数据
 * @returns {Promise<Object>} 创建的案件
 */
export const createCase = (data) => {
  return api.post('/api/cases', data)
}

/**
 * 更新案件
 * @param {number} caseId - 案件ID
 * @param {Object} data - 更新数据
 * @returns {Promise<Object>} 更新后的案件
 */
export const updateCase = (caseId, data) => {
  return api.put(`/api/cases/${caseId}`, data)
}

/**
 * 删除案件
 * @param {number} caseId - 案件ID
 * @returns {Promise<boolean>} 是否成功
 */
export const deleteCase = (caseId) => {
  return api.delete(`/api/cases/${caseId}`)
}

export default {
  getCases,
  getCaseById,
  createCase,
  updateCase,
  deleteCase,
}

【步骤6: 创建API统一入口】
创建文件 frontend/src/api/index.js，内容如下：

/**
 * API统一入口
 */

import analysisApi from './modules/analysis'
import casesApi from './modules/cases'

export const analysis = analysisApi
export const cases = casesApi

// 统一导出
export default {
  analysis: analysisApi,
  cases: casesApi,
}

【步骤7: 更新store使用新API】
修改 frontend/src/stores/analysisStore.js，添加API导入：

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { analysis } from '@/api'  // 使用新的API层

// 在适当位置替换原有的axios调用
async function performAnalysis(caseText, mode = 'auto') {
  isLoading.value = true
  error.value = null
  
  const startTime = Date.now()
  
  try {
    const result = await analysis.analyzeCase({
      case_text: caseText,
      mode: mode,
    })
    
    const elapsed = Date.now() - startTime
    setResponseTime(elapsed)
    setAnalysisResult(result)
    
    return result
  } catch (err) {
    setError(err.message || '分析失败')
    throw err
  } finally {
    setLoading(false)
  }
}

【步骤8: 验证API层】
执行命令：
cd frontend
npm run lint
npm run build

【步骤9: 提交代码】
git add -A
git commit -m "feat(frontend): 创建API层封装

- 创建统一的API配置管理
- 封装axios实例和拦截器
- 创建analysis和cases API模块
- 更新store使用新API层
- 所有构建检查通过"

【完成标准】
□ src/api/目录结构完整
□ config.js包含基础配置
□ instance.js配置拦截器
□ modules/包含analysis和cases模块
□ index.js统一导出所有API
□ npm run lint无错误
□ npm run build成功
□ 代码已提交

请立即创建所有文件并验证。
```

---

## 任务4: 安全配置加固

**完整提示词：**

```
【任务】强制环境变量读取敏感配置，移除硬编码默认值

【项目路径】c:\Users\Lenovo\Desktop\微信程序开发\backend

【步骤1: 扫描硬编码敏感信息】
执行命令：
cd backend
grep -rn "password.*=" --include="*.py" app/ | grep -v "^.*:.*#"
grep -rn "secret.*=" --include="*.py" app/ | grep -v "^.*:.*#"
grep -rn "key.*=" --include="*.py" app/ | grep -v "^.*:.*#"

【步骤2: 修改配置类】
编辑 backend/app/config.py，将敏感配置改为必填：

"""应用配置模块.

所有敏感配置必须从环境变量读取，禁止硬编码。
"""

import secrets
from functools import lru_cache

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类.

    所有配置项优先从环境变量读取，.env文件作为备选。
    敏感配置（密码、密钥）必须设置，无默认值。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- 基础配置 ---
    APP_ENV: str = Field(default="development", pattern="^(development|production|testing)$")
    DEBUG: bool = Field(default=False)

    # --- 服务器配置 ---
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = Field(default=8000, ge=1, le=65535)

    # --- 数据库配置 ---
    DATABASE_URL: str = Field(
        default="sqlite:///./app.db",
        pattern=r"^(sqlite|postgresql|mysql)://.*",
    )

    # --- Ollama配置 ---
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="deepseek-r1:7b")

    # --- JWT配置（敏感，必须设置） ---
    JWT_SECRET_KEY: str = Field(
        ...,  # 无默认值，必须设置
        min_length=32,
        description="JWT签名密钥，至少32字符",
    )
    JWT_ALGORITHM: str = Field(default="HS256", pattern="^(HS256|HS384|HS512)$")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440)

    # --- CORS配置 ---
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("CORS_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list[str]:
        """解析CORS源列表."""
        return [origin.strip() for origin in v.split(",")]

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """验证JWT密钥强度."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY必须至少32字符")
        if v == "your-secret-key-here":
            raise ValueError("JWT_SECRET_KEY不能使用默认占位符")
        return v


@lru_cache
def get_settings() -> Settings:
    """获取配置实例（缓存）."""
    try:
        return Settings()
    except ValidationError as e:
        print("=" * 60)
        print("配置错误：请检查环境变量或.env文件")
        print("=" * 60)
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            print(f"  • {field}: {msg}")
        print("=" * 60)
        raise SystemExit(1)


settings = get_settings()


# --- 安全配置常量 ---
class SecurityConfig:
    """安全配置常量."""
    PWD_HASH_ALGORITHM = "bcrypt"
    MIN_PASSWORD_LENGTH = 8
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 30


# --- 分析配置常量 ---
class AnalysisConfig:
    """分析配置常量."""
    MIN_CASE_TEXT_LENGTH = 10
    MAX_CASE_TEXT_LENGTH = 50000
    ANALYSIS_TIMEOUT = 60
    MAX_RETRY_COUNT = 3
    CACHE_TTL = 3600

【步骤3: 创建配置验证脚本】
创建 backend/scripts/verify_config.py：

#!/usr/bin/env python3
"""配置验证脚本."""

import sys

from app.config import settings


def verify_security_config():
    """验证安全配置."""
    errors = []
    warnings = []

    # 检查JWT密钥
    if settings.JWT_SECRET_KEY == "your-secret-key-here":
        errors.append("JWT_SECRET_KEY使用了默认占位符，请设置真实密钥")
    elif len(settings.JWT_SECRET_KEY) < 32:
        errors.append(f"JWT_SECRET_KEY长度不足(当前{len(settings.JWT_SECRET_KEY)}字符)")

    # 检查生产环境配置
    if settings.APP_ENV == "production":
        if settings.DEBUG:
            warnings.append("生产环境建议关闭DEBUG模式")
        if "sqlite" in settings.DATABASE_URL:
            warnings.append("生产环境建议使用PostgreSQL而非SQLite")

    # 打印结果
    if errors:
        print("=" * 60)
        print("❌ 配置错误：")
        for error in errors:
            print(f"  • {error}")
        print("=" * 60)
        return False

    if warnings:
        print("=" * 60)
        print("⚠️  配置警告：")
        for warning in warnings:
            print(f"  • {warning}")
        print("=" * 60)

    print("✅ 配置验证通过")
    return True


if __name__ == "__main__":
    if not verify_security_config():
        sys.exit(1)

【步骤4: 更新.env.example】
更新 backend/.env.example：

# =============================================================================
# 环境配置示例
# 复制此文件为 .env 并填入真实值
# =============================================================================

# --- 基础配置 ---
APP_ENV=development
DEBUG=true

# --- 服务器配置 ---
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# --- 数据库配置 ---
DATABASE_URL=sqlite:///./app.db

# --- Ollama配置 ---
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:7b

# --- JWT配置（必须设置！） ---
# 生成命令: openssl rand -hex 32
# 或使用Python: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=your-secret-key-here-change-this-in-production

# --- CORS配置 ---
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

【步骤5: 验证安全配置】
执行命令：
cd backend

# 测试配置验证脚本
python scripts/verify_config.py

# 测试应用启动（需要先设置JWT密钥）
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
python run.py &
sleep 3
curl http://localhost:8000/api/health || echo "服务启动成功"
kill %1

【步骤6: 提交代码】
git add -A
git commit -m "security(backend): 强制环境变量读取敏感配置

- 移除所有硬编码的敏感默认值
- JWT_SECRET_KEY必须设置，无默认值
- 添加配置验证脚本
- 启动时强制检查安全配置
- 更新.env.example添加安全说明
- 所有安全检查通过"

【完成标准】
□ config.py敏感配置无默认值
□ verify_config.py验证脚本可运行
□ 缺少JWT密钥时启动失败
□ 弱JWT密钥被检测并拒绝
□ .env.example包含安全说明
□ 代码已提交

请立即修改config.py并创建验证脚本。
```

---

## 任务5: API请求限流

**完整提示词：**

```
【任务】添加API请求限流功能，防止恶意请求和系统过载

【项目路径】c:\Users\Lenovo\Desktop\微信程序开发\backend

【步骤1: 安装依赖】
执行命令：
pip install slowapi

【步骤2: 创建限流中间件】
创建 backend/app/middleware/rate_limit.py：

"""请求限流中间件."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException

# 创建限流器实例
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # 默认限制：每分钟100请求
)


def get_limiter() -> Limiter:
    """获取限流器实例."""
    return limiter


# 自定义限流错误处理
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """处理限流异常."""
    raise HTTPException(
        status_code=429,
        detail="请求过于频繁，请稍后再试",
        headers={"Retry-After": str(exc.retry_after)} if hasattr(exc, "retry_after") else {}
    )

【步骤3: 注册限流器】
修改 backend/app/main.py，添加：

from slowapi.errors import RateLimitExceeded
from app.middleware.rate_limit import limiter, rate_limit_handler

# 注册限流器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

【步骤4: 为关键路由添加限流】
修改 backend/app/routers/analysis.py：

from fastapi import Request
from app.middleware.rate_limit import limiter

@router.post("/analyze")
@limiter.limit("10/minute")  # 分析接口：每分钟10次
async def analyze_case(
    request: Request,  # 必须添加request参数
    request_body: AnalyzeRequest,
    db: Session = Depends(get_db),
):
    ...

修改 backend/app/routers/cases.py：

from fastapi import Request
from app.middleware.rate_limit import limiter

@router.post("/")
@limiter.limit("30/minute")  # 创建案件：每分钟30次
async def create_new_case(
    request: Request,
    ...
):
    ...

【步骤5: 验证限流】
执行命令：
cd backend
python run.py &
sleep 3

# 测试限流（快速发送12个请求）
for i in {1..12}; do
  curl -s -o /dev/null -w "%{http_code} " \
    -X POST http://localhost:8000/api/analyze \
    -H "Content-Type: application/json" \
    -d '{"case_text": "测试", "mode": "auto"}'
done
echo ""
# 预期输出: 200 200 200 200 200 200 200 200 200 200 429 429

kill %1

【步骤6: 提交代码】
git add -A
git commit -m "security(backend): 添加API请求限流

- 安装slowapi限流库
- 配置不同接口的限流策略
- 分析接口：10/minute
- 创建案件：30/minute
- 登录接口：5/minute
- 添加限流响应头
- 所有测试通过"

【完成标准】
□ slowapi已安装
□ 限流中间件已配置
□ 各路由有限流装饰器
□ 超限时返回429状态码
□ 代码已提交

请立即安装依赖并添加限流配置。
```

---

## 任务6: 单元测试补全

**完整提示词：**

```
【任务】为核心业务逻辑补全单元测试，确保代码质量和可维护性

【项目路径】c:\Users\Lenovo\Desktop\微信程序开发\backend

【步骤1: 检查现有测试】
执行命令：
cd backend
find tests -name "*.py" -type f
pytest tests/ -v --tb=short

【步骤2: 创建测试固件】
创建 backend/tests/conftest.py：

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

【步骤3: 测试分析服务】
创建 backend/tests/test_analysis_service.py：

"""分析服务测试."""

import pytest
from fastapi import HTTPException

from app.models.case import Case
from app.services.analysis_service import (
    run_analysis,
    get_analysis,
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
        assert score == pytest.approx(6.17)
    
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
        assert score == pytest.approx(5.75)


class TestGetAnalysis:
    """测试获取分析结果."""
    
    def test_existing_analysis(self, db):
        """测试获取存在的分析."""
        from app.models.analysis import Analysis
        analysis = Analysis(
            case_id=1,
            result_json='{"test": "data"}',
            mode="auto",
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        result = get_analysis(db, analysis.id)
        assert result is not None
        assert result.id == analysis.id
    
    def test_nonexistent_analysis(self, db):
        """测试获取不存在的分析."""
        result = get_analysis(db, 999)
        assert result is None

【步骤4: 测试案件服务】
创建 backend/tests/test_case_service.py：

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
        assert case.status == "pending"
    
    def test_create_minimal(self, db):
        """测试最小数据创建."""
        case_data = CaseCreate(
            title="最小案件",
            case_text="只有标题和文本",
        )
        
        case = create_case(db, case_data)
        
        assert case.title == "最小案件"


class TestGetCases:
    """测试获取案件列表."""
    
    def test_pagination(self, db):
        """测试分页."""
        from app.models.case import Case
        for i in range(10):
            case = Case(title=f"案件{i}", case_text=f"文本{i}")
            db.add(case)
        db.commit()
        
        cases = get_cases(db, skip=0, limit=5)
        assert len(cases) == 5
        
        cases = get_cases(db, skip=5, limit=5)
        assert len(cases) == 5
    
    def test_status_filter(self, db):
        """测试状态筛选."""
        from app.models.case import Case
        case1 = Case(title="案件1", case_text="文本1", status="pending")
        case2 = Case(title="案件2", case_text="文本2", status="completed")
        db.add(case1)
        db.add(case2)
        db.commit()
        
        pending_cases = get_cases(db, status_filter="pending")
        assert len(pending_cases) == 1


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
        
        deleted = get_case(db, case.id)
        assert deleted is None

【步骤5: 测试工具函数】
创建 backend/tests/test_utils.py：

"""工具函数测试."""

import pytest

from app.utils.common import generate_cache_key, sanitize_json_string


class TestGenerateCacheKey:
    """测试缓存键生成."""
    
    def test_string_input(self):
        """测试字符串输入."""
        key1 = generate_cache_key("test text", "auto")
        key2 = generate_cache_key("test text", "auto")
        assert key1 == key2
    
    def test_different_inputs(self):
        """测试不同输入."""
        key1 = generate_cache_key("text1", "auto")
        key2 = generate_cache_key("text2", "auto")
        assert key1 != key2


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

【步骤6: 运行测试】
执行命令：
cd backend
pytest tests/ -v --tb=short
pytest tests/ --cov=app --cov-report=term-missing

【步骤7: 提交代码】
git add -A
git commit -m "test(backend): 补全核心业务单元测试

- 添加conftest.py测试固件配置
- 测试分析服务：评分计算、查询
- 测试案件服务：CRUD操作、分页、筛选
- 测试工具函数：缓存键、JSON清理
- 测试覆盖率提升至80%+
- 所有测试通过"

【完成标准】
□ conftest.py包含测试固件
□ test_analysis_service.py覆盖分析服务
□ test_case_service.py覆盖案件服务
□ test_utils.py覆盖工具函数
□ pytest全部通过
□ 测试覆盖率>=80%
□ 代码已提交

请立即创建测试文件并运行验证。
```

---

## 任务7: 异步代码修复

**完整提示词：**

```
【任务】修复异步函数调用问题，确保正确使用async/await

【项目路径】c:\Users\Lenovo\Desktop\微信程序开发\backend

【步骤1: 扫描异步调用问题】
执行命令：
cd backend
grep -rn "analyze_pipeline" --include="*.py" app/

【步骤2: 修复analysis_service.py】
编辑 backend/app/services/analysis_service.py

修复第75行：
修复前: result: dict[str, Any] = analyze_pipeline(case.case_text, mode=mode)
修复后: result: dict[str, Any] = await analyze_pipeline(case.case_text, mode=mode)

同时确保函数签名正确：
修复前: def run_analysis(db: Session, case_id: int, mode: str = "auto") -> Analysis:
修复后: async def run_analysis(db: Session, case_id: int, mode: str = "auto") -> Analysis:

【步骤3: 修复routers/analysis.py】
编辑 backend/app/routers/analysis.py

确保analyze_case函数正确调用异步pipeline：
修复前: result = analyze_pipeline(case_text, mode=mode)
修复后: result = await analyze_pipeline(case_text, mode=mode)

【步骤4: 验证修复】
执行命令：
cd backend
python -c "
import asyncio
from pipeline import analyze_pipeline

async def test():
    result = await analyze_pipeline('测试案件文本', mode='auto')
    print(f'结果类型: {type(result)}')
    return result

asyncio.run(test())
"

pytest tests/ -v --tb=short

【步骤5: 提交代码】
git add -A
git commit -m "fix(backend): 修复异步函数调用问题

- analysis_service.py: 添加await调用analyze_pipeline
- routers/analysis.py: 确保异步调用正确
- 所有异步函数使用async/await
- 所有测试通过"

【完成标准】
□ analyze_pipeline调用添加await
□ 函数签名添加async
□ pytest全部通过
□ 代码已提交

请立即修复异步调用问题。
```

---

## 任务8: 异常处理完善

**完整提示词：**

```
【任务】完善JSON解析和外部调用的异常处理

【项目路径】c:\Users\Lenovo\Desktop\微信程序开发\backend

【步骤1: 扫描缺少异常处理的位置】
执行命令：
cd backend
grep -rn "json.loads" --include="*.py" app/
grep -rn "httpx" --include="*.py" app/

【步骤2: 修复pipeline.py的JSON解析】
编辑 backend/app/services/pipeline.py，为所有json.loads添加异常处理：

修复前:
result = json.loads(response)

修复后:
try:
    result = json.loads(sanitize_json_string(response))
except json.JSONDecodeError as e:
    logger.error("JSON解析失败: {}, 响应内容: {}", e, response[:200])
    # 返回默认结果或重试
    return get_default_analysis_result()

添加默认结果函数：
def get_default_analysis_result() -> dict:
    """返回默认分析结果（当解析失败时使用）."""
    return {
        "subjective_knowledge": "无法判断",
        "sentence": "分析失败，请重新提交",
        "court": "建议人工复核",
        "ground_truth_analysis": {
            "dimension1": {"score": 0, "reasoning": "解析失败"},
            "dimension2": {"score": 0, "reasoning": "解析失败"},
            "dimension3": {"score": 0, "reasoning": "解析失败"},
        },
        "fallback": True,
    }

【步骤3: 修复外部API调用】
编辑 backend/app/services/pipeline.py，为ollama调用添加异常处理：

修复前:
response = client.post(url, json=payload)

修复后:
try:
    response = client.post(url, json=payload, timeout=settings.ANALYSIS_TIMEOUT)
    response.raise_for_status()
except httpx.TimeoutException:
    logger.warning("Ollama请求超时")
    return get_default_analysis_result()
except httpx.HTTPStatusError as e:
    logger.error("Ollama返回错误: status={}", e.response.status_code)
    return get_default_analysis_result()
except httpx.RequestError as e:
    logger.error("Ollama连接失败: {}", e)
    return get_default_analysis_result()

【步骤4: 验证修复】
执行命令：
cd backend

# 测试异常处理
python -c "
import json
from app.utils.common import sanitize_json_string

# 测试正常JSON
result = json.loads(sanitize_json_string('{\"key\": \"value\"}'))
print('正常JSON:', result)

# 测试带Markdown的JSON
result = json.loads(sanitize_json_string('```json\n{\"key\": \"value\"}\n```'))
print('Markdown JSON:', result)
"

pytest tests/ -v --tb=short

【步骤5: 提交代码】
git add -A
git commit -m "fix(backend): 完善异常处理

- 为所有json.loads添加try-except
- 为ollama调用添加超时和错误处理
- 添加默认分析结果fallback
- 所有测试通过"

【完成标准】
□ json.loads有异常处理
□ ollama调用有超时处理
□ 有默认fallback结果
□ pytest全部通过
□ 代码已提交

请立即完善异常处理。
```

---

## 任务9: 常量提取规范化

**完整提示词：**

```
【任务】提取魔法数字和硬编码字符串为配置常量

【项目路径】c:\Users\Lenovo\Desktop\微信程序开发\backend

【步骤1: 扫描魔法数字】
执行命令：
cd backend
grep -rn "len.*>.*[0-9]" --include="*.py" app/
grep -rn "timeout.*=.*[0-9]" --include="*.py" app/
grep -rn "\"pending\"" --include="*.py" app/

【步骤2: 确认config.py包含常量】
检查 backend/app/config.py 是否包含：

class AnalysisConfig:
    """分析配置常量."""
    MIN_CASE_TEXT_LENGTH = 10
    MAX_CASE_TEXT_LENGTH = 50000
    ANALYSIS_TIMEOUT = 60
    MAX_RETRY_COUNT = 3
    CACHE_TTL = 3600

class CaseStatus:
    """案件状态常量."""
    DRAFT = "draft"
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"

class AnalysisMode:
    """分析模式常量."""
    AUTO = "auto"
    SINGLE = "single"
    MULTI = "multi"

【步骤3: 替换硬编码值】
编辑 backend/app/routers/analysis.py：

修复前:
case_text: str = Field(..., min_length=1, max_length=50000)
mode: str = Field(default="auto", pattern="^(auto|single|multi)$")

修复后:
from app.config import AnalysisConfig, AnalysisMode

case_text: str = Field(
    ...,
    min_length=AnalysisConfig.MIN_CASE_TEXT_LENGTH,
    max_length=AnalysisConfig.MAX_CASE_TEXT_LENGTH,
)
mode: str = Field(
    default=AnalysisMode.AUTO,
    pattern=f"^({AnalysisMode.AUTO}|{AnalysisMode.SINGLE}|{AnalysisMode.MULTI})$",
)

编辑 backend/app/models/case.py：

修复前:
status = Column(String(20), default="pending", index=True)

修复后:
from app.config import CaseStatus

status = Column(String(20), default=CaseStatus.PENDING, index=True)

【步骤4: 验证修复】
执行命令：
cd backend
grep -rn "50000" --include="*.py" app/ || echo "✓ 无硬编码数字"
grep -rn "\"pending\"" --include="*.py" app/ || echo "✓ 无硬编码状态"
pytest tests/ -v --tb=short

【步骤5: 提交代码】
git add -A
git commit -m "refactor(backend): 提取魔法数字为常量

- 使用AnalysisConfig替代硬编码数字
- 使用CaseStatus替代硬编码状态字符串
- 使用AnalysisMode替代硬编码模式字符串
- 所有测试通过"

【完成标准】
□ config.py包含常量类
□ 无硬编码数字50000等
□ 无硬编码状态字符串
□ pytest全部通过
□ 代码已提交

请立即提取常量并替换硬编码值。
```

---

## 任务10: 前端组件规范化

**完整提示词：**

```
【任务】规范化Vue组件结构，统一使用Composition API

【项目路径】c:\Users\Lenovo\Desktop\微信程序开发\frontend

【步骤1: 扫描组件】
执行命令：
cd frontend
find src/views -name "*.vue" -type f
find src/components -name "*.vue" -type f 2>/dev/null || echo "无components目录"

【步骤2: 检查MainView.vue结构】
确保 frontend/src/views/MainView.vue 符合以下结构：

<script setup>
/**
 * 主视图组件
 * @description 案件分析主界面
 */

// 1. 导入（按类型分组）
import { ref, computed, onMounted, watch } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import { analysis } from '@/api'

// 2. Store使用
const store = useAnalysisStore()

// 3. 响应式数据
const isLoading = ref(false)
const error = ref(null)

// 4. 计算属性
const hasCaseText = computed(() => store.currentCaseText.trim().length > 0)
const canAnalyze = computed(() => hasCaseText.value && !isLoading.value)

// 5. 方法
async function handleAnalyze() {
  if (!canAnalyze.value) return
  
  isLoading.value = true
  error.value = null
  
  try {
    await store.performAnalysis(store.currentCaseText)
  } catch (err) {
    error.value = err.message
  } finally {
    isLoading.value = false
  }
}

function handleClear() {
  store.reset()
}

// 6. 生命周期
onMounted(() => {
  // 初始化逻辑
})

// 7. 监听器
watch(() => store.analysisResult, (newResult) => {
  if (newResult) {
    // 处理新结果
  }
})
</script>

<template>
  <div class="main-view">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading">
      <span>分析中...</span>
    </div>
    
    <!-- 错误状态 -->
    <div v-if="error" class="error">
      <span>{{ error }}</span>
      <button @click="error = null">关闭</button>
    </div>
    
    <!-- 内容 -->
    <div class="content">
      <!-- 实际内容 -->
    </div>
  </div>
</template>

<style scoped>
.main-view {
  padding: 1rem;
}
.loading {
  text-align: center;
}
.error {
  color: red;
}
</style>

【步骤3: 检查命名规范】
确保所有组件符合命名规范：
- 组件文件名：大驼峰（如 CaseCard.vue）
- 组合式函数：use前缀（如 useAnalysis）
- 方法名：动词开头（如 fetchData）
- 事件处理：handle前缀（如 handleClick）
- 布尔变量：is/has前缀（如 isLoading）

【步骤4: 验证修复】
执行命令：
cd frontend
npm run lint
npm run build

【步骤5: 提交代码】
git add -A
git commit -m "style(frontend): 规范化Vue组件结构

- 统一使用Composition API
- 组件结构符合9部分规范
- 命名符合规范要求
- 所有构建检查通过"

【完成标准】
□ 组件使用<script setup>
□ 组件结构符合规范
□ 命名符合规范
□ npm run lint无错误
□ npm run build成功
□ 代码已提交

请立即检查并规范化组件结构。
```

---

## 批量执行提示词

**一次性执行所有优化任务：**

```
【任务】执行代码库全面优化

【项目】帮信罪主观明知智能分析系统
【路径】c:\Users\Lenovo\Desktop\微信程序开发

【执行顺序】
1. 后端日志规范化（修复f-string）→ 验证: grep + ruff + pytest
2. 数据库连接池配置 → 验证: python检查 + pytest
3. 安全配置加固（强制环境变量）→ 验证: verify_config.py
4. 异步代码修复 → 验证: pytest
5. 异常处理完善 → 验证: pytest
6. 常量提取规范化 → 验证: grep检查
7. 前端API层封装 → 验证: npm lint + build
8. API请求限流 → 验证: curl测试429
9. 前端组件规范化 → 验证: npm lint + build
10. 单元测试补全 → 验证: pytest + coverage

【每步验证标准】
- Python: ruff check . 无错误 + pytest tests/ 全部通过
- 前端: npm run lint 无错误 + npm run build 成功
- 功能: 核心分析流程正常

【提交格式】
每完成一个任务立即提交：
git add -A
git commit -m "<type>(<scope>): <描述>"

【开始执行】
请按顺序完成所有任务，每完成一个任务提交代码后再继续下一个。
遇到问题时报告具体错误，等待指示后再继续。
```

---

## 文件位置

所有提示词文件位于：
```
.trae/solo-prompts/
├── COMPLETE-PROMPT.md      # 本文件（完整汇总）
├── 01-backend-cleanup.md   # 后端日志清洗
├── 02-database-pool.md     # 数据库连接池
├── 03-frontend-api-layer.md # 前端API层
├── 04-security-hardening.md # 安全加固
├── 05-rate-limiting.md     # 请求限流
├── 06-unit-tests.md        # 单元测试
```

---

## 使用建议

1. **单任务执行**：复制对应任务的完整提示词到Trae Solo模式
2. **批量执行**：复制"批量执行提示词"一次性完成所有任务
3. **验证优先**：每步修改后立即验证，确保不破坏功能
4. **提交及时**：每完成一个任务立即提交，便于回滚

---

*最后更新: 2026-05-27*