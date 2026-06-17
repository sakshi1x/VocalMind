# Entry point for Urgency Service
import asyncio
import json
import aio_pika
from app.config import RABBIT_URL, EXCHANGE, QUEUE, IN_KEY, OUT_KEY
from app.processor.urgency import compute_urgency
from shared.database.session import SessionLocal
from shared.utils.logger import get_queue_logger
from shared.database.services import audio as audio_crud

queue_logger = get_queue_logger()



async def process(message, exchange):
    async with message.process():
        data = json.loads(message.body.decode())
        audio_id = data.get("request_id")

        async with SessionLocal() as db:
            await audio_crud.update_audio(
                db=db,
                audio_id=audio_id,
                status="processing",
                current_stage="urgency_service",
            )

        urgency = compute_urgency(
            data.get("sentiment"),
            data.get("emotion"),
            data.get("category")
        )

        data["urgency"] = urgency

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(data).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=OUT_KEY
        )

        queue_logger.info(
            "Published urgency event",
            extra={
                "service": "urgency-service",
                "queue": QUEUE,
                "exchange": EXCHANGE,
                "routing_key": OUT_KEY,
                "request_id": data.get("request_id"),
                "event": "publish.success",
            },
        )

        print("⚡ urgency:", urgency)


async def main():
    conn = await aio_pika.connect_robust(RABBIT_URL)
    ch = await conn.channel()
    await ch.set_qos(prefetch_count=1)

    exchange = await ch.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)

    queue = await ch.declare_queue(QUEUE, durable=True)
    await queue.bind(exchange, routing_key=IN_KEY)
    queue_logger.info(
        "Queue bound to exchange",
        extra={
            "service": "urgency-service",
            "queue": QUEUE,
            "exchange": EXCHANGE,
            "routing_key": IN_KEY,
            "event": "queue.bind",
        },
    )

    await queue.consume(lambda m: process(m, exchange))

    print("⚡ urgency service running")

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())