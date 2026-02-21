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
    # Support both formats:
    # 1. Full DATABASE_URL (for Docker Compose / local development)
    # 2. Separate components (for Cloud Run - DB_PASSWORD comes from Secret Manager)
    database_url: str = ""  # Optional if using separate components
    db_user: str = "thetamind"  # Default user (can be overridden by env var)
    db_name: str = "thetamind"  # Default database name (thetamind_prod for Cloud Run, thetamind for local)
    db_password: str = ""  # From Secret Manager in Cloud Run, or .env for local
    cloudsql_connection_name: str = ""  # For Cloud Run Unix socket connection
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
    # When False (dev): do not call Tiger for option chain; load from fixture to avoid 开发/生产 抢占
    tiger_use_live_api: bool = True  # Production: True. Development: False + option_chain_fixture.json
    tiger_option_chain_fixture_path: str = ""  # Path to option_chain_fixture.json; empty = app/data/fixtures/option_chain_fixture.json

    # Financial Modeling Prep API (for FinanceToolkit)
    # Required for market data. Only FMP is used; Yahoo Finance is not used.
    financial_modeling_prep_key: str = ""

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
    lemon_squeezy_frontend_url: str = ""  # Frontend URL for payment success redirect (e.g., http://localhost:3000 or https://your-ngrok-url.ngrok-free.dev)
    # Subscription Pricing (in USD)
    subscription_price_monthly: float = 9.9  # Monthly subscription price
    subscription_price_yearly: float = 99.0  # Yearly subscription price

    # JWT Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Application Environment
    environment: str = "development"
    debug: bool = False

    # AI Provider Configuration (default Gemini; ZenMux supported)
    # Can be overridden by: AI_PROVIDER environment variable or .env file
    ai_provider: str = "gemini"  # "gemini" (default) or "zenmux"
    ai_model_timeout: int = 900  # 15 min default; synthesis (long report) may need up to 15–20 min
    ai_model_default: str = "gemini-3-flash-preview"  # Report model - Gemini 3 Flash (faster, higher quota; use gemini-2.5-pro if needed)
    ai_model_fallback: str = "deepseek-chat"  # Reserved for error handling/fallback scenarios
    
    # AI Image Generation Configuration
    ai_image_model: str = "gemini-3-pro-image"  # Image generation model (Gemini 3 Pro Image for Vertex AI)
    ai_image_provider: str = "gemini"  # "gemini" (default) or "zenmux" - which provider to use for strategy chart images

    # Google Cloud Configuration (for Vertex AI)
    # Required for Vertex AI API key (AQ...) authentication
    google_vertex_api_key: str = ""  # AQ.xxx key for Vertex AI fallback
    google_cloud_project: str = "friendly-vigil-481107-h3"  # Google Cloud Project ID
    google_cloud_location: str = "global"  # Vertex AI location (use "global" for Gemini 3 Pro)
    
    # ZenMux Configuration (optional; when AI_PROVIDER=zenmux or AI_IMAGE_PROVIDER=zenmux)
    zenmux_api_key: str = ""
    zenmux_model: str = "gemini-2.5-pro"
    zenmux_api_base: str = "https://api.zenmux.com"
    zenmux_vertex_ai_base: str = "https://zenmux.ai/api/vertex-ai"  # Vertex AI protocol endpoint for image generation

    # Timezone
    timezone: str = "UTC"

    # Frontend Domain Configuration (for CORS and OAuth redirects)
    domain: str = ""  # Production domain (e.g., https://thetamind.com or thetamind.com)
    allowed_origins: str = ""  # Comma-separated list of allowed origins (e.g., "https://app.example.com,https://www.example.com")
    
    # Scheduler Configuration
    enable_scheduler: bool = False  # Set to True to enable automatic scheduled jobs (e.g., daily picks generation)
    # Feature flags: set to True to enable in UI and scheduler (default False for staged rollout)
    enable_anomaly_radar: bool = False  # 异动雷达: scheduler scan + API + frontend display
    enable_daily_picks: bool = False  # 每日精选: scheduler job + API + frontend display

    # Cloudflare R2 Storage Configuration
    cloudflare_r2_account_id: str = ""  # Cloudflare account ID
    cloudflare_r2_access_key_id: str = ""  # R2 access key ID
    cloudflare_r2_secret_access_key: str = ""  # R2 secret access key
    cloudflare_r2_bucket_name: str = ""  # R2 bucket name
    cloudflare_r2_public_url_base: str = ""  # Public URL base (e.g., https://pub-xxx.r2.dev or custom domain)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-construct DATABASE_URL if using Cloud SQL (separate components)
        # This happens after pydantic has loaded all env vars and secrets
        # Priority:
        # 1. If DATABASE_URL is explicitly set (Docker Compose / local), use it
        # 2. If CLOUDSQL_CONNECTION_NAME is set (Cloud Run), construct from components
        # 3. Otherwise, try to get from environment variable as fallback
        
        import os
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Check if we have a valid database_url already (from env var or .env file)
        # Pydantic should have already loaded it if DATABASE_URL env var exists
        if self.database_url and self.database_url.strip():
            # DATABASE_URL is already set (local development / Docker Compose)
            # No need to construct it
            logger.info("Using DATABASE_URL from environment variable")
            pass
        elif self.cloudsql_connection_name:
            # Cloud Run: Use Unix socket connection
            # Format: postgresql+asyncpg://user:password@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
            # DB_PASSWORD comes from Secret Manager via --update-secrets
            if not self.db_password:
                # Try to get from environment variable directly (Secret Manager injection)
                self.db_password = os.getenv("DB_PASSWORD", "")
            
            if not self.db_password:
                raise ValueError(
                    "DB_PASSWORD must be set for Cloud Run. "
                    "Ensure DB_PASSWORD secret is configured in Secret Manager and "
                    "included in --update-secrets for Cloud Run deployment."
                )
            
            if not self.db_user:
                self.db_user = "thetamind"
            
            if not self.db_name:
                self.db_name = "thetamind_prod"
            
            self.database_url = (
                f"postgresql+asyncpg://{self.db_user}:{self.db_password}@/{self.db_name}"
                f"?host=/cloudsql/{self.cloudsql_connection_name}"
            )
            logger.info(
                f"Constructed DATABASE_URL for Cloud Run: "
                f"user={self.db_user}, db={self.db_name}, "
                f"cloudsql={self.cloudsql_connection_name}"
            )
        else:
            # Fallback: try to get from DATABASE_URL env var directly
            # This handles cases where pydantic didn't pick it up (e.g., set after import)
            fallback_url = os.getenv("DATABASE_URL", "")
            if fallback_url:
                self.database_url = fallback_url
                logger.info("Using DATABASE_URL from environment variable (fallback)")
            elif not self.database_url or not self.database_url.strip():
                # Final check: if still empty, raise error with helpful message
                raise ValueError(
                    "DATABASE_URL must be set in environment variables or .env file. "
                    "For local development, set DATABASE_URL in docker-compose.yml or .env file. "
                    "For Cloud Run, provide CLOUDSQL_CONNECTION_NAME, DB_USER, DB_NAME, "
                    "and DB_PASSWORD (from Secret Manager)."
                )

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

