"""Application configuration loaded from environment variables.

Configuration Priority (highest to lowest):
1. Docker container environment: section (only for internal container configs like DB_HOST, REDIS_URL with service names)
2. System environment variables (export VAR=value)
3. .env file (recommended - single source of truth for all user configurations)
4. Default values in config.py (lowest)

For Docker deployments:
- Use .env file for ALL user configurations (single source of truth)
- docker-compose.yml environment: only contains container-internal overrides (service names, etc.)
- Do NOT modify docker-compose.yml for user configurations
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    Settings are loaded in this priority order:
    1. Environment variables (system or Docker container)
    2. .env file
    3. Default values defined here
    
    In Docker: docker-compose.yml environment: overrides .env file.
    """

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

    # Google Services (OAuth)
    google_client_id: str
    google_client_secret: str
    # Google API Key (optional - only needed if using gemini provider)
    google_api_key: str = ""

    # Lemon Squeezy Payment
    lemon_squeezy_api_key: str = ""
    lemon_squeezy_webhook_secret: str = ""
    lemon_squeezy_store_id: str = ""
    lemon_squeezy_variant_id: str = ""  # Monthly variant ID
    lemon_squeezy_variant_id_yearly: str = ""  # Yearly variant ID

    # JWT Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Application Environment
    environment: str = "development"
    debug: bool = False

    # AI Provider Configuration
    # Can be overridden by: AI_PROVIDER environment variable or .env file
    ai_provider: str = "gemini"  # Default: gemini (direct API). Options: gemini, zenmux, qwen, deepseek, etc.
    ai_model_timeout: int = 600  # Increased to 600s (10 minutes) for deep research workflow (3-phase agentic process)
    ai_model_default: str = "gemini-3.0-pro-preview"  # Standard model for ALL users (Free & Pro) - Gemini 3.0 Pro
    ai_model_fallback: str = "deepseek-chat"  # Reserved for error handling/fallback scenarios
    
    # AI Image Generation Configuration
    ai_image_model: str = "gemini-3-pro-image"  # Image generation model (Gemini 3 Pro Image for Vertex AI)

    # Google Cloud Configuration (for Vertex AI)
    # Required for Vertex AI API key (AQ...) authentication
    google_cloud_project: str = "friendly-vigil-481107-h3"  # Google Cloud Project ID
    google_cloud_location: str = "us-central1"  # Vertex AI location/region
    
    # ZenMux Configuration
    # Required if AI_PROVIDER=zenmux
    # Can be overridden by: ZENMUX_API_KEY, ZENMUX_MODEL, ZENMUX_API_BASE environment variables or .env file
    zenmux_api_key: str = ""
    zenmux_model: str = "gemini-3.0-pro-preview"  # Model to use via ZenMux (must match ai_model_default for consistency)
    zenmux_api_base: str = "https://api.zenmux.com"

    # Timezone
    timezone: str = "UTC"

    # Frontend Domain Configuration (for CORS and OAuth redirects)
    domain: str = ""  # Production domain (e.g., https://thetamind.com or thetamind.com)
    allowed_origins: str = ""  # Comma-separated list of allowed origins (e.g., "https://app.example.com,https://www.example.com")
    
    # Scheduler Configuration
    enable_scheduler: bool = False  # Set to True to enable automatic scheduled jobs (e.g., daily picks generation)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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

