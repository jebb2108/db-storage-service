from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from src.config import config


class Word(BaseModel):
    """
    Модель слова для отображения на frontend
    """
    id: Optional[int] = Field(None, description="Уникальный идентификатор слова в базе данных")
    user_id: int = Field(..., description="Уникальный идентификатор пользователя")
    nickname: Optional[str] = Field(None, description="Никнейм пользователя")
    word: Optional[str] = Field(None, description="Слово, которое нужно добавить в словарь")
    part_of_speech: Optional[str] = Field(None, description="Часть речи слова")
    translation: Optional[str] = Field(None, description="Перевод слова")
    is_public: bool = Field(False, description="Видно ли слово остальным пользователям")
    created_at: Optional[str] = Field(None, description="Время создания карточки со словом")
    context: Optional[str] = Field(None, description="Контекст к слову")
    audio: Optional[bytes] = Field(None, description="bytes of audio recording")

    @classmethod
    @model_validator(mode='before')
    def set_datetime_to_string(cls, values):
        try:
            created_at = values['created_at']
            if isinstance(created_at, datetime):
                values['created_at'] = values['created_at'].date().isoformat()

            elif isinstance(created_at, date):
                values['created_at'] = values['created_at'].isoformat()

            return values

        except KeyError:
            values.update(
                created_at=datetime.now(tz=config.tz_info).isoformat()
            )
            return values


class Stats(BaseModel):
    """
    Модель статистики слов пользователя
    """
    total: int = Field(0, description="total count of all words")
    nouns: int = Field(0, description="count of nouns")
    verbs: int = Field(0, description="count of verbs")
    adjectives: int = Field(0, description="count of adjectives")
    adverbs: int = Field(0, description="count of adverbs")
    others: int = Field(0, description="count of other words")

    @model_validator(mode='after')
    def set_total_status(self) -> 'Stats':
        self.total =  self.nouns + \
                      self.verbs + \
                      self.adjectives + \
                      self.adverbs + \
                      self.others
        return self
