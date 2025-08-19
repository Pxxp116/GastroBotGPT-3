from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache

class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 1000
    OPENAI_TEMPERATURE: float = 0.7
    
    # Backend
    BACKEND_BASE_URL: str
    BACKEND_TIMEOUT: int = 30
    BACKEND_RETRY_ATTEMPTS: int = 3
    
    # Reservas
    DEFAULT_DURATION_MIN: int = 120  # Actualizado para coincidir con el backend
    MAX_DURATION_MIN: int = 180
    MIN_DURATION_MIN: int = 60
    
    # Estado
    REDIS_URL: Optional[str] = None
    STATE_TTL_SECONDS: int = 3600  # 1 hora
    
    # Sistema
    TIMEZONE: str = "Europe/Madrid"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["*"]
    
    # Límites
    MAX_CONVERSATION_LENGTH: int = 50
    MAX_MESSAGE_LENGTH: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()