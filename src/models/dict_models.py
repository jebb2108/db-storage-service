from typing import Union, Optional

from pydantic import BaseModel, Field, model_validator


class Word(BaseModel):
    """
    Модель слова для отображения на frontend
    """
    id: Optional[int] = Field(None, description="Уникальный идентификатор слова в базе данных")
    user_id: int = Field(..., description="Уникальный идентификатор пользователя")
    nickname: str = Field(None, description="Никнейм пользователя")
    word: Union[str, None] = Field(None, description="Слово, которое нужно добавить в словарь")
    part_of_speech: Union[str, None] = Field(None, description="Часть речи слова")
    translation: Union[str, None] = Field(None, description="Перевод слова")
    is_public: bool = Field(False, description="Видно ли слово остальным пользователям")
    context: Optional[str] = Field(None, description="Контекст к слову")
    audio: Optional[bytes] = Field(None, description="bytes of audio recording")


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
