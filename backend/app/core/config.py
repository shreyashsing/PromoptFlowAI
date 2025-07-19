"""
Application configuration settings.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "PromptFlow AI"
    DEBUG: bool = False
    
    # API settings
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database settings
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # AI service settings
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4o"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"
    
    # Security settings
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()