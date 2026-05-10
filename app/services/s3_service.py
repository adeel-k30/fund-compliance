import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


s3_client = boto3.client(
    "s3",
    region_name=settings.aws_region,
    endpoint_url=settings.aws_endpoint_url,
    aws_access_key_id=settings.aws_access_key,
    aws_secret_access_key=settings.aws_secret_key
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



