from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(default="AI COO", alias="APP_NAME")
    env: str = Field(default="development", alias="ENV")
    secret_key: str = Field(..., alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=14, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    rate_limit_per_minute: int = Field(default=20, alias="RATE_LIMIT_PER_MINUTE")
    csv_max_bytes: int = Field(default=5 * 1024 * 1024, alias="CSV_MAX_BYTES")
    analytics_summary_cache_ttl_seconds: int = Field(default=5, alias="ANALYTICS_SUMMARY_CACHE_TTL_SECONDS")
    alerts_cache_ttl_seconds: int = Field(default=5, alias="ALERTS_CACHE_TTL_SECONDS")
    transactions_cache_ttl_seconds: int = Field(default=5, alias="TRANSACTIONS_CACHE_TTL_SECONDS")
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=0, alias="DB_MAX_OVERFLOW")
    db_pool_timeout_seconds: int = Field(default=30, alias="DB_POOL_TIMEOUT_SECONDS")
    db_pool_recycle_seconds: int = Field(default=1800, alias="DB_POOL_RECYCLE_SECONDS")
    api_db_pool_size: int | None = Field(default=None, alias="API_DB_POOL_SIZE")
    api_db_max_overflow: int | None = Field(default=None, alias="API_DB_MAX_OVERFLOW")
    api_db_pool_timeout_seconds: int | None = Field(default=None, alias="API_DB_POOL_TIMEOUT_SECONDS")
    api_db_pool_recycle_seconds: int | None = Field(default=None, alias="API_DB_POOL_RECYCLE_SECONDS")
    worker_db_pool_size: int | None = Field(default=None, alias="WORKER_DB_POOL_SIZE")
    worker_db_max_overflow: int | None = Field(default=None, alias="WORKER_DB_MAX_OVERFLOW")
    worker_db_pool_timeout_seconds: int | None = Field(default=None, alias="WORKER_DB_POOL_TIMEOUT_SECONDS")
    worker_db_pool_recycle_seconds: int | None = Field(default=None, alias="WORKER_DB_POOL_RECYCLE_SECONDS")

    minio_endpoint: str = Field(default="minio:9000", alias="MINIO_ENDPOINT")
    minio_public_base_url: str = Field(default="", alias="MINIO_PUBLIC_BASE_URL")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="reports", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    smtp_host: str = Field(default="localhost", alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    email_dry_run: bool = Field(default=True, alias="EMAIL_DRY_RUN")

    ai_provider: str = Field(default="stub", alias="AI_PROVIDER")
    ai_openai_api_key: str = Field(default="", alias="AI_OPENAI_API_KEY")
    ai_openai_model: str = Field(default="gpt-4o-mini", alias="AI_OPENAI_MODEL")
    ai_openai_base_url: str = Field(default="https://api.openai.com/v1", alias="AI_OPENAI_BASE_URL")
    ai_timeout_seconds: int = Field(default=20, alias="AI_TIMEOUT_SECONDS")

    auth_cookie_mode: bool = Field(default=False, alias="AUTH_COOKIE_MODE")
    auth_cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    auth_cookie_samesite: str = Field(default="lax", alias="COOKIE_SAMESITE")
    access_cookie_name: str = Field(default="ai_coo_access_token", alias="ACCESS_COOKIE_NAME")
    refresh_cookie_name: str = Field(default="ai_coo_refresh_token", alias="REFRESH_COOKIE_NAME")
    csrf_cookie_name: str = Field(default="ai_coo_csrf_token", alias="CSRF_COOKIE_NAME")
    csrf_header_name: str = Field(default="X-CSRF-Token", alias="CSRF_HEADER_NAME")
    expose_invite_token_in_response: bool = Field(default=True, alias="EXPOSE_INVITE_TOKEN_IN_RESPONSE")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = Field(default=0.0, alias="SENTRY_TRACES_SAMPLE_RATE")
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_publishable_key: str = Field(default="", alias="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")


@lru_cache
def get_settings() -> Settings:
    return Settings()
