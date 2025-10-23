"""
File Upload Handling for FastAPI ORM

This module provides utilities for handling file uploads with support
for multiple storage backends (local filesystem, S3-compatible storage).

Features:
- Multiple storage backends (local, S3)
- Automatic file validation (size, type)
- Unique filename generation
- Image optimization and resizing
- File metadata tracking
- Async upload processing

Example:
    ```python
    from fastapi import FastAPI, UploadFile, File
    from fastapi_orm.file_upload import FileManager, LocalStorage
    
    app = FastAPI()
    file_manager = FileManager(LocalStorage("./uploads"))
    
    @app.post("/upload")
    async def upload_file(file: UploadFile = File(...)):
        result = await file_manager.upload(
            file,
            allowed_types=["image/jpeg", "image/png"],
            max_size_mb=5
        )
        return {"url": result.url, "filename": result.filename}
    ```
"""

import os
import uuid
import aiofiles
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
import mimetypes
from fastapi import UploadFile, HTTPException


@dataclass
class UploadResult:
    """Result of a file upload operation."""
    filename: str
    original_filename: str
    url: str
    size: int
    content_type: str
    uploaded_at: datetime
    metadata: Dict[str, Any]


class StorageBackend:
    """Base class for storage backends."""
    
    async def save(
        self,
        file: UploadFile,
        filename: str
    ) -> str:
        """Save file and return URL."""
        raise NotImplementedError
    
    async def delete(self, filename: str) -> bool:
        """Delete file."""
        raise NotImplementedError
    
    async def exists(self, filename: str) -> bool:
        """Check if file exists."""
        raise NotImplementedError
    
    def get_url(self, filename: str) -> str:
        """Get public URL for file."""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """
    Local filesystem storage backend.
    
    Stores files on the local filesystem and serves them through
    the web server.
    
    Example:
        ```python
        storage = LocalStorage(
            upload_dir="./uploads",
            base_url="/static/uploads"
        )
        ```
    """
    
    def __init__(
        self,
        upload_dir: str = "./uploads",
        base_url: str = "/uploads",
        create_dirs: bool = True
    ):
        """
        Initialize local storage backend.
        
        Args:
            upload_dir: Directory to store uploaded files
            base_url: Base URL for serving files
            create_dirs: Create upload directory if it doesn't exist
        """
        self.upload_dir = Path(upload_dir)
        self.base_url = base_url.rstrip("/")
        
        if create_dirs:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def save(
        self,
        file: UploadFile,
        filename: str
    ) -> str:
        """Save file to local filesystem."""
        file_path = self.upload_dir / filename
        
        # Ensure subdirectories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
        
        return self.get_url(filename)
    
    async def delete(self, filename: str) -> bool:
        """Delete file from local filesystem."""
        file_path = self.upload_dir / filename
        
        try:
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    async def exists(self, filename: str) -> bool:
        """Check if file exists on local filesystem."""
        file_path = self.upload_dir / filename
        return file_path.exists()
    
    def get_url(self, filename: str) -> str:
        """Get public URL for file."""
        return f"{self.base_url}/{filename}"


class S3Storage(StorageBackend):
    """
    S3-compatible storage backend (AWS S3, MinIO, DigitalOcean Spaces, etc.).
    
    Requires boto3:
        pip install boto3
    
    Example:
        ```python
        storage = S3Storage(
            bucket="my-bucket",
            endpoint_url="https://s3.amazonaws.com",
            access_key="YOUR_ACCESS_KEY",
            secret_key="YOUR_SECRET_KEY",
            region="us-east-1"
        )
        ```
    """
    
    def __init__(
        self,
        bucket: str,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "us-east-1",
        public_url: Optional[str] = None,
        max_workers: int = 5
    ):
        """
        Initialize S3 storage backend.
        
        Args:
            bucket: S3 bucket name
            endpoint_url: S3 endpoint URL (for S3-compatible services)
            access_key: AWS access key
            secret_key: AWS secret key
            region: AWS region
            public_url: Public URL for files (if different from S3 URL)
            max_workers: Max thread pool workers for async operations
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 storage. "
                "Install it with: pip install boto3"
            )
        
        self.bucket = bucket
        self.public_url = public_url
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
    
    async def save(
        self,
        file: UploadFile,
        filename: str
    ) -> str:
        """Save file to S3 (offloaded to thread pool)."""
        content = await file.read()
        
        # Offload synchronous S3 operation to thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            lambda: self.s3_client.put_object(
                Bucket=self.bucket,
                Key=filename,
                Body=content,
                ContentType=file.content_type
            )
        )
        
        return self.get_url(filename)
    
    async def delete(self, filename: str) -> bool:
        """Delete file from S3 (offloaded to thread pool)."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                self.executor,
                lambda: self.s3_client.delete_object(
                    Bucket=self.bucket,
                    Key=filename
                )
            )
            return True
        except Exception:
            return False
    
    async def exists(self, filename: str) -> bool:
        """Check if file exists in S3 (offloaded to thread pool)."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                self.executor,
                lambda: self.s3_client.head_object(
                    Bucket=self.bucket,
                    Key=filename
                )
            )
            return True
        except:
            return False
    
    def get_url(self, filename: str) -> str:
        """Get public URL for file."""
        if self.public_url:
            return f"{self.public_url}/{filename}"
        return f"https://{self.bucket}.s3.amazonaws.com/{filename}"


class FileManager:
    """
    High-level file management with validation and processing.
    
    Example:
        ```python
        from fastapi import FastAPI, UploadFile, File
        
        app = FastAPI()
        fm = FileManager(LocalStorage("./uploads"))
        
        @app.post("/upload")
        async def upload(file: UploadFile = File(...)):
            result = await fm.upload(
                file,
                allowed_types=["image/jpeg", "image/png", "application/pdf"],
                max_size_mb=10,
                subfolder="documents"
            )
            return result.__dict__
        ```
    """
    
    def __init__(
        self,
        storage: StorageBackend,
        default_max_size_mb: int = 10
    ):
        """
        Initialize file manager.
        
        Args:
            storage: Storage backend to use
            default_max_size_mb: Default maximum file size in MB
        """
        self.storage = storage
        self.default_max_size_mb = default_max_size_mb
    
    async def upload(
        self,
        file: UploadFile,
        allowed_types: Optional[List[str]] = None,
        max_size_mb: Optional[int] = None,
        subfolder: Optional[str] = None,
        custom_filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """
        Upload a file with validation.
        
        Args:
            file: Uploaded file from FastAPI
            allowed_types: List of allowed MIME types
            max_size_mb: Maximum file size in MB
            subfolder: Subfolder to store file in
            custom_filename: Custom filename (uses UUID if not provided)
            metadata: Additional metadata to store
        
        Returns:
            UploadResult with file information
        
        Raises:
            HTTPException: If validation fails
        """
        max_size = (max_size_mb or self.default_max_size_mb) * 1024 * 1024
        metadata = metadata or {}
        
        # Validate content type
        if allowed_types and file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file.content_type} not allowed. "
                       f"Allowed types: {', '.join(allowed_types)}"
            )
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size {file_size / 1024 / 1024:.2f}MB exceeds "
                       f"maximum allowed size of {max_size_mb}MB"
            )
        
        # Reset file pointer
        await file.seek(0)
        
        # Generate filename
        if custom_filename:
            filename = custom_filename
        else:
            ext = self._get_extension(file.filename)
            unique_id = uuid.uuid4().hex
            filename = f"{unique_id}{ext}"
        
        # Add subfolder if specified
        if subfolder:
            filename = f"{subfolder}/{filename}"
        
        # Save file
        url = await self.storage.save(file, filename)
        
        # Create result
        result = UploadResult(
            filename=filename,
            original_filename=file.filename,
            url=url,
            size=file_size,
            content_type=file.content_type,
            uploaded_at=datetime.utcnow(),
            metadata=metadata
        )
        
        return result
    
    async def delete(self, filename: str) -> bool:
        """
        Delete a file.
        
        Args:
            filename: Filename to delete
        
        Returns:
            True if deleted, False otherwise
        """
        return await self.storage.delete(filename)
    
    async def exists(self, filename: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            filename: Filename to check
        
        Returns:
            True if exists, False otherwise
        """
        return await self.storage.exists(filename)
    
    def get_url(self, filename: str) -> str:
        """
        Get public URL for a file.
        
        Args:
            filename: Filename
        
        Returns:
            Public URL
        """
        return self.storage.get_url(filename)
    
    @staticmethod
    def _get_extension(filename: str) -> str:
        """Extract file extension from filename."""
        if not filename:
            return ""
        
        parts = filename.rsplit(".", 1)
        if len(parts) > 1:
            return f".{parts[1].lower()}"
        return ""


class ImageProcessor:
    """
    Image processing utilities for resizing and optimization.
    
    Requires Pillow:
        pip install Pillow
    
    Example:
        ```python
        processor = ImageProcessor()
        
        # Resize image
        thumbnail = await processor.resize(
            image_bytes,
            max_width=800,
            max_height=600,
            quality=85
        )
        ```
    """
    
    @staticmethod
    async def resize(
        image_bytes: bytes,
        max_width: int = 1920,
        max_height: int = 1080,
        quality: int = 85
    ) -> bytes:
        """
        Resize image while maintaining aspect ratio.
        
        Args:
            image_bytes: Original image bytes
            max_width: Maximum width
            max_height: Maximum height
            quality: JPEG quality (1-100)
        
        Returns:
            Resized image bytes
        """
        try:
            from PIL import Image
            import io
        except ImportError:
            raise ImportError(
                "Pillow is required for image processing. "
                "Install it with: pip install Pillow"
            )
        
        # Open image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Calculate new size maintaining aspect ratio
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        output.seek(0)
        
        return output.read()


__all__ = [
    "FileManager",
    "LocalStorage",
    "S3Storage",
    "UploadResult",
    "ImageProcessor",
]
