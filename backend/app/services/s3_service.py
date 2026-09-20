"""Amazon S3 integration — receipt and user-uploaded image storage.

Credentials never leave the server. Returns the object key plus an S3
URL; presigned GET URLs can be minted for private buckets.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class S3Unavailable(Exception):
    pass


_CONTENT_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "application/pdf": "pdf",
}


class S3Service:
    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self._settings.aws_s3_bucket)

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config

                self._client = boto3.client(
                    "s3",
                    region_name=self._settings.aws_region,
                    aws_access_key_id=self._settings.aws_access_key_id,
                    aws_secret_access_key=self._settings.aws_secret_access_key,
                    config=Config(connect_timeout=5, read_timeout=30),
                )
            except Exception as exc:  # pragma: no cover
                raise S3Unavailable(f"S3 client init failed: {exc!r}") from exc
        return self._client

    def build_key(self, *, user_id: UUID, prefix: str, content_type: str) -> str:
        ext = _CONTENT_EXT.get(content_type, "bin")
        return f"{prefix}/{user_id}/{uuid4()}.{ext}"

    def object_url(self, key: str) -> str:
        bucket = self._settings.aws_s3_bucket
        region = self._settings.aws_region or "ap-south-1"
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

    def upload_bytes(
        self, *, user_id: UUID, data: bytes, content_type: str, prefix: str
    ) -> dict[str, str]:
        """Upload bytes under ``{prefix}/{user_id}/…`` → {"key", "url"}."""
        if not self.enabled:
            raise S3Unavailable("AWS_S3_BUCKET is not configured")
        key = self.build_key(user_id=user_id, prefix=prefix, content_type=content_type)
        try:
            self._get_client().put_object(
                Bucket=self._settings.aws_s3_bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
        except Exception as exc:
            logger.warning("S3 upload failed: %r", exc)
            raise S3Unavailable(f"S3 upload failed: {exc!r}") from exc
        return {"key": key, "url": self.object_url(key)}

    def presigned_get_url(self, key: str, expires_seconds: int = 3600) -> str:
        try:
            return self._get_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": self._settings.aws_s3_bucket, "Key": key},
                ExpiresIn=expires_seconds,
            )
        except Exception as exc:  # pragma: no cover
            raise S3Unavailable(f"Presign failed: {exc!r}") from exc
