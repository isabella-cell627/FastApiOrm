import pytest
import pytest_asyncio
import tempfile
import os

pytest.importorskip("aiofiles", reason="aiofiles is required for file upload tests")

from fastapi_orm.file_upload import StorageBackend, UploadResult


def test_storage_backend_class():
    """Test StorageBackend class exists"""
    assert StorageBackend is not None


def test_upload_result_class():
    """Test UploadResult dataclass exists"""
    assert UploadResult is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
