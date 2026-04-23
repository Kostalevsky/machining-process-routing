from io import BytesIO
from typing import BinaryIO
from urllib.parse import urlparse, urlunparse

import boto3
from botocore.client import BaseClient

from app.core.config import settings


class S3Storage:
    def __init__(self) -> None:
        self.bucket = settings.s3_bucket
        self._client: BaseClient = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )

    def upload_bytes(self, *, data: bytes, object_key: str, content_type: str) -> None:
        fileobj: BinaryIO = BytesIO(data)
        self._client.upload_fileobj(
            fileobj,
            self.bucket,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )

    def download_bytes(self, object_key: str) -> bytes:
        response = self._client.get_object(Bucket=self.bucket, Key=object_key)
        return response["Body"].read()

    def generate_presigned_url(self, object_key: str) -> str:
        presigned_url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=settings.s3_presign_expire_seconds,
        )
        return _replace_base_url(presigned_url, settings.s3_public_endpoint_url)


def get_storage() -> S3Storage:
    return S3Storage()


def _replace_base_url(url: str, public_base_url: str) -> str:
    original = urlparse(url)
    public = urlparse(public_base_url)
    return urlunparse(
        (
            public.scheme,
            public.netloc,
            original.path,
            original.params,
            original.query,
            original.fragment,
        )
    )
