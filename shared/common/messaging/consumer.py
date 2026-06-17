from shared.common.messaging.connection import get_connection, get_channel
from shared.common.messaging.exchange import get_exchange
from shared.common.messaging.message import decode

class Consumer:

    def __init__(self, queue_name: str, routing_key: str, handler):
        self.queue_name = queue_name
        self.routing_key = routing_key
        self.handler = handler

    async def start(self):
        connection = await get_connection()
        channel = await get_channel(connection)
        exchange = await get_exchange(channel)

        queue = await channel.declare_queue(self.queue_name, durable=True)
        await queue.bind(exchange, routing_key=self.routing_key)

        async with queue.iterator() as q:
            async for message in q:
                async with message.process():
                    data = decode(message.body)
                    await self.handler(data)