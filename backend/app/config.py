from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "PropIQ"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host:5432/dbname

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Anthropic (Claude)
    ANTHROPIC_API_KEY: str = ""

    # RERA
    RERA_BASE_URL: str = "https://rera.gov.in"

    # MCA21
    MCA_BASE_URL: str = "https://www.mca.gov.in"

    # News APIs
    NEWSAPI_KEY: str = ""
    GNEWS_API_KEY: str = ""

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM: str = "noreply@propiq.in"

    # Storage (S3-compatible)
    S3_ENDPOINT: str = ""
    S3_BUCKET: str = "propiq-reports"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Scraper settings
    SCRAPER_REQUEST_DELAY_SECONDS: float = 2.0
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_TIMEOUT_SECONDS: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
