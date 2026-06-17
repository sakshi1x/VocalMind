import os
import uuid
from pathlib import Path



BASE_DIR = Path("/Users/rumsan/Documents/apps/grievance-ai-system")

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def save_file(file_bytes: bytes, audio_filename: str) -> str:
    unique_name = f"{uuid.uuid4()}_{audio_filename}"
    file_path = UPLOAD_DIR / unique_name

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    return file_path