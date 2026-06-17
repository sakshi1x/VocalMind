import aio_pika
from config.settings import RABBIT_URL

async def get_connection():
    return await aio_pika.connect_robust(RABBIT_URL)

async def get_channel(connection):
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    return channel