"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"

    # Tiger Brokers API
    tiger_api_key: str = ""  # Legacy - may not be needed for Open SDK
    tiger_api_secret: str = ""  # Legacy - may not be needed for Open SDK
    tiger_private_key: str = ""  # Private key file path or key content string
    tiger_id: str = ""  # Tiger ID for SDK authentication
    tiger_account: str = ""  # Account identifier
    tiger_sandbox: bool = True
    tiger_props_path: str | None = None  # Optional: Path to tiger_openapi_config.properties file (preferred method)

    # Google Services
    google_api_key: str
    google_client_id: str
    google_client_secret: str

    # Lemon Squeezy Payment
    lemon_squeezy_api_key: str = ""
    lemon_squeezy_webhook_secret: str = ""
    lemon_squeezy_store_id: str = ""
    lemon_squeezy_variant_id: str = ""  # Optional for development

    # JWT Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Application Environment
    environment: str = "development"
    debug: bool = False

    # AI Model Configuration
    ai_model_timeout: int = 30
    ai_model_default: str = "gemini-3.0-pro"  # Use gemini-3.0-pro (latest) or gemini-2.5-pro
    ai_model_fallback: str = "deepseek-chat"

    # Timezone
    timezone: str = "UTC"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings()

