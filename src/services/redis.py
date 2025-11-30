import json
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import TYPE_CHECKING, Optional, Dict, Any

import redis.asyncio as redis

from config import config
from logconf import opt_logger as log

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = log.setup_logger('redis')


class RedisService:

    def __init__(self):
        self.redis_client: Optional["Redis"] = None
        self.q = None

    def get_client(self) -> "Redis":
        return self.redis_client

    async def get_searched_words(self, word: str) -> Optional[Dict[str, Any]]:
        try:
            # Используем клиент напрямую
            words_dict = await self.redis_client.hgetall(f"searched_word:{word}")
            if words_dict:
                # Декодируем значения из JSON
                return {k: json.loads(v) for k, v in words_dict.items()}
            return None

        except Exception as e:
            logger.error(f"Error getting searched words from Redis: {e}")
            return None

    async def save_search_result(self, word, all_users_words, interval: timedelta) -> None:
        """ Сохраняем переводы одно слова от разных пользователй в оперативной памяти """

        # При отсутствии слов, выходим из метода
        if not all_users_words:
            logger.debug("No data to save in Redis for word: %s", word)
            return

        try:
            key = f"searched_word:{word}"
            # Подготавливаем данные для hset
            mapping = {}
            for nickname, word_data in all_users_words.items():
                mapping[nickname] = json.dumps(word_data)

            # Используем pipeline для batch операций
            async with self.redis_client.pipeline() as pipe:
                await pipe.hset(key, mapping=mapping)
                await pipe.expire(key, interval)
                await pipe.execute()

        except Exception as e:
            logger.error(f"Error saving search result to Redis: {e}")
            raise

    @asynccontextmanager
    async def transaction(self):
        """Контекстный менеджер для транзакций (если все еще нужен для других операций)"""
        try:
            async with self.redis_client.pipeline() as pipe:
                yield pipe
                await pipe.execute()
        except Exception as e:
            logger.warning(f"Error handling redis transaction: {e}")
            raise

    async def connect(self):
        """Установка подключения к Redis"""
        if not self.q:
            self.q = defaultdict(list)

        try:
            self.redis_client = redis.Redis.from_url(
                url=config.REDIS_URL,
                decode_responses=True,
                encoding='utf-8'
            )
            # Проверяем подключение
            await self.redis_client.ping()
            logger.debug("Connected successfully to Redis")

        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            self.redis_client = None


# Глобальный экземпляр сервиса
redis_service = RedisService()