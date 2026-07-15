# Wrapper around boto3 for S3 file operations (upload, download, delete).
#
# In development, `endpoint_url` points at LocalStack (a local AWS emulator)
# so we don't need real AWS credentials. In production, remove that setting
# and boto3 will talk to real S3 automatically.
#
# The s3_client is a module-level singleton — created once when the module
# loads so we don't open a new connection on every request.

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


s3_client = boto3.client(
    "s3",
    region_name=settings.aws_region,
    endpoint_url=settings.s3_endpoint_url,  # None in production → uses real AWS
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key
)

def upload_file_to_s3(file_bytes: bytes, s3_key: str) -> str:
    try:
        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=file_bytes
        )
        return s3_key
    except ClientError as e:
        raise ValueError(f"Failed to upload file to S3: {e}")


def download_file_from_s3(s3_key: str) -> bytes:
    try:
        response = s3_client.get_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key
        )
        return response['Body'].read()
    except ClientError as e:
        raise ValueError(f"Failed to download file from S3: {e}")


def delete_file_from_s3(s3_key: str) -> None:
    try:
        s3_client.delete_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key
        )
    except ClientError as e:
        raise ValueError(f"Failed to delete file from S3: {e}")



