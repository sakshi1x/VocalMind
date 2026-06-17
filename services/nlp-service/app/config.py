# NLP Service config
import os
import dotenv
dotenv.load_dotenv()

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://sentiment:password@rabbitmq:5672/")
EXCHANGE_NAME = "grievance.events"

QUEUE_NAME = "nlp.analysis_queue"

ROUTING_KEY_IN = "text.translated"
ROUTING_KEY_OUT = "nlp.analyzed"