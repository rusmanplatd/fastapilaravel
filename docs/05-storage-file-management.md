# Storage & File Management System

## Overview

The storage system provides Laravel-style file management with multiple drivers, comprehensive upload handling, and cloud storage integration. It supports local, S3, Google Cloud, Azure, and other storage backends.

## Storage Drivers

### Available Drivers
**Location:** `app/Storage/`

**Supported Storage Types:**
- **Local**: File system storage
- **S3**: Amazon S3 and S3-compatible services
- **Google Cloud**: Google Cloud Storage
- **Azure**: Azure Blob Storage
- **DigitalOcean**: DigitalOcean Spaces
- **MinIO**: Self-hosted S3-compatible storage
- **FTP**: FTP server storage

### Driver Configuration
**Location:** `config/filesystems.py`

```python
FILESYSTEMS = {
    "default": "local",
    
    "disks": {
        "local": {
            "driver": "local",
            "root": "storage/app",
            "url": "/storage",
            "visibility": "public"
        },
        
        "public": {
            "driver": "local", 
            "root": "storage/app/public",
            "url": "/storage",
            "visibility": "public"
        },
        
        "s3": {
            "driver": "s3",
            "bucket": "your-bucket-name",
            "region": "us-east-1",
            "key": "your-access-key",
            "secret": "your-secret-key",
            "url": "https://s3.amazonaws.com",
            "endpoint": None,
            "visibility": "public"
        },
        
        "gcs": {
            "driver": "gcs",
            "bucket": "your-gcs-bucket",
            "project_id": "your-project-id",
            "key_file": "path/to/service-account.json"
        },
        
        "azure": {
            "driver": "azure",
            "account_name": "your-account",
            "account_key": "your-key",
            "container": "your-container"
        }
    }
}
```

### Dynamic Disk Configuration
```python
from app.Storage import Storage

# Configure S3 disk at runtime
Storage.configure_disk("s3_backup", "s3", 
    bucket="backup-bucket",
    region="us-west-2",
    key="backup-access-key",
    secret="backup-secret-key"
)

# Configure Google Cloud disk
Storage.configure_disk("gcs_media", "gcs",
    bucket="media-bucket", 
    project_id="my-project",
    credentials_path="/path/to/credentials.json"
)
```

## Storage Facade

### Basic File Operations
**Location:** `app/Storage/StorageFacade.py`

```python
from app.Storage import Storage

# Default disk operations
Storage.put("file.txt", "content")
Storage.get("file.txt")
Storage.exists("file.txt")
Storage.delete("file.txt")
Storage.copy("file.txt", "backup.txt")
Storage.move("file.txt", "archive/file.txt")

# Specific disk operations  
Storage.disk("s3").put("uploads/image.jpg", image_data)
Storage.disk("gcs").get("backups/data.json")
Storage.disk("azure").delete("temp/old-file.pdf")
```

### Advanced File Operations
```python
# File metadata
metadata = Storage.metadata("document.pdf")
print(f"Size: {metadata['size']} bytes")
print(f"Modified: {metadata['last_modified']}")

# Directory operations
Storage.make_directory("uploads/2025")
Storage.delete_directory("temp/old-uploads")
files = Storage.files("uploads")
directories = Storage.directories("uploads")

# URL generation
public_url = Storage.url("uploads/image.jpg") 
temporary_url = Storage.temporary_url("private/document.pdf", expires=3600)
```

### Stream Operations
```python
# Stream large files
with Storage.read_stream("large-file.zip") as stream:
    for chunk in stream:
        process_chunk(chunk)

# Write streams
def data_generator():
    for i in range(1000000):
        yield f"Line {i}\n"

Storage.write_stream("data.txt", data_generator())
```

## File Upload System

### Upload Handler
**Location:** `app/Storage/UploadHandler.py`

**Features:**
- File size validation
- MIME type checking
- Virus scanning integration
- Image processing and thumbnails
- Metadata extraction
- Progress tracking

### Upload Configuration
```python
from app.Storage import UploadConfig

# Basic upload config
config = UploadConfig(
    max_file_size=20 * 1024 * 1024,  # 20MB
    allowed_extensions={'.jpg', '.png', '.pdf', '.docx'},
    upload_path='uploads/documents',
    organize_by_date=True,
    generate_thumbnails=True
)
```

### FastAPI Integration
**Location:** `app/Storage/Dependencies.py`

```python
from fastapi import Depends, File, UploadFile
from app.Storage import UploadHandler, UploadConfig

# Image upload dependency
ImageUploadDep = create_upload_dependency(
    allowed_extensions=[".jpg", ".png", ".gif", ".webp"],
    max_file_size=5 * 1024 * 1024,  # 5MB
    generate_thumbnails=True,
    disk="s3"
)

# Document upload dependency
DocumentUploadDep = create_upload_dependency(
    allowed_extensions=[".pdf", ".docx", ".txt"],
    max_file_size=10 * 1024 * 1024,  # 10MB
    virus_scan=True,
    disk="local"
)

@app.post("/upload/image")
async def upload_image(result: UploadResult = Depends(ImageUploadDep)):
    return {
        "url": result.url,
        "path": result.file_path,
        "thumbnails": result.thumbnails,
        "metadata": result.metadata
    }
```

### Advanced Upload Features
```python
from app.Storage import UploadHandler

# Custom upload handler
class CustomUploadHandler(UploadHandler):
    async def process_file(self, file: UploadFile) -> UploadResult:
        # Custom validation
        await self.validate_file_content(file)
        
        # Custom processing
        processed_file = await self.apply_watermark(file)
        
        # Store with custom naming
        file_path = await self.store_with_hash(processed_file)
        
        return UploadResult(
            file_path=file_path,
            url=self.generate_url(file_path),
            metadata=await self.extract_metadata(processed_file)
        )
```

## Image Processing

### Current Implementation
**Features:**
- Automatic thumbnail generation
- Image resizing and optimization
- Format conversion
- Metadata extraction (EXIF, etc.)
- Watermark application

### Image Processing Example
```python
from app.Storage import ImageProcessor

processor = ImageProcessor()

# Generate thumbnails
thumbnails = await processor.generate_thumbnails(
    image_path="uploads/photo.jpg",
    sizes=[(150, 150), (300, 300), (800, 600)],
    crop=True,
    quality=85
)

# Optimize images
await processor.optimize_image(
    source="uploads/large.jpg",
    destination="uploads/optimized.jpg", 
    max_width=1200,
    max_height=800,
    quality=80
)

# Apply watermark
await processor.add_watermark(
    image="uploads/photo.jpg",
    watermark="assets/logo.png",
    position="bottom-right",
    opacity=0.7
)
```

## Cloud Storage Features

### S3 Integration
**Features:**
- Multi-region support
- Presigned URL generation
- Multipart upload for large files
- Server-side encryption
- CDN integration (CloudFront)

```python
from app.Storage import S3FilesystemAdapter

# Configure S3 with custom settings
s3 = S3FilesystemAdapter(
    bucket="my-bucket",
    region="us-east-1", 
    access_key="key",
    secret_key="secret",
    endpoint_url="https://custom-s3.com",
    use_ssl=True
)

# Generate presigned URL
presigned_url = s3.get_presigned_url(
    "uploads/document.pdf",
    expires_in=3600,
    method="GET"
)

# Multipart upload for large files
upload_id = s3.create_multipart_upload("large-file.zip")
part_urls = s3.generate_presigned_post_urls(upload_id, num_parts=5)
```

### Google Cloud Storage
```python
from app.Storage import GoogleCloudStorageAdapter

gcs = GoogleCloudStorageAdapter(
    bucket="my-gcs-bucket",
    project_id="my-project",
    credentials_path="/path/to/service-account.json"
)

# Set object metadata
gcs.put_with_metadata("data.json", json_data, {
    "cache-control": "public, max-age=3600",
    "content-type": "application/json",
    "custom-field": "value"
})
```

### Azure Blob Storage
```python
from app.Storage import AzureBlobStorageAdapter

azure = AzureBlobStorageAdapter(
    account_name="myaccount",
    account_key="key",
    container="files"
)

# Upload with access tier
azure.put_with_tier("archive/data.zip", data, tier="Archive")
```

## File Management Commands

### Storage Commands
```bash
# Storage operations
make storage-link         # Create symbolic link for public storage
make storage-test         # Test storage connections
make storage-cleanup      # Clean up temporary files
make storage-info         # Show storage disk information
make storage-usage        # Show storage usage statistics
make storage-backup       # Backup storage directory
```

### Custom Storage Commands
```python
from app.Console.Command import Command

class StorageCleanupCommand(Command):
    signature = "storage:cleanup {--disk=local} {--days=30}"
    description = "Clean up old files from storage"
    
    def handle(self):
        disk_name = self.option("disk")
        days = int(self.option("days"))
        
        disk = Storage.disk(disk_name)
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Find and delete old files
        old_files = disk.find_files_older_than(cutoff_date)
        for file_path in old_files:
            disk.delete(file_path)
            self.info(f"Deleted: {file_path}")
```

## Security Features

### File Validation
```python
from app.Storage import FileValidator

validator = FileValidator()

# Validate file type
is_valid = validator.validate_file_type(file, allowed_types=['image/jpeg'])

# Validate file content
is_safe = validator.validate_file_content(file)  # Checks for malicious content

# Virus scanning (requires ClamAV or similar)
is_clean = await validator.scan_for_viruses(file)
```

### Access Control
```python
# Private disk with authorization
@app.get("/files/{file_path:path}")
async def download_file(file_path: str, user: User = Depends(get_current_user)):
    # Check permissions
    if not user.can_access_file(file_path):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Generate temporary download URL
    disk = Storage.disk("private")
    return disk.download_response(file_path)
```

### File Encryption
```python
from app.Storage import EncryptedFilesystemAdapter

# Encrypted storage adapter
encrypted_disk = EncryptedFilesystemAdapter(
    base_adapter=Storage.disk("local"),
    encryption_key=app_config["encryption_key"]
)

# Files are automatically encrypted/decrypted
encrypted_disk.put("sensitive.txt", "confidential data")
decrypted_content = encrypted_disk.get("sensitive.txt")
```

## Performance Optimization

### Caching
```python
from app.Storage import CachedFilesystemAdapter

# Add caching layer to any storage driver
cached_s3 = CachedFilesystemAdapter(
    base_adapter=Storage.disk("s3"),
    cache_driver="redis",
    cache_ttl=3600
)

# Frequently accessed files are cached locally
content = cached_s3.get("frequently-accessed.json")  # Cached after first read
```

### CDN Integration
```python
from app.Storage import CDNFilesystemAdapter

# Automatically sync files to CDN
cdn_disk = CDNFilesystemAdapter(
    base_adapter=Storage.disk("s3"),
    cdn_url="https://cdn.example.com",
    auto_invalidate=True
)

# Files are automatically distributed to CDN
cdn_disk.put("assets/style.css", css_content)
public_url = cdn_disk.url("assets/style.css")  # Returns CDN URL
```

## API Endpoints

### File Management API
```python
# Upload endpoint
@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    disk: str = Query("local"),
    folder: str = Query("uploads")
):
    storage_disk = Storage.disk(disk)
    file_path = await storage_disk.put_upload(file, folder)
    return {"path": file_path, "url": storage_disk.url(file_path)}

# Download endpoint
@app.get("/api/files/download/{file_path:path}")
async def download_file(file_path: str, disk: str = Query("local")):
    storage_disk = Storage.disk(disk)
    return storage_disk.download_response(file_path)

# File info endpoint
@app.get("/api/files/info/{file_path:path}")
async def file_info(file_path: str, disk: str = Query("local")):
    storage_disk = Storage.disk(disk)
    metadata = storage_disk.metadata(file_path)
    return {
        "path": file_path,
        "size": metadata["size"],
        "modified": metadata["last_modified"],
        "url": storage_disk.url(file_path)
    }
```

## Testing

### Storage Testing
```python
from app.Testing.StorageTestUtils import StorageFake

def test_file_storage():
    # Use fake storage for testing
    Storage.fake("s3")
    
    # Perform storage operations
    Storage.disk("s3").put("test.txt", "content")
    
    # Assertions
    Storage.disk("s3").assert_exists("test.txt")
    Storage.disk("s3").assert_missing("nonexistent.txt")
    
    content = Storage.disk("s3").get("test.txt")
    assert content == "content"
```

## Improvements

### Performance Enhancements
1. **Async operations**: Full async/await support for all operations
2. **Connection pooling**: Reuse connections for better performance
3. **Batch operations**: Bulk file operations for efficiency
4. **Smart caching**: Intelligent caching based on access patterns

### Advanced Features
1. **File versioning**: Track file changes and maintain versions
2. **Metadata indexing**: Search files by metadata
3. **Compression**: Automatic file compression for storage efficiency
4. **Deduplication**: Eliminate duplicate files to save space

### Developer Experience
1. **Storage browser**: Web interface for file management
2. **Migration tools**: Easy migration between storage drivers
3. **Usage analytics**: Track storage usage and costs
4. **Backup automation**: Automated backup strategies

### Enterprise Features
1. **Multi-tenancy**: Tenant-isolated storage
2. **Compliance**: GDPR, HIPAA compliance features
3. **Audit trails**: Track all file operations
4. **Disaster recovery**: Cross-region replication and backup