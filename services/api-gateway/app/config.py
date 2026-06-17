# API Gateway config
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://sentiment:password@rabbitmq:5672/")
EXCHANGE_NAME = os.getenv("EXCHANGE_NAME", "grievance.events")
ENTRY_ROUTING_KEY = "audio.raw"

BASE_DIR = os.getenv("BASE_DIR", Path(__file__).resolve().parent.parent.parent.parent)

# AWS S3 and audio upload config
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_PUBLIC_DOMAIN = os.getenv("R2_PUBLIC_DOMAIN")
R2_URL_FORMAT = os.getenv("R2_URL_FORMAT", "https://{bucket}.{public_domain}/{key}")

