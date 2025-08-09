from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, BinaryIO, TextIO, Callable
from abc import ABC, abstractmethod
from datetime import datetime
import mimetypes
import json
import hashlib


class FilesystemAdapter(ABC):
    """Abstract filesystem adapter."""
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    def get(self, path: str) -> bytes:
        """Get file contents."""
        pass
    
    @abstractmethod
    def put(self, path: str, contents: Union[str, bytes]) -> bool:
        """Store a file."""
        pass
    
    @abstractmethod
    def put_file(self, path: str, file: Union[BinaryIO, TextIO]) -> bool:
        """Store an uploaded file."""
        pass
    
    @abstractmethod
    def prepend(self, path: str, data: str) -> bool:
        """Prepend to a file."""
        pass
    
    @abstractmethod
    def append(self, path: str, data: str) -> bool:
        """Append to a file."""
        pass
    
    @abstractmethod
    def delete(self, paths: Union[str, List[str]]) -> bool:
        """Delete file(s)."""
        pass
    
    @abstractmethod
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy a file."""
        pass
    
    @abstractmethod
    def move(self, from_path: str, to_path: str) -> bool:
        """Move a file."""
        pass
    
    @abstractmethod
    def size(self, path: str) -> int:
        """Get file size."""
        pass
    
    @abstractmethod
    def last_modified(self, path: str) -> int:
        """Get last modified timestamp."""
        pass
    
    @abstractmethod
    def files(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of files."""
        pass
    
    @abstractmethod
    def all_files(self, directory: Optional[str] = None) -> List[str]:
        """Get all files recursively."""
        pass
    
    @abstractmethod
    def directories(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of directories."""
        pass
    
    @abstractmethod
    def all_directories(self, directory: Optional[str] = None) -> List[str]:
        """Get all directories recursively."""
        pass
    
    @abstractmethod
    def make_directory(self, path: str) -> bool:
        """Create directory."""
        pass
    
    @abstractmethod
    def delete_directory(self, directory: str) -> bool:
        """Delete directory."""
        pass


class LocalFilesystemAdapter(FilesystemAdapter):
    """Local filesystem adapter."""
    
    def __init__(self, root: str = '') -> None:
        self.root = Path(root) if root else Path.cwd()
        self.root.mkdir(parents=True, exist_ok=True)
    
    def _full_path(self, path: str) -> Path:
        """Get full path."""
        return self.root / path.lstrip('/')
    
    def exists(self, path: str) -> bool:
        """Check if file exists."""
        return self._full_path(path).exists()
    
    def get(self, path: str) -> bytes:
        """Get file contents."""
        full_path = self._full_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return full_path.read_bytes()
    
    def put(self, path: str, contents: Union[str, bytes]) -> bool:
        """Store a file."""
        try:
            full_path = self._full_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            if isinstance(contents, str):
                full_path.write_text(contents, encoding='utf-8')
            else:
                full_path.write_bytes(contents)
            return True
        except Exception:
            return False
    
    def put_file(self, path: str, file: Union[BinaryIO, TextIO]) -> bool:
        """Store an uploaded file."""
        try:
            full_path = self._full_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'wb') as f:
                if hasattr(file, 'read'):
                    content = file.read()
                    if isinstance(content, str):
                        content = content.encode('utf-8')
                    f.write(content)
                else:
                    # Type ignore for now since we can't properly type this without more context
                    shutil.copyfileobj(file, f)  # type: ignore
            return True
        except Exception:
            return False
    
    def prepend(self, path: str, data: str) -> bool:
        """Prepend to a file."""
        try:
            full_path = self._full_path(path)
            if full_path.exists():
                existing = full_path.read_text(encoding='utf-8')
                full_path.write_text(data + existing, encoding='utf-8')
            else:
                full_path.write_text(data, encoding='utf-8')
            return True
        except Exception:
            return False
    
    def append(self, path: str, data: str) -> bool:
        """Append to a file."""
        try:
            full_path = self._full_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'a', encoding='utf-8') as f:
                f.write(data)
            return True
        except Exception:
            return False
    
    def delete(self, paths: Union[str, List[str]]) -> bool:
        """Delete file(s)."""
        if isinstance(paths, str):
            paths = [paths]
        
        try:
            for path in paths:
                full_path = self._full_path(path)
                if full_path.exists():
                    if full_path.is_file():
                        full_path.unlink()
                    else:
                        shutil.rmtree(full_path)
            return True
        except Exception:
            return False
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy a file."""
        try:
            from_full = self._full_path(from_path)
            to_full = self._full_path(to_path)
            to_full.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(from_full, to_full)
            return True
        except Exception:
            return False
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move a file."""
        try:
            from_full = self._full_path(from_path)
            to_full = self._full_path(to_path)
            to_full.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(from_full), str(to_full))
            return True
        except Exception:
            return False
    
    def size(self, path: str) -> int:
        """Get file size."""
        full_path = self._full_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return full_path.stat().st_size
    
    def last_modified(self, path: str) -> int:
        """Get last modified timestamp."""
        full_path = self._full_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return int(full_path.stat().st_mtime)
    
    def files(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of files."""
        if directory is None:
            search_path = self.root
        else:
            search_path = self._full_path(directory)
        
        if not search_path.exists():
            return []
        
        files = []
        if recursive:
            for item in search_path.rglob('*'):
                if item.is_file():
                    files.append(str(item.relative_to(self.root)))
        else:
            for item in search_path.iterdir():
                if item.is_file():
                    files.append(str(item.relative_to(self.root)))
        
        return files
    
    def all_files(self, directory: Optional[str] = None) -> List[str]:
        """Get all files recursively."""
        return self.files(directory, recursive=True)
    
    def directories(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of directories."""
        if directory is None:
            search_path = self.root
        else:
            search_path = self._full_path(directory)
        
        if not search_path.exists():
            return []
        
        directories = []
        if recursive:
            for item in search_path.rglob('*'):
                if item.is_dir():
                    directories.append(str(item.relative_to(self.root)))
        else:
            for item in search_path.iterdir():
                if item.is_dir():
                    directories.append(str(item.relative_to(self.root)))
        
        return directories
    
    def all_directories(self, directory: Optional[str] = None) -> List[str]:
        """Get all directories recursively."""
        return self.directories(directory, recursive=True)
    
    def make_directory(self, path: str) -> bool:
        """Create directory."""
        try:
            full_path = self._full_path(path)
            full_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False
    
    def delete_directory(self, directory: str) -> bool:
        """Delete directory."""
        try:
            full_path = self._full_path(directory)
            if full_path.exists() and full_path.is_dir():
                shutil.rmtree(full_path)
            return True
        except Exception:
            return False


class FilesystemManager:
    """Laravel-style filesystem manager."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config or {}
        self._disks: Dict[str, FilesystemAdapter] = {}
        self._default_disk = 'local'
        
        # Create default disks
        self._create_default_disks()
    
    def _create_default_disks(self) -> None:
        """Create default filesystem disks."""
        # Local disk
        local_config = self._config.get('disks', {}).get('local', {})
        root = local_config.get('root', 'storage/app')
        self._disks['local'] = LocalFilesystemAdapter(root)
        
        # Public disk
        public_config = self._config.get('disks', {}).get('public', {})
        public_root = public_config.get('root', 'storage/app/public')
        self._disks['public'] = LocalFilesystemAdapter(public_root)
    
    def disk(self, name: Optional[str] = None) -> FilesystemAdapter:
        """Get a filesystem disk."""
        name = name or self._default_disk
        
        if name not in self._disks:
            self._disks[name] = self._create_disk(name)
        
        return self._disks[name]
    
    def _create_disk(self, name: str) -> FilesystemAdapter:
        """Create a filesystem disk."""
        config = self._config.get('disks', {}).get(name, {})
        driver = config.get('driver', 'local')
        
        if driver == 'local':
            root = config.get('root', f'storage/app/{name}')
            return LocalFilesystemAdapter(root)
        elif driver == 's3':
            return self._create_s3_adapter(config)
        elif driver == 'ftp':
            return self._create_ftp_adapter(config)
        elif driver == 'sftp':
            return self._create_sftp_adapter(config)
        elif driver == 'azure':
            return self._create_azure_adapter(config)
        elif driver == 'gcs':
            return self._create_gcs_adapter(config)
        elif driver == 'dropbox':
            return self._create_dropbox_adapter(config)
        elif driver == 'memory':
            return self._create_memory_adapter(config)
        elif hasattr(self, '_custom_drivers') and driver in self._custom_drivers:
            # Use custom driver
            return self._custom_drivers[driver]()
        else:
            raise ValueError(f"Filesystem driver '{driver}' not supported")
    
    def _create_s3_adapter(self, config: Dict[str, Any]) -> FilesystemAdapter:
        """Create S3 filesystem adapter."""
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
        except ImportError:
            raise ImportError("boto3 is required for S3 filesystem. Install with: pip install boto3")
        
        return S3FilesystemAdapter(config)
    
    def _create_ftp_adapter(self, config: Dict[str, Any]) -> FilesystemAdapter:
        """Create FTP filesystem adapter."""
        return FTPFilesystemAdapter(config)
    
    def _create_sftp_adapter(self, config: Dict[str, Any]) -> FilesystemAdapter:
        """Create SFTP filesystem adapter."""
        try:
            import paramiko
        except ImportError:
            raise ImportError("paramiko is required for SFTP filesystem. Install with: pip install paramiko")
        
        return SFTPFilesystemAdapter(config)
    
    def _create_azure_adapter(self, config: Dict[str, Any]) -> FilesystemAdapter:
        """Create Azure Blob Storage filesystem adapter."""
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise ImportError("azure-storage-blob is required for Azure filesystem. Install with: pip install azure-storage-blob")
        
        return AzureBlobFilesystemAdapter(config)
    
    def _create_gcs_adapter(self, config: Dict[str, Any]) -> FilesystemAdapter:
        """Create Google Cloud Storage filesystem adapter."""
        try:
            from google.cloud import storage as gcs
        except ImportError:
            raise ImportError("google-cloud-storage is required for GCS filesystem. Install with: pip install google-cloud-storage")
        
        return GoogleCloudStorageAdapter(config)
    
    def _create_dropbox_adapter(self, config: Dict[str, Any]) -> FilesystemAdapter:
        """Create Dropbox filesystem adapter."""
        try:
            import dropbox
        except ImportError:
            raise ImportError("dropbox is required for Dropbox filesystem. Install with: pip install dropbox")
        
        return DropboxFilesystemAdapter(config)
    
    def _create_memory_adapter(self, config: Dict[str, Any]) -> FilesystemAdapter:
        """Create memory filesystem adapter."""
        return MemoryFilesystemAdapter(config)
    
    def get_default_driver(self) -> str:
        """Get the default filesystem disk."""
        return self._default_disk
    
    def set_default_driver(self, name: str) -> None:
        """Set the default filesystem disk."""
        self._default_disk = name
    
    def extend(self, driver: str, creator: Callable[[], FilesystemAdapter]) -> None:
        """Register a custom filesystem driver."""
        if not hasattr(self, '_custom_drivers'):
            self._custom_drivers = {}
        self._custom_drivers[driver] = creator
    
    def cloud(self) -> FilesystemAdapter:
        """Get the cloud filesystem disk."""
        cloud_disk = self._config.get('cloud', 's3')
        return self.disk(cloud_disk)
    
    # Proxy methods to default disk
    def exists(self, path: str) -> bool:
        """Check if file exists on default disk."""
        return self.disk().exists(path)
    
    def get(self, path: str) -> bytes:
        """Get file contents from default disk."""
        return self.disk().get(path)
    
    def put(self, path: str, contents: Union[str, bytes]) -> bool:
        """Store a file on default disk."""
        return self.disk().put(path, contents)
    
    def put_file(self, path: str, file: Union[BinaryIO, TextIO]) -> bool:
        """Store an uploaded file on default disk."""
        return self.disk().put_file(path, file)
    
    def prepend(self, path: str, data: str) -> bool:
        """Prepend to a file on default disk."""
        return self.disk().prepend(path, data)
    
    def append(self, path: str, data: str) -> bool:
        """Append to a file on default disk."""
        return self.disk().append(path, data)
    
    def delete(self, paths: Union[str, List[str]]) -> bool:
        """Delete file(s) from default disk."""
        return self.disk().delete(paths)
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy a file on default disk."""
        return self.disk().copy(from_path, to_path)
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move a file on default disk."""
        return self.disk().move(from_path, to_path)
    
    def size(self, path: str) -> int:
        """Get file size from default disk."""
        return self.disk().size(path)
    
    def last_modified(self, path: str) -> int:
        """Get last modified timestamp from default disk."""
        return self.disk().last_modified(path)
    
    def files(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of files from default disk."""
        return self.disk().files(directory, recursive)
    
    def all_files(self, directory: Optional[str] = None) -> List[str]:
        """Get all files recursively from default disk."""
        return self.disk().all_files(directory)
    
    def directories(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of directories from default disk."""
        return self.disk().directories(directory, recursive)
    
    def all_directories(self, directory: Optional[str] = None) -> List[str]:
        """Get all directories recursively from default disk."""
        return self.disk().all_directories(directory)
    
    def make_directory(self, path: str) -> bool:
        """Create directory on default disk."""
        return self.disk().make_directory(path)
    
    def delete_directory(self, directory: str) -> bool:
        """Delete directory from default disk."""
        return self.disk().delete_directory(directory)
    
    # Additional Laravel-style methods
    def missing(self, path: str) -> bool:
        """Check if file is missing."""
        return not self.exists(path)
    
    def read(self, path: str) -> str:
        """Read file as string."""
        return self.get(path).decode('utf-8')
    
    def write(self, path: str, contents: str) -> bool:
        """Write string to file."""
        return self.put(path, contents)
    
    def read_stream(self, path: str) -> BinaryIO:
        """Get file as stream."""
        # This would return a proper stream
        import io
        return io.BytesIO(self.get(path))
    
    def write_stream(self, path: str, resource: BinaryIO) -> bool:
        """Write stream to file."""
        return self.put_file(path, resource)
    
    def url(self, path: str) -> str:
        """Get public URL for file."""
        # This would generate proper URLs
        return f"/storage/{path}"
    
    def temporary_url(self, path: str, expiration: datetime) -> str:
        """Get temporary URL for file."""
        # This would generate signed temporary URLs
        return self.url(path)
    
    def checksum(self, path: str) -> str:
        """Get file checksum."""
        contents = self.get(path)
        return hashlib.md5(contents).hexdigest()
    
    def mime_type(self, path: str) -> Optional[str]:
        """Get file MIME type."""
        mime_type, _ = mimetypes.guess_type(path)
        return mime_type
    
    def json(self, path: str) -> Any:
        """Read JSON file."""
        contents = self.read(path)
        return json.loads(contents)
    
    def put_json(self, path: str, data: Any) -> bool:
        """Write data as JSON file."""
        contents = json.dumps(data, indent=2)
        return self.write(path, contents)
    
    # Laravel-style helper methods
    def download(self, path: str, name: Optional[str] = None) -> bytes:
        """Download a file."""
        return self.get(path)
    
    def response(self, path: str, name: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        """Create a file response."""
        # This would be used in FastAPI to return file responses
        from fastapi.responses import Response
        contents = self.get(path)
        mime_type = self.mime_type(path) or 'application/octet-stream'
        
        response_headers = headers or {}
        if name:
            response_headers['Content-Disposition'] = f'attachment; filename="{name}"'
        
        return Response(
            content=contents,
            media_type=mime_type,
            headers=response_headers
        )
    
    def stream_download(self, path: str, name: Optional[str] = None):
        """Stream download a file."""
        # For large files, this would implement streaming
        return self.download(path, name)
    
    def put_file_as(self, path: str, file: Union[BinaryIO, TextIO], name: str) -> str:
        """Store file with a specific name."""
        full_path = f"{path.rstrip('/')}/{name}"
        self.put_file(full_path, file)
        return full_path
    
    def path(self, path: str) -> str:
        """Get absolute path to file."""
        disk = self.disk()
        if hasattr(disk, '_full_path'):
            return str(disk._full_path(path))
        return path
    
    def build_temp_url(self, path: str, expiration: datetime, options: Optional[Dict[str, Any]] = None) -> str:
        """Build a temporary URL with custom options."""
        return self.temporary_url(path, expiration)
    
    def with_disk(self, disk: str):
        """Return a new instance using the specified disk."""
        new_manager = FilesystemManager(self._config)
        new_manager.set_default_driver(disk)
        return new_manager
    
    def disk_config(self, disk: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a disk."""
        disk_name = disk or self._default_disk
        return self._config.get('disks', {}).get(disk_name, {})
    
    def available_drivers(self) -> List[str]:
        """Get list of available drivers."""
        return ['local', 's3', 'ftp', 'sftp', 'azure', 'gcs', 'dropbox', 'memory']
    
    def file_hash(self, path: str, algorithm: str = 'md5') -> str:
        """Get file hash using specified algorithm."""
        contents = self.get(path)
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(contents)
        return hash_obj.hexdigest()
    
    def file_exists_in_cloud(self, path: str) -> bool:
        """Check if file exists in cloud storage."""
        return self.cloud().exists(path)
    
    def sync_to_cloud(self, local_path: str, cloud_path: Optional[str] = None) -> bool:
        """Sync local file to cloud storage."""
        cloud_path = cloud_path or local_path
        if self.exists(local_path):
            contents = self.get(local_path)
            return self.cloud().put(cloud_path, contents)
        return False
    
    def sync_from_cloud(self, cloud_path: str, local_path: Optional[str] = None) -> bool:
        """Sync cloud file to local storage."""
        local_path = local_path or cloud_path
        if self.cloud().exists(cloud_path):
            contents = self.cloud().get(cloud_path)
            return self.put(local_path, contents)
        return False


# Global filesystem manager instance
filesystem_manager_instance: Optional[FilesystemManager] = None


def get_filesystem_manager() -> FilesystemManager:
    """Get the global filesystem manager instance."""
    global filesystem_manager_instance
    if filesystem_manager_instance is None:
        filesystem_manager_instance = FilesystemManager()
    return filesystem_manager_instance


def storage(disk: Optional[str] = None) -> FilesystemAdapter:
    """Get a filesystem disk."""
    return get_filesystem_manager().disk(disk)


# Convenience functions
def storage_path(path: str = '') -> str:
    """Get storage path."""
    from app.Foundation import app
    return app().storage_path(path)


def public_path(path: str = '') -> str:
    """Get public path."""
    from app.Foundation import app
    return app().public_path(path)


# Advanced filesystem adapters merged from LaravelFilesystemDrivers.py
import logging

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

try:
    from azure.storage.blob import BlobServiceClient, BlobClient
    from azure.core.exceptions import ResourceNotFoundError
    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False

try:
    from google.cloud import storage as gcs
    from google.api_core import exceptions as gcs_exceptions
    HAS_GCS = True
except ImportError:
    HAS_GCS = False

try:
    import dropbox
    from dropbox.exceptions import ApiError, AuthError
    HAS_DROPBOX = True
except ImportError:
    HAS_DROPBOX = False

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False


class S3FilesystemAdapter(FilesystemAdapter):
    """Amazon S3 filesystem adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        if not HAS_BOTO3:
            raise ImportError("boto3 is required for S3 filesystem. Install with: pip install boto3")
        
        self.bucket = config['bucket']
        self.region = config.get('region', 'us-east-1')
        self.visibility = config.get('visibility', 'private')
        self.path_style = config.get('use_path_style_endpoint', False)
        self.endpoint = config.get('endpoint')
        self.prefix = config.get('prefix', '').lstrip('/')
        
        # Configure S3 client
        aws_config = {
            'region_name': self.region,
            'aws_access_key_id': config.get('key'),
            'aws_secret_access_key': config.get('secret'),
        }
        
        if config.get('token'):
            aws_config['aws_session_token'] = config['token']
        
        if self.endpoint:
            aws_config['endpoint_url'] = self.endpoint
        
        self.s3_client = boto3.client('s3', **aws_config)
        self.s3_resource = boto3.resource('s3', **aws_config)
        self.bucket_resource = self.s3_resource.Bucket(self.bucket)
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _full_path(self, path: str) -> str:
        """Get full S3 key path."""
        path = path.lstrip('/')
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path
    
    def exists(self, path: str) -> bool:
        """Check if file exists."""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=self._full_path(path))
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def get(self, path: str) -> bytes:
        """Get file contents."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=self._full_path(path))
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
    def put(self, path: str, contents: Union[str, bytes]) -> bool:
        """Store a file."""
        try:
            if isinstance(contents, str):
                contents = contents.encode('utf-8')
            
            extra_args = {}
            if self.visibility == 'public':
                extra_args['ACL'] = 'public-read'
            
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=self._full_path(path),
                Body=contents,
                **extra_args
            )
            return True
        except Exception as e:
            self.logger.error(f"Error putting file {path}: {e}")
            return False
    
    def put_file(self, path: str, file: Union[BinaryIO, TextIO]) -> bool:
        """Store an uploaded file."""
        try:
            content = file.read()
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            return self.put(path, content)
        except Exception as e:
            self.logger.error(f"Error putting file {path}: {e}")
            return False
    
    def prepend(self, path: str, data: str) -> bool:
        """Prepend to a file."""
        try:
            existing = ""
            if self.exists(path):
                existing = self.get(path).decode('utf-8')
            return self.put(path, data + existing)
        except Exception as e:
            self.logger.error(f"Error prepending to file {path}: {e}")
            return False
    
    def append(self, path: str, data: str) -> bool:
        """Append to a file."""
        try:
            existing = ""
            if self.exists(path):
                existing = self.get(path).decode('utf-8')
            return self.put(path, existing + data)
        except Exception as e:
            self.logger.error(f"Error appending to file {path}: {e}")
            return False
    
    def delete(self, paths: Union[str, List[str]]) -> bool:
        """Delete file(s)."""
        if isinstance(paths, str):
            paths = [paths]
        
        try:
            delete_objects = [{'Key': self._full_path(path)} for path in paths]
            self.s3_client.delete_objects(
                Bucket=self.bucket,
                Delete={'Objects': delete_objects}
            )
            return True
        except Exception as e:
            self.logger.error(f"Error deleting files {paths}: {e}")
            return False
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy a file."""
        try:
            copy_source = {'Bucket': self.bucket, 'Key': self._full_path(from_path)}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket,
                Key=self._full_path(to_path)
            )
            return True
        except Exception as e:
            self.logger.error(f"Error copying file {from_path} to {to_path}: {e}")
            return False
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move a file."""
        try:
            if self.copy(from_path, to_path):
                return self.delete(from_path)
            return False
        except Exception as e:
            self.logger.error(f"Error moving file {from_path} to {to_path}: {e}")
            return False
    
    def size(self, path: str) -> int:
        """Get file size."""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=self._full_path(path))
            return response['ContentLength']
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
    def last_modified(self, path: str) -> int:
        """Get last modified timestamp."""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=self._full_path(path))
            return int(response['LastModified'].timestamp())
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
    def files(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of files."""
        prefix = self._full_path(directory) if directory else self.prefix
        if prefix and not prefix.endswith('/'):
            prefix += '/'
        
        files = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                
                # Remove prefix
                if self.prefix and key.startswith(self.prefix + '/'):
                    key = key[len(self.prefix) + 1:]
                elif self.prefix and key.startswith(self.prefix):
                    key = key[len(self.prefix):]
                
                # Check if it's a file (not directory)
                if not key.endswith('/'):
                    if recursive or '/' not in key.strip('/'):
                        files.append(key)
        
        return files
    
    def all_files(self, directory: Optional[str] = None) -> List[str]:
        """Get all files recursively."""
        return self.files(directory, recursive=True)
    
    def directories(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of directories."""
        prefix = self._full_path(directory) if directory else self.prefix
        if prefix and not prefix.endswith('/'):
            prefix += '/'
        
        directories = set()
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix, Delimiter='/'):
            # Common prefixes are directories
            for common_prefix in page.get('CommonPrefixes', []):
                dir_path = common_prefix['Prefix']
                
                # Remove prefix and trailing slash
                if self.prefix and dir_path.startswith(self.prefix + '/'):
                    dir_path = dir_path[len(self.prefix) + 1:]
                elif self.prefix and dir_path.startswith(self.prefix):
                    dir_path = dir_path[len(self.prefix):]
                
                dir_path = dir_path.rstrip('/')
                if dir_path:
                    directories.add(dir_path)
        
        return list(directories)
    
    def all_directories(self, directory: Optional[str] = None) -> List[str]:
        """Get all directories recursively."""
        return self.directories(directory, recursive=True)
    
    def make_directory(self, path: str) -> bool:
        """Create directory (S3 doesn't have directories, but we can create a marker)."""
        try:
            directory_path = self._full_path(path).rstrip('/') + '/'
            self.s3_client.put_object(Bucket=self.bucket, Key=directory_path)
            return True
        except Exception as e:
            self.logger.error(f"Error creating directory {path}: {e}")
            return False
    
    def delete_directory(self, directory: str) -> bool:
        """Delete directory and all contents."""
        try:
            prefix = self._full_path(directory)
            if not prefix.endswith('/'):
                prefix += '/'
            
            objects_to_delete = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get('Contents', []):
                    objects_to_delete.append({'Key': obj['Key']})
            
            if objects_to_delete:
                self.s3_client.delete_objects(
                    Bucket=self.bucket,
                    Delete={'Objects': objects_to_delete}
                )
            
            return True
        except Exception as e:
            self.logger.error(f"Error deleting directory {directory}: {e}")
            return False


class FTPFilesystemAdapter(FilesystemAdapter):
    """FTP filesystem adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        self.host = config['host']
        self.port = config.get('port', 21)
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.root = config.get('root', '/').rstrip('/')
        self.passive = config.get('passive', True)
        self.ssl = config.get('ssl', False)
        self.timeout = config.get('timeout', 30)
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _connect(self) -> ftplib.FTP:
        """Create FTP connection."""
        import ftplib
        
        if self.ssl:
            ftp = ftplib.FTP_TLS()
        else:
            ftp = ftplib.FTP()
        
        ftp.connect(self.host, self.port, timeout=self.timeout)
        ftp.login(self.username, self.password)
        
        if self.ssl:
            ftp.prot_p()  # Enable encryption for data transfers
        
        ftp.set_pasv(self.passive)
        
        if self.root:
            ftp.cwd(self.root)
        
        return ftp
    
    def _full_path(self, path: str) -> str:
        """Get full FTP path."""
        path = path.lstrip('/')
        if self.root:
            return f"{self.root}/{path}" if path else self.root
        return f"/{path}" if path else "/"
    
    def exists(self, path: str) -> bool:
        """Check if file exists."""
        import ftplib
        try:
            with self._connect() as ftp:
                try:
                    ftp.size(self._full_path(path))
                    return True
                except ftplib.error_perm:
                    return False
        except Exception:
            return False
    
    def get(self, path: str) -> bytes:
        """Get file contents."""
        import ftplib
        try:
            with self._connect() as ftp:
                bio = io.BytesIO()
                ftp.retrbinary(f'RETR {self._full_path(path)}', bio.write)
                return bio.getvalue()
        except ftplib.error_perm as e:
            if '550' in str(e):  # File not found
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
    def put(self, path: str, contents: Union[str, bytes]) -> bool:
        """Store a file."""
        try:
            if isinstance(contents, str):
                contents = contents.encode('utf-8')
            
            with self._connect() as ftp:
                # Create directory if needed
                dir_path = '/'.join(self._full_path(path).split('/')[:-1])
                if dir_path and dir_path != self.root:
                    self._make_directory_recursive(ftp, dir_path)
                
                bio = io.BytesIO(contents)
                ftp.storbinary(f'STOR {self._full_path(path)}', bio)
                return True
        except Exception as e:
            self.logger.error(f"Error putting file {path}: {e}")
            return False
    
    def put_file(self, path: str, file: Union[BinaryIO, TextIO]) -> bool:
        """Store an uploaded file."""
        try:
            content = file.read()
            if isinstance(content, str):
                content = content.encode('utf-8')
            return self.put(path, content)
        except Exception as e:
            self.logger.error(f"Error putting file {path}: {e}")
            return False
    
    def prepend(self, path: str, data: str) -> bool:
        """Prepend to a file."""
        try:
            existing = ""
            if self.exists(path):
                existing = self.get(path).decode('utf-8')
            return self.put(path, data + existing)
        except Exception:
            return False
    
    def append(self, path: str, data: str) -> bool:
        """Append to a file."""
        try:
            existing = ""
            if self.exists(path):
                existing = self.get(path).decode('utf-8')
            return self.put(path, existing + data)
        except Exception:
            return False
    
    def delete(self, paths: Union[str, List[str]]) -> bool:
        """Delete file(s)."""
        import ftplib
        if isinstance(paths, str):
            paths = [paths]
        
        try:
            with self._connect() as ftp:
                for path in paths:
                    try:
                        ftp.delete(self._full_path(path))
                    except ftplib.error_perm:
                        pass  # File might not exist
                return True
        except Exception:
            return False
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy a file."""
        try:
            contents = self.get(from_path)
            return self.put(to_path, contents)
        except Exception:
            return False
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move a file."""
        import ftplib
        try:
            with self._connect() as ftp:
                ftp.rename(self._full_path(from_path), self._full_path(to_path))
                return True
        except Exception:
            # Fallback to copy and delete
            if self.copy(from_path, to_path):
                return self.delete(from_path)
            return False
    
    def size(self, path: str) -> int:
        """Get file size."""
        import ftplib
        try:
            with self._connect() as ftp:
                return ftp.size(self._full_path(path))
        except ftplib.error_perm as e:
            if '550' in str(e):
                raise FileNotFoundError(f"File not found: {path}")
            raise
    
    def last_modified(self, path: str) -> int:
        """Get last modified timestamp."""
        try:
            with self._connect() as ftp:
                response = ftp.voidcmd(f'MDTM {self._full_path(path)}')
                # Parse MDTM response (format: 213 YYYYMMDDHHMMSS)
                timestamp_str = response.split()[1]
                dt = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                return int(dt.timestamp())
        except Exception:
            # Fallback to current time if MDTM not supported
            return int(datetime.now().timestamp())
    
    def files(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of files."""
        import ftplib
        try:
            with self._connect() as ftp:
                if directory:
                    ftp.cwd(self._full_path(directory))
                
                files = []
                items = ftp.nlst()
                
                for item in items:
                    try:
                        # Check if it's a file
                        ftp.size(item)
                        files.append(item)
                    except ftplib.error_perm:
                        # It's a directory or doesn't exist
                        pass
                
                return files
        except Exception:
            return []
    
    def all_files(self, directory: Optional[str] = None) -> List[str]:
        """Get all files recursively."""
        return self.files(directory, recursive=True)
    
    def directories(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of directories."""
        import ftplib
        try:
            with self._connect() as ftp:
                if directory:
                    ftp.cwd(self._full_path(directory))
                
                directories = []
                items = ftp.nlst()
                
                for item in items:
                    try:
                        # Try to change to directory
                        current_dir = ftp.pwd()
                        ftp.cwd(item)
                        ftp.cwd(current_dir)
                        directories.append(item)
                    except ftplib.error_perm:
                        # Not a directory
                        pass
                
                return directories
        except Exception:
            return []
    
    def all_directories(self, directory: Optional[str] = None) -> List[str]:
        """Get all directories recursively."""
        return self.directories(directory, recursive=True)
    
    def make_directory(self, path: str) -> bool:
        """Create directory."""
        try:
            with self._connect() as ftp:
                self._make_directory_recursive(ftp, self._full_path(path))
                return True
        except Exception:
            return False
    
    def delete_directory(self, directory: str) -> bool:
        """Delete directory."""
        try:
            with self._connect() as ftp:
                ftp.rmd(self._full_path(directory))
                return True
        except Exception:
            return False
    
    def _make_directory_recursive(self, ftp, path: str) -> None:
        """Create directory recursively."""
        import ftplib
        parts = path.strip('/').split('/')
        current_path = ''
        
        for part in parts:
            if part:
                current_path += f'/{part}'
                try:
                    ftp.mkd(current_path)
                except ftplib.error_perm:
                    # Directory might already exist
                    pass


# Add more adapters as needed for SFTP, Azure, GCS, Dropbox, etc.
class SFTPFilesystemAdapter(FilesystemAdapter):
    """SFTP filesystem adapter stub."""
    
    def __init__(self, config: Dict[str, Any]):
        if not HAS_PARAMIKO:
            raise ImportError("paramiko is required for SFTP filesystem. Install with: pip install paramiko")
        raise NotImplementedError("SFTP adapter implementation required")
    
    def exists(self, path: str) -> bool: raise NotImplementedError
    def get(self, path: str) -> bytes: raise NotImplementedError
    def put(self, path: str, contents: Union[str, bytes]) -> bool: raise NotImplementedError
    def put_file(self, path: str, file: Union[BinaryIO, TextIO]) -> bool: raise NotImplementedError
    def prepend(self, path: str, data: str) -> bool: raise NotImplementedError
    def append(self, path: str, data: str) -> bool: raise NotImplementedError
    def delete(self, paths: Union[str, List[str]]) -> bool: raise NotImplementedError
    def copy(self, from_path: str, to_path: str) -> bool: raise NotImplementedError
    def move(self, from_path: str, to_path: str) -> bool: raise NotImplementedError
    def size(self, path: str) -> int: raise NotImplementedError
    def last_modified(self, path: str) -> int: raise NotImplementedError
    def files(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]: raise NotImplementedError
    def all_files(self, directory: Optional[str] = None) -> List[str]: raise NotImplementedError
    def directories(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]: raise NotImplementedError
    def all_directories(self, directory: Optional[str] = None) -> List[str]: raise NotImplementedError
    def make_directory(self, path: str) -> bool: raise NotImplementedError
    def delete_directory(self, directory: str) -> bool: raise NotImplementedError


class AzureBlobFilesystemAdapter(FilesystemAdapter):
    """Azure Blob Storage filesystem adapter stub."""
    
    def __init__(self, config: Dict[str, Any]):
        if not HAS_AZURE:
            raise ImportError("azure-storage-blob is required for Azure filesystem. Install with: pip install azure-storage-blob")
        raise NotImplementedError("Azure adapter implementation required")
    
    def exists(self, path: str) -> bool: raise NotImplementedError
    def get(self, path: str) -> bytes: raise NotImplementedError
    def put(self, path: str, contents: Union[str, bytes]) -> bool: raise NotImplementedError
    def put_file(self, path: str, file: Union[BinaryIO, TextIO]) -> bool: raise NotImplementedError
    def prepend(self, path: str, data: str) -> bool: raise NotImplementedError
    def append(self, path: str, data: str) -> bool: raise NotImplementedError
    def delete(self, paths: Union[str, List[str]]) -> bool: raise NotImplementedError
    def copy(self, from_path: str, to_path: str) -> bool: raise NotImplementedError
    def move(self, from_path: str, to_path: str) -> bool: raise NotImplementedError
    def size(self, path: str) -> int: raise NotImplementedError
    def last_modified(self, path: str) -> int: raise NotImplementedError
    def files(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]: raise NotImplementedError
    def all_files(self, directory: Optional[str] = None) -> List[str]: raise NotImplementedError
    def directories(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]: raise NotImplementedError
    def all_directories(self, directory: Optional[str] = None) -> List[str]: raise NotImplementedError
    def make_directory(self, path: str) -> bool: raise NotImplementedError
    def delete_directory(self, directory: str) -> bool: raise NotImplementedError


class GoogleCloudStorageAdapter(FilesystemAdapter):
    """Google Cloud Storage filesystem adapter stub."""
    
    def __init__(self, config: Dict[str, Any]):
        if not HAS_GCS:
            raise ImportError("google-cloud-storage is required for GCS filesystem. Install with: pip install google-cloud-storage")
        raise NotImplementedError("GCS adapter implementation required")
    
    def exists(self, path: str) -> bool: raise NotImplementedError
    def get(self, path: str) -> bytes: raise NotImplementedError
    def put(self, path: str, contents: Union[str, bytes]) -> bool: raise NotImplementedError
    def put_file(self, path: str, file: Union[BinaryIO, TextIO]) -> bool: raise NotImplementedError
    def prepend(self, path: str, data: str) -> bool: raise NotImplementedError
    def append(self, path: str, data: str) -> bool: raise NotImplementedError
    def delete(self, paths: Union[str, List[str]]) -> bool: raise NotImplementedError
    def copy(self, from_path: str, to_path: str) -> bool: raise NotImplementedError
    def move(self, from_path: str, to_path: str) -> bool: raise NotImplementedError
    def size(self, path: str) -> int: raise NotImplementedError
    def last_modified(self, path: str) -> int: raise NotImplementedError
    def files(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]: raise NotImplementedError
    def all_files(self, directory: Optional[str] = None) -> List[str]: raise NotImplementedError
    def directories(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]: raise NotImplementedError
    def all_directories(self, directory: Optional[str] = None) -> List[str]: raise NotImplementedError
    def make_directory(self, path: str) -> bool: raise NotImplementedError
    def delete_directory(self, directory: str) -> bool: raise NotImplementedError


class DropboxFilesystemAdapter(FilesystemAdapter):
    """Dropbox filesystem adapter stub."""
    
    def __init__(self, config: Dict[str, Any]):
        if not HAS_DROPBOX:
            raise ImportError("dropbox is required for Dropbox filesystem. Install with: pip install dropbox")
        raise NotImplementedError("Dropbox adapter implementation required")
    
    def exists(self, path: str) -> bool: raise NotImplementedError
    def get(self, path: str) -> bytes: raise NotImplementedError
    def put(self, path: str, contents: Union[str, bytes]) -> bool: raise NotImplementedError
    def put_file(self, path: str, file: Union[BinaryIO, TextIO]) -> bool: raise NotImplementedError
    def prepend(self, path: str, data: str) -> bool: raise NotImplementedError
    def append(self, path: str, data: str) -> bool: raise NotImplementedError
    def delete(self, paths: Union[str, List[str]]) -> bool: raise NotImplementedError
    def copy(self, from_path: str, to_path: str) -> bool: raise NotImplementedError
    def move(self, from_path: str, to_path: str) -> bool: raise NotImplementedError
    def size(self, path: str) -> int: raise NotImplementedError
    def last_modified(self, path: str) -> int: raise NotImplementedError
    def files(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]: raise NotImplementedError
    def all_files(self, directory: Optional[str] = None) -> List[str]: raise NotImplementedError
    def directories(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]: raise NotImplementedError
    def all_directories(self, directory: Optional[str] = None) -> List[str]: raise NotImplementedError
    def make_directory(self, path: str) -> bool: raise NotImplementedError
    def delete_directory(self, directory: str) -> bool: raise NotImplementedError


class MemoryFilesystemAdapter(FilesystemAdapter):
    """In-memory filesystem adapter for testing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._files: Dict[str, bytes] = {}
        self._directories: set[str] = set()
        self._metadata: Dict[str, Dict[str, Any]] = {}
        
    def _normalize_path(self, path: str) -> str:
        """Normalize path."""
        return path.lstrip('/')
    
    def exists(self, path: str) -> bool:
        """Check if file exists."""
        return self._normalize_path(path) in self._files
    
    def get(self, path: str) -> bytes:
        """Get file contents."""
        normalized_path = self._normalize_path(path)
        if normalized_path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._files[normalized_path]
    
    def put(self, path: str, contents: Union[str, bytes]) -> bool:
        """Store a file."""
        if isinstance(contents, str):
            contents = contents.encode('utf-8')
        
        normalized_path = self._normalize_path(path)
        self._files[normalized_path] = contents
        self._metadata[normalized_path] = {
            'size': len(contents),
            'last_modified': int(datetime.now().timestamp())
        }
        
        # Ensure parent directories exist
        parts = normalized_path.split('/')
        for i in range(len(parts) - 1):
            dir_path = '/'.join(parts[:i+1])
            self._directories.add(dir_path)
        
        return True
    
    def put_file(self, path: str, file: Union[BinaryIO, TextIO]) -> bool:
        """Store an uploaded file."""
        content = file.read()
        if isinstance(content, str):
            content = content.encode('utf-8')
        return self.put(path, content)
    
    def prepend(self, path: str, data: str) -> bool:
        """Prepend to a file."""
        existing = ""
        if self.exists(path):
            existing = self.get(path).decode('utf-8')
        return self.put(path, data + existing)
    
    def append(self, path: str, data: str) -> bool:
        """Append to a file."""
        existing = ""
        if self.exists(path):
            existing = self.get(path).decode('utf-8')
        return self.put(path, existing + data)
    
    def delete(self, paths: Union[str, List[str]]) -> bool:
        """Delete file(s)."""
        if isinstance(paths, str):
            paths = [paths]
        
        for path in paths:
            normalized_path = self._normalize_path(path)
            if normalized_path in self._files:
                del self._files[normalized_path]
                if normalized_path in self._metadata:
                    del self._metadata[normalized_path]
        
        return True
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy a file."""
        if not self.exists(from_path):
            return False
        
        contents = self.get(from_path)
        return self.put(to_path, contents)
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move a file."""
        if self.copy(from_path, to_path):
            return self.delete(from_path)
        return False
    
    def size(self, path: str) -> int:
        """Get file size."""
        normalized_path = self._normalize_path(path)
        if normalized_path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._metadata[normalized_path]['size']
    
    def last_modified(self, path: str) -> int:
        """Get last modified timestamp."""
        normalized_path = self._normalize_path(path)
        if normalized_path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._metadata[normalized_path]['last_modified']
    
    def files(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of files."""
        if directory is None:
            prefix = ""
        else:
            prefix = self._normalize_path(directory)
            if prefix and not prefix.endswith('/'):
                prefix += '/'
        
        files = []
        for file_path in self._files.keys():
            if file_path.startswith(prefix):
                relative_path = file_path[len(prefix):]
                if recursive or '/' not in relative_path:
                    files.append(relative_path)
        
        return files
    
    def all_files(self, directory: Optional[str] = None) -> List[str]:
        """Get all files recursively."""
        return self.files(directory, recursive=True)
    
    def directories(self, directory: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Get list of directories."""
        if directory is None:
            prefix = ""
        else:
            prefix = self._normalize_path(directory)
            if prefix and not prefix.endswith('/'):
                prefix += '/'
        
        dirs = []
        for dir_path in self._directories:
            if dir_path.startswith(prefix):
                relative_path = dir_path[len(prefix):]
                if recursive or '/' not in relative_path:
                    dirs.append(relative_path)
        
        return dirs
    
    def all_directories(self, directory: Optional[str] = None) -> List[str]:
        """Get all directories recursively."""
        return self.directories(directory, recursive=True)
    
    def make_directory(self, path: str) -> bool:
        """Create directory."""
        normalized_path = self._normalize_path(path)
        self._directories.add(normalized_path)
        return True
    
    def delete_directory(self, directory: str) -> bool:
        """Delete directory."""
        normalized_path = self._normalize_path(directory)
        if normalized_path in self._directories:
            self._directories.remove(normalized_path)
        
        # Delete all files in directory
        prefix = normalized_path + '/' if normalized_path else ''
        files_to_delete = [
            file_path for file_path in self._files.keys()
            if file_path.startswith(prefix)
        ]
        
        for file_path in files_to_delete:
            del self._files[file_path]
            if file_path in self._metadata:
                del self._metadata[file_path]
        
        return True