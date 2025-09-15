from pydantic import BaseSettings, PostgresDsn, validator, AnyHttpUrl
from typing import List, Optional, Dict, Any, Union
import logging
import os
from pathlib import Path


class Settings(BaseSettings):
    # API settings
    API_TITLE: str = "Zoom Platform Microservice"
    API_DESCRIPTION: str = "Microservice for Zoom platform integration"
    API_VERSION: str = "0.1.0"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    
    # Base settings
    ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "development_secret_key"
    
    # Database settings
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: str = "5432"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_NAME: str = "zoom_platform"
    
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None
    
    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("DATABASE_USER"),
            password=values.get("DATABASE_PASSWORD"),
            host=values.get("DATABASE_HOST"),
            port=values.get("DATABASE_PORT"),
            path=f"/{values.get('DATABASE_NAME') or ''}",
        )
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # API Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_SECOND: int = 10
    
    # Logging settings
    LOG_LEVEL: int = logging.INFO
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # JWT settings
    JWT_SECRET_KEY: str = "jwt_secret_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Zoom API settings
    ZOOM_API_KEY: str = ""
    ZOOM_API_SECRET: str = ""
    ZOOM_API_BASE_URL: str = "https://api.zoom.us/v2"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Ensure settings are loaded correctly
if settings.ENV == "production" and settings.DEBUG:
    import warnings
    warnings.warn("Debug mode is enabled in production environment")