from typing import TYPE_CHECKING

from src.services.database import database_service
from src.services.rabbitmq import rabbitmq_service
from src.services.redis import redis_service

if TYPE_CHECKING:
    from src.services.database import DatabaseService
    from src.services.rabbitmq import RabbitMQService
    from src.services.redis import RedisService


async def get_database() -> "DatabaseService":
    if not database_service.initialized:
        await database_service.connect()
    return database_service

async def get_rabbit() -> "RabbitMQService":
    if not rabbitmq_service.initialized:
        await rabbitmq_service.connect()
    return rabbitmq_service

async def get_redis() -> "RedisService":
    if not redis_service.redis_client:
        await redis_service.connect()
    return redis_service