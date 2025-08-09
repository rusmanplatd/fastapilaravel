from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, BinaryIO, Callable, Set
from dataclasses import dataclass, field
from pathlib import Path
import uuid
import mimetypes
import hashlib
import tempfile
import os
from datetime import datetime

from fastapi import UploadFile, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from PIL import Image
import magic

from .FilesystemAdapter import FilesystemAdapter
from .CloudStorageAdapters import S3FilesystemAdapter


@dataclass
class UploadConfig:
    """Configuration for file uploads."""
    
    # File size limits
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_total_size: int = 100 * 1024 * 1024  # 100MB
    
    # Allowed file types
    allowed_extensions: Set[str] = field(default_factory=lambda: {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',  # Images
        '.pdf', '.doc', '.docx', '.txt', '.rtf',  # Documents
        '.mp4', '.avi', '.mov', '.mkv', '.webm',  # Videos
        '.mp3', '.wav', '.flac', '.ogg',  # Audio
        '.zip', '.rar', '.tar', '.gz'  # Archives
    })
    
    allowed_mime_types: Set[str] = field(default_factory=lambda: {
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
        'application/pdf', 'text/plain', 'text/rtf',
        'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo',
        'audio/mpeg', 'audio/wav', 'audio/x-flac', 'audio/ogg',
        'application/zip', 'application/x-rar-compressed'
    })
    
    # Upload paths
    upload_path: str = 'uploads'
    organize_by_date: bool = True
    organize_by_type: bool = True
    
    # Security
    scan_for_viruses: bool = False
    check_file_headers: bool = True
    sanitize_filename: bool = True
    
    # Image processing
    auto_resize_images: bool = False
    max_image_width: int = 1920
    max_image_height: int = 1080
    image_quality: int = 85
    generate_thumbnails: bool = False
    thumbnail_sizes: List[tuple] = field(default_factory=lambda: [(150, 150), (300, 300)])


@dataclass 
class UploadResult:
    """Result of a file upload operation."""
    
    success: bool
    file_path: str
    original_filename: str
    size: int
    mime_type: str
    hash: str
    url: Optional[str] = None
    thumbnail_urls: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class FileValidator:
    """Validates uploaded files according to configuration."""
    
    def __init__(self, config: UploadConfig):
        self.config = config
    
    def validate_file(self, file: UploadFile) -> None:
        """Validate an uploaded file."""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.config.allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File extension '{file_ext}' not allowed"
            )
        
        # Check MIME type
        if file.content_type and file.content_type not in self.config.allowed_mime_types:
            raise HTTPException(
                status_code=400,
                detail=f"MIME type '{file.content_type}' not allowed"
            )
        
        # Check file size
        if hasattr(file, 'size') and file.size > self.config.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {self.config.max_file_size} bytes"
            )
    
    def validate_file_content(self, file_path: str) -> None:
        """Validate file content using file headers."""
        if not self.config.check_file_headers:
            return
        
        try:
            # Check file magic bytes
            file_type = magic.from_file(file_path, mime=True)
            
            # Verify the detected MIME type is allowed
            if file_type not in self.config.allowed_mime_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"File content type '{file_type}' not allowed"
                )
        except Exception:
            # magic library not available or other error
            pass


class FileNameSanitizer:
    """Sanitizes file names for safe storage."""
    
    @staticmethod
    def sanitize(filename: str) -> str:
        """Sanitize a filename."""
        # Remove or replace dangerous characters
        import re
        
        # Get file extension
        path = Path(filename)
        name = path.stem
        ext = path.suffix
        
        # Remove dangerous characters
        name = re.sub(r'[^\w\-_.]', '_', name)
        
        # Remove multiple underscores
        name = re.sub(r'_+', '_', name)
        
        # Trim underscores from start/end
        name = name.strip('_')
        
        # Ensure we have a name
        if not name:
            name = 'file'
        
        return f"{name}{ext}"
    
    @staticmethod
    def generate_unique_name(original_filename: str) -> str:
        """Generate a unique filename."""
        path = Path(original_filename)
        name = path.stem
        ext = path.suffix
        
        # Add UUID to ensure uniqueness
        unique_id = str(uuid.uuid4())[:8]
        
        return f"{name}_{unique_id}{ext}"


class ImageProcessor:
    """Processes uploaded images."""
    
    def __init__(self, config: UploadConfig):
        self.config = config
    
    def process_image(self, file_path: str, storage: FilesystemAdapter) -> Dict[str, str]:
        """Process an uploaded image."""
        thumbnail_urls = {}
        
        try:
            # Open image
            with Image.open(file_path) as img:
                # Auto-resize if enabled
                if self.config.auto_resize_images:
                    self._resize_image(img, file_path)
                
                # Generate thumbnails if enabled
                if self.config.generate_thumbnails:
                    thumbnail_urls = self._generate_thumbnails(img, file_path, storage)
            
        except Exception as e:
            print(f"Image processing error: {e}")
        
        return thumbnail_urls
    
    def _resize_image(self, img: Image.Image, file_path: str) -> None:
        """Resize image if it exceeds maximum dimensions."""
        if (img.width > self.config.max_image_width or 
            img.height > self.config.max_image_height):
            
            img.thumbnail(
                (self.config.max_image_width, self.config.max_image_height),
                Image.Resampling.LANCZOS
            )
            
            # Save resized image
            img.save(file_path, quality=self.config.image_quality, optimize=True)
    
    def _generate_thumbnails(
        self, 
        img: Image.Image, 
        original_path: str, 
        storage: FilesystemAdapter
    ) -> Dict[str, str]:
        """Generate thumbnails for an image."""
        thumbnail_urls = {}
        
        for width, height in self.config.thumbnail_sizes:
            # Create thumbnail
            thumbnail = img.copy()
            thumbnail.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            # Generate thumbnail path
            path = Path(original_path)
            thumb_path = f"{path.parent}/{path.stem}_thumb_{width}x{height}{path.suffix}"
            
            # Save thumbnail to temporary file
            with tempfile.NamedTemporaryFile(suffix=path.suffix, delete=False) as temp_file:
                thumbnail.save(temp_file.name, quality=self.config.image_quality)
                
                # Upload thumbnail to storage
                with open(temp_file.name, 'rb') as thumb_file:
                    storage.put(thumb_path, thumb_file.read())
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
                # Generate URL if storage supports it
                if hasattr(storage, 'url'):
                    thumbnail_urls[f"{width}x{height}"] = storage.url(thumb_path)
        
        return thumbnail_urls


class UploadHandler:
    """Handles file uploads with validation, processing, and storage."""
    
    def __init__(
        self, 
        storage: FilesystemAdapter, 
        config: Optional[UploadConfig] = None
    ):
        self.storage = storage
        self.config = config or UploadConfig()
        self.validator = FileValidator(self.config)
        self.sanitizer = FileNameSanitizer()
        self.image_processor = ImageProcessor(self.config)
    
    async def upload_file(
        self, 
        file: UploadFile,
        path_override: Optional[str] = None,
        filename_override: Optional[str] = None
    ) -> UploadResult:
        """Upload a single file."""
        try:
            # Validate file
            self.validator.validate_file(file)
            
            # Read file content
            content = await file.read()
            
            # Generate file path
            if filename_override:
                filename = filename_override
            elif self.config.sanitize_filename:
                filename = self.sanitizer.sanitize(file.filename)
            else:
                filename = file.filename
            
            # Make filename unique
            filename = self.sanitizer.generate_unique_name(filename)
            
            # Generate storage path
            storage_path = path_override or self._generate_storage_path(filename)
            full_path = f"{storage_path}/{filename}"
            
            # Calculate file hash
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Save to temporary file for content validation and processing
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name
            
            try:
                # Validate file content
                self.validator.validate_file_content(temp_path)
                
                # Store file
                success = self.storage.put(full_path, content)
                
                if not success:
                    return UploadResult(
                        success=False,
                        file_path="",
                        original_filename=file.filename,
                        size=len(content),
                        mime_type=file.content_type or "",
                        hash=file_hash,
                        error="Failed to store file"
                    )
                
                # Process image if applicable
                thumbnail_urls = {}
                if self._is_image(file.content_type):
                    thumbnail_urls = self.image_processor.process_image(temp_path, self.storage)
                
                # Generate URL if storage supports it
                url = None
                if hasattr(self.storage, 'url'):
                    url = self.storage.url(full_path)
                
                # Get file metadata
                metadata = self._extract_metadata(temp_path, file.content_type)
                
                return UploadResult(
                    success=True,
                    file_path=full_path,
                    original_filename=file.filename,
                    size=len(content),
                    mime_type=file.content_type or "",
                    hash=file_hash,
                    url=url,
                    thumbnail_urls=thumbnail_urls,
                    metadata=metadata
                )
            
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
                
        except HTTPException:
            raise
        except Exception as e:
            return UploadResult(
                success=False,
                file_path="",
                original_filename=file.filename or "",
                size=0,
                mime_type="",
                hash="",
                error=str(e)
            )
    
    async def upload_multiple_files(
        self, 
        files: List[UploadFile],
        path_override: Optional[str] = None
    ) -> List[UploadResult]:
        """Upload multiple files."""
        results = []
        total_size = 0
        
        # Check total size limit
        for file in files:
            if hasattr(file, 'size'):
                total_size += file.size
        
        if total_size > self.config.max_total_size:
            raise HTTPException(
                status_code=413,
                detail=f"Total upload size too large. Maximum: {self.config.max_total_size} bytes"
            )
        
        # Upload each file
        for file in files:
            result = await self.upload_file(file, path_override)
            results.append(result)
        
        return results
    
    def download_file(self, file_path: str, filename: Optional[str] = None) -> FileResponse:
        """Download a file from storage."""
        if not self.storage.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # For local storage, return FileResponse
        if hasattr(self.storage, '_full_path'):
            local_path = self.storage._full_path(file_path)
            return FileResponse(
                path=str(local_path),
                filename=filename or Path(file_path).name
            )
        
        # For cloud storage, stream the file
        content = self.storage.get(file_path)
        if content is None:
            raise HTTPException(status_code=404, detail="File not found")
        
        def generate():
            yield content
        
        return StreamingResponse(
            generate(),
            media_type='application/octet-stream',
            headers={'Content-Disposition': f'attachment; filename="{filename or Path(file_path).name}"'}
        )
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about a stored file."""
        if not self.storage.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        info = {
            'path': file_path,
            'size': self.storage.size(file_path),
            'last_modified': self.storage.last_modified(file_path),
            'mime_type': self.storage.mime_type(file_path)
        }
        
        # Add URL if storage supports it
        if hasattr(self.storage, 'url'):
            info['url'] = self.storage.url(file_path)
        
        # Add signed URL if storage supports it
        if hasattr(self.storage, 'temporary_url'):
            info['download_url'] = self.storage.temporary_url(file_path, expires_in=3600)
        
        return info
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage."""
        return self.storage.delete(file_path)
    
    def _generate_storage_path(self, filename: str) -> str:
        """Generate storage path for a file."""
        path_parts = [self.config.upload_path]
        
        # Organize by date
        if self.config.organize_by_date:
            now = datetime.now()
            path_parts.extend([str(now.year), f"{now.month:02d}", f"{now.day:02d}"])
        
        # Organize by file type
        if self.config.organize_by_type:
            file_ext = Path(filename).suffix.lower()
            
            if file_ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}:
                path_parts.append('images')
            elif file_ext in {'.pdf', '.doc', '.docx', '.txt', '.rtf'}:
                path_parts.append('documents')
            elif file_ext in {'.mp4', '.avi', '.mov', '.mkv', '.webm'}:
                path_parts.append('videos')
            elif file_ext in {'.mp3', '.wav', '.flac', '.ogg'}:
                path_parts.append('audio')
            else:
                path_parts.append('other')
        
        return '/'.join(path_parts)
    
    def _is_image(self, mime_type: Optional[str]) -> bool:
        """Check if file is an image."""
        if not mime_type:
            return False
        return mime_type.startswith('image/')
    
    def _extract_metadata(self, file_path: str, mime_type: Optional[str]) -> Dict[str, Any]:
        """Extract metadata from file."""
        metadata = {}
        
        try:
            if self._is_image(mime_type):
                # Extract image metadata
                with Image.open(file_path) as img:
                    metadata.update({
                        'width': img.width,
                        'height': img.height,
                        'format': img.format,
                        'mode': img.mode
                    })
                    
                    # Extract EXIF data
                    if hasattr(img, '_getexif') and img._getexif():
                        metadata['exif'] = dict(img._getexif())
        
        except Exception:
            pass
        
        return metadata


# Convenience functions
def create_upload_handler(
    storage: FilesystemAdapter,
    config: Optional[UploadConfig] = None
) -> UploadHandler:
    """Create an upload handler with the given storage and configuration."""
    return UploadHandler(storage, config)


def create_image_upload_handler(storage: FilesystemAdapter) -> UploadHandler:
    """Create an upload handler optimized for images."""
    config = UploadConfig(
        allowed_extensions={'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'},
        allowed_mime_types={'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'},
        auto_resize_images=True,
        generate_thumbnails=True,
        max_file_size=5 * 1024 * 1024  # 5MB
    )
    return UploadHandler(storage, config)


def create_document_upload_handler(storage: FilesystemAdapter) -> UploadHandler:
    """Create an upload handler optimized for documents."""
    config = UploadConfig(
        allowed_extensions={'.pdf', '.doc', '.docx', '.txt', '.rtf'},
        allowed_mime_types={
            'application/pdf', 'text/plain', 'text/rtf',
            'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        },
        max_file_size=20 * 1024 * 1024,  # 20MB
        auto_resize_images=False,
        generate_thumbnails=False
    )
    return UploadHandler(storage, config)