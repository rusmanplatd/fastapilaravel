"""
Laravel-style File Storage Example for FastAPI Laravel

This example demonstrates comprehensive file storage usage including:
- Multiple storage drivers (Local, S3, GCS, Azure, FTP)
- File upload handling with validation and processing
- Image processing and thumbnail generation
- Storage facade operations
- FastAPI dependencies and endpoints
- Security and validation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import os
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

# Storage imports
from app.Storage import (
    Storage, StorageManager, LocalFilesystemAdapter,
    EnhancedS3Adapter, GoogleCloudStorageAdapter, AzureBlobStorageAdapter,
    UploadHandler, UploadConfig, UploadResult,
    StorageDisk, FileManagerDep, UploadHandlerDep, ImageUploadDep,
    SingleUploadDep, MultipleUploadDep, ImageUploadResultDep,
    get_storage_disk, create_upload_dependency, create_image_dependency,
    storage_exists, storage_get, storage_put, storage_delete, storage_url
)

# FastAPI app
app = FastAPI(
    title="File Storage Example",
    description="Demonstrates Laravel-style file storage in FastAPI",
    version="1.0.0"
)

# Create storage directories
os.makedirs("storage/app/public", exist_ok=True)
os.makedirs("storage/app/uploads", exist_ok=True)
os.makedirs("storage/app/temp", exist_ok=True)

# Mount static files for public storage
app.mount("/storage", StaticFiles(directory="storage/app/public"), name="storage")


# Storage Configuration Examples

def configure_storage_disks() -> None:
    """Configure various storage disks."""
    
    # Local storage configurations
    Storage.configure_disk("local", "local", root="storage/app")
    Storage.configure_disk("public", "local", root="storage/app/public")
    Storage.configure_disk("temp", "local", root="storage/app/temp")
    
    # S3 configuration (requires AWS credentials)
    Storage.configure_disk("s3", "s3",
        bucket="my-bucket",
        region="us-east-1",
        key=os.getenv("AWS_ACCESS_KEY_ID"),
        secret=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    
    # Google Cloud Storage (requires service account)
    Storage.configure_disk("gcs", "gcs",
        bucket="my-gcs-bucket",
        project_id="my-project",
        key_file=os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )
    
    # Azure Blob Storage
    Storage.configure_disk("azure", "azure",
        account="mystorageaccount",
        container="mycontainer",
        key=os.getenv("AZURE_STORAGE_KEY")
    )
    
    # DigitalOcean Spaces
    Storage.configure_disk("spaces", "do_spaces",
        bucket="my-space",
        region="nyc3",
        key=os.getenv("DO_SPACES_KEY"),
        secret=os.getenv("DO_SPACES_SECRET")
    )
    
    # MinIO (self-hosted S3-compatible)
    Storage.configure_disk("minio", "minio",
        bucket="my-bucket",
        endpoint="http://localhost:9000",
        key="minioadmin",
        secret="minioadmin",
        use_ssl=False
    )
    
    # FTP storage
    Storage.configure_disk("ftp", "ftp",
        host="ftp.example.com",
        username="ftpuser",
        password="ftppass",
        root="/uploads"
    )


# Initialize storage configuration
configure_storage_disks()


# Custom upload handlers
ImageUpload = create_image_dependency(
    max_size=5 * 1024 * 1024,  # 5MB
    auto_resize=True,
    generate_thumbnails=True,
    disk="public"
)

DocumentUpload = create_upload_dependency(
    allowed_extensions=[".pdf", ".doc", ".docx", ".txt"],
    max_file_size=20 * 1024 * 1024,  # 20MB
    disk="local"
)


# Basic File Operations

@app.get("/")
async def root():
    """Root endpoint with API documentation."""
    return {
        "message": "Laravel-style File Storage Example API",
        "endpoints": {
            "basic_operations": {
                "upload_file": "/files/upload",
                "upload_multiple": "/files/upload-multiple",
                "download_file": "/files/{file_path:path}",
                "file_info": "/files/{file_path:path}/info",
                "delete_file": "/files/{file_path:path}",
                "list_files": "/files/list"
            },
            "image_operations": {
                "upload_image": "/images/upload",
                "image_info": "/images/{file_path:path}/info",
                "image_thumbnail": "/images/{file_path:path}/thumbnail/{size}"
            },
            "storage_operations": {
                "storage_info": "/storage/info",
                "disk_operations": "/storage/disk/{disk_name}/files",
                "copy_between_disks": "/storage/copy"
            },
            "advanced": {
                "batch_upload": "/files/batch-upload",
                "temporary_url": "/files/{file_path:path}/temporary-url",
                "file_hash": "/files/{file_path:path}/hash"
            }
        }
    }


# Basic File Upload and Management

@app.post("/files/upload")
async def upload_file(
    result: UploadResult = Depends(SingleUploadDep)
) -> Dict[str, Any]:
    """Upload a single file."""
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return {
        "success": True,
        "message": "File uploaded successfully",
        "file": {
            "path": result.file_path,
            "original_name": result.original_filename,
            "size": result.size,
            "mime_type": result.mime_type,
            "hash": result.hash,
            "url": result.url
        }
    }


@app.post("/files/upload-multiple")
async def upload_multiple_files(
    results: List[UploadResult] = Depends(MultipleUploadDep)
) -> Dict[str, Any]:
    """Upload multiple files."""
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    return {
        "success": len(failed) == 0,
        "message": f"Uploaded {len(successful)} files successfully, {len(failed)} failed",
        "files": [
            {
                "path": r.file_path,
                "original_name": r.original_filename,
                "size": r.size,
                "url": r.url
            }
            for r in successful
        ],
        "errors": [{"file": r.original_filename, "error": r.error} for r in failed]
    }


@app.get("/files/{file_path:path}")
async def download_file(
    file_path: str,
    storage: StorageDisk = Depends()
) -> FileResponse:
    """Download a file."""
    if not storage.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # For local storage, return FileResponse
    if hasattr(storage, '_full_path'):
        local_path = storage._full_path(file_path)
        return FileResponse(
            path=str(local_path),
            filename=Path(file_path).name
        )
    
    # For cloud storage, stream the file
    content = storage.get(file_path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    
    def generate():
        yield content
    
    return StreamingResponse(
        generate(),
        media_type='application/octet-stream',
        headers={'Content-Disposition': f'attachment; filename="{Path(file_path).name}"'}
    )


@app.get("/files/{file_path:path}/info")
async def get_file_info(
    file_path: str,
    manager: FileManagerDep = Depends()
) -> Dict[str, Any]:
    """Get file information."""
    return manager.get_info(file_path)


@app.delete("/files/{file_path:path}")
async def delete_file(
    file_path: str,
    manager: FileManagerDep = Depends()
) -> Dict[str, Any]:
    """Delete a file."""
    success = manager.delete(file_path)
    
    return {
        "success": success,
        "message": "File deleted successfully" if success else "Failed to delete file"
    }


@app.get("/files/list")
async def list_files(
    directory: str = "",
    storage: StorageDisk = Depends()
) -> Dict[str, Any]:
    """List files in directory."""
    files = storage.files(directory)
    directories = storage.directories(directory)
    
    return {
        "directory": directory,
        "files": files,
        "directories": directories,
        "total_files": len(files),
        "total_directories": len(directories)
    }


# Image Operations

@app.post("/images/upload")
async def upload_image(
    result: UploadResult = Depends(ImageUploadResultDep)
) -> Dict[str, Any]:
    """Upload an image with processing."""
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    response = {
        "success": True,
        "message": "Image uploaded and processed successfully",
        "image": {
            "path": result.file_path,
            "original_name": result.original_filename,
            "size": result.size,
            "mime_type": result.mime_type,
            "url": result.url
        }
    }
    
    # Add thumbnail information if available
    if result.thumbnail_urls:
        response["image"]["thumbnails"] = result.thumbnail_urls
    
    # Add image metadata if available
    if result.metadata:
        response["image"]["metadata"] = result.metadata
    
    return response


@app.get("/images/{file_path:path}/info")
async def get_image_info(
    file_path: str,
    storage: StorageDisk = Depends()
) -> Dict[str, Any]:
    """Get detailed image information."""
    if not storage.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    info = {
        "path": file_path,
        "size": storage.size(file_path),
        "mime_type": storage.mime_type(file_path),
        "url": storage.url(file_path) if hasattr(storage, 'url') else None
    }
    
    # Try to get image metadata
    try:
        from PIL import Image
        if hasattr(storage, '_full_path'):
            with Image.open(storage._full_path(file_path)) as img:
                info.update({
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode
                })
    except Exception:
        pass
    
    return info


# Storage Disk Operations

@app.get("/storage/info")
async def get_storage_info() -> Dict[str, Any]:
    """Get information about configured storage disks."""
    manager = Storage._get_manager()
    
    disk_info = {}
    for name, adapter in manager.disks.items():
        disk_info[name] = Storage.disk_info(name)
    
    return {
        "default_disk": manager.default_disk,
        "disks": disk_info
    }


@app.get("/storage/disk/{disk_name}/files")
async def list_disk_files(
    disk_name: str,
    directory: str = "",
    storage: FilesystemAdapter = Depends(get_storage_disk)
) -> Dict[str, Any]:
    """List files on a specific storage disk."""
    try:
        files = storage.files(directory)
        directories = storage.directories(directory)
        
        return {
            "disk": disk_name,
            "directory": directory,
            "files": files,
            "directories": directories
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/storage/copy")
async def copy_between_disks(
    source_disk: str = Form(...),
    target_disk: str = Form(...),
    source_path: str = Form(...),
    target_path: str = Form(...)
) -> Dict[str, Any]:
    """Copy file between storage disks."""
    try:
        source_storage = Storage.disk(source_disk)
        target_storage = Storage.disk(target_disk)
        
        if not source_storage.exists(source_path):
            raise HTTPException(status_code=404, detail="Source file not found")
        
        # Get file content from source
        content = source_storage.get(source_path)
        if content is None:
            raise HTTPException(status_code=500, detail="Failed to read source file")
        
        # Put to target
        success = target_storage.put(target_path, content)
        
        return {
            "success": success,
            "message": "File copied successfully" if success else "Failed to copy file",
            "source": {"disk": source_disk, "path": source_path},
            "target": {"disk": target_disk, "path": target_path}
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Advanced Operations

@app.post("/files/batch-upload")
async def batch_upload(
    files: List[UploadFile] = File(...),
    target_disk: str = Form("local"),
    organize_by_type: bool = Form(True)
) -> Dict[str, Any]:
    """Batch upload files with organization."""
    try:
        storage = Storage.disk(target_disk)
        handler = UploadHandler(storage, UploadConfig(organize_by_type=organize_by_type))
        
        results = await handler.upload_multiple_files(files)
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        return {
            "success": len(failed) == 0,
            "total_files": len(files),
            "successful": len(successful),
            "failed": len(failed),
            "files": [
                {
                    "path": r.file_path,
                    "original_name": r.original_filename,
                    "size": r.size
                }
                for r in successful
            ],
            "errors": [{"file": r.original_filename, "error": r.error} for r in failed]
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/files/{file_path:path}/temporary-url")
async def get_temporary_url(
    file_path: str,
    expires_in: int = 3600,
    disk_name: str = "local"
) -> Dict[str, Any]:
    """Get a temporary URL for a file."""
    try:
        storage = Storage.disk(disk_name)
        
        if not storage.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        if hasattr(storage, 'temporary_url'):
            url = storage.temporary_url(file_path, expires_in)
            return {
                "url": url,
                "expires_in": expires_in,
                "file_path": file_path
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail="Storage driver does not support temporary URLs"
            )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/files/{file_path:path}/hash")
async def get_file_hash(
    file_path: str,
    algorithm: str = "sha256",
    storage: StorageDisk = Depends()
) -> Dict[str, Any]:
    """Get hash of a file."""
    if not storage.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    content = storage.get(file_path)
    if content is None:
        raise HTTPException(status_code=500, detail="Failed to read file")
    
    import hashlib
    
    try:
        hasher = getattr(hashlib, algorithm)()
        hasher.update(content)
        hash_value = hasher.hexdigest()
        
        return {
            "file_path": file_path,
            "algorithm": algorithm,
            "hash": hash_value,
            "size": len(content)
        }
    
    except AttributeError:
        raise HTTPException(status_code=400, detail=f"Unsupported hash algorithm: {algorithm}")


# Utility Endpoints

@app.post("/storage/test-connection/{disk_name}")
async def test_storage_connection(disk_name: str) -> Dict[str, Any]:
    """Test connection to a storage disk."""
    try:
        storage = Storage.disk(disk_name)
        
        # Try to write and read a test file
        test_content = "Storage connection test"
        test_path = "test/connection_test.txt"
        
        # Write test file
        write_success = storage.put(test_path, test_content)
        if not write_success:
            return {"connected": False, "error": "Failed to write test file"}
        
        # Read test file
        read_content = storage.get_string(test_path)
        if read_content != test_content:
            return {"connected": False, "error": "Failed to read test file correctly"}
        
        # Clean up test file
        storage.delete(test_path)
        
        return {
            "connected": True,
            "disk": disk_name,
            "driver": storage.__class__.__name__
        }
    
    except Exception as e:
        return {"connected": False, "error": str(e)}


@app.get("/storage/usage/{disk_name}")
async def get_storage_usage(disk_name: str) -> Dict[str, Any]:
    """Get storage usage statistics."""
    try:
        storage = Storage.disk(disk_name)
        
        # Count files and calculate total size
        all_files = storage.files()
        total_files = len(all_files)
        total_size = sum(storage.size(f) or 0 for f in all_files)
        
        usage = {
            "disk": disk_name,
            "total_files": total_files,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
        
        # Add free space for local storage
        if hasattr(storage, 'root_path'):
            import shutil
            free_space = shutil.disk_usage(storage.root_path).free
            usage["free_space"] = free_space
            usage["free_space_mb"] = round(free_space / (1024 * 1024), 2)
        
        return usage
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)