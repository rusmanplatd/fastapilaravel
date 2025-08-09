from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, BinaryIO, Callable
from abc import abstractmethod
from datetime import datetime, timedelta
import os
import io
import json
import base64
import hashlib
import hmac
import urllib.parse
from pathlib import Path

from .FilesystemAdapter import FilesystemAdapter


class S3FilesystemAdapter(FilesystemAdapter):
    """
    Enhanced S3 filesystem adapter with full AWS S3 integration.
    
    Provides complete Laravel-compatible S3 storage functionality including
    presigned URLs, multipart uploads, and advanced S3 features.
    """
    
    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        session_token: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        public_url: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        self.bucket = bucket
        self.region = region
        self.access_key_id = access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_access_key = secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.session_token = session_token or os.getenv('AWS_SESSION_TOKEN')
        self.endpoint_url = endpoint_url
        self.public_url = public_url
        self.config = kwargs
        
        # Try to initialize boto3 client
        self._client: Optional[Any] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize boto3 S3 client."""
        try:
            import boto3
            from botocore.config import Config
            
            config = Config(
                region_name=self.region,
                retries={'max_attempts': 3, 'mode': 'adaptive'},
                max_pool_connections=50
            )
            
            session = boto3.Session(
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                aws_session_token=self.session_token
            )
            
            self._client = session.client(
                's3',
                config=config,
                endpoint_url=self.endpoint_url
            )
            
        except ImportError:
            print("Warning: boto3 not installed. S3 operations will not work.")
            self._client = None
    
    def _ensure_client(self) -> Any:
        """Ensure boto3 client is available."""
        if self._client is None:
            raise RuntimeError("S3 client not available. Install boto3: pip install boto3")
        return self._client
    
    def exists(self, path: str) -> bool:
        """Check if file exists in S3."""
        try:
            client = self._ensure_client()
            client.head_object(Bucket=self.bucket, Key=path.lstrip('/'))
            return True
        except Exception:
            return False
    
    def get(self, path: str) -> Optional[bytes]:
        """Get file contents from S3."""
        try:
            client = self._ensure_client()
            response = client.get_object(Bucket=self.bucket, Key=path.lstrip('/'))
            return response['Body'].read()  # type: ignore[no-any-return]
        except Exception:
            return None
    
    def put(
        self, 
        path: str, 
        contents: Union[str, bytes, BinaryIO], 
        visibility: str = 'private',
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> bool:
        """Put file to S3 with advanced options."""
        try:
            client = self._ensure_client()
            
            # Prepare content
            if isinstance(contents, str):
                body = contents.encode('utf-8')
                content_type = content_type or 'text/plain; charset=utf-8'
            elif hasattr(contents, 'read'):
                body = contents.read() if hasattr(contents, 'read') else contents  # type: ignore[assignment]
            else:
                body = contents
            
            # Prepare extra args
            extra_args: Dict[str, Any] = {}
            
            if content_type:
                extra_args['ContentType'] = content_type
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            if visibility == 'public':
                extra_args['ACL'] = 'public-read'
            
            # Upload file
            if hasattr(body, 'read'):
                client.upload_fileobj(body, self.bucket, path.lstrip('/'), ExtraArgs=extra_args)
            else:
                client.put_object(
                    Bucket=self.bucket,
                    Key=path.lstrip('/'),
                    Body=body,
                    **extra_args
                )
            
            return True
        except Exception as e:
            print(f"S3 put error: {e}")
            return False
    
    def delete(self, path: str) -> bool:
        """Delete file from S3."""
        try:
            client = self._ensure_client()
            client.delete_object(Bucket=self.bucket, Key=path.lstrip('/'))
            return True
        except Exception:
            return False
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy file within S3."""
        try:
            client = self._ensure_client()
            copy_source = {'Bucket': self.bucket, 'Key': from_path.lstrip('/')}
            client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket,
                Key=to_path.lstrip('/')
            )
            return True
        except Exception:
            return False
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move file within S3."""
        return self.copy(from_path, to_path) and self.delete(from_path)
    
    def size(self, path: str) -> Optional[int]:
        """Get file size from S3."""
        try:
            client = self._ensure_client()
            response = client.head_object(Bucket=self.bucket, Key=path.lstrip('/'))
            return response['ContentLength']  # type: ignore[no-any-return]
        except Exception:
            return None
    
    def last_modified(self, path: str) -> Optional[datetime]:
        """Get last modified time from S3."""
        try:
            client = self._ensure_client()
            response = client.head_object(Bucket=self.bucket, Key=path.lstrip('/'))
            return response['LastModified'].replace(tzinfo=None)  # type: ignore[no-any-return]
        except Exception:
            return None
    
    def files(self, directory: str = "", recursive: bool = False) -> List[str]:
        """List files in S3 directory."""
        try:
            client = self._ensure_client()
            prefix = directory.strip('/') + '/' if directory else ''
            delimiter = '' if recursive else '/'
            
            files = []
            paginator = client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(
                Bucket=self.bucket,
                Prefix=prefix,
                Delimiter=delimiter
            ):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if not key.endswith('/'):  # Skip directories
                        files.append(key)
            
            return sorted(files)
        except Exception:
            return []
    
    def directories(self, directory: str = "") -> List[str]:
        """List directories in S3."""
        try:
            client = self._ensure_client()
            prefix = directory.strip('/') + '/' if directory else ''
            
            dirs = []
            paginator = client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(
                Bucket=self.bucket,
                Prefix=prefix,
                Delimiter='/'
            ):
                for common_prefix in page.get('CommonPrefixes', []):
                    dir_name = common_prefix['Prefix'].rstrip('/')
                    dirs.append(dir_name)
            
            return sorted(dirs)
        except Exception:
            return []
    
    def url(self, path: str) -> str:
        """Get public URL for S3 object."""
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{path.lstrip('/')}"
        
        if self.endpoint_url:
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket}/{path.lstrip('/')}"
        
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{path.lstrip('/')}"
    
    def temporary_url(
        self, 
        path: str, 
        expires_in: int = 3600,
        method: str = 'GET',
        response_headers: Optional[Dict[str, str]] = None
    ) -> str:
        """Generate presigned URL for S3 object."""
        try:
            client = self._ensure_client()
            
            params = {
                'Bucket': self.bucket,
                'Key': path.lstrip('/')
            }
            
            if response_headers:
                params.update(response_headers)
            
            return client.generate_presigned_url(  # type: ignore[no-any-return]
                f's3:{method.lower()}_object',
                Params=params,
                ExpiresIn=expires_in
            )
        except Exception:
            return self.url(path)
    
    def signed_upload_url(
        self,
        path: str,
        expires_in: int = 3600,
        conditions: Optional[List[Dict[str, Any]]] = None,
        fields: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Generate presigned POST URL for direct uploads."""
        try:
            client = self._ensure_client()
            
            response = client.generate_presigned_post(
                Bucket=self.bucket,
                Key=path.lstrip('/'),
                Fields=fields,
                Conditions=conditions or [],
                ExpiresIn=expires_in
            )
            
            return response  # type: ignore[no-any-return]
        except Exception:
            return {'url': self.url(path), 'fields': {}}
    
    def get_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """Get object metadata from S3."""
        try:
            client = self._ensure_client()
            response = client.head_object(Bucket=self.bucket, Key=path.lstrip('/'))
            
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response.get('ContentType'),
                'etag': response['ETag'].strip('"'),
                'metadata': response.get('Metadata', {}),
                'storage_class': response.get('StorageClass', 'STANDARD')
            }
        except Exception:
            return None
    
    def set_visibility(self, path: str, visibility: str) -> bool:
        """Set object visibility (public/private)."""
        try:
            client = self._ensure_client()
            
            acl = 'public-read' if visibility == 'public' else 'private'
            client.put_object_acl(
                Bucket=self.bucket,
                Key=path.lstrip('/'),
                ACL=acl
            )
            return True
        except Exception:
            return False


class GoogleCloudStorageAdapter(FilesystemAdapter):
    """
    Google Cloud Storage adapter for Laravel-style storage operations.
    """
    
    def __init__(
        self,
        bucket: str,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        credentials_json: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> None:
        self.bucket_name = bucket
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.credentials_json = credentials_json
        self.config = kwargs
        
        self._client: Optional[Any] = None
        self._bucket: Optional[Any] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Google Cloud Storage client."""
        try:
            from google.cloud import storage
            from google.oauth2 import service_account
            
            if self.credentials_json:
                credentials = service_account.Credentials.from_service_account_info(
                    self.credentials_json
                )
                self._client = storage.Client(credentials=credentials, project=self.project_id)
            elif self.credentials_path:
                self._client = storage.Client.from_service_account_json(
                    self.credentials_path, project=self.project_id
                )
            else:
                self._client = storage.Client(project=self.project_id)
            
            self._bucket = self._client.bucket(self.bucket_name)
            
        except ImportError:
            print("Warning: google-cloud-storage not installed. GCS operations will not work.")
            self._client = None
            self._bucket = None
    
    def _ensure_client(self) -> Any:
        """Ensure GCS client is available."""
        if self._client is None:
            raise RuntimeError("GCS client not available. Install google-cloud-storage")
        return self._client
    
    def _ensure_bucket(self) -> Any:
        """Ensure GCS bucket is available."""
        if self._bucket is None:
            raise RuntimeError("GCS bucket not available")
        return self._bucket
    
    def exists(self, path: str) -> bool:
        """Check if file exists in GCS."""
        try:
            bucket = self._ensure_bucket()
            blob = bucket.blob(path.lstrip('/'))
            return blob.exists()  # type: ignore[no-any-return]
        except Exception:
            return False
    
    def get(self, path: str) -> Optional[bytes]:
        """Get file contents from GCS."""
        try:
            bucket = self._ensure_bucket()
            blob = bucket.blob(path.lstrip('/'))
            return blob.download_as_bytes()  # type: ignore[no-any-return]
        except Exception:
            return None
    
    def put(
        self, 
        path: str, 
        contents: Union[str, bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Put file to GCS."""
        try:
            bucket = self._ensure_bucket()
            blob = bucket.blob(path.lstrip('/'))
            
            if content_type:
                blob.content_type = content_type
            
            if metadata:
                blob.metadata = metadata
            
            if isinstance(contents, str):
                blob.upload_from_string(contents)
            elif hasattr(contents, 'read'):
                blob.upload_from_file(contents)
            else:
                blob.upload_from_string(contents)
            
            return True
        except Exception:
            return False
    
    def delete(self, path: str) -> bool:
        """Delete file from GCS."""
        try:
            bucket = self._ensure_bucket()
            blob = bucket.blob(path.lstrip('/'))
            blob.delete()
            return True
        except Exception:
            return False
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy file within GCS."""
        try:
            bucket = self._ensure_bucket()
            source_blob = bucket.blob(from_path.lstrip('/'))
            bucket.copy_blob(source_blob, bucket, to_path.lstrip('/'))
            return True
        except Exception:
            return False
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move file within GCS."""
        return self.copy(from_path, to_path) and self.delete(from_path)
    
    def size(self, path: str) -> Optional[int]:
        """Get file size from GCS."""
        try:
            bucket = self._ensure_bucket()
            blob = bucket.blob(path.lstrip('/'))
            blob.reload()
            return blob.size  # type: ignore[no-any-return]
        except Exception:
            return None
    
    def last_modified(self, path: str) -> Optional[datetime]:
        """Get last modified time from GCS."""
        try:
            bucket = self._ensure_bucket()
            blob = bucket.blob(path.lstrip('/'))
            blob.reload()
            return blob.updated.replace(tzinfo=None) if blob.updated else None
        except Exception:
            return None
    
    def files(self, directory: str = "") -> List[str]:
        """List files in GCS directory."""
        try:
            bucket = self._ensure_bucket()
            prefix = directory.strip('/') + '/' if directory else ''
            
            files = []
            for blob in bucket.list_blobs(prefix=prefix):
                if not blob.name.endswith('/'):
                    files.append(blob.name)
            
            return sorted(files)
        except Exception:
            return []
    
    def directories(self, directory: str = "") -> List[str]:
        """List directories in GCS."""
        try:
            bucket = self._ensure_bucket()
            prefix = directory.strip('/') + '/' if directory else ''
            
            dirs = set()
            for blob in bucket.list_blobs(prefix=prefix):
                # Extract directory from blob name
                relative_path = blob.name[len(prefix):]
                if '/' in relative_path:
                    dir_name = relative_path.split('/')[0]
                    dirs.add(f"{prefix}{dir_name}")
            
            return sorted(list(dirs))
        except Exception:
            return []
    
    def url(self, path: str) -> str:
        """Get public URL for GCS object."""
        return f"https://storage.googleapis.com/{self.bucket_name}/{path.lstrip('/')}"
    
    def temporary_url(self, path: str, expires_in: int = 3600, method: str = 'GET') -> str:
        """Generate signed URL for GCS object."""
        try:
            bucket = self._ensure_bucket()
            blob = bucket.blob(path.lstrip('/'))
            
            expiration = datetime.utcnow() + timedelta(seconds=expires_in)
            
            return blob.generate_signed_url(  # type: ignore[no-any-return]
                expiration=expiration,
                method=method
            )
        except Exception:
            return self.url(path)


class AzureBlobStorageAdapter(FilesystemAdapter):
    """
    Azure Blob Storage adapter for Laravel-style storage operations.
    """
    
    def __init__(
        self,
        account_name: str,
        container: str,
        account_key: Optional[str] = None,
        sas_token: Optional[str] = None,
        connection_string: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        self.account_name = account_name
        self.container_name = container
        self.account_key = account_key
        self.sas_token = sas_token
        self.connection_string = connection_string
        self.config = kwargs
        
        self._client: Optional[Any] = None
        self._container_client: Optional[Any] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Azure Blob Storage client."""
        try:
            from azure.storage.blob import BlobServiceClient
            
            if self.connection_string:
                self._client = BlobServiceClient.from_connection_string(self.connection_string)
            elif self.account_key:
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self._client = BlobServiceClient(account_url=account_url, credential=self.account_key)
            elif self.sas_token:
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self._client = BlobServiceClient(account_url=account_url, credential=self.sas_token)
            else:
                raise ValueError("Must provide either connection_string, account_key, or sas_token")
            
            self._container_client = self._client.get_container_client(self.container_name)
            
        except ImportError:
            print("Warning: azure-storage-blob not installed. Azure operations will not work.")
            self._client = None
            self._container_client = None
    
    def _ensure_container_client(self) -> Any:
        """Ensure Azure container client is available."""
        if self._container_client is None:
            raise RuntimeError("Azure container client not available")
        return self._container_client
    
    def exists(self, path: str) -> bool:
        """Check if blob exists in Azure."""
        try:
            container_client = self._ensure_container_client()
            blob_client = container_client.get_blob_client(path.lstrip('/'))
            return blob_client.exists()  # type: ignore[no-any-return]
        except Exception:
            return False
    
    def get(self, path: str) -> Optional[bytes]:
        """Get blob contents from Azure."""
        try:
            container_client = self._ensure_container_client()
            blob_client = container_client.get_blob_client(path.lstrip('/'))
            return blob_client.download_blob().readall()  # type: ignore[no-any-return]
        except Exception:
            return None
    
    def put(
        self, 
        path: str, 
        contents: Union[str, bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Put blob to Azure."""
        try:
            container_client = self._ensure_container_client()
            blob_client = container_client.get_blob_client(path.lstrip('/'))
            
            blob_client.upload_blob(
                contents,
                content_type=content_type,
                metadata=metadata,
                overwrite=True
            )
            return True
        except Exception:
            return False
    
    def delete(self, path: str) -> bool:
        """Delete blob from Azure."""
        try:
            container_client = self._ensure_container_client()
            blob_client = container_client.get_blob_client(path.lstrip('/'))
            blob_client.delete_blob()
            return True
        except Exception:
            return False
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy blob within Azure."""
        try:
            container_client = self._ensure_container_client()
            
            source_blob_client = container_client.get_blob_client(from_path.lstrip('/'))
            dest_blob_client = container_client.get_blob_client(to_path.lstrip('/'))
            
            source_url = source_blob_client.url
            dest_blob_client.start_copy_from_url(source_url)
            return True
        except Exception:
            return False
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move blob within Azure."""
        return self.copy(from_path, to_path) and self.delete(from_path)
    
    def size(self, path: str) -> Optional[int]:
        """Get blob size from Azure."""
        try:
            container_client = self._ensure_container_client()
            blob_client = container_client.get_blob_client(path.lstrip('/'))
            properties = blob_client.get_blob_properties()
            return properties.size  # type: ignore[no-any-return]
        except Exception:
            return None
    
    def last_modified(self, path: str) -> Optional[datetime]:
        """Get last modified time from Azure."""
        try:
            container_client = self._ensure_container_client()
            blob_client = container_client.get_blob_client(path.lstrip('/'))
            properties = blob_client.get_blob_properties()
            return properties.last_modified.replace(tzinfo=None) if properties.last_modified else None
        except Exception:
            return None
    
    def files(self, directory: str = "") -> List[str]:
        """List blobs in Azure directory."""
        try:
            container_client = self._ensure_container_client()
            prefix = directory.strip('/') + '/' if directory else ''
            
            files = []
            for blob in container_client.list_blobs(name_starts_with=prefix):
                if not blob.name.endswith('/'):
                    files.append(blob.name)
            
            return sorted(files)
        except Exception:
            return []
    
    def directories(self, directory: str = "") -> List[str]:
        """List directories in Azure."""
        try:
            container_client = self._ensure_container_client()
            prefix = directory.strip('/') + '/' if directory else ''
            
            dirs = set()
            for blob in container_client.list_blobs(name_starts_with=prefix):
                relative_path = blob.name[len(prefix):]
                if '/' in relative_path:
                    dir_name = relative_path.split('/')[0]
                    dirs.add(f"{prefix}{dir_name}")
            
            return sorted(list(dirs))
        except Exception:
            return []
    
    def url(self, path: str) -> str:
        """Get public URL for Azure blob."""
        return f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{path.lstrip('/')}"
    
    def temporary_url(self, path: str, expires_in: int = 3600, method: str = 'GET') -> str:
        """Generate SAS URL for Azure blob."""
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            from datetime import datetime, timezone
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=path.lstrip('/'),
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            )
            
            return f"{self.url(path)}?{sas_token}"
        except Exception:
            return self.url(path)


class DigitalOceanSpacesAdapter(S3FilesystemAdapter):
    """
    DigitalOcean Spaces adapter (S3-compatible).
    
    Inherits from S3FilesystemAdapter since Spaces uses S3-compatible API.
    """
    
    def __init__(
        self,
        bucket: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        **kwargs: Any
    ) -> None:
        # DigitalOcean Spaces endpoint format
        endpoint_url = f"https://{region}.digitaloceanspaces.com"
        
        super().__init__(
            bucket=bucket,
            region=region,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
            **kwargs
        )
    
    def url(self, path: str) -> str:
        """Get public URL for DigitalOcean Spaces object."""
        return f"https://{self.bucket}.{self.region}.digitaloceanspaces.com/{path.lstrip('/')}"


class MinIOAdapter(S3FilesystemAdapter):
    """
    MinIO adapter (S3-compatible).
    
    Inherits from S3FilesystemAdapter since MinIO uses S3-compatible API.
    """
    
    def __init__(
        self,
        bucket: str,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        secure: bool = True,
        **kwargs: Any
    ) -> None:
        super().__init__(
            bucket=bucket,
            region="us-east-1",  # MinIO doesn't require specific region
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
            **kwargs
        )
        self.secure = secure
    
    def url(self, path: str) -> str:
        """Get public URL for MinIO object."""
        scheme = "https" if self.secure else "http"
        endpoint = (self.endpoint_url or "").replace("http://", "").replace("https://", "")
        return f"{scheme}://{endpoint}/{self.bucket}/{path.lstrip('/')}"


class FTPFilesystemAdapter(FilesystemAdapter):
    """
    FTP filesystem adapter for Laravel-style storage operations.
    """
    
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 21,
        passive: bool = True,
        timeout: int = 30,
        root_path: str = "/",
        **kwargs: Any
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.passive = passive
        self.timeout = timeout
        self.root_path = root_path.rstrip('/')
        self.config = kwargs
        
        self._connection: Optional[Any] = None
    
    def _get_connection(self) -> Any:
        """Get FTP connection."""
        try:
            import ftplib
            
            if self._connection is None:
                self._connection = ftplib.FTP()
                self._connection.connect(self.host, self.port, timeout=self.timeout)
                self._connection.login(self.username, self.password)
                
                if self.passive:
                    self._connection.set_pasv(True)
            
            return self._connection
        except ImportError:
            raise RuntimeError("ftplib not available")
    
    def _full_path(self, path: str) -> str:
        """Get full FTP path."""
        clean_path = path.lstrip('/')
        return f"{self.root_path}/{clean_path}" if clean_path else self.root_path
    
    def exists(self, path: str) -> bool:
        """Check if file exists on FTP server."""
        try:
            ftp = self._get_connection()
            full_path = self._full_path(path)
            
            # Try to get file size (will fail if file doesn't exist)
            ftp.size(full_path)
            return True
        except Exception:
            return False
    
    def get(self, path: str) -> Optional[bytes]:
        """Get file contents from FTP server."""
        try:
            ftp = self._get_connection()
            full_path = self._full_path(path)
            
            data = io.BytesIO()
            ftp.retrbinary(f"RETR {full_path}", data.write)
            return data.getvalue()
        except Exception:
            return None
    
    def put(self, path: str, contents: Union[str, bytes, BinaryIO]) -> bool:
        """Put file to FTP server."""
        try:
            ftp = self._get_connection()
            full_path = self._full_path(path)
            
            # Ensure directory exists
            directory = '/'.join(full_path.split('/')[:-1])
            if directory and directory != self.root_path:
                self._ensure_directory_exists(directory)
            
            # Prepare data
            if isinstance(contents, str):
                data = io.BytesIO(contents.encode('utf-8'))
            elif hasattr(contents, 'read'):
                data = io.BytesIO(contents.read() if hasattr(contents, 'read') else contents)  # type: ignore[arg-type]
            else:
                data = io.BytesIO(contents)
            
            ftp.storbinary(f"STOR {full_path}", data)
            return True
        except Exception:
            return False
    
    def delete(self, path: str) -> bool:
        """Delete file from FTP server."""
        try:
            ftp = self._get_connection()
            full_path = self._full_path(path)
            ftp.delete(full_path)
            return True
        except Exception:
            return False
    
    def copy(self, from_path: str, to_path: str) -> bool:
        """Copy file on FTP server."""
        # FTP doesn't support server-side copy, so download and upload
        content = self.get(from_path)
        if content is None:
            return False
        return self.put(to_path, content)
    
    def move(self, from_path: str, to_path: str) -> bool:
        """Move file on FTP server."""
        try:
            ftp = self._get_connection()
            from_full = self._full_path(from_path)
            to_full = self._full_path(to_path)
            
            # Ensure target directory exists
            to_directory = '/'.join(to_full.split('/')[:-1])
            if to_directory and to_directory != self.root_path:
                self._ensure_directory_exists(to_directory)
            
            ftp.rename(from_full, to_full)
            return True
        except Exception:
            # Fallback to copy and delete
            return self.copy(from_path, to_path) and self.delete(from_path)
    
    def size(self, path: str) -> Optional[int]:
        """Get file size from FTP server."""
        try:
            ftp = self._get_connection()
            full_path = self._full_path(path)
            return ftp.size(full_path)  # type: ignore[no-any-return]
        except Exception:
            return None
    
    def last_modified(self, path: str) -> Optional[datetime]:
        """Get last modified time from FTP server."""
        try:
            ftp = self._get_connection()
            full_path = self._full_path(path)
            
            # Get modification time
            mdtm_response = ftp.sendcmd(f"MDTM {full_path}")
            # Response format: "213 YYYYMMDDHHMMSS"
            timestamp_str = mdtm_response.split()[1]
            
            # Parse timestamp
            return datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
        except Exception:
            return None
    
    def files(self, directory: str = "") -> List[str]:
        """List files in FTP directory."""
        try:
            ftp = self._get_connection()
            full_path = self._full_path(directory)
            
            files = []
            file_list = ftp.nlst(full_path)
            
            for item in file_list:
                # Check if it's a file (not directory)
                try:
                    ftp.size(item)  # This will fail for directories
                    # Remove root path prefix for relative paths
                    relative_path = item
                    if relative_path.startswith(self.root_path + '/'):
                        relative_path = relative_path[len(self.root_path) + 1:]
                    files.append(relative_path)
                except Exception:
                    pass  # Skip directories
            
            return sorted(files)
        except Exception:
            return []
    
    def directories(self, directory: str = "") -> List[str]:
        """List directories in FTP directory."""
        try:
            ftp = self._get_connection()
            full_path = self._full_path(directory)
            
            dirs = []
            file_list = ftp.nlst(full_path)
            
            for item in file_list:
                # Check if it's a directory
                try:
                    ftp.size(item)  # This will fail for directories
                except Exception:
                    # It's a directory
                    relative_path = item
                    if relative_path.startswith(self.root_path + '/'):
                        relative_path = relative_path[len(self.root_path) + 1:]
                    dirs.append(relative_path)
            
            return sorted(dirs)
        except Exception:
            return []
    
    def _ensure_directory_exists(self, directory: str) -> bool:
        """Ensure directory exists on FTP server."""
        try:
            ftp = self._get_connection()
            
            # Split path into components
            parts = directory.strip('/').split('/')
            current_path = self.root_path
            
            for part in parts:
                if not part:
                    continue
                
                current_path = f"{current_path}/{part}"
                
                try:
                    # Try to change to directory
                    current_dir = ftp.pwd()
                    ftp.cwd(current_path)
                    ftp.cwd(current_dir)  # Change back
                except Exception:
                    # Directory doesn't exist, create it
                    try:
                        ftp.mkd(current_path)
                    except Exception:
                        return False
            
            return True
        except Exception:
            return False
    
    def __del__(self) -> None:
        """Close FTP connection on cleanup."""
        if self._connection:
            try:
                self._connection.quit()
            except Exception:
                pass