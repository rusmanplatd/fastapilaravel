"""
Service Provider for Blade Template System
Handles service injection and advanced template features
"""
from __future__ import annotations

from typing import Dict, Any, Optional, Callable, Type
from abc import ABC, abstractmethod
import inspect


class ServiceContract(ABC):
    """Base contract for injectable services"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the service name for injection"""
        pass


class ConfigService(ServiceContract):
    """Configuration service for templates"""
    
    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        self.config_data = config_data or {}
    
    def get_name(self) -> str:
        return "config_service"
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation support"""
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def has(self, key: str) -> bool:
        """Check if configuration key exists"""
        return self.get(key) is not None
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        keys = key.split('.')
        target = self.config_data
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value


class AuthService(ServiceContract):
    """Authentication service for templates"""
    
    def __init__(self) -> None:
        self.current_user = None
    
    def get_name(self) -> str:
        return "auth"
    
    def user(self) -> Any:
        """Get current authenticated user"""
        return self.current_user
    
    def check(self) -> bool:
        """Check if user is authenticated"""
        return self.current_user is not None
    
    def guest(self) -> bool:
        """Check if user is a guest"""
        return self.current_user is None
    
    def id(self) -> Optional[int]:
        """Get current user ID"""
        return getattr(self.current_user, 'id', None) if self.current_user else None
    
    def set_user(self, user: Any) -> None:
        """Set current user"""
        self.current_user = user


class CacheService(ServiceContract):
    """Cache service for template fragments"""
    
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
    
    def get_name(self) -> str:
        return "cache"
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        return self._cache.get(key, default)
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Put value in cache"""
        self._cache[key] = value
        if ttl:
            import time
            self._ttl[key] = time.time() + ttl
    
    def forget(self, key: str) -> None:
        """Remove value from cache"""
        self._cache.pop(key, None)
        self._ttl.pop(key, None)
    
    def has(self, key: str) -> bool:
        """Check if key exists in cache"""
        return key in self._cache
    
    def remember(self, key: str, callback: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        """Get cached value or execute callback and cache result"""
        if self.has(key):
            return self.get(key)
        
        value = callback()
        self.put(key, value, ttl)
        return value


class RequestService(ServiceContract):
    """Request service for template context"""
    
    def __init__(self) -> None:
        self.current_request: Optional[Any] = None
    
    def get_name(self) -> str:
        return "request"
    
    def url(self) -> str:
        """Get current request URL"""
        return getattr(self.current_request, 'url', '') if self.current_request else ''
    
    def path(self) -> str:
        """Get current request path"""
        return getattr(self.current_request, 'path', '') if self.current_request else ''
    
    def method(self) -> str:
        """Get request method"""
        return getattr(self.current_request, 'method', 'GET') if self.current_request else 'GET'
    
    def is_secure(self) -> bool:
        """Check if request is HTTPS"""
        return getattr(self.current_request, 'is_secure', False) if self.current_request else False
    
    def header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get request header"""
        if self.current_request is None:
            return default
        
        headers = getattr(self.current_request, 'headers', {})
        result = headers.get(name, default)
        return str(result) if result is not None else None
    
    def set_request(self, request: Any) -> None:
        """Set current request"""
        self.current_request = request


class UrlService(ServiceContract):
    """URL generation service"""
    
    def __init__(self) -> None:
        self.routes: Dict[str, str] = {}
        self.base_url = "http://localhost:8000"
    
    def get_name(self) -> str:
        return "url"
    
    def route(self, name: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate route URL"""
        if name in self.routes:
            url = self.routes[name]
            if params:
                for key, value in params.items():
                    url = url.replace(f"{{{key}}}", str(value))
            return url
        return f"/{name}"
    
    def to(self, path: str) -> str:
        """Generate absolute URL"""
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
    
    def asset(self, path: str) -> str:
        """Generate asset URL"""
        return f"{self.base_url}/assets/{path.lstrip('/')}"
    
    def register_route(self, name: str, pattern: str) -> None:
        """Register a route pattern"""
        self.routes[name] = pattern


class TranslationService(ServiceContract):
    """Translation service for i18n"""
    
    def __init__(self) -> None:
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_locale = 'en'
    
    def get_name(self) -> str:
        return "translator"
    
    def translate(self, key: str, replacements: Optional[Dict[str, Any]] = None, locale: Optional[str] = None) -> str:
        """Translate a key"""
        locale = locale or self.current_locale
        
        if locale in self.translations:
            translation = self.translations[locale].get(key, key)
        else:
            translation = key
        
        if replacements:
            for placeholder, value in replacements.items():
                translation = translation.replace(f":{placeholder}", str(value))
        
        return translation
    
    def choice(self, key: str, count: int, replacements: Optional[Dict[str, Any]] = None, locale: Optional[str] = None) -> str:
        """Translate with pluralization"""
        if count == 1:
            return self.translate(f"{key}.singular", replacements, locale)
        else:
            return self.translate(f"{key}.plural", replacements, locale)
    
    def set_locale(self, locale: str) -> None:
        """Set current locale"""
        self.current_locale = locale
    
    def load_translations(self, locale: str, translations: Dict[str, str]) -> None:
        """Load translations for a locale"""
        if locale not in self.translations:
            self.translations[locale] = {}
        self.translations[locale].update(translations)


class ServiceContainer:
    """Service container for dependency injection"""
    
    def __init__(self) -> None:
        self.services: Dict[str, ServiceContract] = {}
        self.singletons: Dict[str, Any] = {}
        self.bindings: Dict[str, Callable[..., Any]] = {}
    
    def register(self, service: ServiceContract) -> None:
        """Register a service"""
        self.services[service.get_name()] = service
    
    def bind(self, name: str, factory: Callable[..., Any]) -> None:
        """Bind a factory function"""
        self.bindings[name] = factory
    
    def singleton(self, name: str, factory: Callable[..., Any]) -> None:
        """Register a singleton"""
        self.singletons[name] = factory
    
    def get(self, name: str) -> Any:
        """Get service instance"""
        # Check registered services first
        if name in self.services:
            return self.services[name]
        
        # Check singletons
        if name in self.singletons:
            if not isinstance(self.singletons[name], object) or callable(self.singletons[name]):
                # Create singleton instance
                factory = self.singletons[name]
                instance = factory() if callable(factory) else factory
                self.singletons[name] = instance
            return self.singletons[name]
        
        # Check bindings
        if name in self.bindings:
            return self.bindings[name]()
        
        raise KeyError(f"Service '{name}' not found")
    
    def has(self, name: str) -> bool:
        """Check if service exists"""
        return name in self.services or name in self.singletons or name in self.bindings


class BladeServiceProvider:
    """Service provider for Blade templates"""
    
    def __init__(self, container: Optional[ServiceContainer] = None):
        self.container = container or ServiceContainer()
        self._setup_default_services()
    
    def _setup_default_services(self) -> None:
        """Setup default services"""
        # Register core services
        self.container.register(ConfigService())
        self.container.register(AuthService())
        self.container.register(CacheService())
        self.container.register(RequestService())
        self.container.register(UrlService())
        self.container.register(TranslationService())
    
    def register_service(self, service: ServiceContract) -> None:
        """Register a custom service"""
        self.container.register(service)
    
    def get_template_context(self) -> Dict[str, Any]:
        """Get services for template context"""
        context = {}
        
        # Add all services to template context
        for name, service in self.container.services.items():
            context[name] = service
        
        # Add convenience methods
        context['config'] = self.container.get('config_service').get
        context['auth'] = self.container.get('auth')
        context['cache'] = self.container.get('cache')
        context['url'] = self.container.get('url')
        context['__'] = self.container.get('translator').translate
        context['trans'] = self.container.get('translator').translate
        context['trans_choice'] = self.container.get('translator').choice
        
        return context
    
    def inject_service(self, name: str, service_name: str) -> Callable[..., Any]:
        """Create a service injection directive"""
        def directive_callback(content: str) -> str:
            return f"{{{{ {name}.{content.strip()} }}}}"
        
        return directive_callback
    
    def create_service_directives(self) -> Dict[str, Callable[..., Any]]:
        """Create service injection directives"""
        directives = {}
        
        # Create @config directive
        directives['config'] = lambda content: f"{{{{ config('{content.strip()}') }}}}"
        
        # Create @auth directive helpers
        directives['user'] = lambda content: "{{ auth.user() }}"
        directives['userid'] = lambda content: "{{ auth.id() }}"
        
        # Create @url directive
        directives['route'] = lambda content: f"{{{{ url.route('{content.strip()}') }}}}"
        
        # Create @cache directive
        directives['cache'] = self._cache_directive
        
        return directives
    
    def _cache_directive(self, content: str) -> str:
        """Cache directive implementation"""
        # Parse cache directive: @cache('key', 60)
        import re
        match = re.match(r"['\"](.+?)['\"](?:,\s*(\d+))?", content)
        if match:
            key = match.group(1)
            ttl = match.group(2)
            return f"{{% set _cache_key = '{key}' %}}{{% if cache.has(_cache_key) %}}{{% else %}}"
        return "<!-- Invalid cache directive -->"


# Global service provider instance
blade_service_provider = BladeServiceProvider()