from __future__ import annotations

from typing import Any
from app.Support.ServiceContainer import ServiceProvider, ServiceContainer


class AppServiceProvider(ServiceProvider):
    """Main application service provider."""
    
    def register(self) -> None:
        """Register core services in the container."""
        
        # Register Cache Manager
        self.container.singleton("CacheManager", lambda c: self._create_cache_manager())
        
        # Register Mail Manager
        self.container.singleton("MailManager", lambda c: self._create_mail_manager())
        
        # Register Queue Service
        self.container.singleton("QueueService", lambda c: self._create_queue_service())
        
        # Register Notification Service
        self.container.singleton("NotificationService", lambda c: self._create_notification_service())
        
        # Register Auth Service
        self.container.singleton("AuthService", lambda c: self._create_auth_service())
        
        # Register Activity Log Service
        self.container.singleton("ActivityLogService", lambda c: self._create_activity_log_service())
        
        # Register Config Repository
        self.container.singleton("ConfigRepository", lambda c: self._create_config_repository())
        
        # Register Gate
        self.container.singleton("Gate", lambda c: self._create_gate())
        
        # Register Validator
        self.container.singleton("Validator", lambda c: self._create_validator())
        
        # Register Password Utils
        self.container.singleton("PasswordUtils", lambda c: self._create_password_utils())
        
        # Register Broadcast Manager
        self.container.singleton("BroadcastManager", lambda c: self._create_broadcast_manager())
        
        # Register Event Dispatcher
        self.container.singleton("EventDispatcher", lambda c: self._create_event_dispatcher())
        
        # Register File System Adapter
        self.container.singleton("FilesystemAdapter", lambda c: self._create_filesystem_adapter())
    
    def boot(self) -> None:
        """Boot the service provider."""
        # Register Facades
        self._register_facades()
        
        # Set up aliases
        self._register_aliases()
    
    def _create_cache_manager(self) -> Any:
        """Create cache manager instance."""
        from app.Cache.CacheStore import CacheManager
        return CacheManager()
    
    def _create_mail_manager(self) -> Any:
        """Create mail manager instance."""
        from app.Mail.Mailable import MailManager
        return MailManager()
    
    def _create_queue_service(self) -> Any:
        """Create queue service instance."""
        from app.Services.QueueService import QueueService
        from config.database import get_database
        db = next(get_database())
        return QueueService(db)
    
    def _create_notification_service(self) -> Any:
        """Create notification service instance."""
        from app.Services.NotificationService import NotificationService
        return NotificationService()
    
    def _create_auth_service(self) -> Any:
        """Create auth service instance."""
        from app.Services.AuthService import AuthService
        from config.database import get_database
        db = next(get_database())
        return AuthService(db)
    
    def _create_activity_log_service(self) -> Any:
        """Create activity log service instance."""
        from app.Services.ActivityLogService import ActivityLogService
        from config.database import get_database
        db = next(get_database())
        return ActivityLogService(db)
    
    def _create_config_repository(self) -> Any:
        """Create config repository instance."""
        from app.Support.Config import ConfigRepository
        return ConfigRepository()
    
    def _create_gate(self) -> Any:
        """Create gate instance."""
        from app.Policies.Policy import Gate
        return Gate()
    
    def _create_validator(self) -> Any:
        """Create validator instance."""
        from app.Validation.Validator import Validator
        return Validator()
    
    def _create_password_utils(self) -> Any:
        """Create password utils instance."""
        from app.Utils.PasswordUtils import PasswordUtils
        return PasswordUtils()
    
    def _create_broadcast_manager(self) -> Any:
        """Create broadcast manager instance."""
        from app.Broadcasting.BroadcastManager import BroadcastManager
        return BroadcastManager()
    
    def _create_event_dispatcher(self) -> Any:
        """Create event dispatcher instance."""
        from app.Events import EventDispatcher
        return EventDispatcher()
    
    def _create_filesystem_adapter(self) -> Any:
        """Create filesystem adapter instance."""
        from app.Storage.FilesystemAdapter import FilesystemAdapter
        return FilesystemAdapter()
    
    def _register_facades(self) -> None:
        """Register facade mappings."""
        pass  # Facades are already registered via their get_facade_accessor methods
    
    def _register_aliases(self) -> None:
        """Register service aliases."""
        # Common aliases
        self.container.alias("AuthService", "auth")
        self.container.alias("CacheManager", "cache")
        self.container.alias("MailManager", "mail")
        self.container.alias("QueueService", "queue")
        self.container.alias("ConfigRepository", "config")
        self.container.alias("Gate", "gate")
        self.container.alias("EventDispatcher", "events")