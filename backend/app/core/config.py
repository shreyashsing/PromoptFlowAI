"""
Application configuration settings.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "PromptFlow AI"
    DEBUG: bool = False
    
    # API settings
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    # Database settings
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""  # Anon key for client-side operations
    SUPABASE_SERVICE_ROLE_KEY: str = ""  # Service role key for backend operations
    
    # AI service settings
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4.1"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"
    
    # ReAct Agent settings
    USE_REACT_AGENT: bool = True  # Enable ReAct agent by default
    REACT_AGENT_FALLBACK: bool = True  # Enable fallback to original agent
    REACT_AGENT_MAX_ITERATIONS: int = 10  # Maximum reasoning iterations
    
    # Security settings
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OAuth settings
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = ""
    LOG_CONSOLE: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()