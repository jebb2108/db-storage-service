import json
from typing import TYPE_CHECKING, Optional

import aio_pika

from models import Location, Payment, User, Profile

from config import config
from logconf import opt_logger as log

if TYPE_CHECKING:
    from aio_pika.abc import AbstractChannel
    from aio_pika.abc import AbstractRobustConnection
    from models.bot_models import User


logger = log.setup_logger('rabbitmq')


class RabbitMQService:
    def __init__(self):
        self.connection: Optional["AbstractRobustConnection"] = None
        self.channel: Optional["AbstractChannel"] = None
        self.default_exchange = None
        self.new_users_exchange = None
        self.messages_exchange = None
        self.initialized = False

    async def connect(self):
        """Установка подключения к RabbitMQ"""
        self.connection = await aio_pika.connect_robust(config.rabbit.url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)

        # Объявляем обменники и очереди при подключении
        await self.declare_exchanges_and_queues()

        self.initialized = True

    async def declare_exchanges_and_queues(self):
        """Объявление всех обменников и очередей"""
        """
        Объясвляем обменник и очередь для обрабтки пользовательской информации
        """
        self.new_users_exchange = await self.channel.declare_exchange(
            name=config.rabbit.queue.new_users, type="direct"
        )
        new_users_queue = await self.channel.declare_queue(name=config.rabbit.queue.new_users)
        await new_users_queue.bind(self.new_users_exchange, config.rabbit.queue.new_users)


    async def publish_user(self, user: "User"):
        """Публикация нового пользователя и транзакции"""
        json_user = json.dumps({
            "purpose": config.purpose.add_user,
            "user": user.model_dump_json(),
        }).encode()

        logger.info(f'received data: {user}')

        await self.new_users_exchange.publish(
            aio_pika.Message(
                body=json_user, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.rabbit.queue.new_users
        )

    async def publish_payment(self, payment: "Payment"):
        """Публикация нового пользователя и транзакции"""
        json_user = json.dumps({
            "purpose": config.purpose.create_payment,
            "payment": payment.model_dump_json(),
        }).encode()

        logger.info(f'Received data: {payment}')

        await self.new_users_exchange.publish(
            aio_pika.Message(
                body=json_user, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.rabbit.queue.new_users
        )


    async def publish_profile(self, profile: "Profile"):
        json_profile = json.dumps({
            "purpose": config.purpose.add_profile,
            "profile": profile.model_dump_json()
        }).encode()

        await self.new_users_exchange.publish(
            aio_pika.Message(
                body=json_profile, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.rabbit.queue.new_users
        )


    async def publish_location(self, location: "Location"):
        """Публикация местоположения пользователя"""
        json_location = json.dumps({
            "purpose": config.purpose.add_location,
            "location": location.model_dump_json()
        }).encode()

        await self.new_users_exchange.publish(
            aio_pika.Message(
                body=json_location, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.rabbit.queue.new_users
        )

    async def disconnect(self):
        """Закрытие подключения"""
        if self.connection:
            await self.connection.close()


# Глобальный экземпляр сервиса
rabbitmq_service = RabbitMQService()
