# Translation Service config
import os
from dotenv import load_dotenv


load_dotenv()

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://sentiment:password@rabbitmq:5672/")
EXCHANGE_NAME = "grievance.events"

QUEUE_NAME = "translation.queue"

ROUTING_KEY_IN = "language.detected"
ROUTING_KEY_OUT = "text.translated"



openai_api_key = os.getenv("OPENAI_API_KEY")
translation_model = os.getenv("TRANSLATION_MODEL")

USE_OPENAI = bool(openai_api_key)

model = translation_model