"""
Configuration with Vertex AI and Internal Security
"""
import os
from typing import List, Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings - Internal network only"""
    
    # Application
    APP_NAME: str = "AWS Cost AI Agent"
    VERSION: str = "3.2.0"
    ENVIRONMENT: str = "production"
    
    # Server - INTERNAL ONLY
    HOST: str = "127.0.0.1"  # Changed from 0.0.0.0 to localhost only
    PORT: int = 8000
    WORKERS: int = 4
    UNIX_SOCKET: Optional[str] = None  # "/var/run/aws-cost-agent.sock"
    
    # Security - API Key still needed for internal auth
    AGENT_API_KEY: str = ""
    DISABLE_AUTH: bool = False
    
    # CORS - Internal IPs only
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    ALLOWED_INTERNAL_IPS: List[str] = ["127.0.0.1", "::1", "10.0.0.0/8", "172.16.0.0/12"]
    
    # AWS
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "aws-cost-agent-data"
    USE_SECRETS_MANAGER: bool = True  # Load secrets from AWS Secrets Manager
    SECRETS_MANAGER_SECRET_NAME: str = "aws-cost-agent/secrets"
    
    # Google Cloud - Vertex AI (Service Account Auth)
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = "us-central1"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""  # Path to service account JSON
    VERTEX_AI_MODEL: str = "gemini-1.5-flash"
    
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
    LOG_FILE: str = "/var/log/aws-cost-agent/app.log"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    def get_admin_emails(self) -> List[str]:
        return [e.strip() for e in self.ADMIN_EMAILS.split(",") if e.strip()]

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
