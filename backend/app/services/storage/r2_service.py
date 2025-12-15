"""Cloudflare R2 storage service for images and files.

R2 is S3-compatible, so we use boto3 to interact with it.
"""

import base64
import logging
from io import BytesIO
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class R2StorageService:
    """Cloudflare R2 storage service using S3-compatible API."""

    def __init__(
        self,
        account_id: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bucket_name: str | None = None,
        public_url_base: str | None = None,
    ):
        """
        Initialize R2 storage service.

        Args:
            account_id: Cloudflare account ID
            access_key_id: R2 access key ID
            secret_access_key: R2 secret access key
            bucket_name: R2 bucket name
            public_url_base: Base URL for public access (e.g., https://pub-xxx.r2.dev)
        """
        self.account_id = account_id or settings.cloudflare_r2_account_id
        self.access_key_id = access_key_id or settings.cloudflare_r2_access_key_id
        self.secret_access_key = (
            secret_access_key or settings.cloudflare_r2_secret_access_key
        )
        self.bucket_name = bucket_name or settings.cloudflare_r2_bucket_name
        self.public_url_base = public_url_base or settings.cloudflare_r2_public_url_base

        if not all([self.account_id, self.access_key_id, self.secret_access_key, self.bucket_name]):
            logger.warning(
                "R2 credentials not fully configured. R2 storage will be disabled."
            )
            self._client = None
            return

        # R2 endpoint URL format: https://<account_id>.r2.cloudflarestorage.com
        endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"

        # Create S3-compatible client for R2
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",  # R2 doesn't use regions
        )

        logger.info(f"R2 storage service initialized for bucket: {self.bucket_name}")

    def is_enabled(self) -> bool:
        """Check if R2 storage is enabled and configured."""
        return self._client is not None

    async def upload_image(
        self,
        image_data: bytes | str,
        object_key: str,
        content_type: str = "image/png",
    ) -> str:
        """
        Upload image to R2.

        Args:
            image_data: Image data as bytes or base64 string
            object_key: Object key (path) in R2 bucket
            content_type: MIME type of the image

        Returns:
            Public URL of the uploaded image

        Raises:
            ValueError: If R2 is not enabled
            Exception: If upload fails
        """
        if not self.is_enabled():
            raise ValueError("R2 storage is not enabled or configured")

        # Convert base64 string to bytes if needed
        if isinstance(image_data, str):
            # Remove data URL prefix if present
            if image_data.startswith("data:"):
                image_data = image_data.split(",", 1)[-1]
            # Decode base64
            image_data = base64.b64decode(image_data)

        try:
            # Upload to R2
            self._client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=image_data,
                ContentType=content_type,
                # Make object publicly readable if public_url_base is configured
                ACL="public-read" if self.public_url_base else "private",
            )

            logger.info(f"Image uploaded to R2: {object_key} ({len(image_data)} bytes)")

            # Return public URL (ensure it starts with https://)
            if self.public_url_base:
                # Use custom public URL if configured
                public_url = f"{self.public_url_base.rstrip('/')}/{object_key}"
                # Ensure URL starts with https://
                if not public_url.startswith("http://") and not public_url.startswith("https://"):
                    public_url = f"https://{public_url}"
                return public_url
            else:
                # Fallback to R2 public URL format
                return f"https://{self.account_id}.r2.dev/{object_key}"

        except ClientError as e:
            logger.error(f"Failed to upload image to R2: {e}")
            raise Exception(f"R2 upload failed: {str(e)}")

    async def get_image(self, object_key: str) -> bytes:
        """
        Get image from R2.

        Args:
            object_key: Object key (path) in R2 bucket

        Returns:
            Image data as bytes

        Raises:
            ValueError: If R2 is not enabled
            Exception: If download fails
        """
        if not self.is_enabled():
            raise ValueError("R2 storage is not enabled or configured")

        try:
            response = self._client.get_object(Bucket=self.bucket_name, Key=object_key)
            image_data = response["Body"].read()
            logger.info(f"Image retrieved from R2: {object_key} ({len(image_data)} bytes)")
            return image_data

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                raise FileNotFoundError(f"Image not found in R2: {object_key}")
            logger.error(f"Failed to get image from R2: {e}")
            raise Exception(f"R2 download failed: {str(e)}")

    async def delete_image(self, object_key: str) -> None:
        """
        Delete image from R2.

        Args:
            object_key: Object key (path) in R2 bucket

        Raises:
            ValueError: If R2 is not enabled
            Exception: If deletion fails
        """
        if not self.is_enabled():
            raise ValueError("R2 storage is not enabled or configured")

        try:
            self._client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info(f"Image deleted from R2: {object_key}")

        except ClientError as e:
            logger.error(f"Failed to delete image from R2: {e}")
            raise Exception(f"R2 deletion failed: {str(e)}")

    def generate_object_key(
        self,
        user_id: str,
        strategy_hash: str | None = None,
        image_id: str | None = None,
        extension: str = "png",
    ) -> str:
        """
        Generate object key for R2 storage.

        Format: strategy_chart/{user_id}/{strategy_hash}.{extension}
        
        If strategy_hash is not available, falls back to: strategy_chart/{user_id}/{image_id}.{extension}

        Args:
            user_id: User UUID
            strategy_hash: Strategy hash (preferred for filename, enables caching)
            image_id: Image UUID (fallback if strategy_hash is not available)
            extension: File extension (default: png)

        Returns:
            Object key string
        """
        # Use strategy_hash as filename if available (enables caching for same strategy)
        # Otherwise fall back to image_id
        filename = strategy_hash if strategy_hash else image_id
        if not filename:
            raise ValueError("Either strategy_hash or image_id must be provided")
        
        return f"strategy_chart/{user_id}/{filename}.{extension}"


# Singleton instance
_r2_service: R2StorageService | None = None


def get_r2_service() -> R2StorageService:
    """Get singleton R2 storage service instance."""
    global _r2_service
    if _r2_service is None:
        _r2_service = R2StorageService()
    return _r2_service

