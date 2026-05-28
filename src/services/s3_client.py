import logging
from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from src.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_s3_client() -> BaseClient:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket(bucket: str | None = None) -> None:
    settings = get_settings()
    bucket = bucket or settings.s3_bucket
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchBucket", "NotFound"}:
            logger.info("Creating bucket %s", bucket)
            client.create_bucket(Bucket=bucket)
        else:
            raise


def upload_fileobj(fileobj: BinaryIO, key: str, content_type: str = "application/pdf") -> None:
    client = get_s3_client()
    bucket = get_settings().s3_bucket
    client.upload_fileobj(fileobj, bucket, key, ExtraArgs={"ContentType": content_type})


def download_bytes(key: str) -> bytes:
    client = get_s3_client()
    bucket = get_settings().s3_bucket
    resp = client.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


def presigned_url(key: str, expires_in: int = 3600) -> str:
    client = get_s3_client()
    bucket = get_settings().s3_bucket
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def ping() -> bool:
    try:
        get_s3_client().list_buckets()
        return True
    except Exception:
        logger.exception("S3 ping failed")
        return False
