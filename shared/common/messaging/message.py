import json
import aio_pika

def encode(data: dict) -> aio_pika.Message:
    return aio_pika.Message(
        body=json.dumps(data).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
    )

def decode(body: bytes) -> dict:
    return json.loads(body.decode())