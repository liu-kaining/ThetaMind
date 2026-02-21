"""AI Provider Registry for managing and selecting AI providers."""

import logging
from typing import Type

from app.services.ai.base import BaseAIProvider

logger = logging.getLogger(__name__)

# Provider name constants (ZenMux disabled - kept for reference)
PROVIDER_ZENMUX = "zenmux"
PROVIDER_GEMINI = "gemini"
# Future extensions
PROVIDER_QWEN = "qwen"
PROVIDER_DEEPSEEK = "deepseek"


class ProviderRegistry:
    """Registry for AI providers with lazy initialization."""
    
    _providers: dict[str, Type[BaseAIProvider]] = {}
    _instances: dict[str, BaseAIProvider | None] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: Type[BaseAIProvider]) -> None:
        """
        Register an AI provider class.
        
        Args:
            name: Provider identifier (e.g., "zenmux", "gemini")
            provider_class: Provider class that implements BaseAIProvider
        """
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered AI provider: {name}")
    
    @classmethod
    def get_provider(cls, name: str) -> BaseAIProvider | None:
        """
        Get provider instance with lazy initialization.
        
        Args:
            name: Provider identifier
            
        Returns:
            Provider instance or None if initialization failed
        """
        name_lower = name.lower()
        
        # Check if already initialized (including failed attempts)
        if name_lower in cls._instances:
            instance = cls._instances[name_lower]
            if instance is None:
                logger.warning(f"Provider '{name}' was previously unavailable")
            return instance
        
        # Check if registered
        if name_lower not in cls._providers:
            logger.error(f"Provider '{name}' is not registered. Available: {list(cls._providers.keys())}")
            cls._instances[name_lower] = None
            return None
        
        # Lazy initialization
        provider_class = cls._providers[name_lower]
        try:
            logger.info(f"Initializing AI provider: {name}")
            instance = provider_class()
            cls._instances[name_lower] = instance
            logger.info(f"Successfully initialized provider: {name}")
            return instance
        except Exception as e:
            logger.warning("Provider '%s' unavailable (e.g. missing API key): %s", name, e)
            cls._instances[name_lower] = None
            return None
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())
    
    @classmethod
    def is_available(cls, name: str) -> bool:
        """Check if a provider is available (registered and initialized)."""
        instance = cls.get_provider(name)
        return instance is not None

