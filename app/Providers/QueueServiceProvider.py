from __future__ import annotations

from typing import TYPE_CHECKING
from app.Foundation.ServiceProvider import ServiceProvider
from app.Queue.QueueManager import global_queue_manager, QueueConfig
from app.Services.QueueService import QueueService
from app.Utils.Logger import get_logger

if TYPE_CHECKING:
    from app.Foundation.Application import Application

logger = get_logger(__name__)


class QueueServiceProvider(ServiceProvider):
    """Service provider for Queue functionality."""

    def register(self) -> None:
        """Register Queue services."""
        container = self.app.container
        
        # Register queue manager as singleton
        container.singleton('queue', lambda: global_queue_manager)
        
        # Register queue service
        container.bind('queue.service', lambda: QueueService(
            container.resolve('db.connection')
        ))
        
        # Register facade aliases
        container.alias('Queue', 'queue')
        container.alias('QueueManager', 'queue')
        
        logger.info("Queue services registered")

    def boot(self) -> None:
        """Bootstrap queue services."""
        config = self.app.container.resolve('config')
        queue_manager = self.app.container.resolve('queue')
        
        # Configure default queues
        self._configure_default_queues(queue_manager, config)
        
        # Setup queue monitoring if enabled
        if config.get('queue.monitoring.enabled', False):
            self._setup_queue_monitoring(queue_manager)
        
        logger.info("Queue services booted")
    
    def _configure_default_queues(self, queue_manager, config) -> None:
        """Configure default queue definitions."""
        try:
            # Default queue
            queue_manager.define_queue(
                "default",
                connection=config.get('queue.default_connection', 'database'),
                max_attempts=config.get('queue.max_attempts', 3),
                timeout=config.get('queue.timeout', 60),
                memory_limit=config.get('queue.memory_limit', 128)
            )
            
            # High priority queue
            queue_manager.define_queue(
                "high-priority",
                connection=config.get('queue.default_connection', 'database'),
                max_attempts=3,
                timeout=120,
                memory_limit=256,
                rate_limit_enabled=True,
                rate_limit_max=50,
                rate_limit_window=60
            )
            
            # Email queue
            queue_manager.define_queue(
                "emails",
                connection=config.get('queue.default_connection', 'database'),
                max_attempts=5,
                timeout=30,
                memory_limit=64
            )
            
            # Notifications queue
            queue_manager.define_queue(
                "notifications",
                connection=config.get('queue.default_connection', 'database'),
                max_attempts=3,
                timeout=30,
                memory_limit=64
            )
            
            logger.info("Default queues configured")
            
        except Exception as e:
            logger.error(f"Failed to configure default queues: {e}")
    
    def _setup_queue_monitoring(self, queue_manager) -> None:
        """Setup queue monitoring and health checks."""
        try:
            # Enable queue monitoring
            monitor = queue_manager.monitor
            
            # Configure health check intervals
            for queue_name in ['default', 'high-priority', 'emails', 'notifications']:
                config = queue_manager.get_queue_config(queue_name)
                if config.health_check_enabled:
                    driver = queue_manager.get_driver(config.connection)
                    monitor.health_check(queue_name, driver)
            
            logger.info("Queue monitoring configured")
            
        except Exception as e:
            logger.error(f"Failed to setup queue monitoring: {e}")
    
    def provides(self) -> list[str]:
        """Get the services provided by this provider."""
        return [
            'queue',
            'queue.service',
            'Queue',
            'QueueManager'
        ]