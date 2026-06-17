from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # Ollama configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "deepseek-r1:7b"
    OLLAMA_UPSTREAM_URL: str = "http://localhost:11434"

    # Server configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./app.db"

    # JWT
    # 开发环境默认值仅为占位符，实际应通过环境变量配置
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Default admin
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"

    # Logging
    LOG_LEVEL: str = "DEBUG"

    # Neo4j (leave empty for in-memory graph)
    NEO4J_URI: Optional[str] = None
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # Inference server
    INFERENCE_HOST: str = "0.0.0.0"
    INFERENCE_PORT: int = 8001

    # CORS 配置
    # 开发环境：逗号分隔的具体域名列表，例如 http://localhost:5173,http://127.0.0.1:5173
    # 生产环境：必须配置为实际的前端域名，严禁使用通配符(*)
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # CORS 允许的 HTTP 方法
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"

    # CORS 允许的请求头
    CORS_ALLOW_HEADERS: str = "Authorization,Content-Type,Accept,X-Requested-With"

    # 运行环境标识：development | production
    APP_ENV: str = "development"

    # Parsed CORS origins
    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            if self.APP_ENV == "production":
                raise ValueError(
                    "CORS_ORIGINS 不允许在生产环境使用通配符(*)，"
                    "请明确指定允许的前端域名列表。"
                )
            return ["*"]
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]

    # Parsed CORS methods
    @property
    def cors_methods_list(self) -> List[str]:
        return [m.strip() for m in self.CORS_ALLOW_METHODS.split(",") if m.strip()]

    # Parsed CORS headers
    @property
    def cors_headers_list(self) -> List[str]:
        return [h.strip() for h in self.CORS_ALLOW_HEADERS.split(",") if h.strip()]

    model_config = {"env_file": ".env", "case_sensitive": True}

    def validate_jwt_security(self) -> None:
        """验证 JWT 密钥安全配置

        生产环境下必须正确配置 JWT_SECRET_KEY 环境变量，
        未配置或使用默认占位符将阻止应用启动。
        """
        default_placeholder = "change-this-to-a-secure-random-secret-key-in-production"
        jwt_key = self.JWT_SECRET_KEY

        if not jwt_key or jwt_key == default_placeholder:
            if self.APP_ENV == "production":
                raise RuntimeError(
                    "安全错误: 生产环境下必须配置 JWT_SECRET_KEY 环境变量。\n"
                    "请使用以下命令生成安全密钥:\n"
                    "  python scripts/generate_jwt_secret.py\n"
                    "并将生成的密钥添加到环境变量或 .env 文件中。"
                )
            else:
                # 开发环境如果未配置，使用占位符保证能运行
                if not jwt_key:
                    self.JWT_SECRET_KEY = default_placeholder
                import warnings

                warnings.warn(
                    "安全警告: JWT_SECRET_KEY 未配置或使用默认占位符。\n"
                    "开发环境可以继续使用占位符，但生产环境必须更换为安全随机密钥。\n"
                    "生成命令: python scripts/generate_jwt_secret.py"
                )


settings = Settings()
