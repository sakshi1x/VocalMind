# ASR Service config
import os
import dotenv
dotenv.load_dotenv()

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://sentiment:password@rabbitmq:5672/")
EXCHANGE_NAME = "grievance.events"

QUEUE_NAME = "audio_transcription_queue"

ROUTING_KEY_IN = "audio.uploaded"
ROUTING_KEY_OUT = "transcription.completed"

# ASR Model Configuration
SHORT_ASR_MODEL = os.getenv("SHORT_ASR_MODEL", "omniASR_LLM_1B_v2")
LONG_ASR_MODEL = os.getenv("LONG_ASR_MODEL", "omniASR_LLM_Unlimited_300M_v2")
SHORT_ASR_MODEL_CACHE_DIR = os.getenv("SHORT_ASR_MODEL_CACHE_DIR", "model_cache/short_asr")
LONG_ASR_MODEL_CACHE_DIR = os.getenv("LONG_ASR_MODEL_CACHE_DIR", "model_cache/long_asr")