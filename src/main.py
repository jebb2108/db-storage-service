import uvicorn
from endpoints.handlers import router
import json
from datetime import datetime
from functools import wraps
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from faststream.rabbit.annotations import RabbitMessage

from config import config
from dependencies import get_database
from logconf import opt_logger as log

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from models import User, Payment

logger = log.setup_logger('worker')
broker = RabbitBroker(config.rabbit.url, logger=logger)


# Словарь для хранения зарегистрированных
# обработчиков по их назначению (purpose)
purposes = {}

# Декоратор для регистрации функций обработчиков
def register_purpose(purpose: str):

    # Внешняя обертка декоратора,
    # принимающая параметр purpose
    def decorator(fn):
        # Сохраняем метаданные оригинальной функции
        @wraps(fn)
        # Асинхронная обертка вокруг оригинальной функции
        async def wrapper(data):
            # Вызов оригинальной асинхронной функции
            return await fn(data)

        # Регистрируем функцию-обертку в
        # словаре purposes под указанным ключом purpose
        purposes[purpose] = wrapper

        # Возвращаем зарегистрированную функцию-обертку
        return wrapper

    # Возвращаем сам декоратор
    return decorator



@register_purpose(config.purpose.add_user)
async def add_user(data: dict) -> None:
    """ Добавляет пользователя """
    database = await get_database()
    user_dict = json.loads(data["user"])
    user_data = User(**user_dict)
    await database.update_user(user_data)
    await database.create_payment(Payment(user_id=user_data.user_id))
    logger.info("New user processed by worker")


@register_purpose(config.purpose.create_payment)
async def create_payment(data: dict) -> None:
    """ Создает платеж пользователя """
    database = await get_database()
    payment_dict = json.loads(data["payment"])
    payment_dict["until"] = datetime.fromisoformat(payment_dict["until"])
    await database.create_payment(Payment(**payment_dict))
    logger.info("New payment processed by worker")


@register_purpose(config.purpose.add_profile)
async def add_profile(data: dict) -> None:
    database = await get_database()
    profile = json.loads(data["profile"])
    bday = profile.get("birthday")
    day, month, year = bday.split('-')
    date_str = f"{year}-{month}-{day}"
    date_obj = datetime.fromisoformat(date_str).date()
    profile["birthday"] = date_obj
    await database.add_users_profile(**profile)
    return None


@register_purpose(config.purpose.add_location)
async def add_location(data: dict) -> None:
    database = await get_database()
    location = json.loads(data["location"])
    await database.add_users_location(**location)
    return None


@register_purpose(config.purpose.create_payment)
async def add_payment(data: dict) -> None:
    database = await get_database()
    payment_dict = json.loads(data["payment"])
    payment = Payment(**payment_dict)
    await database.create_payment(payment)
    return None

@broker.subscriber(config.rabbit.queue.new_users)
async def handle_new_users(data: dict, msg: RabbitMessage):
    """ Находит обработчик для запроса в БД """
    logger.info(f'Received message: {data}')
    try:
        purpose = data.get("purpose")
        handler = purposes.get(purpose)
        # Вызываем соответствующий обработчик
        if handler: await handler(data)

        logger.info(f"Successfully processed message with purpose: {purpose}")

    except Exception as e:
        logger.error(f"Error in DB execution: {e}")

    finally: await msg.ack()


async def background_worker():
    while True:
        try:
            logging.info("Starting worker...")
            worker = FastStream(broker, logger=logger)
            await worker.run()

        except Exception as e:
            logging.error(f"Worker error: {e}")
            break


@asynccontextmanager
async def lifespan(app: FastAPI): # noqa
    # Запускаем воркер при старте приложения
    await get_database()
    task = asyncio.create_task(background_worker())
    logging.info("Background worker started")
    yield

    # Останавливаем воркер при завершении
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logging.info("Background worker stopped")


app = FastAPI(lifespan=lifespan)
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run('main:app', host='0.0.0.0', port=config.ports.api, reload=True)