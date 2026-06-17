import logging
import os
import subprocess
import tempfile
from urllib.parse import urlparse

import boto3
from botocore.client import Config

from app.config import (
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET,
)

logger = logging.getLogger(__name__)

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

def download_from_r2(r2_url: str) -> str:
    """
    Download private R2 object locally.
    """

    parsed = urlparse(r2_url)

    # Entire path is the key
    key = parsed.path.lstrip("/")

    if not key:
        raise ValueError(f"Invalid R2 URL: {r2_url}")

    extension = os.path.splitext(key)[1]

    tmp = tempfile.NamedTemporaryFile(
        suffix=extension,
        delete=False,
    )

    local_path = tmp.name
    tmp.close()

    print(f"[DEBUG] Downloading key: {key}")
    print(f"[DEBUG] Local path: {local_path}")

    s3.download_file(
        Bucket=R2_BUCKET,
        Key=key,
        Filename=local_path,
    )

    return local_path

def convert_to_wav(input_path: str) -> str:
    """
    Converts audio to wav and returns LOCAL wav path.
    DOES NOT upload back to R2.
    DOES NOT delete original file.
    """

    print(f"[DEBUG] convert_to_wav input_path: {input_path}")

    is_url = input_path.startswith("http")

    local_input_path = input_path

    # Download from R2 if URL
    if is_url:
        local_input_path = download_from_r2(input_path)

        print(f"[DEBUG] Downloaded local file: {local_input_path}")

    output_path = local_input_path + ".converted.wav"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            local_input_path,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "wav",
            output_path,
        ],
        check=True,
        capture_output=True,
    )

    print(f"[DEBUG] Converted wav path: {output_path}")

    return output_path