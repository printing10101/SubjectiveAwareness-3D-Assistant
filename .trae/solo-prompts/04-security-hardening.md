# Trae Solo 提示词 - 安全加固

## 任务目标
修复安全配置问题，强制环境变量读取敏感配置，移除硬编码默认值。

## 执行步骤

### 步骤1: 扫描硬编码敏感信息
```bash
cd backend

# 扫描密码、密钥等敏感信息
grep -r "password.*=" --include="*.py" . | grep -v "^.*:.*#"
grep -r "secret.*=" --include="*.py" . | grep -v "^.*:.*#"
grep -r "key.*=" --include="*.py" . | grep -v "^.*:.*#"

# 特别关注config.py
head -50 app/config.py
```

### 步骤2: 修改配置类强制环境变量
编辑 `backend/app/config.py`：

```python
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
        return v


@lru_cache
def get_settings() -> Settings:
    """获取配置实例（缓存）."""
    try:
        return Settings()
    except ValidationError as e:
        # 启动时验证失败，打印友好错误
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

    # 密码哈希算法
    PWD_HASH_ALGORITHM = "bcrypt"
    # 密码最小长度
    MIN_PASSWORD_LENGTH = 8
    # 最大登录失败次数
    MAX_LOGIN_ATTEMPTS = 5
    # 登录锁定时间(分钟)
    LOGIN_LOCKOUT_MINUTES = 30


# --- 分析配置常量 ---
class AnalysisConfig:
    """分析配置常量."""

    # 案件文本最小长度
    MIN_CASE_TEXT_LENGTH = 10
    # 案件文本最大长度
    MAX_CASE_TEXT_LENGTH = 50000
    # 分析超时时间(秒)
    ANALYSIS_TIMEOUT = 60
    # 最大重试次数
    MAX_RETRY_COUNT = 3
    # 缓存TTL(秒)
    CACHE_TTL = 3600
```

### 步骤3: 创建启动检查脚本
创建 `backend/scripts/verify_config.py`：

```python
#!/usr/bin/env python3
"""配置验证脚本.

启动前检查所有必需配置是否正确设置。
"""

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
        errors.append(f"JWT_SECRET_KEY长度不足(当前{len(settings.JWT_SECRET_KEY)}字符，需要至少32字符)")

    # 检查环境
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
```

### 步骤4: 更新.env.example
创建安全的 `.env.example`：

```bash
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
# 开发环境使用SQLite，生产环境使用PostgreSQL
DATABASE_URL=sqlite:///./app.db

# --- Ollama配置 ---
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:7b

# --- JWT配置（必须设置！） ---
# 生成命令: openssl rand -hex 32
JWT_SECRET_KEY=your-secret-key-here-change-this-in-production

# --- CORS配置 ---
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### 步骤5: 修改启动流程
更新 `backend/run.py` 添加配置检查：

```python
#!/usr/bin/env python3
"""应用启动脚本."""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 先验证配置
from scripts.verify_config import verify_security_config

if not verify_security_config():
    sys.exit(1)

# 再启动应用
import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
    )
```

### 步骤6: 验证安全配置
```bash
cd backend

# 1. 测试缺少JWT密钥时启动失败
unset JWT_SECRET_KEY
python scripts/verify_config.py  # 应该失败

# 2. 测试弱密钥检测
JWT_SECRET_KEY="short" python scripts/verify_config.py  # 应该失败

# 3. 测试正确配置
export JWT_SECRET_KEY=$(openssl rand -hex 32)
python scripts/verify_config.py  # 应该成功

# 4. 测试应用启动
python run.py &
sleep 3
curl http://localhost:8000/api/health
kill %1
```

### 步骤7: 提交代码
```bash
git add -A
git commit -m "security(backend): 强制环境变量读取敏感配置

- 移除所有硬编码的敏感默认值
- JWT_SECRET_KEY必须设置，无默认值
- 添加配置验证脚本
- 启动时强制检查安全配置
- 更新.env.example添加安全说明
- 所有安全检查通过"
```

## 完成标准
- [ ] `config.py` 敏感配置无默认值
- [ ] `verify_config.py` 验证脚本可运行
- [ ] 缺少JWT密钥时启动失败
- [ ] 弱JWT密钥被检测并拒绝
- [ ] `.env.example` 包含安全说明
- [ ] `run.py` 启动前验证配置
- [ ] 代码已提交

## 验证命令
```bash
cd backend

# 测试配置验证
python scripts/verify_config.py

# 测试应用启动
python run.py
```
