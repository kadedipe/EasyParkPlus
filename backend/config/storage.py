"""File storage configuration."""

import os
from typing import Dict, Any, Optional
from pathlib import Path

from . import config


class StorageConfig:
    """File storage configuration."""
    
    # Local storage
    LOCAL_UPLOAD_DIR: Path = config.BASE_DIR / config.UPLOAD_FOLDER
    LOCAL_TEMP_DIR: Path = config.BASE_DIR / 'tmp'
    
    # Cloud storage
    PROVIDER: str = os.getenv('STORAGE_PROVIDER', 'local')  # local, s3, gcs, azure
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY: str = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_S3_BUCKET: str = os.getenv('AWS_S3_BUCKET', '')
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    AWS_S3_ENDPOINT: Optional[str] = os.getenv('AWS_S3_ENDPOINT')
    
    # Google Cloud Storage
    GCS_BUCKET: str = os.getenv('GCS_BUCKET', '')
    GCS_PROJECT_ID: str = os.getenv('GCS_PROJECT_ID', '')
    GCS_CREDENTIALS: str = os.getenv('GCS_CREDENTIALS', '')
    
    # Azure Blob Storage
    AZURE_CONNECTION_STRING: str = os.getenv('AZURE_CONNECTION_STRING', '')
    AZURE_CONTAINER: str = os.getenv('AZURE_CONTAINER', '')
    
    # File settings
    MAX_FILE_SIZE: int = config.MAX_CONTENT_LENGTH
    ALLOWED_EXTENSIONS: set = config.ALLOWED_EXTENSIONS
    
    # Image processing
    IMAGE_MAX_WIDTH: int = 1920
    IMAGE_MAX_HEIGHT: int = 1080
    IMAGE_QUALITY: int = 85
    THUMBNAIL_SIZE: tuple = (300, 300)
    
    # URL settings
    PUBLIC_URL_PREFIX: str = os.getenv('PUBLIC_URL_PREFIX', '/static')
    CDN_URL: Optional[str] = os.getenv('CDN_URL')
    
    # Cache settings
    CACHE_CONTROL: str = "public, max-age=31536000"
    CACHE_CONTROL_PROFILE: str = "public, max-age=86400"
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration based on provider."""
        if self.PROVIDER == 's3':
            return {
                'access_key': self.AWS_ACCESS_KEY_ID,
                'secret_key': self.AWS_SECRET_ACCESS_KEY,
                'bucket': self.AWS_S3_BUCKET,
                'region': self.AWS_REGION,
                'endpoint': self.AWS_S3_ENDPOINT,
            }
        elif self.PROVIDER == 'gcs':
            return {
                'bucket': self.GCS_BUCKET,
                'project': self.GCS_PROJECT_ID,
                'credentials': self.GCS_CREDENTIALS,
            }
        elif self.PROVIDER == 'azure':
            return {
                'connection_string': self.AZURE_CONNECTION_STRING,
                'container': self.AZURE_CONTAINER,
            }
        else:
            return {
                'upload_dir': str(self.LOCAL_UPLOAD_DIR),
                'temp_dir': str(self.LOCAL_TEMP_DIR),
            }


storage_config = StorageConfig()