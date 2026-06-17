# Entry point for ASR Service

import asyncio
import json
import os

import aio_pika
import psutil

os.environ.setdefault(
    "HF_HUB_DISABLE_PROGRESS_BARS",
    "1",
)

os.environ.setdefault(
    "TRANSFORMERS_NO_PROGRESS_BAR",
    "1",
)

os.environ.setdefault(
    "HF_HUB_DISABLE_TELEMETRY",
    "1",
)

from app.config import (
    RABBIT_URL,
    EXCHANGE_NAME,
    QUEUE_NAME,
    ROUTING_KEY_IN,
    ROUTING_KEY_OUT,
)

from app.processor.asr import (
    transcribe,
    model_manager,
)

from shared.utils.logger import (
    get_queue_logger,
)

queue_logger = get_queue_logger()


async def process_message(
    message: aio_pika.IncomingMessage,
    exchange,
):

    async with message.process(
        requeue=False
    ):

        try:

            data = json.loads(
                message.body.decode()
            )

            queue_logger.info(
                "Received ASR input message",
                extra={
                    "service": "asr-service",
                    "queue": QUEUE_NAME,
                    "exchange": EXCHANGE_NAME,
                    "routing_key": ROUTING_KEY_IN,
                    "request_id": data.get(
                        "request_id"
                    ),
                    "audio_path": data.get(
                        "audio_path"
                    ),
                    "event": "process.start",
                },
            )

            wav_path = data.get(
                "wav_path"
            )

            if not wav_path:

                raise ValueError(
                    "Missing wav_path "
                    "in ASR input"
                )

            # 🎤 Transcribe
            transcript = await transcribe(
                wav_path
            )

            queue_logger.info(
                "Transcription completed",
                extra={
                    "service": "asr-service",
                    "queue": QUEUE_NAME,
                    "exchange": EXCHANGE_NAME,
                    "wav_path": wav_path,
                    "request_id": data.get(
                        "request_id"
                    ),
                    "event": (
                        "transcription.completed"
                    ),
                },
            )

            # Update payload
            data["transcript"] = transcript
            print(f"Transcription result: {transcript}")
            data["event"] = ROUTING_KEY_OUT

            # 🚀 Publish result
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(
                        data
                    ).encode(),
                    delivery_mode=(
                        aio_pika.DeliveryMode.PERSISTENT
                    ),
                ),
                routing_key=ROUTING_KEY_OUT,
            )

            queue_logger.info(
                "Published ASR output event",
                extra={
                    "service": "asr-service",
                    "queue": QUEUE_NAME,
                    "exchange": EXCHANGE_NAME,
                    "routing_key": (
                        ROUTING_KEY_OUT
                    ),
                    "request_id": data.get(
                        "request_id"
                    ),
                    "event": (
                        "publish.success"
                    ),
                },
            )

        except Exception as e:
            queue_logger.exception(f"ASR processing failed: {e}")
            print(f"FAILED REQUEST: {data.get('request_id') if 'data' in dir() else 'unknown'}")
            raise


async def main():

    # ✅ PRELOAD MODEL
    print("ASR model preload: starting")
    queue_logger.info(
        "Preloading ASR model",
        extra={
            "service": "asr-service",
            "event": "model.preload.start",
        },
    )

    try:
        print("ASR model load wrapper: before get_model")
        print("STARTING ASR service")
        print(f"ROUTING_KEY_IN = {ROUTING_KEY_IN}")
        print(f"RABBIT_URL = {RABBIT_URL}")
        queue_logger.info(
            "Loading ASR model...",
            extra={
                "service": "asr-service",
                "event": "model.loading.start",
            },
        )
        model_manager.get_model()
        import psutil

        process = psutil.Process()

        print(
            "RAM after model load:",
            process.memory_info().rss / 1024 / 1024,
            "MB"
        )
        print("ASR model load wrapper: after get_model")
        queue_logger.info(
            "ASR model loaded successfully",
            extra={
                "service": "asr-service",
                "event": "model.loading.success",
            },
        )
    except Exception:
        queue_logger.exception(
            "Failed to load ASR model",
            extra={
                "service": "asr-service",
                "event": "model.loading.failure",
            },
        )
        raise

    queue_logger.info(
        "ASR model loaded",
        extra={
            "service": "asr-service",
            "event": "model.preload.success",
        },
    )

    # RabbitMQ connection
    connection = (
        await aio_pika.connect_robust(
            RABBIT_URL
        )
    )

    channel = await connection.channel()

    await channel.set_qos(
        prefetch_count=1
    )

    exchange = (
        await channel.declare_exchange(
            EXCHANGE_NAME,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
    )

    queue = await channel.declare_queue(
        QUEUE_NAME,
        durable=True,
    )

    # Queue binding
    await queue.bind(
        exchange,
        routing_key=ROUTING_KEY_IN,
    )

    queue_logger.info(
        "Queue bound to exchange",
        extra={
            "service": "asr-service",
            "queue": QUEUE_NAME,
            "exchange": EXCHANGE_NAME,
            "routing_key": ROUTING_KEY_IN,
            "event": "queue.bind",
        },
    )
    print("ASR queue bound, about to start consumer")

    # Start consumer
    await queue.consume(
        lambda msg: process_message(
            msg,
            exchange,
        )
    )

    queue_logger.info(
        "ASR service startup complete",
        extra={
            "service": "asr-service",
            "queue": QUEUE_NAME,
            "exchange": EXCHANGE_NAME,
            "event": "service.started",
        },
    )
    print("ASR service startup complete")

    await asyncio.Future()


if __name__ == "__main__":

    queue_logger.info(
        "Starting asr-service",
        extra={
            "service": "asr-service",
            "queue": QUEUE_NAME,
            "exchange": EXCHANGE_NAME,
            "event": "service.starting",
        },
    )

    asyncio.run(main())