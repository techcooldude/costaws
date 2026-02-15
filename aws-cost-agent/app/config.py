"""Configuration management with environment-based settings."""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AWS Cost AI Agent"
    VERSION: str = "4.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Security
    AGENT_API_KEY: str = ""
    SECRET_KEY: str = ""
    DISABLE_AUTH: bool = False
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["*"]

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "aws-cost-agent-data"
    USE_AWS_SECRETS_MANAGER: bool = False

    # AI/LLM
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Datadog
    DATADOG_API_KEY: str = ""
    DATADOG_APP_KEY: str = ""
    DATADOG_SITE: str = "datadoghq.com"

    # SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SENDER_EMAIL: str = ""

    # Scheduler
    SCHEDULE_DAY: str = "monday"
    SCHEDULE_HOUR: int = 9
    ANOMALY_THRESHOLD: float = 20.0
    ADMIN_EMAILS: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "text"
    LOG_FILE: str = "/var/log/aws-cost-agent/app.log"

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_CALLS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # Retry
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 2.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_admin_emails(self) -> List[str]:
        if not self.ADMIN_EMAILS:
            return []
        return [e.strip() for e in self.ADMIN_EMAILS.split(",") if e.strip()]

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
