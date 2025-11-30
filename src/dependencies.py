from services.database import database_service
from services.rabbitmq import rabbitmq_service
from services.redis import redis_service


async def get_database():
    if not database_service.initialized:
        await database_service.connect()
    return database_service

async def get_rabbit():
    if not rabbitmq_service.initialized:
        await rabbitmq_service.connect()
    return rabbitmq_service

async def get_redis():
    if not redis_service.redis_client:
        await redis_service.connect()
    return redis_service