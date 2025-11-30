from fastapi import APIRouter, Depends
from fastapi.params import Query

from dependencies import get_database, get_rabbit

from typing import TYPE_CHECKING

from models.bot_models import User, Payment
from services.rabbitmq import RabbitMQService
from logconf import opt_logger as log

if TYPE_CHECKING:
    from services.database import DatabaseService

router = APIRouter()
logger = log.setup_logger('handlers')

@router.get('/user_exists')
async def check_user_exists(
        user_id: int = Query(..., description='User ID', examples=[123]),
        database: "DatabaseService"=Depends(get_database)
):
    if await database.check_user_exists(user_id):
        return {"user_exists": True}
    return {"user_exists": False}

@router.get('/users')
async def get_user_info(
        user_id: int = Query(..., description='User ID', examples=[123]),
        profile: bool = Query(False, description='Whether profile needed or not'),
        all_info: bool = Query(False, description='Whether base & profile info needed'),
        database: "DatabaseService" = Depends(get_database)
):
    if all_info:
        user_data = await database.get_all_user_info(user_id)
        return {'user_data': user_data}
    elif profile:
        user_data = await database.get_users_profile(user_id)
        return {'user_data': user_data}
    else:
        user_data = await database.get_user_info(user_id)
        return {'user_data': user_data}


@router.post('/users')
async def add_user_and_payment(
        user_data: User,
        rabbit: "RabbitMQService" = Depends(get_rabbit)
):
    logger.info('Sending messages to RabbitMQ')
    await rabbit.publish_user(user_data)

