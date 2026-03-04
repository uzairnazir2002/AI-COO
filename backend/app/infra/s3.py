import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings


def s3_client():
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=f"http://{s.minio_endpoint}",
        aws_access_key_id=s.minio_access_key,
        aws_secret_access_key=s.minio_secret_key,
        region_name="us-east-1",
    )


def ensure_bucket(client) -> None:
    s = get_settings()
    try:
        client.head_bucket(Bucket=s.minio_bucket)
    except ClientError:
        client.create_bucket(Bucket=s.minio_bucket)
