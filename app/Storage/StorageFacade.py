from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, BinaryIO
from pathlib import Path

from .FilesystemAdapter import FilesystemAdapter, LocalFilesystemAdapter, StorageManager
from .CloudStorageAdapters import (
    S3FilesystemAdapter, GoogleCloudStorageAdapter, AzureBlobStorageAdapter,
    DigitalOceanSpacesAdapter, MinIOAdapter, FTPFilesystemAdapter
)
from .UploadHandler import UploadHandler, UploadConfig, create_upload_handler


class Storage:
    """
    Laravel-style Storage facade for file operations.
    
    Provides a unified interface for working with different storage drivers
    and includes additional utilities for file management.
    """
    
    _manager: Optional[StorageManager] = None
    _upload_handlers: Dict[str, UploadHandler] = {}
    
    @classmethod
    def _get_manager(cls) -> StorageManager:
        """Get the storage manager instance."""
        if cls._manager is None:
            cls._manager = StorageManager()
        return cls._manager
    
    @classmethod
    def disk(cls, name: Optional[str] = None) -> FilesystemAdapter:
        """Get a storage disk instance."""
        return cls._get_manager().disk(name)
    
    @classmethod
    def extend(cls, name: str, adapter: FilesystemAdapter) -> None:
        """Register a custom storage adapter."""
        cls._get_manager().extend(name, adapter)
    
    @classmethod
    def configure_disk(cls, name: str, driver: str, **config: Any) -> None:
        """Configure a storage disk with the given driver and configuration."""
        adapter = cls._create_adapter(driver, **config)
        cls.extend(name, adapter)
    
    @classmethod
    def _create_adapter(cls, driver: str, **config: Any) -> FilesystemAdapter:
        """Create a storage adapter based on driver configuration."""
        if driver == 'local':
            return LocalFilesystemAdapter(
                root_path=config.get('root', 'storage')
            )
        
        elif driver == 's3':
            return S3FilesystemAdapter(
                bucket=config['bucket'],
                region=config.get('region', 'us-east-1'),
                access_key_id=config.get('key'),
                secret_access_key=config.get('secret'),
                session_token=config.get('token'),
                endpoint_url=config.get('endpoint'),
                public_url=config.get('url')
            )
        
        elif driver == 'gcs':
            return GoogleCloudStorageAdapter(
                bucket=config['bucket'],
                project_id=config.get('project_id'),
                credentials_path=config.get('key_file'),
                credentials_json=config.get('key_file_contents')
            )
        
        elif driver == 'azure':
            return AzureBlobStorageAdapter(
                account_name=config['account'],
                container=config['container'],
                account_key=config.get('key'),
                sas_token=config.get('sas_token'),
                connection_string=config.get('connection_string')
            )
        
        elif driver == 'do_spaces':
            return DigitalOceanSpacesAdapter(
                bucket=config['bucket'],
                region=config['region'],
                access_key_id=config['key'],
                secret_access_key=config['secret']
            )
        
        elif driver == 'minio':
            return MinIOAdapter(
                bucket=config['bucket'],
                endpoint_url=config['endpoint'],
                access_key_id=config['key'],
                secret_access_key=config['secret'],
                secure=config.get('use_ssl', True)
            )
        
        elif driver == 'ftp':
            return FTPFilesystemAdapter(
                host=config['host'],
                username=config['username'],
                password=config['password'],
                port=config.get('port', 21),
                root_path=config.get('root', '/'),
                passive=config.get('passive', True),
                timeout=config.get('timeout', 30)
            )
        
        else:
            raise ValueError(f"Unknown storage driver: {driver}")
    
    # File operations (delegate to default disk)
    
    @classmethod
    def exists(cls, path: str) -> bool:
        """Check if a file exists."""
        return cls.disk().exists(path)
    
    @classmethod
    def missing(cls, path: str) -> bool:
        """Check if a file is missing."""
        return cls.disk().missing(path)
    
    @classmethod
    def get(cls, path: str) -> Optional[bytes]:
        """Get file contents."""
        return cls.disk().get(path)
    
    @classmethod
    def get_string(cls, path: str) -> Optional[str]:
        """Get file contents as string."""
        return cls.disk().get_string(path)
    
    @classmethod
    def put(cls, path: str, contents: Union[str, bytes, BinaryIO]) -> bool:
        """Store file contents."""
        return cls.disk().put(path, contents)
    
    @classmethod
    def put_string(cls, path: str, contents: str) -> bool:
        """Store string contents."""
        return cls.disk().put_string(path, contents)
    
    @classmethod
    def put_file(cls, path: str, file: Union[str, Path, BinaryIO]) -> bool:
        """Store a file from local filesystem or file-like object."""
        if isinstance(file, (str, Path)):
            # Read from local file
            with open(file, 'rb') as f:
                return cls.put(path, f.read())
        else:
            # File-like object
            return cls.put(path, file.read())
    
    @classmethod
    def put_file_as(cls, file: Union[str, Path, BinaryIO], path: str) -> bool:
        """Store a file with a specific path."""
        return cls.put_file(path, file)
    
    @classmethod
    def prepend(cls, path: str, contents: Union[str, bytes]) -> bool:
        """Prepend content to a file."""
        return cls.disk().prepend(path, contents)
    
    @classmethod
    def append(cls, path: str, contents: Union[str, bytes]) -> bool:
        """Append content to a file."""
        return cls.disk().append(path, contents)
    
    @classmethod
    def delete(cls, path: Union[str, List[str]]) -> bool:
        """Delete one or more files."""
        if isinstance(path, list):
            return all(cls.disk().delete(p) for p in path)
        return cls.disk().delete(path)
    
    @classmethod
    def copy(cls, from_path: str, to_path: str) -> bool:
        """Copy a file."""
        return cls.disk().copy(from_path, to_path)
    
    @classmethod
    def move(cls, from_path: str, to_path: str) -> bool:
        """Move a file."""
        return cls.disk().move(from_path, to_path)
    
    @classmethod
    def size(cls, path: str) -> Optional[int]:
        """Get file size."""
        return cls.disk().size(path)
    
    @classmethod
    def last_modified(cls, path: str) -> Optional[int]:
        """Get last modified timestamp."""
        dt = cls.disk().last_modified(path)
        return int(dt.timestamp()) if dt else None
    
    @classmethod
    def files(cls, directory: str = "", recursive: bool = False) -> List[str]:
        """Get all files in a directory."""
        adapter = cls.disk()
        if hasattr(adapter, 'files'):
            if 'recursive' in adapter.files.__code__.co_varnames:
                return adapter.files(directory, recursive)
            else:
                return adapter.files(directory)
        return []
    
    @classmethod
    def all_files(cls, directory: str = "") -> List[str]:
        """Get all files recursively."""
        return cls.files(directory, recursive=True)
    
    @classmethod
    def directories(cls, directory: str = "") -> List[str]:
        """Get all directories."""
        return cls.disk().directories(directory)
    
    @classmethod
    def all_directories(cls, directory: str = "") -> List[str]:
        """Get all directories recursively."""
        # Implement recursive directory listing
        adapter = cls.disk()
        all_dirs = []
        
        def collect_dirs(current_dir: str) -> None:
            dirs = adapter.directories(current_dir)
            all_dirs.extend(dirs)
            for subdir in dirs:
                collect_dirs(subdir)
        
        collect_dirs(directory)
        return sorted(all_dirs)
    
    @classmethod
    def make_directory(cls, path: str) -> bool:
        """Create a directory."""
        adapter = cls.disk()
        if hasattr(adapter, 'make_directory'):
            return adapter.make_directory(path)
        return False
    
    @classmethod
    def delete_directory(cls, path: str) -> bool:
        """Delete a directory."""
        adapter = cls.disk()
        if hasattr(adapter, 'delete_directory'):
            return adapter.delete_directory(path)
        return False
    
    # URL generation
    
    @classmethod
    def url(cls, path: str) -> str:
        """Get the URL for a file."""
        adapter = cls.disk()
        if hasattr(adapter, 'url'):
            return adapter.url(path)
        raise RuntimeError("Current storage driver does not support URLs")
    
    @classmethod
    def temporary_url(cls, path: str, expires_in: int = 3600, **options: Any) -> str:
        """Get a temporary URL for a file."""
        adapter = cls.disk()
        if hasattr(adapter, 'temporary_url'):
            return adapter.temporary_url(path, expires_in, **options)
        return cls.url(path)
    
    # Upload handling
    
    @classmethod
    def upload_handler(cls, disk: Optional[str] = None, config: Optional[UploadConfig] = None) -> UploadHandler:
        """Get an upload handler for the specified disk."""
        disk_name = disk or 'default'
        
        if disk_name not in cls._upload_handlers:
            storage_disk = cls.disk(disk)
            cls._upload_handlers[disk_name] = create_upload_handler(storage_disk, config)
        
        return cls._upload_handlers[disk_name]
    
    # Utility methods
    
    @classmethod
    def disk_info(cls, disk: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a storage disk."""
        adapter = cls.disk(disk)
        
        info = {
            'driver': adapter.__class__.__name__,
            'supports_urls': hasattr(adapter, 'url'),
            'supports_temporary_urls': hasattr(adapter, 'temporary_url'),
            'supports_directories': hasattr(adapter, 'make_directory')
        }
        
        # Add driver-specific info
        if hasattr(adapter, 'bucket'):
            info['bucket'] = adapter.bucket
        if hasattr(adapter, 'region'):
            info['region'] = adapter.region
        if hasattr(adapter, 'root_path'):
            info['root_path'] = str(adapter.root_path)
        
        return info
    
    @classmethod
    def download(cls, path: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a download response for a file."""
        return cls._get_manager().download_response(path, name)
    
    @classmethod
    def path(cls, path: str) -> str:
        """Get the full path to a file."""
        adapter = cls.disk()
        if hasattr(adapter, '_full_path'):
            return str(adapter._full_path(path))
        return path
    
    @classmethod
    def disk_free_space(cls, disk: Optional[str] = None) -> Optional[int]:
        """Get free space on disk (local storage only)."""
        adapter = cls.disk(disk)
        if hasattr(adapter, 'root_path'):
            import shutil
            return shutil.disk_usage(adapter.root_path).free
        return None
    
    @classmethod
    def mime_type(cls, path: str) -> Optional[str]:
        """Get MIME type of a file."""
        return cls.disk().mime_type(path)
    
    @classmethod
    def hash(cls, path: str, algorithm: str = 'sha256') -> Optional[str]:
        """Get hash of a file."""
        content = cls.get(path)
        if content is None:
            return None
        
        import hashlib
        hasher = getattr(hashlib, algorithm)()
        hasher.update(content)
        return hasher.hexdigest()
    
    @classmethod
    def checksum(cls, path: str) -> Optional[str]:
        """Get MD5 checksum of a file."""
        return cls.hash(path, 'md5')


# Global storage instance
storage = Storage()


# Helper functions for common operations
def storage_disk(name: Optional[str] = None) -> FilesystemAdapter:
    """Get a storage disk instance."""
    return Storage.disk(name)


def storage_exists(path: str) -> bool:
    """Check if a file exists on default storage."""
    return Storage.exists(path)


def storage_get(path: str) -> Optional[bytes]:
    """Get file contents from default storage."""
    return Storage.get(path)


def storage_put(path: str, contents: Union[str, bytes]) -> bool:
    """Store file on default storage."""
    return Storage.put(path, contents)


def storage_delete(path: Union[str, List[str]]) -> bool:
    """Delete file(s) from default storage."""
    return Storage.delete(path)


def storage_url(path: str) -> str:
    """Get URL for file on default storage."""
    return Storage.url(path)


def storage_download(path: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Create download response for file on default storage."""
    return Storage.download(path, name)