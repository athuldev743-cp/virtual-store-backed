# app/utils/cloudinary_utils.py
import cloudinary
import cloudinary.uploader
import os
from fastapi import UploadFile

# Configure Cloudinary using your environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

def upload_to_cloudinary(file: UploadFile, folder: str = "products") -> str:
    """
    Upload a FastAPI UploadFile to Cloudinary.

    Args:
        file (UploadFile): The uploaded file from FastAPI form.
        folder (str): Cloudinary folder to store the file in.

    Returns:
        str: The URL of the uploaded image.
    """
    try:
        result = cloudinary.uploader.upload(
            file.file,
            folder=folder,
            public_id=None,  # auto-generated
            overwrite=True,
            resource_type="image"
        )
        return result.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload failed: {e}")
        return None
