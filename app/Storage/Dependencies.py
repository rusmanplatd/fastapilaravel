from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Annotated
from fastapi import Depends, HTTPException, UploadFile, Form, File, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

from .FilesystemAdapter import FilesystemAdapter
from .UploadHandler import UploadHandler, UploadConfig, UploadResult
from .StorageFacade import Storage


class StorageConfig(BaseModel):
    """Configuration for storage dependencies."""
    
    disk: str = "local"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_files: int = 10
    allowed_extensions: List[str] = [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
        ".pdf", ".doc", ".docx", ".txt", ".rtf",
        ".mp4", ".avi", ".mov", ".mkv", ".webm",
        ".mp3", ".wav", ".flac", ".ogg",
        ".zip", ".rar", ".tar", ".gz"
    ]
    organize_by_date: bool = True
    auto_resize_images: bool = True
    generate_thumbnails: bool = True


class UploadParameters(BaseModel):
    """Parameters for file upload."""
    
    path: Optional[str] = Field(None, description="Custom upload path")
    filename: Optional[str] = Field(None, description="Custom filename")
    public: bool = Field(False, description="Make file publicly accessible")
    overwrite: bool = Field(False, description="Overwrite existing file")


# Storage Dependencies

def get_storage_disk(disk_name: str = "local") -> FilesystemAdapter:
    """Get a storage disk instance."""
    try:
        return Storage.disk(disk_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def get_default_storage() -> FilesystemAdapter:
    """Get the default storage disk."""
    return Storage.disk()


def get_upload_handler(
    storage: FilesystemAdapter = Depends(get_default_storage),
    config: Optional[UploadConfig] = None
) -> UploadHandler:
    """Get an upload handler with the default storage."""
    return UploadHandler(storage, config)


def get_image_upload_handler(
    storage: FilesystemAdapter = Depends(get_default_storage)
) -> UploadHandler:
    """Get an upload handler optimized for images."""
    from .UploadHandler import create_image_upload_handler
    return create_image_upload_handler(storage)


def get_document_upload_handler(
    storage: FilesystemAdapter = Depends(get_default_storage)
) -> UploadHandler:
    """Get an upload handler optimized for documents."""
    from .UploadHandler import create_document_upload_handler
    return create_document_upload_handler(storage)


# File Upload Dependencies

async def single_file_upload(
    file: UploadFile = File(...),
    params: UploadParameters = Depends(),
    handler: UploadHandler = Depends(get_upload_handler)
) -> UploadResult:
    """Handle single file upload."""
    return await handler.upload_file(
        file=file,
        path_override=params.path,
        filename_override=params.filename
    )


async def multiple_file_upload(
    files: List[UploadFile] = File(...),
    path: Optional[str] = Form(None),
    handler: UploadHandler = Depends(get_upload_handler)
) -> List[UploadResult]:
    """Handle multiple file uploads."""
    return await handler.upload_multiple_files(files, path)


async def image_upload(
    file: UploadFile = File(...),
    params: UploadParameters = Depends(),
    handler: UploadHandler = Depends(get_image_upload_handler)
) -> UploadResult:
    """Handle image file upload with processing."""
    return await handler.upload_file(
        file=file,
        path_override=params.path,
        filename_override=params.filename
    )


async def document_upload(
    file: UploadFile = File(...),
    params: UploadParameters = Depends(),
    handler: UploadHandler = Depends(get_document_upload_handler)
) -> UploadResult:
    """Handle document file upload."""
    return await handler.upload_file(
        file=file,
        path_override=params.path,
        filename_override=params.filename
    )


# File Management Dependencies

def create_file_manager_dependency(
    disk: str = "local",
    require_auth: bool = False
) -> Callable[..., Any]:
    """Create a file manager dependency for a specific disk."""
    
    def file_manager(
        storage: FilesystemAdapter = Depends(lambda: get_storage_disk(disk))
    ) -> 'FileManager':
        return FileManager(storage)
    
    if require_auth:
        # Add authentication requirement
        security = HTTPBearer()
        
        def authenticated_file_manager(
            storage: FilesystemAdapter = Depends(lambda: get_storage_disk(disk)),
            token: str = Depends(security)
        ) -> 'FileManager':
            # Here you would validate the token
            # For now, we'll just return the manager
            return FileManager(storage)
        
        return authenticated_file_manager
    
    return file_manager


class FileManager:
    """File management utility with storage operations."""
    
    def __init__(self, storage: FilesystemAdapter):
        self.storage = storage
    
    def exists(self, path: str) -> bool:
        """Check if file exists."""
        return self.storage.exists(path)
    
    def get_info(self, path: str) -> Dict[str, Any]:
        """Get file information."""
        if not self.storage.exists(path):
            raise HTTPException(status_code=404, detail="File not found")
        
        info = {
            'path': path,
            'size': self.storage.size(path),
            'last_modified': self.storage.last_modified(path),
            'mime_type': self.storage.mime_type(path)
        }
        
        if hasattr(self.storage, 'url'):
            info['url'] = self.storage.url(path)
        
        return info
    
    def delete(self, path: str) -> bool:
        """Delete a file."""
        if not self.storage.exists(path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return self.storage.delete(path)
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy a file."""
        if not self.storage.exists(from_path):
            raise HTTPException(status_code=404, detail="Source file not found")
        
        return self.storage.copy(from_path, to_path)
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move a file."""
        if not self.storage.exists(from_path):
            raise HTTPException(status_code=404, detail="Source file not found")
        
        return self.storage.move(from_path, to_path)
    
    def list_files(self, directory: str = "") -> List[str]:
        """List files in directory."""
        return self.storage.files(directory)
    
    def list_directories(self, directory: str = "") -> List[str]:
        """List directories."""
        return self.storage.directories(directory)


# Specialized Dependencies

def create_upload_dependency(
    allowed_extensions: Optional[List[str]] = None,
    max_file_size: int = 10 * 1024 * 1024,
    max_files: int = 10,
    disk: str = "local"
) -> Callable[..., Any]:
    """Create a custom upload dependency with specific restrictions."""
    
    config = UploadConfig(
        allowed_extensions=set(allowed_extensions) if allowed_extensions else set(),
        max_file_size=max_file_size,
        max_total_size=max_file_size * max_files
    )
    
    def custom_upload_handler(
        storage: FilesystemAdapter = Depends(lambda: get_storage_disk(disk))
    ) -> UploadHandler:
        return UploadHandler(storage, config)
    
    return custom_upload_handler


def create_image_dependency(
    max_size: int = 5 * 1024 * 1024,
    auto_resize: bool = True,
    generate_thumbnails: bool = True,
    disk: str = "local"
) -> Callable[..., Any]:
    """Create an image upload dependency."""
    
    config = UploadConfig(
        allowed_extensions={'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'},
        allowed_mime_types={'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'},
        max_file_size=max_size,
        auto_resize_images=auto_resize,
        generate_thumbnails=generate_thumbnails
    )
    
    def image_handler(
        storage: FilesystemAdapter = Depends(lambda: get_storage_disk(disk))
    ) -> UploadHandler:
        return UploadHandler(storage, config)
    
    return image_handler


def create_document_dependency(
    max_size: int = 20 * 1024 * 1024,
    disk: str = "local"
) -> Callable[..., Any]:
    """Create a document upload dependency."""
    
    config = UploadConfig(
        allowed_extensions={'.pdf', '.doc', '.docx', '.txt', '.rtf'},
        allowed_mime_types={
            'application/pdf', 'text/plain', 'text/rtf',
            'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        },
        max_file_size=max_size,
        auto_resize_images=False,
        generate_thumbnails=False
    )
    
    def document_handler(
        storage: FilesystemAdapter = Depends(lambda: get_storage_disk(disk))
    ) -> UploadHandler:
        return UploadHandler(storage, config)
    
    return document_handler


# Type aliases for convenience
StorageDisk = Annotated[FilesystemAdapter, Depends(get_default_storage)]
FileManagerDep = Annotated[FileManager, Depends(create_file_manager_dependency())]
UploadHandlerDep = Annotated[UploadHandler, Depends(get_upload_handler)]
ImageUploadDep = Annotated[UploadHandler, Depends(get_image_upload_handler)]
DocumentUploadDep = Annotated[UploadHandler, Depends(get_document_upload_handler)]

# Upload result dependencies
SingleUploadDep = Annotated[UploadResult, Depends(single_file_upload)]
MultipleUploadDep = Annotated[List[UploadResult], Depends(multiple_file_upload)]
ImageUploadResultDep = Annotated[UploadResult, Depends(image_upload)]
DocumentUploadResultDep = Annotated[UploadResult, Depends(document_upload)]


# Validation Dependencies

def validate_file_path(path: str) -> str:
    """Validate and sanitize file path."""
    # Remove any directory traversal attempts
    import os.path
    normalized = os.path.normpath(path)
    if normalized.startswith('../') or normalized.startswith('/'):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return normalized


def validate_file_exists(
    path: str = Depends(validate_file_path),
    storage: FilesystemAdapter = Depends(get_default_storage)
) -> str:
    """Validate that a file exists."""
    if not storage.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return path


ValidatedPath = Annotated[str, Depends(validate_file_path)]
ExistingFile = Annotated[str, Depends(validate_file_exists)]