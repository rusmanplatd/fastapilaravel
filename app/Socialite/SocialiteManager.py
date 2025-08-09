from __future__ import annotations

from typing import Dict, Any, Optional, Type
from fastapi import Request, HTTPException

from .Contracts import Provider
from .Providers import (
    GitHubProvider,
    GoogleProvider, 
    TwitterProvider,
    FacebookProvider,
    LinkedInProvider,
    DiscordProvider,
)


class SocialiteManager:
    """
    Social authentication manager similar to Laravel Socialite.
    
    Manages multiple OAuth providers and provides a unified interface
    for social authentication across different platforms.
    """
    
    def __init__(self, config: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        self.config = config or {}
        self._providers: Dict[str, Type[Provider]] = {
            'github': GitHubProvider,
            'google': GoogleProvider,
            'twitter': TwitterProvider,
            'facebook': FacebookProvider,
            'linkedin': LinkedInProvider,
            'discord': DiscordProvider,
        }
        self._instances: Dict[str, Provider] = {}
    
    def driver(self, provider_name: str) -> Provider:
        """
        Get a social provider instance.
        
        Args:
            provider_name: The name of the provider (github, google, etc.)
            
        Returns:
            Provider instance
            
        Raises:
            HTTPException: If provider is not configured or doesn't exist
        """
        if provider_name in self._instances:
            return self._instances[provider_name]
        
        if provider_name not in self._providers:
            raise HTTPException(
                status_code=404,
                detail=f"Social provider '{provider_name}' is not supported"
            )
        
        if provider_name not in self.config:
            raise HTTPException(
                status_code=500,
                detail=f"Social provider '{provider_name}' is not configured"
            )
        
        provider_config = self.config[provider_name]
        provider_class = self._providers[provider_name]
        
        required_keys = ['client_id', 'client_secret', 'redirect_uri']
        for key in required_keys:
            if key not in provider_config:
                raise HTTPException(
                    status_code=500,
                    detail=f"Missing configuration key '{key}' for provider '{provider_name}'"
                )
        
        self._instances[provider_name] = provider_class(
            client_id=provider_config['client_id'],
            client_secret=provider_config['client_secret'],
            redirect_uri=provider_config['redirect_uri'],
            scopes=provider_config.get('scopes', [])
        )
        
        return self._instances[provider_name]
    
    def extend(self, provider_name: str, provider_class: Type[Provider]) -> None:
        """
        Register a custom social provider.
        
        Args:
            provider_name: Name of the provider
            provider_class: Provider class implementing Provider interface
        """
        self._providers[provider_name] = provider_class
        # Remove cached instance if exists
        if provider_name in self._instances:
            del self._instances[provider_name]
    
    def get_supported_providers(self) -> list[str]:
        """Get list of supported provider names."""
        return list(self._providers.keys())
    
    def is_configured(self, provider_name: str) -> bool:
        """Check if a provider is configured."""
        return (
            provider_name in self._providers and 
            provider_name in self.config and
            all(
                key in self.config[provider_name] 
                for key in ['client_id', 'client_secret', 'redirect_uri']
            )
        )