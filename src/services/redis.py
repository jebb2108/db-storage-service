import json
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import TYPE_CHECKING, Optional, Dict, Any

import redis.asyncio as redis

from src.config import config
from src.logconf import opt_logger as log

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = log.setup_logger('redis')


class RedisService:

    def __init__(self):
        self.redis_client: Optional["Redis"] = None
        self.q = None

    def get_client(self) -> "Redis":
        return self.redis_client


    async def connect(self):
        """Установка подключения к Redis"""

        try:
            self.redis_client = redis.Redis.from_url(
                url=config.REDIS_URL,
                decode_responses=True,
                encoding='utf-8'
            )

        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            self.redis_client = None


# Глобальный экземпляр сервиса
redis_service = RedisService()