from __future__ import annotations

import os
from typing import Dict, Any

# Default logging configuration
default = 'stack'

channels: Dict[str, Dict[str, Any]] = {
    'stack': {
        'driver': 'stack',
        'channels': ['single'],
        'ignore_exceptions': False,
    },
    
    'single': {
        'driver': 'single',
        'path': 'storage/logs/laravel.log',
        'level': os.getenv('LOG_LEVEL', 'debug'),
        'replace_placeholders': True,
    },
    
    'daily': {
        'driver': 'daily',
        'path': 'storage/logs/laravel.log',
        'level': os.getenv('LOG_LEVEL', 'debug'),
        'days': 14,
        'replace_placeholders': True,
    },
    
    'stderr': {
        'driver': 'stderr',
        'level': os.getenv('LOG_LEVEL', 'debug'),
        'formatter': 'laravel',
        'formatter_with': {
            'format': '[%datetime%] %channel%.%level_name%: %message% %context% %extra%',
            'date_format': 'Y-m-d H:i:s',
        },
    },
    
    'syslog': {
        'driver': 'syslog',
        'level': os.getenv('LOG_LEVEL', 'debug'),
        'facility': 'user',
    },
    
    'emergency': {
        'driver': 'single',
        'path': 'storage/logs/emergency.log',
        'level': 'emergency',
    },
    
    'json': {
        'driver': 'single',
        'path': 'storage/logs/json.log',
        'level': os.getenv('LOG_LEVEL', 'debug'),
        'formatter': 'json',
    },
    
    'database': {
        'driver': 'single',
        'path': 'storage/logs/database.log',
        'level': 'debug',
    },
    
    'queue': {
        'driver': 'single', 
        'path': 'storage/logs/queue.log',
        'level': 'debug',
    },
    
    'auth': {
        'driver': 'single',
        'path': 'storage/logs/auth.log',
        'level': 'info',
    },
    
    'performance': {
        'driver': 'daily',
        'path': 'storage/logs/performance.log',
        'level': 'info',
        'days': 7,
    },
    
    'security': {
        'driver': 'daily',
        'path': 'storage/logs/security.log',
        'level': 'warning',
        'days': 30,
    }
}

# Deprecations logging
deprecations: Dict[str, Any] = {
    'channel': os.getenv('LOG_DEPRECATIONS_CHANNEL'),
    'trace': False,
}

# Default logging level
level = os.getenv('LOG_LEVEL', 'debug')