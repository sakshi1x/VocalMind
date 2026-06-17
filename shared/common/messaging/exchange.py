import aio_pika
from config.settings import EXCHANGE_NAME

async def get_exchange(channel):
    return await channel.declare_exchange(
        EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True
    )