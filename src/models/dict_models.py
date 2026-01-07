from datetime import datetime, date
from typing import Optional, Union, Any, Dict

from pydantic import BaseModel, Field, model_validator, field_validator

from src.config import config


class Word(BaseModel):
    """
    Модель слова пользователя (для базы данных)
    """
    id: Optional[int] = Field(None, description="Для корректной работы базы данных")
    user_id: int = Field(..., description="Уникальный идентификатор пользователя")
    nickname: Optional[str] = Field(None, description="Для отображения публичных слов и никнеймов к ним")
    word: Optional[str] = Field(None, description="Слово, которое нужно добавить в словарь")
    translations: Optional[dict] = Field(None, description="Перевод слова")
    is_public: bool = Field(False, description="Видно ли слово остальным пользователям")
    created_at:Optional[Any] = Field(None, description="Время создания карточки со словом")
    context: Optional[str] = Field(None, description="Контекст к слову")
    audio: Optional[bytes] = Field(None, description="bytes of audio recording")

    @classmethod
    @field_validator('created_at', mode='before')
    def set_datetime_to_string(cls, value):
        if isinstance(value, datetime):
            value = value.date().isoformat()
        elif isinstance(value, str):
            try:
                datetime.fromisoformat(value)
            except ValueError:
                value = datetime.now(tz=config.tz_info).isoformat()

        return value



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
