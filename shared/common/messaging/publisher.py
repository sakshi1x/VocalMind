from shared.common.messaging.connection import get_connection, get_channel
from shared.common.messaging.exchange import get_exchange
from shared.common.messaging.message import encode

class Publisher:

    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        self.connection = await get_connection()
        self.channel = await get_channel(self.connection)
        self.exchange = await get_exchange(self.channel)

    async def publish(self, data: dict, routing_key: str):
        await self.exchange.publish(
            encode(data),
            routing_key=routing_key
        )

    async def close(self):
        await self.connection.close()