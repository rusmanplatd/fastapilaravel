"""
Laravel-style File Upload system with validation
"""
from __future__ import annotations

import os
import uuid
import hashlib
import mimetypes
from typing import Dict, List, Optional, Any, Union, BinaryIO
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from fastapi import UploadFile, HTTPException, status
from PIL import Image


class FileValidationError(Exception):
    """Custom exception for file validation errors"""
    pass


class ImageFormat(Enum):
    """Supported image formats"""
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    BMP = "bmp"


@dataclass
class UploadedFileInfo:
    """Information about an uploaded file"""
    filename: str
    original_filename: str
    mime_type: str
    size: int
    path: str
    url: str
    hash: str
    extension: str
    disk: str = "local"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class FileUploadValidator:
    """Laravel-style file upload validator"""
    
    def __init__(
        self,
        max_size: Optional[int] = None,  # in bytes
        allowed_mimes: Optional[List[str]] = None,
        allowed_extensions: Optional[List[str]] = None,
        min_width: Optional[int] = None,  # for images
        max_width: Optional[int] = None,  # for images
        min_height: Optional[int] = None,  # for images
        max_height: Optional[int] = None,  # for images
        required: bool = False
    ):
        self.max_size = max_size
        self.allowed_mimes = allowed_mimes or []
        self.allowed_extensions = allowed_extensions or []
        self.min_width = min_width
        self.max_width = max_width
        self.min_height = min_height
        self.max_height = max_height
        self.required = required
    
    def validate(self, file: UploadFile) -> None:
        """Validate uploaded file"""
        if not file:
            if self.required:
                raise FileValidationError("File is required")
            return
        
        # Check file size
        if self.max_size and file.size and file.size > self.max_size:
            raise FileValidationError(f"File size exceeds maximum allowed size of {self.max_size} bytes")
        
        # Check MIME type
        if self.allowed_mimes and file.content_type:
            if file.content_type not in self.allowed_mimes:
                raise FileValidationError(f"File type {file.content_type} is not allowed")
        
        # Check file extension
        if self.allowed_extensions and file.filename:
            ext = Path(file.filename).suffix.lower()
            if ext not in [f'.{ext}' if not ext.startswith('.') else ext for ext in self.allowed_extensions]:
                raise FileValidationError(f"File extension {ext} is not allowed")
        
        # Validate image dimensions if it's an image
        if file.content_type and file.content_type.startswith('image/'):
            self._validate_image_dimensions(file)
    
    def _validate_image_dimensions(self, file: UploadFile) -> None:
        """Validate image dimensions"""
        try:
            # Reset file pointer
            file.file.seek(0)
            
            # Open image
            with Image.open(file.file) as img:
                width, height = img.size
                
                if self.min_width and width < self.min_width:
                    raise FileValidationError(f"Image width {width}px is less than minimum {self.min_width}px")
                
                if self.max_width and width > self.max_width:
                    raise FileValidationError(f"Image width {width}px exceeds maximum {self.max_width}px")
                
                if self.min_height and height < self.min_height:
                    raise FileValidationError(f"Image height {height}px is less than minimum {self.min_height}px")
                
                if self.max_height and height > self.max_height:
                    raise FileValidationError(f"Image height {height}px exceeds maximum {self.max_height}px")
            
            # Reset file pointer again
            file.file.seek(0)
            
        except Exception as e:
            if isinstance(e, FileValidationError):
                raise
            raise FileValidationError(f"Invalid image file: {str(e)}")


class FileUploadManager:
    """Laravel-style file upload manager"""
    
    def __init__(self, storage_path: str = "storage/uploads"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def store(
        self,
        file: UploadFile,
        path: str = "",
        disk: str = "local",
        name: Optional[str] = None,
        validator: Optional[FileUploadValidator] = None
    ) -> UploadedFileInfo:
        """Store uploaded file"""
        
        # Validate file if validator provided
        if validator:
            validator.validate(file)
        
        if not file or not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Generate file info
        original_filename = file.filename
        extension = Path(original_filename).suffix.lower()
        filename = name or self._generate_filename(extension)
        
        # Create directory structure
        upload_path = self.storage_path / path
        upload_path.mkdir(parents=True, exist_ok=True)
        
        # Full file path
        file_path = upload_path / filename
        
        # Read file content
        content = await file.read()
        
        # Calculate file hash
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Write file to disk
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Get MIME type
        mime_type = file.content_type or mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
        
        # Generate URL (would be configurable in production)
        relative_path = file_path.relative_to(self.storage_path)
        url = f"/storage/{relative_path.as_posix()}"
        
        # Get file metadata
        metadata = self._get_file_metadata(file_path, mime_type)
        
        return UploadedFileInfo(
            filename=filename,
            original_filename=original_filename,
            mime_type=mime_type,
            size=len(content),
            path=str(file_path),
            url=url,
            hash=file_hash,
            extension=extension,
            disk=disk,
            metadata=metadata
        )
    
    async def store_multiple(
        self,
        files: List[UploadFile],
        path: str = "",
        disk: str = "local",
        validator: Optional[FileUploadValidator] = None
    ) -> List[UploadedFileInfo]:
        """Store multiple files"""
        uploaded_files = []
        
        for file in files:
            uploaded_file = await self.store(file, path, disk, validator=validator)
            uploaded_files.append(uploaded_file)
        
        return uploaded_files
    
    def delete(self, file_path: str) -> bool:
        """Delete uploaded file"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def exists(self, file_path: str) -> bool:
        """Check if file exists"""
        return Path(file_path).exists()
    
    def get_url(self, file_path: str) -> str:
        """Get public URL for file"""
        relative_path = Path(file_path).relative_to(self.storage_path)
        return f"/storage/{relative_path.as_posix()}"
    
    def _generate_filename(self, extension: str = "") -> str:
        """Generate unique filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}{extension}"
    
    def _get_file_metadata(self, file_path: Path, mime_type: str) -> Dict[str, Any]:
        """Get file metadata"""
        metadata = {
            'size': file_path.stat().st_size,
            'created_at': datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
            'modified_at': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        }
        
        # Add image-specific metadata
        if mime_type.startswith('image/'):
            try:
                with Image.open(file_path) as img:
                    metadata.update({
                        'width': img.width,
                        'height': img.height,
                        'format': img.format,
                        'mode': img.mode,
                    })
            except Exception:
                pass
        
        return metadata


class ImageUploadManager(FileUploadManager):
    """Specialized manager for image uploads with processing capabilities"""
    
    async def store_with_thumbnails(
        self,
        file: UploadFile,
        path: str = "",
        thumbnail_sizes: Optional[Dict[str, tuple]] = None,
        validator: Optional[FileUploadValidator] = None
    ) -> Dict[str, UploadedFileInfo]:
        """Store image with generated thumbnails"""
        
        if thumbnail_sizes is None:
            thumbnail_sizes = {
                'thumb': (150, 150),
                'medium': (300, 300),
                'large': (800, 800)
            }
        
        # Store original image
        original = await self.store(file, path, validator=validator)
        
        result = {'original': original}
        
        # Generate thumbnails
        if original.mime_type.startswith('image/'):
            for size_name, (width, height) in thumbnail_sizes.items():
                thumbnail = self._generate_thumbnail(original.path, width, height, size_name)
                if thumbnail:
                    result[size_name] = thumbnail
        
        return result
    
    def _generate_thumbnail(self, original_path: str, width: int, height: int, suffix: str) -> Optional[UploadedFileInfo]:
        """Generate thumbnail from original image"""
        try:
            with Image.open(original_path) as img:
                # Convert RGBA to RGB if saving as JPEG
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Create thumbnail
                img.thumbnail((width, height), Image.Resampling.LANCZOS)
                
                # Generate thumbnail filename
                original_path_obj = Path(original_path)
                thumbnail_filename = f"{original_path_obj.stem}_{suffix}{original_path_obj.suffix}"
                thumbnail_path = original_path_obj.parent / thumbnail_filename
                
                # Save thumbnail
                img.save(thumbnail_path, quality=85, optimize=True)
                
                # Create file info
                relative_path = thumbnail_path.relative_to(self.storage_path)
                url = f"/storage/{relative_path.as_posix()}"
                
                return UploadedFileInfo(
                    filename=thumbnail_filename,
                    original_filename=thumbnail_filename,
                    mime_type='image/jpeg',
                    size=thumbnail_path.stat().st_size,
                    path=str(thumbnail_path),
                    url=url,
                    hash=self._calculate_file_hash(thumbnail_path),
                    extension=original_path_obj.suffix,
                    metadata={
                        'width': img.width,
                        'height': img.height,
                        'thumbnail_of': original_path,
                        'thumbnail_size': f"{width}x{height}"
                    }
                )
                
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return None
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()


# Global upload manager instance
upload_manager = FileUploadManager()
image_upload_manager = ImageUploadManager()


# Laravel-style validation rules for common file types
class FileValidationRules:
    """Predefined validation rules for common file types"""
    
    @staticmethod
    def image(max_size: int = 2 * 1024 * 1024) -> FileUploadValidator:
        """Image upload validation (2MB max by default)"""
        return FileUploadValidator(
            max_size=max_size,
            allowed_mimes=['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp']
        )
    
    @staticmethod
    def avatar(max_size: int = 1024 * 1024) -> FileUploadValidator:
        """Avatar image validation with size constraints"""
        return FileUploadValidator(
            max_size=max_size,
            allowed_mimes=['image/jpeg', 'image/png'],
            allowed_extensions=['jpg', 'jpeg', 'png'],
            min_width=100,
            max_width=2000,
            min_height=100,
            max_height=2000
        )
    
    @staticmethod
    def document(max_size: int = 10 * 1024 * 1024) -> FileUploadValidator:
        """Document upload validation (10MB max)"""
        return FileUploadValidator(
            max_size=max_size,
            allowed_mimes=['application/pdf', 'application/msword', 
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'text/plain'],
            allowed_extensions=['pdf', 'doc', 'docx', 'txt']
        )
    
    @staticmethod
    def video(max_size: int = 50 * 1024 * 1024) -> FileUploadValidator:
        """Video upload validation (50MB max)"""
        return FileUploadValidator(
            max_size=max_size,
            allowed_mimes=['video/mp4', 'video/avi', 'video/quicktime', 'video/webm'],
            allowed_extensions=['mp4', 'avi', 'mov', 'webm']
        )
    
    @staticmethod
    def audio(max_size: int = 20 * 1024 * 1024) -> FileUploadValidator:
        """Audio upload validation (20MB max)"""
        return FileUploadValidator(
            max_size=max_size,
            allowed_mimes=['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4'],
            allowed_extensions=['mp3', 'wav', 'ogg', 'm4a']
        )