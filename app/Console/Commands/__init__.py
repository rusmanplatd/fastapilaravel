from __future__ import annotations

"""
Console Commands Package

This package contains all the Artisan console commands for the application.
Commands are automatically discovered and registered by the Artisan kernel.
"""

# Import all command classes for auto-discovery
from .MakeServiceCommand import (
    MakeServiceCommand,
    MakeRequestCommand,
    MakeResourceCommand,
    MakeMiddlewareCommand,
    MakeObserverCommand
)
from .MakeJobCommand import (
    MakeJobCommand,
    MakeNotificationCommand,
    MakeEventCommand,
    MakeListenerCommand
)
from .MakePolicyCommand import (
    MakePolicyCommand,
    MakeRuleCommand,
    MakeTestCommand,
    MakeCommandCommand
)

__all__ = [
    # Service and business logic
    'MakeServiceCommand',
    'MakeRequestCommand',
    'MakeResourceCommand',
    'MakeMiddlewareCommand',
    'MakeObserverCommand',
    
    # Queue and events
    'MakeJobCommand',
    'MakeNotificationCommand',
    'MakeEventCommand',
    'MakeListenerCommand',
    
    # Authorization and testing
    'MakePolicyCommand',
    'MakeRuleCommand',
    'MakeTestCommand',
    'MakeCommandCommand'
]