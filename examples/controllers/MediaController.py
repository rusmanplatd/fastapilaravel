"""
Example Media Controller demonstrating file upload functionality
"""
from __future__ import annotations

from typing import List, Dict, Any
from fastapi import UploadFile, HTTPException, status, Request, File, Form
from fastapi.responses import FileResponse

from app.Http.Controllers.BaseController import BaseController
from app.Http.Uploads import (
    upload_manager,
    image_upload_manager,
    FileValidationRules,
    FileValidationError,
    UploadedFileInfo
)


class MediaController(BaseController):
    """Laravel-style Media Controller for file uploads"""
    
    async def upload_image(
        self,
        request: Request,
        file: UploadFile = File(...),
        generate_thumbnails: bool = Form(False)
    ) -> Dict[str, Any]:
        """Upload image with optional thumbnail generation (POST /media/images)"""
        
        try:
            # Validate image
            validator = FileValidationRules.image(max_size=5 * 1024 * 1024)  # 5MB max
            
            if generate_thumbnails:
                # Upload with thumbnails
                uploaded_files = await image_upload_manager.store_with_thumbnails(
                    file=file,
                    path="images",
                    validator=validator,
                    thumbnail_sizes={
                        'thumb': (150, 150),
                        'medium': (400, 400),
                        'large': (800, 800)
                    }
                )
                
                return {
                    'message': 'Image uploaded successfully with thumbnails',
                    'data': {
                        'original': uploaded_files['original'].__dict__,
                        'thumbnails': {
                            k: v.__dict__ for k, v in uploaded_files.items() 
                            if k != 'original'
                        }
                    }
                }
            else:
                # Regular image upload
                uploaded_file = await upload_manager.store(
                    file=file,
                    path="images",
                    validator=validator
                )
                
                return {
                    'message': 'Image uploaded successfully',
                    'data': uploaded_file.__dict__
                }
                
        except FileValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}"
            )
    
    async def upload_avatar(
        self,
        request: Request,
        file: UploadFile = File(...)
    ) -> Dict[str, Any]:
        """Upload user avatar with size constraints (POST /media/avatar)"""
        
        try:
            # Validate avatar with strict constraints
            validator = FileValidationRules.avatar()
            
            # Upload with avatar-specific thumbnails
            uploaded_files = await image_upload_manager.store_with_thumbnails(
                file=file,
                path="avatars",
                validator=validator,
                thumbnail_sizes={
                    'small': (64, 64),
                    'medium': (128, 128),
                    'large': (256, 256)
                }
            )
            
            return {
                'message': 'Avatar uploaded successfully',
                'data': {
                    'original': uploaded_files['original'].__dict__,
                    'sizes': {
                        k: v.__dict__ for k, v in uploaded_files.items() 
                        if k != 'original'
                    }
                }
            }
            
        except FileValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
    
    async def upload_document(
        self,
        request: Request,
        file: UploadFile = File(...),
        category: str = Form("general")
    ) -> Dict[str, Any]:
        """Upload document file (POST /media/documents)"""
        
        try:
            # Validate document
            validator = FileValidationRules.document(max_size=20 * 1024 * 1024)  # 20MB max
            
            uploaded_file = await upload_manager.store(
                file=file,
                path=f"documents/{category}",
                validator=validator
            )
            
            return {
                'message': 'Document uploaded successfully',
                'data': uploaded_file.__dict__
            }
            
        except FileValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
    
    async def upload_multiple(
        self,
        request: Request,
        files: List[UploadFile] = File(...),
        file_type: str = Form("image")
    ) -> Dict[str, Any]:
        """Upload multiple files (POST /media/multiple)"""
        
        try:
            # Choose validator based on file type
            validator_map = {
                'image': FileValidationRules.image(),
                'document': FileValidationRules.document(),
                'video': FileValidationRules.video(),
                'audio': FileValidationRules.audio()
            }
            
            validator = validator_map.get(file_type)
            if not validator:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: {file_type}"
                )
            
            # Upload all files
            uploaded_files = await upload_manager.store_multiple(
                files=files,
                path=f"{file_type}s",
                validator=validator
            )
            
            return {
                'message': f'{len(uploaded_files)} files uploaded successfully',
                'data': [file.__dict__ for file in uploaded_files]
            }
            
        except FileValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
    
    async def delete_file(
        self,
        request: Request,
        file_path: str
    ) -> Dict[str, Any]:
        """Delete uploaded file (DELETE /media/files)"""
        
        # Security check - ensure file is in uploads directory
        if not file_path.startswith('storage/uploads/'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if file exists
        if not upload_manager.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Delete file
        success = upload_manager.delete(file_path)
        
        if success:
            return {'message': 'File deleted successfully'}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file"
            )
    
    async def get_file_info(
        self,
        request: Request,
        file_path: str
    ) -> Dict[str, Any]:
        """Get file information (GET /media/info)"""
        
        # Security check
        if not file_path.startswith('storage/uploads/'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if file exists
        if not upload_manager.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        from pathlib import Path
        import mimetypes
        
        path_obj = Path(file_path)
        stat = path_obj.stat()
        
        # Get MIME type
        mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        
        # Get image metadata if it's an image
        metadata = {}
        if mime_type.startswith('image/'):
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    metadata.update({
                        'width': img.width,
                        'height': img.height,
                        'format': img.format,
                        'mode': img.mode,
                    })
            except Exception:
                pass
        
        return {
            'filename': path_obj.name,
            'size': stat.st_size,
            'mime_type': mime_type,
            'extension': path_obj.suffix,
            'url': upload_manager.get_url(file_path),
            'created_at': stat.st_ctime,
            'modified_at': stat.st_mtime,
            'metadata': metadata
        }
    
    async def serve_file(
        self,
        request: Request,
        file_path: str
    ) -> FileResponse:
        """Serve uploaded file (GET /media/serve/{file_path})"""
        
        # Security check
        if not file_path.startswith('storage/uploads/'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if file exists
        if not upload_manager.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        from pathlib import Path
        import mimetypes
        
        path_obj = Path(file_path)
        mime_type = mimetypes.guess_type(file_path)[0]
        
        return FileResponse(
            path=file_path,
            filename=path_obj.name,
            media_type=mime_type
        )
    
    async def upload_chunked(
        self,
        request: Request,
        chunk: UploadFile = File(...),
        chunk_number: int = Form(...),
        total_chunks: int = Form(...),
        filename: str = Form(...),
        file_id: str = Form(...)
    ) -> Dict[str, Any]:
        """Handle chunked file upload (POST /media/chunked)"""
        
        from pathlib import Path
        import tempfile
        
        # Create temp directory for chunks
        temp_dir = Path(tempfile.gettempdir()) / "chunked_uploads" / file_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Save chunk
        chunk_path = temp_dir / f"chunk_{chunk_number:04d}"
        content = await chunk.read()
        
        with open(chunk_path, "wb") as f:
            f.write(content)
        
        # Check if all chunks are uploaded
        uploaded_chunks = len(list(temp_dir.glob("chunk_*")))
        
        if uploaded_chunks == total_chunks:
            # Combine chunks into final file
            final_content = b""
            
            for i in range(total_chunks):
                chunk_file = temp_dir / f"chunk_{i:04d}"
                with open(chunk_file, "rb") as f:
                    final_content += f.read()
            
            # Create UploadFile-like object
            from io import BytesIO
            file_obj = BytesIO(final_content)
            
            # Create temporary UploadFile
            temp_upload = UploadFile(
                filename=filename,
                file=file_obj,
                size=len(final_content)
            )
            
            # Store the file
            validator = FileValidationRules.image()  # You could make this configurable
            uploaded_file = await upload_manager.store(
                file=temp_upload,
                path="chunked",
                validator=validator
            )
            
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return {
                'message': 'File uploaded successfully',
                'data': uploaded_file.__dict__,
                'completed': True
            }
        else:
            return {
                'message': f'Chunk {chunk_number} uploaded successfully',
                'chunks_received': uploaded_chunks,
                'total_chunks': total_chunks,
                'completed': False
            }