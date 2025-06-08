# app/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # Application settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    PROJECT_NAME: str = "lib.ai"
    VERSION: str = "1.0.0"

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

    # Email settings
    SMTP_HOST: str = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@library.example.com")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "Library Management System")

    # Scheduler settings
    SCHEDULER_INTERVAL_HOURS: int = int(os.getenv("SCHEDULER_INTERVAL_HOURS", 6))
    DUE_SOON_DAYS: int = int(os.getenv("DUE_SOON_DAYS", 5))

    # CORS settings
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    class Config:
        case_sensitive = True


settings = Settings()
