import os
import uuid

import boto3
from botocore.client import Config

from app.config import (
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET,
    R2_ACCOUNT_ID,
)


def upload_file_to_r2(
    file_path: str,
    filename: str = None,
    bucket: str = None,
    folder: str = None,
) -> str:

    bucket = bucket or R2_BUCKET

    filename = filename or os.path.basename(file_path)

    unique_name = f"{uuid.uuid4()}_{filename}"

    key = f"{folder}/{unique_name}" if folder else unique_name

    endpoint_url = (
        f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    )

    s3 = boto3.client(
        "s3",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        endpoint_url=endpoint_url,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )

    with open(file_path, "rb") as f:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=f,
        )

    # Generate downloadable URL
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": bucket,
            "Key": key,
        },
        ExpiresIn=3600,
    )

    return presigned_url