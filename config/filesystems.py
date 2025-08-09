from __future__ import annotations

import os
from typing import Dict, Any

# Default filesystem disk
default = os.getenv('FILESYSTEM_DISK', 'local')

# Cloud storage disk
cloud = os.getenv('FILESYSTEM_CLOUD', 's3')

# Filesystem disks configuration
disks: Dict[str, Dict[str, Any]] = {
    'local': {
        'driver': 'local',
        'root': 'storage/app',
        'serve': True,
        'throw': False,
    },
    
    'public': {
        'driver': 'local',
        'root': 'storage/app/public',
        'url': os.getenv('APP_URL', 'http://localhost:8000') + '/storage',
        'visibility': 'public',
        'serve': True,
        'throw': False,
    },
    
    'temp': {
        'driver': 'local',
        'root': 'storage/app/temp',
        'serve': False,
        'throw': False,
    },
    
    'uploads': {
        'driver': 'local',
        'root': 'storage/app/uploads',
        'url': os.getenv('APP_URL', 'http://localhost:8000') + '/uploads',
        'visibility': 'public',
        'serve': True,
        'throw': False,
    },
    
    'private': {
        'driver': 'local',
        'root': 'storage/app/private',
        'serve': False,
        'throw': False,
    },
    
    # S3 configuration (example)
    's3': {
        'driver': 's3',
        'key': os.getenv('AWS_ACCESS_KEY_ID'),
        'secret': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'region': os.getenv('AWS_DEFAULT_REGION'),
        'bucket': os.getenv('AWS_BUCKET'),
        'url': os.getenv('AWS_URL'),
        'endpoint': os.getenv('AWS_ENDPOINT'),
        'use_path_style_endpoint': os.getenv('AWS_USE_PATH_STYLE_ENDPOINT', False),
        'throw': False,
    },
    
    # FTP configuration (example)
    'ftp': {
        'driver': 'ftp',
        'host': os.getenv('FTP_HOST'),
        'username': os.getenv('FTP_USERNAME'),
        'password': os.getenv('FTP_PASSWORD'),
        'port': int(os.getenv('FTP_PORT', 21)),
        'root': os.getenv('FTP_ROOT', '/'),
        'passive': True,
        'ssl': os.getenv('FTP_SSL', False),
        'timeout': 30,
        'throw': False,
    },
    
    # SFTP configuration (example)
    'sftp': {
        'driver': 'sftp',
        'host': os.getenv('SFTP_HOST'),
        'username': os.getenv('SFTP_USERNAME'),
        'password': os.getenv('SFTP_PASSWORD'),
        'private_key': os.getenv('SFTP_PRIVATE_KEY'),
        'port': int(os.getenv('SFTP_PORT', 22)),
        'root': os.getenv('SFTP_ROOT', '/'),
        'timeout': 30,
        'throw': False,
    },
    
    # Azure Blob Storage configuration (example)
    'azure': {
        'driver': 'azure',
        'account_name': os.getenv('AZURE_STORAGE_ACCOUNT'),
        'account_key': os.getenv('AZURE_STORAGE_KEY'),
        'connection_string': os.getenv('AZURE_STORAGE_CONNECTION_STRING'),
        'container': os.getenv('AZURE_STORAGE_CONTAINER'),
        'prefix': os.getenv('AZURE_STORAGE_PREFIX', ''),
        'throw': False,
    },
    
    # Google Cloud Storage configuration (example)
    'gcs': {
        'driver': 'gcs',
        'project_id': os.getenv('GOOGLE_CLOUD_PROJECT_ID'),
        'key_file': os.getenv('GOOGLE_CLOUD_KEY_FILE'),
        'bucket': os.getenv('GOOGLE_CLOUD_STORAGE_BUCKET'),
        'prefix': os.getenv('GOOGLE_CLOUD_STORAGE_PREFIX', ''),
        'throw': False,
    },
    
    # Dropbox configuration (example)
    'dropbox': {
        'driver': 'dropbox',
        'access_token': os.getenv('DROPBOX_ACCESS_TOKEN'),
        'root': os.getenv('DROPBOX_ROOT', '/'),
        'throw': False,
    },
    
    # Memory filesystem (for testing)
    'memory': {
        'driver': 'memory',
        'throw': False,
    }
}

# Links for public disk
links: Dict[str, str] = {
    'public/storage': 'storage/app/public',
}

# Default visibility
visibility = 'private'

# File serving options
serve_missing_files = False
serve_directory_index = False

# Upload limits
upload_max_filesize = os.getenv('UPLOAD_MAX_FILESIZE', '10M')
upload_max_files = int(os.getenv('UPLOAD_MAX_FILES', 20))

# Allowed file types for uploads
allowed_extensions = [
    # Images
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp',
    # Documents
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf',
    # Archives
    'zip', 'rar', '7z', 'tar', 'gz',
    # Audio
    'mp3', 'wav', 'ogg', 'flac', 'aac',
    # Video
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm',
    # Code
    'html', 'css', 'js', 'json', 'xml', 'csv',
]

# MIME type restrictions
allowed_mime_types = [
    # Images
    'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/svg+xml', 'image/webp',
    # Documents
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain', 'text/rtf',
    # Archives
    'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed',
    'application/x-tar', 'application/gzip',
    # Audio
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/flac', 'audio/aac',
    # Video
    'video/mp4', 'video/x-msvideo', 'video/quicktime', 'video/x-ms-wmv',
    'video/x-flv', 'video/webm',
    # Code
    'text/html', 'text/css', 'application/javascript', 'application/json',
    'application/xml', 'text/csv',
]

# Security settings
scan_uploads = True
quarantine_suspicious_files = True
max_file_scan_size = '100M'

# Image processing
image_quality = 85
image_max_width = 2048
image_max_height = 2048
create_thumbnails = True
thumbnail_sizes = [
    {'width': 150, 'height': 150, 'suffix': 'thumb'},
    {'width': 300, 'height': 300, 'suffix': 'medium'},
    {'width': 800, 'height': 600, 'suffix': 'large'},
]