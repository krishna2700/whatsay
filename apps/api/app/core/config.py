from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "WhatSay API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_SECRET: str = "whatsay_super_secret_jwt_key_2024_production_ready"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/whatsay"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://whatsay.ai",
    ]

    # AI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MAX_TOKENS: int = 3000
    OPENAI_TEMPERATURE: float = 0.3

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    DEFAULT_AI_PROVIDER: str = "openai"

    # Amazon Affiliate
    AMAZON_AFFILIATE_TAG: str = "whatsay-21"
    AMAZON_BASE_URL: str = "https://www.amazon.in"

    # Amazon PA-API (Product Advertising API) — get from Amazon Associates
    # https://affiliate-program.amazon.in/ → Tools → Product Advertising API
    AMAZON_ACCESS_KEY: Optional[str] = None
    AMAZON_SECRET_KEY: Optional[str] = None

    # SerpAPI — Real Amazon India product search (immediate, no Associates needed)
    # Sign up: https://serpapi.com | Free: 100 searches/month
    SERPAPI_KEY: Optional[str] = None

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # GitHub OAuth
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    POSTHOG_KEY: Optional[str] = None

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 30

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def async_database_url(self) -> str:
        """Return async-compatible database URL."""
        url = self.DATABASE_URL
        # Handle Neon PostgreSQL SSL
        if "neon.tech" in url:
            # asyncpg uses ssl=require differently
            url = url.replace("?sslmode=require&channel_binding=require", "")
            url = url.replace("?sslmode=require", "")
            if "postgresql://" in url and "postgresql+asyncpg://" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://")
        return url


settings = Settings()
