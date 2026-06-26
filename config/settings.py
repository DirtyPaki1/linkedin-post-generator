from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List
import os

class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # API Keys
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    serpapi_api_key: str = Field(..., env="SERPAPI_API_KEY")
    
    # Database
    database_url: str = Field("sqlite:///linkedin_posts.db", env="DATABASE_URL")
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    
    # Application
    app_env: str = Field("development", env="APP_ENV")
    debug: bool = Field(True, env="DEBUG")
    secret_key: str = Field("your-secret-key-change-this", env="SECRET_KEY")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # Features
    enable_fact_checking: bool = Field(True, env="ENABLE_FACT_CHECKING")
    enable_analytics: bool = Field(True, env="ENABLE_ANALYTICS")
    enable_caching: bool = Field(True, env="ENABLE_CACHING")
    enable_scheduling: bool = Field(True, env="ENABLE_SCHEDULING")
    enable_multi_language: bool = Field(True, env="ENABLE_MULTI_LANGUAGE")
    
    # Rate Limiting
    rate_limit_requests: int = Field(100, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(60, env="RATE_LIMIT_PERIOD")
    
    # Cache
    cache_ttl_seconds: int = Field(3600, env="CACHE_TTL_SECONDS")
    
    # Default settings
    default_tone: str = Field("professional", env="DEFAULT_TONE")
    default_length: str = Field("medium", env="DEFAULT_LENGTH")
    default_audience: str = Field("professionals", env="DEFAULT_AUDIENCE")
    default_num_posts: int = Field(3, env="DEFAULT_NUM_POSTS")
    
    # Model settings
    default_model: str = Field("groq", env="DEFAULT_MODEL")
    temperature: float = Field(0.7, env="TEMPERATURE")
    max_tokens: int = Field(2000, env="MAX_TOKENS")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Temperature must be between 0 and 1')
        return v
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False

_settings = None

def get_settings() -> Settings:
    """Get singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings