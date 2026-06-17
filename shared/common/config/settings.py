import os
import dotenv
dotenv.load_dotenv()

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://sentiment:password@rabbitmq:5672/")
EXCHANGE_NAME = "grievance.events"

ROUTING_KEYS = {
    "audio_uploaded": "audio.uploaded",
    "transcription_completed": "transcription.completed",
}
