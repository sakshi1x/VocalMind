# Entry point for Translation Service
import asyncio
import json
import aio_pika

from app.config import (
    RABBIT_URL,
    EXCHANGE_NAME,
    QUEUE_NAME,
    ROUTING_KEY_IN,
    ROUTING_KEY_OUT
)
from app.processor.translator import translate
from shared.database.session import SessionLocal
from shared.utils.logger import get_queue_logger
from shared.database.services import audio as audio_crud

queue_logger = get_queue_logger()


async def process_message(message: aio_pika.IncomingMessage, exchange):
    async with message.process():
        data = json.loads(message.body.decode())
        audio_id = data.get("request_id")

        async with SessionLocal() as db:
            await audio_crud.update_audio(
                db=db,
                audio_id=audio_id,
                status="processing",
                current_stage="translation_service",
            )

        text = data.get("transcript")
        lang = data.get("language")

        if not text or not lang:
            print("❌ Missing transcript or language")
            return

        # 🧠 Translate (only non-en should reach here)
        translated_text = await translate(text, lang)
        print(f"Translated text: {translated_text}")

        # update payload
        data["translated_text"] = translated_text
        data["event"] = ROUTING_KEY_OUT

        # 🚀 send to next stage
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(data).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=ROUTING_KEY_OUT
        )

        queue_logger.info(
            "Published translation event",
            extra={
                "service": "translation-service",
                "queue": QUEUE_NAME,
                "exchange": EXCHANGE_NAME,
                "routing_key": ROUTING_KEY_OUT,
                "request_id": data.get("request_id"),
                "event": "publish.success",
            },
        )

        print(f"🌐 Translated ({lang} → en)")


async def main():
    connection = await aio_pika.connect_robust(RABBIT_URL)
    channel = await connection.channel()

    await channel.set_qos(prefetch_count=1)

    exchange = await channel.declare_exchange(
        EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True
    )

    queue = await channel.declare_queue(QUEUE_NAME, durable=True)

    # 👇 ONLY listens to non-English events
    await queue.bind(exchange, routing_key=ROUTING_KEY_IN)
    queue_logger.info(
        "Queue bound to exchange",
        extra={
            "service": "translation-service",
            "queue": QUEUE_NAME,
            "exchange": EXCHANGE_NAME,
            "routing_key": ROUTING_KEY_IN,
            "event": "queue.bind",
        },
    )

    await queue.consume(lambda msg: process_message(msg, exchange))

    print("🌐 Translation service running...")

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())