"""
Pipeline Integration Test — publishes a fake audio message to the entry point
of the pipeline (audio.raw) and lets all worker services process it end-to-end.

Usage:
    RABBIT_URL=amqp://sentiment:password@rabbitmq:5672/ python tests/test_pipeline.py
"""

import asyncio
import json
import os
import aio_pika

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://sentiment:password@rabbitmq:5672/")
EXCHANGE_NAME = "grievance.events"


async def main():
    connection = await aio_pika.connect_robust(RABBIT_URL)
    channel = await connection.channel()

    exchange = await channel.declare_exchange(
        EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    # Minimal payload — simulates what the API Gateway would publish
    payload = {
        "request_id": "test-001",
        "audio_filename": "test_audio.wav",
        # Use a small WAV header so audio-service can save it as a valid file
        # (8 bytes of fake audio bytes encoded as latin1-safe string)
        "audio_bytes": b"RIFF\x00\x00\x00\x00WAVE".decode("latin1"),
    }

    message = aio_pika.Message(
        body=json.dumps(payload).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )

    await exchange.publish(message, routing_key="audio.raw")
    print(f"[TEST] Published message to 'audio.raw' → request_id: {payload['request_id']}")
    print("[TEST] Watch your worker terminals for the pipeline progression.")

    await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
