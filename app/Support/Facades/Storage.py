from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, BinaryIO, TextIO
from datetime import datetime
from app.Support.Facades.Facade import Facade


class Storage(Facade):
    """Storage facade for Laravel-style filesystem operations."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'filesystem'
    
    # Disk management
    @classmethod
    def disk(cls, name: Optional[str] = None) -> Any:
        """Get a filesystem disk."""
        return cls.get_facade_root().disk(name)
    
    @classmethod
    def cloud(cls) -> Any:
        """Get the cloud filesystem disk."""
        return cls.get_facade_root().cloud()
    
    @classmethod
    def build(cls, config: Dict[str, Any]) -> Any:
        """Build a new filesystem instance."""
        from app.Filesystem.FilesystemManager import FilesystemManager
        return FilesystemManager(config)
    
    # File operations
    @classmethod
    def exists(cls, path: str) -> bool:
        """Check if file exists."""
        return cls.get_facade_root().exists(path)
    @classmethod
    def missing(cls, path: str) -> bool:
        """Check if file is missing."""
        return cls.get_facade_root().missing(path)
    @classmethod
    def get(cls, path: str) -> bytes:
        """Get file contents as bytes."""
        return cls.get_facade_root().get(path)
    @classmethod
    def read(cls, path: str) -> str:
        """Read file as string."""
        return cls.get_facade_root().read(path)
    @classmethod
    def put(cls, path: str, contents: Union[str, bytes]) -> bool:
        """Store a file."""
        return cls.get_facade_root().put(path, contents)
    @classmethod
    def write(cls, path: str, contents: str) -> bool:
        """Write string to file."""
        return cls.get_facade_root().write(path, contents)
    @classmethod
    def put_file(cls, path: str, file: Union[BinaryIO, TextIO]) -> bool:
        """Store an uploaded file."""
        return cls.get_facade_root().put_file(path, file)
    @classmethod
    def put_file_as(cls, path: str, file: Union[BinaryIO, TextIO], name: str) -> str:
        """Store file with a specific name."""
        return cls.get_facade_root().put_file_as(path, file, name)
    @classmethod
    def prepend(cls, path: str, data: str) -> bool:
        """Prepend to a file."""
        return cls.get_facade_root().prepend(path, data)
    @classmethod
    def append(cls, path: str, data: str) -> bool:
        """Append to a file."""
        return cls.get_facade_root().append(path, data)
    @classmethod
    def delete(cls, paths: Union[str, List[str]]) -> bool:
        """Delete file(s)."""
        return cls.get_facade_root().delete(paths)
    @classmethod
    def copy(cls, from_path: str, to_path: str) -> bool:
        """Copy a file."""
        return cls.get_facade_root().copy(from_path, to_path)
    @classmethod
    def move(cls, from_path: str, to_path: str) -> bool:
        """Move a file."""
        return cls.get_facade_root().move(from_path, to_path)
    # File metadata
    @classmethod
    def size(cls, path: str) -> int:
        """Get file size."""
        return cls.get_facade_root().size(path)
    @classmethod
    def last_modified(cls, path: str) -> int:
        """Get last modified timestamp."""
        return cls.get_facade_root().last_modified(path)
    @classmethod
    def mime_type(cls, path: str) -> Optional[str]:
        """Get file MIME type."""
        return cls.get_facade_root().mime_type(path)
    # Directory operations
    @classmethod
    def files(cls, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of files."""
        return cls.get_facade_root().files(directory, recursive)
    @classmethod
    def all_files(cls, directory: Optional[str] = None) -> List[str]:
        """Get all files recursively."""
        return cls.get_facade_root().all_files(directory)
    @classmethod
    def directories(cls, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of directories."""
        return cls.get_facade_root().directories(directory, recursive)
    @classmethod
    def all_directories(cls, directory: Optional[str] = None) -> List[str]:
        """Get all directories recursively."""
        return cls.get_facade_root().all_directories(directory)
    @classmethod
    def make_directory(cls, path: str) -> bool:
        """Create directory."""
        return cls.get_facade_root().make_directory(path)
    @classmethod
    def delete_directory(cls, directory: str) -> bool:
        """Delete directory."""
        return cls.get_facade_root().delete_directory(directory)
    # URLs and downloads
    @classmethod
    def url(cls, path: str) -> str:
        """Get public URL for file."""
        return cls.get_facade_root().url(path)
    @classmethod
    def temporary_url(cls, path: str, expiration: datetime) -> str:
        """Get temporary URL for file."""
        return cls.get_facade_root().temporary_url(path, expiration)
    @classmethod
    def download(cls, path: str, name: Optional[str] = None) -> bytes:
        """Download a file."""
        return cls.get_facade_root().download(path, name)
    @classmethod
    def response(cls, path: str, name: Optional[str] = None, headers: Optional[Dict[str, str]] = None) -> Any:
        """Create a file response."""
        return cls.get_facade_root().response(path, name, headers)
    @classmethod
    def stream_download(cls, path: str, name: Optional[str] = None) -> Any:
        """Stream download a file."""
        return cls.get_facade_root().stream_download(path, name)
    # JSON operations
    @classmethod
    def json(cls, path: str) -> Any:
        """Read JSON file."""
        return cls.get_facade_root().json(path)
    
    @classmethod
    def put_json(cls, path: str, data: Any) -> bool:
        """Write data as JSON file."""
        return cls.get_facade_root().put_json(path, data)
    # Utility methods
    @classmethod
    def checksum(cls, path: str) -> str:
        """Get file checksum."""
        return cls.get_facade_root().checksum(path)
    @classmethod
    def file_hash(cls, path: str, algorithm: str = 'md5') -> str:
        """Get file hash using specified algorithm."""
        return cls.get_facade_root().file_hash(path, algorithm)
    @classmethod
    def path(cls, path: str) -> str:
        """Get absolute path to file."""
        return cls.get_facade_root().path(path)
    @classmethod
    def read_stream(cls, path: str) -> BinaryIO:
        """Get file as stream."""
        return cls.get_facade_root().read_stream(path)
    @classmethod
    def write_stream(cls, path: str, resource: BinaryIO) -> bool:
        """Write stream to file."""
        return cls.get_facade_root().write_stream(path, resource)
    # Cloud sync operations
    @classmethod
    def sync_to_cloud(cls, local_path: str, cloud_path: Optional[str] = None) -> bool:
        """Sync local file to cloud storage."""
        return cls.get_facade_root().sync_to_cloud(local_path, cloud_path)
    @classmethod
    def sync_from_cloud(cls, cloud_path: str, local_path: Optional[str] = None) -> bool:
        """Sync cloud file to local storage."""
        return cls.get_facade_root().sync_from_cloud(cloud_path, local_path)
    # Configuration
    @classmethod
    def available_drivers(cls) -> List[str]:
        """Get list of available drivers."""
        return cls.get_facade_root().available_drivers()  # type: ignore    
    @classmethod
    def disk_config(cls, disk: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a disk."""
        return cls.get_facade_root().disk_config(disk)  # type: ignore