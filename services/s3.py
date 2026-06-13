import base64
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from config import settings


def _client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def upload_bytes(key: str, data: bytes, content_type: str) -> str:
    _client().put_object(
        Bucket=settings.AWS_S3_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


def download_bytes(key: str) -> bytes:
    response = _client().get_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=key)
    return response["Body"].read()


def download_as_data_url(key: str, mime_type: str = "image/png") -> Optional[str]:
    """Download a file from S3 and return as a base64 data URL for embedding in HTML."""
    try:
        data = download_bytes(key)
        b64 = base64.b64encode(data).decode()
        return f"data:{mime_type};base64,{b64}"
    except ClientError:
        return None


def delete_object(key: str) -> None:
    _client().delete_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=key)


def list_keys_by_prefix(prefix: str) -> list[str]:
    """Return all S3 object keys whose key starts with *prefix*."""
    client = _client()
    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.AWS_S3_BUCKET_NAME, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def delete_keys(keys: list[str]) -> None:
    """Delete a list of S3 keys in batches of 1 000 (AWS limit)."""
    if not keys:
        return
    client = _client()
    for i in range(0, len(keys), 1000):
        batch = [{"Key": k} for k in keys[i : i + 1000]]
        client.delete_objects(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Delete={"Objects": batch, "Quiet": True},
        )


def presigned_download_url(key: str, expires_in: int = 900) -> str:
    """Generate a presigned S3 URL valid for `expires_in` seconds (default 15 min)."""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )
