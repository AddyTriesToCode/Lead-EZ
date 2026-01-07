from pydantic_settings import BaseSettings
from pathlib import Path 
import dotenv
import os




class Settings(BaseSettings):
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL")
    database_type: str = os.getenv("DATABASE_TYPE")
    
    # API
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_secret_key: str = os.getenv("API_SECRET_KEY", "dev-only-insecure-key-change-in-production")
    api_debug: bool = os.getenv("API_DEBUG", "true").lower() == "true"
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    
    # MCP Server
    mcp_host: str = "localhost"
    mcp_port: int = 8001
    mcp_log_level: str = "INFO"
    
    # Lead Generation
    lead_count: int = 200
    default_lead_count: int = 200
    random_seed: int = 15  # Default if user doesn't provide a seed
    
    # Email - SMTP
    smtp_host: str = os.getenv("SMTP_HOST", "localhost")
    smtp_port: int = int(os.getenv("SMTP_PORT", "1025"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "demo@leadez.com")
    smtp_enabled: bool = os.getenv("SMTP_ENABLED", "false").lower() == "true"
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "false").lower() == "true"
    
    # LinkedIn (always simulated)
    linkedin_dry_run: bool = True
    linkedin_simulate: bool = True
    
    # LLM for enrichment
    llm_provider: str = os.getenv("LLM_PROVIDER", "none")  # none, ollama, openai
    llm_model: str = os.getenv("LLM_MODEL", "mistral")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Rate Limiting
    max_messages_per_minute: int = 10
    max_retries: int = 2
    retry_delay_seconds: int = 2
    
    # Message Generation
    min_confidence_score: int = int(os.getenv("MIN_CONFIDENCE_SCORE", "55"))
    
    # Pipeline defaults
    default_dry_run: bool = True
    dry_run: bool = True
    lead_batch_size: int = 50
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "./storage/logs/leadez.log")
    
    # Frontend
    vite_api_url: str = os.getenv("VITE_API_URL", "http://localhost:8000")
    vite_ws_url: str = os.getenv("VITE_WS_URL", "ws://localhost:8000/ws")
    
    # n8n
    n8n_host: str = "localhost"
    n8n_port: int = 5678
    n8n_protocol: str = "http"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
