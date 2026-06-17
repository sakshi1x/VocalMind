# Entry point for NLP Service
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
from app.processor.main import analyze
from app.processor.category import _get_classifier
from app.processor.sentiment import _get_emotion_pipeline, _get_sentiment_pipeline
from shared.database.session import SessionLocal
from shared.utils.logger import get_queue_logger
from shared.database.services import audio as audio_crud

queue_logger = get_queue_logger()


def _prewarm_models() -> None:
    """Load all ML models into memory before consuming messages.
    Prevents RabbitMQ channel timeouts caused by slow first-message model loads."""
    print("🧠 Pre-warming NLP models (this may take a minute)...")
    _get_classifier()
    print("  ✔ category classifier ready")
    _get_sentiment_pipeline()
    print("  ✔ sentiment model ready")
    _get_emotion_pipeline()
    print("  ✔ emotion model ready")
    print("🧠 All NLP models loaded.")


async def process_message(message: aio_pika.IncomingMessage, exchange):
    async with message.process(requeue=False):
      try:
        data = json.loads(message.body.decode())
        audio_id = data.get("request_id")

        async with SessionLocal() as db:
            await audio_crud.update_audio(
                db=db,
                audio_id=audio_id,
                status="processing",
                current_stage="nlp_service",
            )

        text = data.get("translated_text") or data.get("transcript")
        category = data.get("category")

        if not text:
            print(f"❌ [{audio_id}] No text found for NLP")
            return

        print(f"🧠 [{audio_id}] Starting NLP analysis | text_len={len(text)} category={category}")

        # 🧠 NLP processing
        result = await analyze(text, category)

        print(
            f"🧠 [{audio_id}] NLP result:\n"
            f"   category  : {result['category']} ({result['category_confidence']:.0%})\n"
            f"   sentiment : {result['sentiment']} ({result['sentiment_score']:.0%})\n"
            f"   emotion   : {result['emotion']} ({result['emotion_score']:.0%})\n"
            f"   urgency   : {result['urgency']}"
        )

        # merge results into payload
        data.update(result)
        data["event"] = ROUTING_KEY_OUT

        # 🚀 publish downstream
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(data).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=ROUTING_KEY_OUT
        )

        queue_logger.info(
            "Published NLP event",
            extra={
                "service": "nlp-service",
                "queue": QUEUE_NAME,
                "exchange": EXCHANGE_NAME,
                "routing_key": ROUTING_KEY_OUT,
                "request_id": data.get("request_id"),
                "event": "publish.success",
            },
        )

        print(f"🧠 [{audio_id}] published → {ROUTING_KEY_OUT}")
      except Exception as exc:
          print(f"❌ [{audio_id}] NLP error: {exc}")
          raise


async def main():
    # Load models before connecting to RabbitMQ so the channel never times out
    # waiting for a slow first-message model load.
    await asyncio.to_thread(_prewarm_models)

    connection = await aio_pika.connect_robust(RABBIT_URL)
    channel = await connection.channel()

    await channel.set_qos(prefetch_count=1)

    exchange = await channel.declare_exchange(
        EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True
    )

    queue = await channel.declare_queue(QUEUE_NAME, durable=True)

    # 👇 listens to translated text
    await queue.bind(exchange, routing_key=ROUTING_KEY_IN)
    queue_logger.info(
        "Queue bound to exchange",
        extra={
            "service": "nlp-service",
            "queue": QUEUE_NAME,
            "exchange": EXCHANGE_NAME,
            "routing_key": ROUTING_KEY_IN,
            "event": "queue.bind",
        },
    )

    async def on_message(msg: aio_pika.IncomingMessage) -> None:
        await process_message(msg, exchange)

    await queue.consume(on_message)

    print("🧠 NLP service running...")

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())