from pydoc_data.topics import topics
from typing import TYPE_CHECKING, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query

from src.dependencies import get_database, get_rabbit
from src.logconf import opt_logger as log
from src.models import Location, Profile
from src.models.bot_models import User, Target
from src.services.rabbitmq import RabbitMQService

if TYPE_CHECKING:
    from src.services.database import DatabaseService

router = APIRouter(prefix='/api/v0')
logger = log.setup_logger('handlers')


@router.get('/user_exists')
async def check_user_exists(
        user_id: int = Query(..., description='User ID', examples=[123]),
        database: "DatabaseService"=Depends(get_database)
):
    if await database.user_exists(user_id):
        return {"user_exists": True}
    return {"user_exists": False}

@router.get('/users')
async def get_user_info(
        user_id: int = Query(..., description='User ID', examples=[123]),
        target_field: str = Query(..., description="Users target for quering DB"),
        database: "DatabaseService" = Depends(get_database)
):
    """ Извлекает конкретные данные пользователя из БД """
    try:
        # Пытается привести строку к формату
        target = Target(target_field)
    except Exception:
        raise HTTPException(status_code=400, detail="Incorrect input")

    if target in [
        Target.ALL, Target.PROFILE, Target.NICK,
        Target.DATING, Target.INTRO, Target.STATUS, Target.EMAIL
    ]:
        profile_exists = await database.profile_exists(user_id)
        if not profile_exists: raise HTTPException(status_code=405, detail='Target not allowed')

    if user_data := await database.query_criteria_by_target(user_id, target):
        return user_data

    raise HTTPException(status_code=404, detail=f'Data for user {user_id} not found')

@router.post('/users')
async def save_user_handler(
        user_data: User,
        rabbit: "RabbitMQService" = Depends(get_rabbit)
):
    """ Сохраняет базовую информацию пользователя в БД """
    logger.debug('Sending messages to RabbitMQ')
    await rabbit.publish_user(user_data)

@router.post('/profiles')
async def save_profile_handler(
        profile_data: Profile,
        rabbit: "RabbitMQService" = Depends(get_rabbit)
) -> None:
    """ Сохраняет партнерский профиль пользователя в БД """
    logger.debug('Senfing message to RabbitMQ')
    await rabbit.publish_profile(profile_data)

@router.get('/location')
async def get_location(
        user_id: int = Query(..., description='User ID'),
        database: "DatabaseService" = Depends(get_database)
) -> Dict[str, str]:
    """ Возвращает город и страну пользователя из БД """
    return await database.get_location(user_id)

@router.post('/location')
async def add_location(
        location_data: Location,
        rabbit: "RabbitMQService" = Depends(get_rabbit)
):
    await rabbit.publish_location(location_data)