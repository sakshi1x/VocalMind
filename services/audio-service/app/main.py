# Entry point for Audio Service
import asyncio
import json
import aio_pika

from app.config import RABBIT_URL, EXCHANGE_NAME, AUDIO_UPLOADED
from app.processor.audio_processor import convert_to_wav
from app.utils.file_handler import save_file
from shared.database.session import SessionLocal
from shared.utils.logger import get_queue_logger
from shared.database.services import audio as audio_crud

queue_logger = get_queue_logger()

QUEUE_NAME = "audio.upload_queue"


async def process_message(message: aio_pika.IncomingMessage, exchange):
    async with message.process():
        data = json.loads(message.body.decode())
        audio_id = data.get("request_id")

        queue_logger.info(
            "Received raw audio upload message",
            extra={
                "service": "audio-service",
                "queue": QUEUE_NAME,
                "exchange": EXCHANGE_NAME,
                "routing_key": "audio.raw",
                "request_id": audio_id,
                "audio_filename": data.get("audio_filename"),
                "event": "process.start",
            },
        )

        async with SessionLocal() as db:
            await audio_crud.update_audio(
                db=db,
                audio_id=audio_id,
                status="processing",
                current_stage="audio_service",
            )

        audio_filename = data["audio_filename"]

        queue_logger.info(
            "Saved uploaded audio file",
            extra={
                "service": "audio-service",
                "queue": QUEUE_NAME,
                "exchange": EXCHANGE_NAME,
                "file_path": audio_filename,
                "request_id": audio_id,
                "event": "file.saved",
            },
        )

        # 2. Convert
        wav_path = convert_to_wav(audio_filename)
        queue_logger.info(
            "Converted audio to WAV",
            extra={
                "service": "audio-service",
                "queue": QUEUE_NAME,
                "exchange": EXCHANGE_NAME,
                "wav_path": wav_path,
                "request_id": data.get("request_id"),
                "event": "audio.converted",
            },
        )

        # 3. Upload converted WAV to R2
        from app.utils.r2_handler import upload_file_to_r2
        wav_filename = wav_path.split("/")[-1]
        wav_r2_url = upload_file_to_r2(wav_path, filename=wav_filename)
        queue_logger.info(
            "Uploaded converted WAV to R2",
            extra={
                "service": "audio-service",
                "queue": QUEUE_NAME,
                "exchange": EXCHANGE_NAME,
                "wav_r2_url": wav_r2_url,
                "request_id": data.get("request_id"),
                "event": "audio.wav_uploaded",
            },
        )

        # 4. Update payload
        data["audio_path"] = wav_r2_url
        data["event"] = AUDIO_UPLOADED
        data["wav_path"]=wav_path

        # 5. Publish to next stage
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(data).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=AUDIO_UPLOADED
        )

        queue_logger.info(
            "Published audio upload processor event",
            extra={
                "service": "audio-service",
                "queue": QUEUE_NAME,
                "exchange": EXCHANGE_NAME,
                "routing_key": AUDIO_UPLOADED,
                "request_id": data.get("request_id"),
                "event": "publish.success",
            },
        )

        print(f"Processed audio → {wav_r2_url}")


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

    # 👇 This queue listens for raw uploads
    await queue.bind(exchange, routing_key="audio.raw")
    queue_logger.info(
        "Queue bound to exchange",
        extra={
            "service": "audio-service",
            "queue": QUEUE_NAME,
            "exchange": EXCHANGE_NAME,
            "routing_key": "audio.raw",
            "event": "queue.bind",
        },
    )

    await queue.consume(lambda msg: process_message(msg, exchange))

    queue_logger.info(
        "Audio service startup complete",
        extra={
            "service": "audio-service",
            "queue": QUEUE_NAME,
            "exchange": EXCHANGE_NAME,
            "event": "service.started",
        },
    )
    print("🎧 Audio service running...")

    await asyncio.Future()


if __name__ == "__main__":
    queue_logger.info(
        "Starting audio-service",
        extra={
            "service": "audio-service",
            "queue": QUEUE_NAME,
            "exchange": EXCHANGE_NAME,
            "event": "service.starting",
        },
    )
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass