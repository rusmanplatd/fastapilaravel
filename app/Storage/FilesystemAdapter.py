from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, BinaryIO
from abc import ABC, abstractmethod
import os
import shutil
from pathlib import Path
from datetime import datetime
import mimetypes


class FilesystemAdapter(ABC):
    """Abstract filesystem adapter following Laravel's Storage interface."""
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        pass
    
    @abstractmethod
    def get(self, path: str) -> Optional[bytes]:
        """Get file contents."""
        pass
    
    @abstractmethod
    def put(self, path: str, contents: Union[str, bytes]) -> bool:
        """Store file contents."""
        pass
    
    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete a file."""
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
    def size(self, path: str) -> Optional[int]:
        """Get file size in bytes."""
        pass
    
    @abstractmethod
    def last_modified(self, path: str) -> Optional[datetime]:
        """Get last modified time."""
        pass
    
    @abstractmethod
    def files(self, directory: str = "") -> List[str]:
        """Get all files in a directory."""
        pass
    
    @abstractmethod
    def directories(self, directory: str = "") -> List[str]:
        """Get all directories in a directory."""
        pass
    
    def get_string(self, path: str) -> Optional[str]:
        """Get file contents as string."""
        contents = self.get(path)
        return contents.decode('utf-8') if contents else None
    
    def put_string(self, path: str, contents: str) -> bool:
        """Store string contents."""
        return self.put(path, contents.encode('utf-8'))
    
    def append(self, path: str, contents: Union[str, bytes]) -> bool:
        """Append to a file."""
        existing = self.get(path) or b""
        if isinstance(contents, str):
            contents = contents.encode('utf-8')
        return self.put(path, existing + contents)
    
    def prepend(self, path: str, contents: Union[str, bytes]) -> bool:
        """Prepend to a file."""
        existing = self.get(path) or b""
        if isinstance(contents, str):
            contents = contents.encode('utf-8')
        return self.put(path, contents + existing)
    
    def missing(self, path: str) -> bool:
        """Check if a file is missing."""
        return not self.exists(path)
    
    def mime_type(self, path: str) -> Optional[str]:
        """Get MIME type of a file."""
        mime_type, _ = mimetypes.guess_type(path)
        return mime_type


class LocalFilesystemAdapter(FilesystemAdapter):
    """Local filesystem adapter."""
    
    def __init__(self, root_path: str = "storage") -> None:
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)
    
    def _full_path(self, path: str) -> Path:
        """Get full filesystem path."""
        return self.root_path / path.lstrip('/')
    
    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        return self._full_path(path).exists()
    
    def get(self, path: str) -> Optional[bytes]:
        """Get file contents."""
        try:
            return self._full_path(path).read_bytes()
        except FileNotFoundError:
            return None
    
    def put(self, path: str, contents: Union[str, bytes]) -> bool:
        """Store file contents."""
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
    
    def delete(self, path: str) -> bool:
        """Delete a file."""
        try:
            self._full_path(path).unlink()
            return True
        except FileNotFoundError:
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
    
    def size(self, path: str) -> Optional[int]:
        """Get file size in bytes."""
        try:
            return self._full_path(path).stat().st_size
        except FileNotFoundError:
            return None
    
    def last_modified(self, path: str) -> Optional[datetime]:
        """Get last modified time."""
        try:
            timestamp = self._full_path(path).stat().st_mtime
            return datetime.fromtimestamp(timestamp)
        except FileNotFoundError:
            return None
    
    def files(self, directory: str = "") -> List[str]:
        """Get all files in a directory."""
        try:
            dir_path = self._full_path(directory)
            if not dir_path.is_dir():
                return []
            
            files = []
            for item in dir_path.iterdir():
                if item.is_file():
                    relative_path = str(item.relative_to(self.root_path))
                    files.append(relative_path)
            return sorted(files)
        except Exception:
            return []
    
    def directories(self, directory: str = "") -> List[str]:
        """Get all directories in a directory."""
        try:
            dir_path = self._full_path(directory)
            if not dir_path.is_dir():
                return []
            
            dirs = []
            for item in dir_path.iterdir():
                if item.is_dir():
                    relative_path = str(item.relative_to(self.root_path))
                    dirs.append(relative_path)
            return sorted(dirs)
        except Exception:
            return []
    
    def make_directory(self, path: str) -> bool:
        """Create a directory."""
        try:
            self._full_path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False
    
    def delete_directory(self, path: str) -> bool:
        """Delete a directory."""
        try:
            shutil.rmtree(self._full_path(path))
            return True
        except Exception:
            return False


class S3FilesystemAdapter(FilesystemAdapter):
    """S3 filesystem adapter (placeholder)."""
    
    def __init__(self, bucket: str, region: str = "us-east-1", **kwargs: Any) -> None:
        self.bucket = bucket
        self.region = region
        self.config = kwargs
        # In real implementation, initialize boto3 client here
    
    def exists(self, path: str) -> bool:
        """Check if file exists in S3."""
        # Placeholder - would use boto3
        return False
    
    def get(self, path: str) -> Optional[bytes]:
        """Get file from S3."""
        # Placeholder - would use boto3
        return None
    
    def put(self, path: str, contents: Union[str, bytes]) -> bool:
        """Put file to S3."""
        # Placeholder - would use boto3
        return False
    
    def delete(self, path: str) -> bool:
        """Delete file from S3."""
        # Placeholder - would use boto3
        return False
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy file in S3."""
        # Placeholder - would use boto3
        return False
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move file in S3."""
        return self.copy(from_path, to_path) and self.delete(from_path)
    
    def size(self, path: str) -> Optional[int]:
        """Get file size from S3."""
        # Placeholder - would use boto3
        return None
    
    def last_modified(self, path: str) -> Optional[datetime]:
        """Get last modified time from S3."""
        # Placeholder - would use boto3
        return None
    
    def files(self, directory: str = "") -> List[str]:
        """List files in S3 directory."""
        # Placeholder - would use boto3
        return []
    
    def directories(self, directory: str = "") -> List[str]:
        """List directories in S3."""
        # Placeholder - would use boto3
        return []
    
    def url(self, path: str) -> str:
        """Get public URL for S3 object."""
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{path}"
    
    def temporary_url(self, path: str, expires_in: int = 3600) -> str:
        """Get temporary URL for S3 object."""
        # Placeholder - would use boto3 to generate presigned URL
        return self.url(path)


class StorageManager:
    """Laravel-style storage manager."""
    
    def __init__(self) -> None:
        self.disks: Dict[str, FilesystemAdapter] = {}
        self.default_disk = "local"
        
        # Register default disks
        self.disks["local"] = LocalFilesystemAdapter("storage/app")
        self.disks["public"] = LocalFilesystemAdapter("storage/app/public")
    
    def disk(self, name: Optional[str] = None) -> FilesystemAdapter:
        """Get a filesystem disk."""
        disk_name = name or self.default_disk
        if disk_name not in self.disks:
            raise ValueError(f"Disk '{disk_name}' not found")
        return self.disks[disk_name]
    
    def extend(self, name: str, adapter: FilesystemAdapter) -> None:
        """Register a custom filesystem adapter."""
        self.disks[name] = adapter
    
    # Proxy methods to default disk
    
    def exists(self, path: str) -> bool:
        """Check if file exists on default disk."""
        return self.disk().exists(path)
    
    def get(self, path: str) -> Optional[bytes]:
        """Get file from default disk."""
        return self.disk().get(path)
    
    def put(self, path: str, contents: Union[str, bytes]) -> bool:
        """Put file on default disk."""
        return self.disk().put(path, contents)
    
    def delete(self, path: str) -> bool:
        """Delete file from default disk."""
        return self.disk().delete(path)
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy file on default disk."""
        return self.disk().copy(from_path, to_path)
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move file on default disk."""
        return self.disk().move(from_path, to_path)
    
    def files(self, directory: str = "") -> List[str]:
        """List files on default disk."""
        return self.disk().files(directory)
    
    def download_response(self, path: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a download response."""
        contents = self.get(path)
        if contents is None:
            raise FileNotFoundError(f"File not found: {path}")
        
        filename = name or Path(path).name
        mime_type = self.disk().mime_type(path) or "application/octet-stream"
        
        return {
            "content": contents,
            "media_type": mime_type,
            "filename": filename,
            "headers": {
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        }


# Global storage manager
storage_manager = StorageManager()


def storage(disk: Optional[str] = None) -> FilesystemAdapter:
    """Get storage disk instance."""
    return storage_manager.disk(disk)