"""
Configuration using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    """
    Application settings from environment variables
    """
    
    # ========================================
    # API Configuration
    # ========================================
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    
    API_TITLE: str = "E-Cernova Livro Caixa Rural"
    API_VERSION: str = "0.1.0"
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    
    # ========================================
    # Database
    # ========================================
    DATABASE_URL: str = "postgresql://cernova:cernova123@localhost:5432/cernova_dev"
    DB_ECHO: bool = False  # Log SQL queries
    
    # ========================================
    # SEFAZ
    # ========================================
    SEFAZ_MODE: str = "mock"  # mock or real
    SEFAZ_TIMEOUT: int = 30
    SEFAZ_RETRY_MAX: int = 3
    SEFAZ_RETRY_BACKOFF: int = 2
    
    SEFAZ_USER: Optional[str] = None
    SEFAZ_PASSWORD: Optional[str] = None
    SEFAZ_CERTIFICATE_PATH: Optional[str] = None
    
    # ========================================
    # Claude / Anthropic
    # ========================================
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-5"
    CLAUDE_MAX_TOKENS: int = 2000
    CLAUDE_TEMPERATURE: float = 0.3
    
    # ========================================
    # Azure
    # ========================================
    AZURE_SUBSCRIPTION_ID: Optional[str] = None
    AZURE_RESOURCE_GROUP: str = "rg-livcx-dev"
    AZURE_LOCATION: str = "brazilsouth"
    
    AZURE_KEY_VAULT_NAME: Optional[str] = None
    AZURE_KEY_VAULT_URL: Optional[str] = None
    
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = None
    AZURE_STORAGE_CONTAINER: str = "xml-acervo"
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    
    AZURE_USE_MANAGED_IDENTITY: bool = False
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    
    AZURE_APPINSIGHTS_KEY: Optional[str] = None
    
    # ========================================
    # Authentication (Entra ID)
    # ========================================
    ENTRA_CLIENT_ID: Optional[str] = None
    ENTRA_CLIENT_SECRET: Optional[str] = None
    ENTRA_TENANT_ID: Optional[str] = None
    ENTRA_REDIRECT_URI: str = "http://localhost:8000/auth/callback"
    
    # ========================================
    # Logging
    # ========================================
    LOG_FORMAT: str = "json"  # json or plain
    LOG_FILE_PATH: str = "./logs/app.log"
    
    # ========================================
    # Security
    # ========================================
    JWT_SECRET_KEY: str = "your-secret-key-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Single admin account (no user table yet — see docs/07-arquitetura.md).
    # ADMIN_PASSWORD_HASH is a bcrypt hash, not a plaintext password:
    #   python -c "from src.api.middleware.auth import hash_password; print(hash_password('your-password'))"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: Optional[str] = None
    
    # ========================================
    # CORS
    # ========================================
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # ========================================
    # Rate Limiting
    # ========================================
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # ========================================
    # Testing
    # ========================================
    TESTING: bool = False
    TEST_DATABASE_URL: str = "sqlite:///./test.db"
    
    # ========================================
    # Misc
    # ========================================
    TIMEZONE: str = "America/Sao_Paulo"
    ALLOW_SHUTDOWN: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignorar variáveis extras do .env

# Create singleton instance
settings = Settings()
