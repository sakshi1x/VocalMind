import boto3
from botocore.exceptions import NoCredentialsError
import uuid
from botocore.client import Config

from typing import Optional
from app.config import R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_DOMAIN, R2_URL_FORMAT, R2_ACCOUNT_ID


def upload_file_to_r2(file_bytes: bytes, filename: str, bucket: str = None, folder: Optional[str] = None) -> str:
    """
    Uploads a file to a Cloudflare R2 bucket and returns the public R2 URL.
    """
    bucket = bucket or R2_BUCKET
    unique_name = f"{uuid.uuid4()}_{filename}"
    key = f"{folder}/{unique_name}" if folder else unique_name
    endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        's3',
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        endpoint_url=endpoint_url,
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=file_bytes)
        r2_url = R2_URL_FORMAT.format(bucket=bucket, public_domain=R2_PUBLIC_DOMAIN, key=key)
        # Ensure the URL starts with 'https://' and not 'https:/'
        if r2_url.startswith("https:/") and not r2_url.startswith("https://"):
            r2_url = r2_url.replace("https:/", "https://", 1)
        return r2_url
    except NoCredentialsError:
        raise Exception("R2 credentials not found.")
    except Exception as e:
        raise Exception(f"Failed to upload to R2: {str(e)}")
