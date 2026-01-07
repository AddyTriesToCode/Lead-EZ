from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Environment
    environment: str = "development"
    
    # Database
    database_url: str = "sqlite:///./database/leads.db"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "change-me-in-production"
    
    # Lead Generation
    lead_count: int = 200
    random_seed: int = 42
    
    # Email - Mailhog
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "demo@leadez.com"
    smtp_enabled: bool = False
    
    # LinkedIn (always simulated)
    linkedin_dry_run: bool = True
    
    # LLM for enrichment
    llm_provider: str = "none"  # none, ollama
    llm_model: str = "mistral"
    ollama_host: str = "http://localhost:11434"
    
    # Rate Limiting
    max_messages_per_minute: int = 10
    max_retries: int = 2
    retry_delay_seconds: int = 2
    
    # Pipeline defaults
    default_dry_run: bool = True
    lead_batch_size: int = 50
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
