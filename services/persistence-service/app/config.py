import os
import dotenv
dotenv.load_dotenv()

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://sentiment:password@rabbitmq:5672/")
EXCHANGE = "grievance.events"

QUEUE = "persistence.write_queue"

IN_KEY = "urgency.derived"