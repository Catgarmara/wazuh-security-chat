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


class EmbeddedAISettings(BaseSettings):
    """Embedded AI configuration settings for security appliance with LlamaCpp integration."""
    
    # Core paths and model management
    models_path: str = Field(default="./models", env="MODELS_PATH")
    vectorstore_path: str = Field(default="./data/vectorstore", env="VECTORSTORE_PATH")
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    max_concurrent_models: int = Field(default=3, env="MAX_CONCURRENT_MODELS")
    conversation_memory_size: int = Field(default=10, env="CONVERSATION_MEMORY_SIZE")
    default_temperature: float = Field(default=0.7, env="DEFAULT_TEMPERATURE")
    default_max_tokens: int = Field(default=1024, env="DEFAULT_MAX_TOKENS")
    chunk_size: int = Field(default=500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    
    # Security appliance specific settings
    enable_model_auto_download: bool = Field(default=True, env="ENABLE_MODEL_AUTO_DOWNLOAD")
    default_security_model: str = Field(default="mistral-7b-instruct-v0.1.Q4_K_M.gguf", env="DEFAULT_SECURITY_MODEL")
    ai_model_cache_size_gb: int = Field(default=8, env="MODEL_CACHE_SIZE_GB")  # Fixed: renamed and adjusted default
    enable_gpu_acceleration: bool = Field(default=True, env="ENABLE_GPU_ACCELERATION")
    max_memory_usage_gb: int = Field(default=8, env="MAX_MEMORY_USAGE_GB")
    ai_model_load_timeout_seconds: int = Field(default=300, env="MODEL_LOAD_TIMEOUT_SECONDS")  # Fixed: renamed
    enable_model_quantization: bool = Field(default=True, env="ENABLE_MODEL_QUANTIZATION")
    
    # Resource management and monitoring
    resource_monitoring_interval: int = Field(default=30, env="RESOURCE_MONITORING_INTERVAL")
    auto_unload_inactive_models: bool = Field(default=True, env="AUTO_UNLOAD_INACTIVE_MODELS")
    ai_model_inactivity_timeout_minutes: int = Field(default=30, env="MODEL_INACTIVITY_TIMEOUT_MINUTES")  # Fixed: renamed
    enable_health_checks: bool = Field(default=True, env="ENABLE_HEALTH_CHECKS")
    health_check_interval_seconds: int = Field(default=60, env="HEALTH_CHECK_INTERVAL_SECONDS")
    
    # LlamaCpp specific settings
    n_gpu_layers: int = Field(default=-1, env="N_GPU_LAYERS")
    n_batch: int = Field(default=512, env="N_BATCH")
    n_ctx: int = Field(default=4096, env="N_CTX")
    use_mmap: bool = Field(default=True, env="USE_MMAP")
    use_mlock: bool = Field(default=False, env="USE_MLOCK")
    top_p: float = Field(default=0.9, env="TOP_P")
    top_k: int = Field(default=40, env="TOP_K")
    repeat_penalty: float = Field(default=1.1, env="REPEAT_PENALTY")
    
    # Security and compliance settings
    enable_audit_logging: bool = Field(default=True, env="ENABLE_AUDIT_LOGGING")
    log_model_interactions: bool = Field(default=True, env="LOG_MODEL_INTERACTIONS")
    enable_conversation_encryption: bool = Field(default=False, env="ENABLE_CONVERSATION_ENCRYPTION")
    max_conversation_history_days: int = Field(default=30, env="MAX_CONVERSATION_HISTORY_DAYS")
    
    class Config:
        protected_namespaces = ('settings_',)  # Fix pydantic warnings
    
    @validator("models_path")
    def validate_models_path(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Models path cannot be empty")
        return v.strip()
    
    @validator("vectorstore_path")
    def validate_vectorstore_path(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Vectorstore path cannot be empty")
        return v.strip()
    
    @validator("embedding_model_name")
    def validate_embedding_model_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Embedding model name cannot be empty")
        return v.strip()
    
    @validator("default_security_model")
    def validate_default_security_model(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Default security model cannot be empty")
        if not v.endswith('.gguf'):
            raise ValueError("Default security model must be a GGUF file (.gguf extension)")
        return v.strip()
    
    @validator("chunk_size")
    def validate_chunk_size(cls, v):
        if not 100 <= v <= 2000:
            raise ValueError("Chunk size must be between 100 and 2000")
        return v
    
    @validator("chunk_overlap")
    def validate_chunk_overlap(cls, v):
        if not 0 <= v <= 500:
            raise ValueError("Chunk overlap must be between 0 and 500")
        return v
    
    @validator("default_temperature")
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v
    
    @validator("default_max_tokens")
    def validate_max_tokens(cls, v):
        if not 1 <= v <= 8192:
            raise ValueError("Max tokens must be between 1 and 8192")
        return v
    
    @validator("max_concurrent_models")
    def validate_max_concurrent_models(cls, v):
        if not 1 <= v <= 10:
            raise ValueError("Max concurrent models must be between 1 and 10")
        return v
    
    @validator("conversation_memory_size")
    def validate_conversation_memory_size(cls, v):
        if not 1 <= v <= 100:
            raise ValueError("Conversation memory size must be between 1 and 100")
        return v
    
    @validator("ai_model_cache_size_gb")
    def validate_ai_model_cache_size_gb(cls, v):
        if not 1 <= v <= 100:
            raise ValueError("AI model cache size must be between 1 and 100 GB")
        return v
    
    @validator("max_memory_usage_gb")
    def validate_max_memory_usage_gb(cls, v):
        if not 1 <= v <= 64:
            raise ValueError("Max memory usage must be between 1 and 64 GB")
        return v
    
    @validator("ai_model_load_timeout_seconds")
    def validate_ai_model_load_timeout_seconds(cls, v):
        if not 30 <= v <= 1800:  # 30 seconds to 30 minutes
            raise ValueError("AI model load timeout must be between 30 and 1800 seconds")
        return v
    
    @validator("resource_monitoring_interval")
    def validate_resource_monitoring_interval(cls, v):
        if not 10 <= v <= 300:  # 10 seconds to 5 minutes
            raise ValueError("Resource monitoring interval must be between 10 and 300 seconds")
        return v
    
    @validator("ai_model_inactivity_timeout_minutes")
    def validate_ai_model_inactivity_timeout_minutes(cls, v):
        if not 5 <= v <= 1440:  # 5 minutes to 24 hours
            raise ValueError("AI model inactivity timeout must be between 5 and 1440 minutes")
        return v
    
    @validator("health_check_interval_seconds")
    def validate_health_check_interval_seconds(cls, v):
        if not 30 <= v <= 600:  # 30 seconds to 10 minutes
            raise ValueError("Health check interval must be between 30 and 600 seconds")
        return v
    
    @validator("max_conversation_history_days")
    def validate_max_conversation_history_days(cls, v):
        if not 1 <= v <= 365:
            raise ValueError("Max conversation history days must be between 1 and 365")
        return v
    
    @validator("n_gpu_layers")
    def validate_n_gpu_layers(cls, v):
        if v < -1:
            raise ValueError("GPU layers must be -1 (auto) or >= 0")
        return v
    
    @validator("n_batch")
    def validate_n_batch(cls, v):
        if not 1 <= v <= 2048:
            raise ValueError("Batch size must be between 1 and 2048")
        return v
    
    @validator("n_ctx")
    def validate_n_ctx(cls, v):
        if not 512 <= v <= 32768:
            raise ValueError("Context size must be between 512 and 32768")
        return v
    
    @validator("top_p")
    def validate_top_p(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Top-p must be between 0.0 and 1.0")
        return v
    
    @validator("top_k")
    def validate_top_k(cls, v):
        if not 1 <= v <= 200:
            raise ValueError("Top-k must be between 1 and 200")
        return v
    
    @validator("repeat_penalty")
    def validate_repeat_penalty(cls, v):
        if not 0.5 <= v <= 2.0:
            raise ValueError("Repeat penalty must be between 0.5 and 2.0")
        return v
    
    def validate_appliance_deployment(self) -> bool:
        """
        Validate security appliance deployment settings for consistency and readiness.
        
        Returns:
            bool: True if all settings are valid for deployment
            
        Raises:
            ValueError: If any deployment settings are invalid or inconsistent
        """
        # Validate memory constraints
        if self.max_memory_usage_gb < 2:
            raise ValueError("Security appliance requires at least 2GB memory allocation")
        
        # Validate model cache vs memory usage
        if self.ai_model_cache_size_gb > self.max_memory_usage_gb:
            raise ValueError("AI model cache size cannot exceed max memory usage")
        
        # Validate concurrent models vs memory
        estimated_memory_per_model = 2  # GB estimate for typical security models
        if (self.max_concurrent_models * estimated_memory_per_model) > self.max_memory_usage_gb:
            raise ValueError(
                f"Max concurrent models ({self.max_concurrent_models}) may exceed "
                f"memory limit ({self.max_memory_usage_gb}GB). Consider reducing concurrent models."
            )
        
        # Validate context size vs batch size
        if self.n_batch > self.n_ctx:
            raise ValueError("Batch size cannot exceed context size")
        
        # Validate chunk overlap vs chunk size
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        
        # Validate timeout settings
        if self.ai_model_inactivity_timeout_minutes < 5:
            raise ValueError("AI model inactivity timeout should be at least 5 minutes for stability")
        
        return True
    
    def get_deployment_summary(self) -> dict:
        """
        Get a summary of key deployment settings for security appliance.
        
        Returns:
            dict: Summary of deployment configuration
        """
        return {
            "models_path": self.models_path,
            "max_memory_gb": self.max_memory_usage_gb,
            "max_concurrent_models": self.max_concurrent_models,
            "gpu_acceleration": self.enable_gpu_acceleration,
            "gpu_layers": self.n_gpu_layers if self.enable_gpu_acceleration else 0,
            "context_size": self.n_ctx,
            "default_model": self.default_security_model,
            "auto_download": self.enable_model_auto_download,
            "health_checks": self.enable_health_checks,
            "audit_logging": self.enable_audit_logging,
            "resource_monitoring": self.resource_monitoring_interval
        }


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
    embedded_ai: EmbeddedAISettings = Field(default_factory=EmbeddedAISettings)
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
    
    def validate_security_appliance_config(self) -> bool:
        """
        Validate the complete security appliance configuration.
        
        Returns:
            bool: True if configuration is valid for security appliance deployment
            
        Raises:
            ValueError: If any configuration is invalid for security appliance
        """
        # Validate embedded AI settings
        if not self.embedded_ai.validate_appliance_deployment():
            return False
        
        # Ensure required security settings are present
        if not self.security.secret_key or len(self.security.secret_key) < 32:
            raise ValueError("Security appliance requires a strong secret key (minimum 32 characters)")
        
        # Validate database configuration for appliance
        if not self.database.host or not self.database.name:
            raise ValueError("Security appliance requires valid database configuration")
        
        # Validate Redis configuration for session management
        if not self.redis.host:
            raise ValueError("Security appliance requires Redis for session management")
        
        # Ensure audit logging is enabled for security appliance
        if not self.embedded_ai.enable_audit_logging:
            raise ValueError("Security appliance must have audit logging enabled")
        
        return True
    
    def get_appliance_status(self) -> dict:
        """
        Get security appliance configuration status.
        
        Returns:
            dict: Appliance configuration status and summary
        """
        return {
            "app_name": self.app_name,
            "version": self.version,
            "environment": self.environment.value,
            "embedded_ai": self.embedded_ai.get_deployment_summary(),
            "security_enabled": bool(self.security.secret_key),
            "database_configured": bool(self.database.host and self.database.name),
            "redis_configured": bool(self.redis.host),
            "debug_mode": self.debug
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings = None


def get_settings() -> AppSettings:
    """Get application settings instance with security appliance validation."""
    global _settings
    if _settings is None:
        try:
            _settings = AppSettings()
            # Validate security appliance configuration in production
            if _settings.environment == Environment.PRODUCTION:
                _settings.validate_security_appliance_config()
        except Exception as e:
            # For testing purposes, create settings with minimal required fields
            import os
            os.environ.setdefault("SECRET_KEY", "test_secret_key_for_development_only_32_chars_minimum")
            try:
                _settings = AppSettings()
            except Exception:
                # If still failing, it's a configuration issue
                raise ValueError(f"Security appliance configuration error: {e}")
    return _settings