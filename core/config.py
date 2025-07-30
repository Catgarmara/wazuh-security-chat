"""
Configuration management system with environment variables and settings validation.
"""
import os
from typing import Optional, List
from pydantic import validator, Field
from pydantic_settings import BaseSettings
from enum import Enum


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    name: str = Field(default="wazuh_chat", env="DB_NAME")
    user: str = Field(default="postgres", env="DB_USER")
    password: str = Field(default="", env="DB_PASSWORD")
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    
    @validator("port")
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Database port must be between 1 and 65535")
        return v
    
    @property
    def url(self) -> str:
        """Generate database URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    db: int = Field(default=0, env="REDIS_DB")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    
    @validator("port")
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Redis port must be between 1 and 65535")
        return v
    
    @validator("db")
    def validate_db(cls, v):
        if not 0 <= v <= 15:
            raise ValueError("Redis DB must be between 0 and 15")
        return v
    
    @property
    def url(self) -> str:
        """Generate Redis URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    secret_key: str = Field(env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    bcrypt_rounds: int = Field(default=12, env="BCRYPT_ROUNDS")
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v
    
    @validator("access_token_expire_minutes")
    def validate_access_token_expire(cls, v):
        if not 1 <= v <= 1440:  # 1 minute to 24 hours
            raise ValueError("Access token expiry must be between 1 and 1440 minutes")
        return v
    
    @validator("bcrypt_rounds")
    def validate_bcrypt_rounds(cls, v):
        if not 4 <= v <= 20:
            raise ValueError("Bcrypt rounds must be between 4 and 20")
        return v


class AISettings(BaseSettings):
    """AI/ML configuration settings."""
    
    ollama_host: str = Field(default="localhost", env="OLLAMA_HOST")
    ollama_port: int = Field(default=11434, env="OLLAMA_PORT")
    ollama_model: str = Field(default="llama3", env="OLLAMA_MODEL")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    chunk_size: int = Field(default=500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    max_tokens: int = Field(default=2048, env="MAX_TOKENS")
    temperature: float = Field(default=0.7, env="TEMPERATURE")
    
    @validator("ollama_port")
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Ollama port must be between 1 and 65535")
        return v
    
    @validator("chunk_size")
    def validate_chunk_size(cls, v):
        if not 100 <= v <= 2000:
            raise ValueError("Chunk size must be between 100 and 2000")
        return v
    
    @validator("temperature")
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v
    
    @property
    def ollama_url(self) -> str:
        """Generate Ollama URL."""
        return f"http://{self.ollama_host}:{self.ollama_port}"


class LogSettings(BaseSettings):
    """Log processing configuration settings."""
    
    wazuh_logs_path: str = Field(default="/var/ossec/logs/archives", env="WAZUH_LOGS_PATH")
    default_days_range: int = Field(default=7, env="DEFAULT_DAYS_RANGE")
    max_days_range: int = Field(default=365, env="MAX_DAYS_RANGE")
    ssh_timeout: int = Field(default=10, env="SSH_TIMEOUT")
    log_batch_size: int = Field(default=1000, env="LOG_BATCH_SIZE")
    
    @validator("default_days_range")
    def validate_default_days(cls, v):
        if not 1 <= v <= 365:
            raise ValueError("Default days range must be between 1 and 365")
        return v
    
    @validator("max_days_range")
    def validate_max_days(cls, v):
        if not 1 <= v <= 365:
            raise ValueError("Max days range must be between 1 and 365")
        return v


class AppSettings(BaseSettings):
    """Main application configuration settings."""
    
    app_name: str = Field(default="Wazuh AI Companion", env="APP_NAME")
    version: str = Field(default="2.0.0", env="APP_VERSION")
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    
    # Sub-configurations
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    ai: AISettings = Field(default_factory=AISettings)
    logs: LogSettings = Field(default_factory=LogSettings)
    
    @validator("port")
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Application port must be between 1 and 65535")
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings = None


def get_settings() -> AppSettings:
    """Get application settings instance."""
    global _settings
    if _settings is None:
        try:
            _settings = AppSettings()
        except Exception:
            # For testing purposes, create settings with minimal required fields
            import os
            os.environ.setdefault("SECRET_KEY", "test_secret_key_for_development_only_32_chars_minimum")
            _settings = AppSettings()
    return _settings