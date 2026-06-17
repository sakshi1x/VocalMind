# Urgency Service config
import os
import dotenv
dotenv.load_dotenv()

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://sentiment:password@rabbitmq:5672/")
EXCHANGE = "grievance.events"

QUEUE = "urgency.queue"

IN_KEY = "nlp.analyzed"
OUT_KEY = "urgency.derived"
