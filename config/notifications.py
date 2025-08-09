from __future__ import annotations

import os
from typing import Dict, Any

# Notification channel configurations
NOTIFICATION_CHANNELS: Dict[str, Dict[str, Any]] = {
    'mail': {
        'smtp_host': os.getenv('MAIL_HOST', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('MAIL_PORT', '587')),
        'smtp_user': os.getenv('MAIL_USERNAME'),
        'smtp_password': os.getenv('MAIL_PASSWORD'),
        'use_tls': os.getenv('MAIL_USE_TLS', 'true').lower() == 'true',
        'from_email': os.getenv('MAIL_FROM_ADDRESS', 'noreply@example.com'),
        'from_name': os.getenv('MAIL_FROM_NAME', 'FastAPI Laravel'),
        'mock': os.getenv('MAIL_MOCK', 'true').lower() == 'true'  # Set to false in production
    },
    
    'sms': {
        'provider': os.getenv('SMS_PROVIDER', 'twilio'),  # twilio, aws_sns, etc.
        'api_key': os.getenv('SMS_API_KEY'),
        'api_secret': os.getenv('SMS_API_SECRET'),
        'from_number': os.getenv('SMS_FROM_NUMBER'),
        'base_url': os.getenv('SMS_BASE_URL', 'https://api.twilio.com/2010-04-01'),
        'mock': os.getenv('SMS_MOCK', 'true').lower() == 'true'  # Set to false in production
    },
    
    'push': {
        'provider': os.getenv('PUSH_PROVIDER', 'fcm'),  # fcm, apns, web_push
        'server_key': os.getenv('FCM_SERVER_KEY'),
        'project_id': os.getenv('FCM_PROJECT_ID'),
        'vapid_public_key': os.getenv('VAPID_PUBLIC_KEY'),  # For web push
        'vapid_private_key': os.getenv('VAPID_PRIVATE_KEY'),  # For web push
        'mock': os.getenv('PUSH_MOCK', 'true').lower() == 'true'  # Set to false in production
    },
    
    'slack': {
        'webhook_url': os.getenv('SLACK_WEBHOOK_URL'),
        'default_channel': os.getenv('SLACK_DEFAULT_CHANNEL', '#notifications'),
        'default_username': os.getenv('SLACK_DEFAULT_USERNAME', 'Notification Bot'),
        'default_icon': os.getenv('SLACK_DEFAULT_ICON', ':bell:'),
        'mock': os.getenv('SLACK_MOCK', 'true').lower() == 'true'  # Set to false in production
    },
    
    'discord': {
        'webhook_url': os.getenv('DISCORD_WEBHOOK_URL'),
        'default_username': os.getenv('DISCORD_DEFAULT_USERNAME', 'Notification Bot'),
        'default_avatar_url': os.getenv('DISCORD_DEFAULT_AVATAR_URL'),
        'mock': os.getenv('DISCORD_MOCK', 'true').lower() == 'true'  # Set to false in production
    },
    
    'webhook': {
        'webhook_url': os.getenv('WEBHOOK_URL'),
        'default_headers': {
            'User-Agent': 'FastAPI-Laravel-Notifications/1.0',
            'Authorization': f"Bearer {os.getenv('WEBHOOK_AUTH_TOKEN', '')}" if os.getenv('WEBHOOK_AUTH_TOKEN') else None
        },
        'timeout': int(os.getenv('WEBHOOK_TIMEOUT', '10')),
        'retry_attempts': int(os.getenv('WEBHOOK_RETRY_ATTEMPTS', '3')),
        'verify_ssl': os.getenv('WEBHOOK_VERIFY_SSL', 'true').lower() == 'true',
        'mock': os.getenv('WEBHOOK_MOCK', 'true').lower() == 'true'  # Set to false in production
    }
}

# Remove None values from headers
for channel_config in NOTIFICATION_CHANNELS.values():
    if 'default_headers' in channel_config:
        channel_config['default_headers'] = {
            k: v for k, v in channel_config['default_headers'].items() if v is not None
        }

# Global notification settings
NOTIFICATION_SETTINGS = {
    'queue_enabled': os.getenv('NOTIFICATION_QUEUE_ENABLED', 'false').lower() == 'true',
    'retry_failed': os.getenv('NOTIFICATION_RETRY_FAILED', 'true').lower() == 'true',
    'max_retry_attempts': int(os.getenv('NOTIFICATION_MAX_RETRY_ATTEMPTS', '3')),
    'log_all_notifications': os.getenv('NOTIFICATION_LOG_ALL', 'true').lower() == 'true',
    'rate_limit_enabled': os.getenv('NOTIFICATION_RATE_LIMIT', 'false').lower() == 'true',
    'rate_limit_per_minute': int(os.getenv('NOTIFICATION_RATE_LIMIT_PER_MINUTE', '60'))
}