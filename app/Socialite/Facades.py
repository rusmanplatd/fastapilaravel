from __future__ import annotations

from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .SocialiteManager import SocialiteManager
    from .Contracts import Provider

# Global manager instance
_manager: Optional[SocialiteManager] = None


class Socialite:
    """
    Socialite facade similar to Laravel's Socialite facade.
    
    Provides static-like access to the SocialiteManager instance.
    """
    
    @classmethod
    def _get_manager(cls) -> SocialiteManager:
        """Get the global SocialiteManager instance."""
        global _manager
        if _manager is None:
            from .SocialiteManager import SocialiteManager
            _manager = SocialiteManager()
        return _manager
    
    @classmethod
    def driver(cls, provider_name: str) -> Provider:
        """
        Get a social provider instance.
        
        Args:
            provider_name: Name of the provider (github, google, etc.)
            
        Returns:
            Provider instance
        """
        return cls._get_manager().driver(provider_name)
    
    @classmethod
    def extend(cls, provider_name: str, provider_class: type) -> None:
        """
        Register a custom social provider.
        
        Args:
            provider_name: Name of the provider
            provider_class: Provider class
        """
        cls._get_manager().extend(provider_name, provider_class)
    
    @classmethod
    def set_config(cls, config: Dict[str, Dict[str, Any]]) -> None:
        """
        Set the configuration for all providers.
        
        Args:
            config: Configuration dictionary
        """
        global _manager
        from .SocialiteManager import SocialiteManager
        _manager = SocialiteManager(config)
    
    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported provider names."""
        return cls._get_manager().get_supported_providers()
    
    @classmethod
    def is_configured(cls, provider_name: str) -> bool:
        """Check if a provider is configured."""
        return cls._get_manager().is_configured(provider_name)