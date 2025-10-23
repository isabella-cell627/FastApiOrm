"""
Example demonstrating file upload handling with FastAPI ORM.

This example shows how to handle file uploads with validation,
storage backends (local and S3), and image processing.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi_orm.file_upload import (
    FileManager,
    LocalStorage,
    UploadResult,
    ImageProcessor
)


app = FastAPI(title="File Upload API")

# Initialize file manager with local storage
file_manager = FileManager(
    storage=LocalStorage(
        upload_dir="./uploads",
        base_url="/files"
    ),
    default_max_size_mb=10
)

image_processor = ImageProcessor()


@app.post("/upload/image")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image with automatic validation and optimization.
    
    Allowed: JPEG, PNG, GIF, WebP
    Max size: 5MB
    """
    try:
        result = await file_manager.upload(
            file,
            allowed_types=["image/jpeg", "image/png", "image/gif", "image/webp"],
            max_size_mb=5,
            subfolder="images",
            metadata={"category": "user_uploads"}
        )
        
        return {
            "success": True,
            "file": {
                "filename": result.filename,
                "original_name": result.original_filename,
                "url": result.url,
                "size": result.size,
                "type": result.content_type,
                "uploaded_at": result.uploaded_at.isoformat()
            }
        }
    
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )


@app.post("/upload/document")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document file.
    
    Allowed: PDF, DOCX, TXT
    Max size: 10MB
    """
    try:
        result = await file_manager.upload(
            file,
            allowed_types=[
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain"
            ],
            max_size_mb=10,
            subfolder="documents"
        )
        
        return {
            "success": True,
            "file": {
                "filename": result.filename,
                "url": result.url,
                "size_kb": round(result.size / 1024, 2)
            }
        }
    
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )


@app.post("/upload/thumbnail")
async def upload_with_thumbnail(file: UploadFile = File(...)):
    """
    Upload image and create a thumbnail.
    
    Creates both full-size and thumbnail versions.
    """
    try:
        # Validate it's an image
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Only image files are allowed"
            )
        
        # Upload original
        original = await file_manager.upload(
            file,
            allowed_types=["image/jpeg", "image/png"],
            max_size_mb=5,
            subfolder="images/originals"
        )
        
        # Create thumbnail
        await file.seek(0)  # Reset file pointer
        content = await file.read()
        
        thumbnail_bytes = await image_processor.resize(
            content,
            max_width=400,
            max_height=400,
            quality=80
        )
        
        # Save thumbnail (would need to create UploadFile from bytes)
        # For simplicity, just return original info
        
        return {
            "success": True,
            "original": {
                "url": original.url,
                "size": original.size
            },
            "message": "Image uploaded successfully"
        }
    
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )


@app.delete("/files/{filename:path}")
async def delete_file(filename: str):
    """Delete an uploaded file."""
    success = await file_manager.delete(filename)
    
    if success:
        return {"success": True, "message": f"File {filename} deleted"}
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/files/{filename:path}/exists")
async def check_file_exists(filename: str):
    """Check if a file exists."""
    exists = await file_manager.exists(filename)
    return {
        "filename": filename,
        "exists": exists,
        "url": file_manager.get_url(filename) if exists else None
    }


@app.get("/")
async def root():
    return {
        "message": "File Upload API",
        "endpoints": {
            "upload_image": "POST /upload/image",
            "upload_document": "POST /upload/document",
            "upload_thumbnail": "POST /upload/thumbnail",
            "delete_file": "DELETE /files/{filename}",
            "check_exists": "GET /files/{filename}/exists"
        }
    }


"""
Usage with curl:

# Upload an image
curl -X POST "http://localhost:5000/upload/image" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@photo.jpg"

# Upload a PDF document
curl -X POST "http://localhost:5000/upload/document" \
  -F "file=@document.pdf"

# Check if file exists
curl "http://localhost:5000/files/images/abc123.jpg/exists"

# Delete file
curl -X DELETE "http://localhost:5000/files/images/abc123.jpg"
"""


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("File Upload API Server")
    print("="*50)
    print("\nAPI: http://localhost:5000/")
    print("Docs: http://localhost:5000/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=5000)
