"""config - 系统模块.

本模块为帮信罪主观明知智能分析系统的组成部分。
提供系统运行所需的核心功能和基础支持。

模块功能：
    - 实现特定的业务功能或技术支持
    - 与其他模块协作完成系统任务
    - 提供可复用的接口和工具方法
    - 确保系统稳定性和可维护性

技术栈：Python 3.10+, FastAPI, SQLAlchemy
项目版本：V1.0.0

# 应用装饰器: author 帮信罪智能分析系统开发团队
@author 帮信罪智能分析系统开发团队
# 应用装饰器: version 1.0.0
@version 1.0.0
"""

# 导入模块: from pathlib
from pathlib import Path

# 导入模块: logging
import logging
# 导入模块: os
import os
# 导入模块: secrets
import secrets
# 导入模块: warnings
import warnings

# 导入模块: from pydantic
from pydantic import model_validator
# 导入模块: from pydantic_settings
from pydantic_settings import BaseSettings


# 初始化变量 logger
logger = logging.getLogger(__name__)

_MIN_ENCRYPTION_KEY_LENGTH = 32
_MIN_PASSWORD_LENGTH = 10


# 定义 AnalysisConfig 类
class AnalysisConfig:
    """分析相关常量配置，统一管理所有硬编码数值.

    将所有分散在代码中的魔法数字集中到此类中，便于维护和调整。

    Attributes:
        MIN_CASE_LENGTH: 案件事实文本最小长度
        MAX_TITLE_LENGTH: 案件标题最大长度
        MAX_CASE_TEXT_LENGTH: 案件文本最大长度（API 层面）
        OLLAMA_CHECK_TIMEOUT: Ollama 启动检查超时（秒）
        HEALTH_CHECK_TIMEOUT: 健康检查超时（秒）
        DEFAULT_TIMEOUT: 默认超时（秒）
        CACHE_TTL_SECONDS: 缓存过期时间（秒）
        MAX_CACHE_ENTRIES: 缓存最大条目数
        BCRYPT_ROUNDS: bcrypt 哈希轮数
        MAX_FILE_SIZE_BYTES: 文件上传最大字节数
        MAX_UPLOAD_CONTENT_PREVIEW: 上传内容预览最大字符数
    """

    # 案件文本约束
    MIN_CASE_LENGTH: int = 10
    MIN_CASE_TEXT_LENGTH: int = 10
    MAX_TITLE_LENGTH: int = 50
    MAX_CASE_TEXT_LENGTH: int = 50000

    # HTTP 超时（秒）
    OLLAMA_CHECK_TIMEOUT: float = 10.0
    HEALTH_CHECK_TIMEOUT: float = 5.0

    # 分析默认值
    DEFAULT_TIMEOUT: int = 30

    # 缓存
    CACHE_TTL_SECONDS: int = 3600
    MAX_CACHE_ENTRIES: int = 1000
    # 缓存后端类型: "redis" (推荐生产) | "file" (单机开发/降级方案)
    # - 生产环境强烈推荐使用 redis，支持分布式部署与高并发
    # - 文件缓存仅作为 Redis 不可用时的降级方案或单机开发环境使用
    # 可通过环境变量 CACHE_BACKEND 覆盖
    CACHE_BACKEND: str = os.getenv("CACHE_BACKEND", "redis")
    CACHE_SALT: str = "legal-analysis-v1"
    CACHE_HASH_ALGORITHM: str = "sha256"
    CACHE_HASH_TRUNCATE_LENGTH: int = 16
    # 缓存键前缀 —— 用于在共享 Redis 实例中隔离不同应用/不同环境的缓存数据
    # 推荐格式: "<app-name>:<env>:"  例如 "legal-analysis:prod:"
    # 在 Redis 中，存储的实际 key 形如: "legal-analysis:prod:a1b2c3d4..."
    CACHE_KEY_PREFIX: str = os.getenv("CACHE_KEY_PREFIX", "legal-analysis:dev:")

    # Redis 连接
    # Redis 服务连接 URL，格式: redis://[user:password@]host:port/db
    # - 本地开发: redis://localhost:6379/0
    # - Docker 容器内: redis://redis:6379/0 (使用服务名)
    # - 生产环境: redis://:<password>@<host>:6379/0
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Redis 连接池最大连接数，控制并发访问上限
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
    # 操作失败时的最大重试次数（连接超时/断连时）
    REDIS_RETRY_MAX_ATTEMPTS: int = int(os.getenv("REDIS_RETRY_MAX_ATTEMPTS", "3"))
    # 重试之间的间隔（秒）
    REDIS_RETRY_DELAY: float = float(os.getenv("REDIS_RETRY_DELAY", "0.5"))
    # Socket 读写操作超时（秒）
    REDIS_SOCKET_TIMEOUT: float = float(os.getenv("REDIS_SOCKET_TIMEOUT", "5.0"))
    # Socket 连接建立超时（秒）
    REDIS_SOCKET_CONNECT_TIMEOUT: float = float(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "2.0"))

    # 安全
    BCRYPT_ROUNDS: int = 12
    JWT_ALGORITHM: str = "HS256"
    ENCRYPTION_KEY_MIN_LENGTH: int = 32
    JWT_KEY_ROTATION_DAYS: int = 90
    JWT_KEY_GRACE_PERIOD_DAYS: int = 7
    JWT_KEY_CURRENT_VERSION: int = 1

    # 限流默认配置
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_ANALYZE_ANONYMOUS: str = "5/minute"
    RATE_LIMIT_ANALYZE_USER: str = "10/minute"
    RATE_LIMIT_ANALYZE_ADMIN: str = "30/minute"
    RATE_LIMIT_AUTH: str = "20/minute"
    RATE_LIMIT_GLOBAL: str = "200/minute"

    # 文件上传
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB
    MAX_UPLOAD_CONTENT_PREVIEW: int = 5000

    # 允许的上传文件 MIME 类型
    ALLOWED_UPLOAD_CONTENT_TYPES: frozenset[str] = frozenset(
        {
            "application/pdf",
            "application/msword",
            "application/"
            "vnd.openxmlformats-officedocument."
            "wordprocessingml.document",
            "text/plain",
            "image/jpeg",
            "image/png",
        }
    )

    # 复杂度分类阈值（基于字符数的旧版阈值，保留向后兼容）
    COMPLEXITY_SIMPLE_THRESHOLD: int = 200
    COMPLEXITY_MEDIUM_THRESHOLD: int = 800

    # 复杂度评估 — 多维度分析因子权重
    COMPLEXITY_WEIGHT_KEYWORD: float = 1.5
    COMPLEXITY_WEIGHT_SENTENCE: float = 2.0
    COMPLEXITY_WEIGHT_EVIDENCE: float = 3.5
    COMPLEXITY_WEIGHT_PEOPLE: float = 3.0

    # 复杂度评估 — 综合评分分类阈值
    COMPLEXITY_COMPOSITE_SIMPLE_MAX: float = 30.0
    COMPLEXITY_COMPOSITE_MEDIUM_MAX: float = 60.0

    # Ollama 调用参数（模型推理相关，不随环境变化）
    OLLAMA_NUM_CTX: int = 8192
    OLLAMA_DEFAULT_TEMPERATURE: float = 0.2
    OLLAMA_TOP_P: float = 0.9
    OLLAMA_NUM_PREDICT: int = 4096
    OLLAMA_REPEAT_PENALTY: float = 1.15
    OLLAMA_PIPELINE_TIMEOUT: float = 60.0
    INFERENCE_PROXY_TIMEOUT: float = 120.0

    # Self-Consistency 多次采样配置
    SC_ENABLED: bool = True              # 是否启用多次采样
    SC_NUM_SAMPLES: int = 3              # 采样次数
    SC_TEMPERATURE: float = 0.5          # 采样温度（高于默认值以引入多样性）
    SC_MIN_AGREEMENT: float = 0.6        # 最低一致性阈值（低于此值标记为"低置信度"）

    # 默认评分
    DEFAULT_DIMENSION_SCORE: float = 5.0
    DEFAULT_REASONING: str = "自动分析结果"

    # tenacity 重试配置
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_WAIT_MIN: float = 4.0
    RETRY_WAIT_MAX: float = 10.0
    RETRY_WAIT_MULTIPLIER: float = 1.0

    # ------------------------------------------------------------------
    # 知识库内容约束
    # ------------------------------------------------------------------

    # 知识库条目标题最大长度限制
    MAX_ENTRY_TITLE_LENGTH: int = 255

    # 知识库条目内容最大长度限制
    MAX_ENTRY_CONTENT_LENGTH: int = 100000

    # 单一条目允许关联的最大标签数量
    MAX_TAGS_PER_ENTRY: int = 10

    # 知识库搜索结果分页大小
    SEARCH_RESULT_LIMIT: int = 20

    # 知识衰减检查间隔（天）
    DECAY_CHECK_INTERVAL_DAYS: int = 30

    # 知识陈旧置信度阈值
    STALE_CONFIDENCE_THRESHOLD: float = 0.3

    # ------------------------------------------------------------------
    # 知识生命周期管理
    # ------------------------------------------------------------------

    # 衰减系数 — 控制知识信心评分的每日衰减速度
    # 值越大衰减越快，推荐范围 0.01 ~ 0.05
    KNOWLEDGE_DECAY_COEFFICIENT: float = 0.02

    # 陈旧阈值 — 当confidence低于此值时自动标记为stale
    KNOWLEDGE_STALE_CONFIDENCE_THRESHOLD: float = 0.3

    # 内容过时阈值 — last_verified_at 超过此天数标记为过时
    KNOWLEDGE_OUTDATED_DAYS_THRESHOLD: int = 90

    # 正反馈步长 — 用户正反馈时confidence增量
    KNOWLEDGE_POSITIVE_FEEDBACK_STEP: float = 0.05

    # 负反馈步长 — 用户负反馈时confidence减量
    KNOWLEDGE_NEGATIVE_FEEDBACK_STEP: float = 0.1

    # 矛盾检测最低信心 — 仅检测confidence高于此值的条目
    KNOWLEDGE_CONTRADICTION_MIN_CONFIDENCE: float = 0.7

    # 分批处理大小 — 大数据量时的批处理条数
    KNOWLEDGE_BATCH_SIZE: int = 500

    # 定时任务 — apply_decay 默认执行间隔（秒）
    KNOWLEDGE_DECAY_SCHEDULE_INTERVAL: int = 86400  # 24小时

    # 定时任务 — lint_knowledge_base 默认执行间隔（秒）
    KNOWLEDGE_LINT_SCHEDULE_INTERVAL: int = 604800  # 7天


# 定义 Settings 类
class Settings(BaseSettings):
    """Application settings loaded from environment and .env file."""

    # Ollama configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "deepseek-r1:7b"
    OLLAMA_UPSTREAM_URL: str = "http://localhost:11434"
    OLLAMA_ENABLED: bool = False  # V1专业版默认使用 DeepSeek 云端/规则化兜底，不启动本地推理引擎

    # DeepSeek API configuration
    DEEPSEEK_API_KEY: str = ""  # DeepSeek API 密钥，从 https://platform.deepseek.com/ 获取
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_TEMPERATURE: float = 0.2
    DEEPSEEK_TIMEOUT: float = 120.0
    DEEPSEEK_ENABLED: bool = True  # DeepSeek 功能开关，未配置 API Key 时自动降级

    # Server configuration
    SERVER_HOST: str = "0.0.0.0"  # noqa: S104
    SERVER_PORT: int = 8000
    DEBUG: bool = False  # 默认关闭调试模式，生产环境安全

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    ASYNC_DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_PRE_PING: bool = True
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False
    DB_CONNECT_TIMEOUT: int = 10

    # JWT
    # 开发环境默认值仅为占位符，实际应通过环境变量配置
    JWT_SECRET_KEY: str | None = None
    JWT_SECRET_KEY_PREVIOUS: str | None = None
    JWT_KEY_VERSION: int = 1
    JWT_KEY_CREATED_AT: str = ""
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Default admin
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = ""  # 生产环境必须通过环境变量配置，空值会在启动时生成随机密码

    # Data encryption
    ENCRYPTION_KEY: str | None = None
    ENCRYPTION_KEY_DERIVE: str | None = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    # Neo4j (leave empty for in-memory graph)
    NEO4J_URI: str | None = None
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # 缓存后端配置 —— 可通过环境变量覆盖
    # 取值: "redis" (推荐生产) | "file" (单机/降级)
    CACHE_BACKEND: str = "redis"
    # 缓存键前缀，用于隔离不同应用/环境的命名空间
    CACHE_KEY_PREFIX: str = "legal-analysis:dev:"

    # Inference server
    INFERENCE_HOST: str = "0.0.0.0"  # noqa: S104
    INFERENCE_PORT: int = 8001

    # Ollama 客户端连接池（支持 .env 运行时覆盖）
    OLLAMA_MAX_CONNECTIONS: int = 10
    OLLAMA_MAX_KEEPALIVE_CONNECTIONS: int = 5
    OLLAMA_CONNECT_TIMEOUT: float = 5.0
    OLLAMA_KEEPALIVE_EXPIRY: float = 30.0

    # Ollama 限流与队列
    OLLAMA_MAX_CONCURRENT: int = 3
    OLLAMA_QUEUE_MAXSIZE: int = 100
    OLLAMA_RETRY_MAX_ATTEMPTS: int = 2
    OLLAMA_RETRY_DELAY: float = 1.0

    # 动态超时策略
    OLLAMA_TIMEOUT_BASE: float = 60.0
    OLLAMA_TIMEOUT_PER_1000_CHARS: float = 30.0
    OLLAMA_TIMEOUT_MAX: float = 300.0

    # CORS 配置
    # 开发环境：逗号分隔的具体域名列表，例如 http://localhost:5173,http://127.0.0.1:5173
    # 生产环境：必须配置为实际的前端域名，严禁使用通配符(*)
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # CORS 允许的 HTTP 方法
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"

    # CORS 允许的请求头
    CORS_ALLOW_HEADERS: str = (
        "Authorization,Content-Type,Accept,X-Requested-With"
    )

    # 运行环境标识：development | production
    APP_ENV: str = "development"

    # Sentry 错误追踪配置（未配置 DSN 时 Sentry 不启用，应用正常运行）
    # 在 Sentry 平台 -> Project -> Settings -> Client Keys (DSN) 获取
    SENTRY_DSN: str | None = None
    # 区分部署环境的标识：development / staging / production
    SENTRY_ENVIRONMENT: str | None = None
    # 性能追踪采样率，范围 0.0-1.0
    # - 生产环境推荐 0.1-0.2 以控制性能开销
    # - 开发/测试环境可设为 1.0 以捕获所有追踪
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    # 是否在事件中附加堆栈跟踪信息
    SENTRY_ATTACH_STACKTRACE: bool = True
    # Sentry 服务端点（一般无需修改，使用默认 https://sentry.io）
    SENTRY_SEND_DEFAULT_PII: bool = False
    # 发送事件的超时时间（秒）
    SENTRY_TIMEOUT: float = 5.0

    # Parsed CORS origins
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        if self.CORS_ORIGINS == "*":
            if self.APP_ENV == "production":
                msg = (
                    "CORS_ORIGINS 不允许在生产环境使用通配符(*)，"
                    "请明确指定允许的前端域名列表。"
                )
                raise ValueError(msg)
            return ["*"]
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    # Parsed CORS methods
    @property
    def cors_methods_list(self) -> list[str]:
        """Parse CORS_ALLOW_METHODS into a list."""
        return [
            m.strip()
            for m in self.CORS_ALLOW_METHODS.split(",")
            if m.strip()
        ]

    # Parsed CORS headers
    @property
    def cors_headers_list(self) -> list[str]:
        """Parse CORS_ALLOW_HEADERS into a list."""
        return [
            h.strip()
            for h in self.CORS_ALLOW_HEADERS.split(",")
            if h.strip()
        ]

    # 初始化变量 model_config
    model_config = {
        "env_file": str(Path(__file__).parent.parent / ".env"),
        "case_sensitive": True
    }

    # 应用装饰器: model_validator
    @model_validator(mode='after')
    def _validate_security_settings(self) -> "Settings":
        self._validate_jwt()
        self._validate_encryption_key()
        self._validate_admin_password()
        self._validate_debug_mode()
        return self

    def _validate_admin_password(self) -> None:
        """验证默认管理员密码安全性."""
        if not self.DEFAULT_ADMIN_PASSWORD:
            generated_password = secrets.token_urlsafe(16)
            self.DEFAULT_ADMIN_PASSWORD = generated_password
            logger.warning(
                "=" * 60 + "\n"
                "安全警告: 未配置 DEFAULT_ADMIN_PASSWORD，已自动生成随机密码。\n"
                f"生成的管理员密码: {generated_password}\n"
                "请妥善保存此密码，或通过环境变量配置自定义密码。\n"
                + "=" * 60
            )
            return

        weak_passwords = {
            "admin123", "password", "123456", "admin", "root",
            "test", "demo", "default", "changeme", "letmein",
        }
        if self.DEFAULT_ADMIN_PASSWORD.lower() in weak_passwords:
            if self.APP_ENV == "production":
                msg = (
                    "安全错误: DEFAULT_ADMIN_PASSWORD 使用了弱密码 "
                    f"'{self.DEFAULT_ADMIN_PASSWORD}'。\n"
                    "生产环境必须配置强密码（至少16字符，包含大小写字母、数字和特殊字符）。\n"
                    "请通过环境变量配置安全密码。"
                )
                raise RuntimeError(msg)
            warnings.warn(
                f"安全警告: DEFAULT_ADMIN_PASSWORD 使用了弱密码 '{self.DEFAULT_ADMIN_PASSWORD}'。\n"
                "开发环境可以继续使用，但生产环境必须更换为强密码。",
                stacklevel=2,
            )

        if len(self.DEFAULT_ADMIN_PASSWORD) < _MIN_PASSWORD_LENGTH:
            if self.APP_ENV == "production":
                msg = (
                    f"安全错误: DEFAULT_ADMIN_PASSWORD 长度不足 "
                    f"({len(self.DEFAULT_ADMIN_PASSWORD)} 字符)，"
                    f"生产环境密码至少需要 {_MIN_PASSWORD_LENGTH} 个字符。"
                )
                raise RuntimeError(msg)
            warnings.warn(
                f"安全警告: DEFAULT_ADMIN_PASSWORD 长度不足 "
                f"({len(self.DEFAULT_ADMIN_PASSWORD)} 字符)，"
                f"建议使用至少 {_MIN_PASSWORD_LENGTH} 个字符的密码。",
                stacklevel=2,
            )

    def _validate_debug_mode(self) -> None:
        """验证 DEBUG 模式安全性."""
        if self.DEBUG and self.APP_ENV == "production":
            msg = (
                "安全错误: 生产环境不允许开启 DEBUG 模式。\n"
                "DEBUG 模式会禁用限流、暴露详细错误信息，存在严重安全风险。\n"
                "请设置 DEBUG=false 或 APP_ENV=development。"
            )
            raise RuntimeError(msg)

    def _validate_jwt(self) -> None:
        """验证 JWT 密钥安全性."""
        default_placeholder = (
            "change-this-to-a-secure-random-secret-key-in-production"
        )
        jwt_key = self.JWT_SECRET_KEY

        if not jwt_key or jwt_key == default_placeholder:
            if self.APP_ENV == "production":
                msg = (
                    "安全错误: 生产环境下必须配置 JWT_SECRET_KEY 环境变量。\n"
                    "请使用以下命令生成安全密钥:\n"
                    "  python scripts/generate_jwt_secret.py\n"
                    "并将生成的密钥添加到环境变量或 .env 文件中。"
                )
                raise RuntimeError(msg)
            if not jwt_key:
                self.JWT_SECRET_KEY = default_placeholder
            warnings.warn(
                "安全警告: JWT_SECRET_KEY 未配置或使用默认占位符。\n"
                "开发环境可以继续使用占位符，但生产环境必须更换为安全随机密钥。\n"
                "生成命令: python scripts/generate_jwt_secret.py",
                stacklevel=2,
            )

        _MIN_SECRET_KEY_LENGTH = 32
        if self.JWT_KEY_VERSION < 1:
            msg = "JWT密钥版本号无效，必须 >= 1"
            raise RuntimeError(msg)

        if (
            self.JWT_SECRET_KEY_PREVIOUS
            and len(self.JWT_SECRET_KEY_PREVIOUS) < _MIN_SECRET_KEY_LENGTH
        ):
            warnings.warn(
                "安全警告: 前一个 JWT_SECRET_KEY 长度不足 32 字符，可能存在安全风险。",
                stacklevel=2,
            )

    def _validate_encryption_key(self) -> None:
        """验证加密密钥安全性."""
        encryption_key = self.ENCRYPTION_KEY
        derive_key = self.ENCRYPTION_KEY_DERIVE

        if encryption_key:
            if len(encryption_key) < _MIN_ENCRYPTION_KEY_LENGTH:
                msg = (
                    f"安全错误: ENCRYPTION_KEY 长度不足 "
                    f"({len(encryption_key)} 字符)，"
                    f"至少需要 {_MIN_ENCRYPTION_KEY_LENGTH} 个字符 (256位)。"
                )
                logger.error(msg)
                raise RuntimeError(msg)
            logger.info("ENCRYPTION_KEY 已通过安全验证")
            return

        if derive_key:
            if len(derive_key) < _MIN_ENCRYPTION_KEY_LENGTH:
                msg = (
                    f"安全错误: ENCRYPTION_KEY_DERIVE 长度不足 "
                    f"({len(derive_key)} 字符)，"
                    f"至少需要 {_MIN_ENCRYPTION_KEY_LENGTH} 个字符 (256位)。"
                )
                logger.error(msg)
                raise RuntimeError(msg)
            logger.info("ENCRYPTION_KEY_DERIVE 已通过安全验证")
            return

        if self.APP_ENV == "production":
            msg = (
                "安全错误: 生产环境下必须配置 "
                "ENCRYPTION_KEY 环境变量。\n"
                "请使用以下命令生成安全密钥:\n"
                '  python -c "import secrets; '
                'print(secrets.token_urlsafe(32))"\n'
                "或: openssl rand -base64 32\n"
                "并将生成的密钥添加到环境变量或 "
                ".env 文件中。"
            )
            logger.critical(msg)
            raise RuntimeError(msg)

        generated_key = secrets.token_urlsafe(32)
        self.ENCRYPTION_KEY = generated_key
        logger.warning(
            "=" * 60 + "\n"
            "安全警告: 未配置 ENCRYPTION_KEY，已自动生成临时加密密钥。\n"
            "当前密钥仅用于开发环境，严禁在生产环境使用！\n"
            "生成命令: python -c "
            '"import secrets; print(secrets.token_urlsafe(32))"\n'
            + "=" * 60
        )


# 初始化变量 settings
settings = Settings()
