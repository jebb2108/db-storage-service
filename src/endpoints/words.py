from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, Response, status
from fastapi.params import Query

from src.dependencies import get_database, get_rabbit
from src.logconf import opt_logger as log
from src.models import Word
from src.services.rabbitmq import RabbitMQService

if TYPE_CHECKING:
    from src.services.database import DatabaseService

router = APIRouter(prefix='/api/v0')
logger = log.setup_logger('words')

@router.get('/words')
async def get_words_handler(
    user_id: int = Query(..., description="User ID"),
    database: "DatabaseService" = Depends(get_database)
):
    """ Перенаправляет запрос на получение слова пользователя """
    data = await database.query_words(user_id=user_id, word=None)
    return data or Response(status_code=204)


@router.post("/words")
async def save_word_handler(
        word_data: Word,
        response: "Response",
        rabbit: "RabbitMQService" = Depends(get_rabbit),
        database: "DatabaseService" = Depends(get_database)
):
    if not await database.word_exists(word_data):
        await rabbit.publish_word(word_data)
        return Response(status_code=200)
    else:
        response.status_code = status.HTTP_409_CONFLICT
        return {'status': 'Word Already Exists'}

@router.put("/words")
async def edit_word_handler(
        word_data: Word,
        response: "Response",
        rabbit: "RabbitMQService" = Depends(get_rabbit),
        database: "DatabaseService" = Depends(get_database)
):
    if await database.word_exists(word_data):
        await rabbit.publish_word(word_data)
        return Response(status_code=200)
    else:
        response.status_code = status.HTTP_409_CONFLICT
        return {'status': 'Word Does Not Exist'}


@router.delete("/words")
async def api_delete_word_handler(
        user_id: int = Query(..., description="User ID"),
        word_id: int = Query(..., description="Word ID which it goes by in DB"),
        database: "DatabaseService" = Depends(get_database)
):
    await database.delete_word(user_id, word_id)
    return Response(status_code=200)


@router.get("/words/search")
async def api_search_word_handler(
        word: str = Query(..., description="Слово для поиска среди пользователей"),
        user_id: Optional[int] = Query(None, description="User ID пользователя"),
        database: "DatabaseService" = Depends(get_database)
):
    # Ищем слово от пользователя
    data = await database.query_words(user_id=user_id, word=word)
    return data or Response(status_code=204)


@router.get("/words/stats")
async def api_stats_handler(
        user_id: int = Query(..., description="USer ID"),
        database: "DatabaseService" = Depends(get_database)
):
    """ Обработчик статистики слов пользователя """
    data = await database.get_user_stats(user_id)
    return data or Response(status_code=204)
