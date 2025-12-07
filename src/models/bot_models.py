from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Any

from pydantic import BaseModel, Field, field_validator


class Target(str, Enum):
    """ Модель для запроса в БД """
    ALL = 'all'
    USER = 'users'
    PROFILE = 'profiles'
    NAME = 'username'
    NICK = 'nickname'
    LANG = 'language'
    FLUENCY = 'fluency'
    TOPICS = 'topics'
    DATING = 'dating'
    INTRO = 'intro'
    EMAIL = 'email'
    ACTIVE = 'is_active'
    BLOCKED = 'blocked_bot'
    STATUS = 'status'
    CODE = 'lang_code'




class Coordinates(BaseModel):
    """
    Модель первичной обработки геолокации пользователя
    """
    latitude: float
    longitude: float


class User(BaseModel):
    """
    Модель нового пользователя (для базы данных).
    """

    user_id: int
    username: Optional[str]
    camefrom: str
    first_name: str
    language: str
    fluency: int
    topics: List[str]
    lang_code: str

class Profile(BaseModel):
    """
    Модель профиля пользователя (для базы данных)
    """
    user_id: int = Field(..., description="User ID")
    nickname: str = Field(..., description="Уникальный никнейм пользователя")
    email: str = Field(..., description="Email пользователя")
    gender: str = Field(..., description="Пол пользователя")
    intro: str = Field(..., description="Краткая информация о пользователе")
    birthday: date = Field(..., description="Дата рождения пользователя")
    dating: Optional[bool] = Field(False, description="Согласие на дэйтинг")
    status: Optional[str] = Field('rookie', description="Видимый статус пользователя")

    @field_validator('birthday', mode='before')
    def parse_birthday(cls, value: Any) -> date: # noqa
        """ Парсит строку в date, поддерживая разные форматы """

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            # Пробует разные форматы даты
            formats = [
                "%d-%m-%Y",  # 03-01-2002
                "%Y-%m-%d",  # 2002-01-03 (ISO)
                "%d/%m/%Y",  # 03/01/2002
                "%m/%d/%Y",  # 01/03/2002
                "%d.%m.%Y",  # 03.01.2002
                "%Y.%m.%d",  # 2002.01.03
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

            raise ValueError(f"Invalid date format: {value}")


class Location(BaseModel):
    """
    Модель вторичной обработки геолокации пользователя (для базы данных)
    """
    user_id: int = Field(..., description="User ID")
    latitude: Optional[str] = Field(None, description="Долгота координаты")
    longitude: Optional[str] = Field(None, description="Широта координаты")
    city: Optional[str] = Field(None, description="Город пользователя")
    country: Optional[str] = Field(None, description="Страна пользователя")
    tzone: Optional[str] = Field(None, description="Временная зона пользователя")
