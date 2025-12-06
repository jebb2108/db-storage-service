from typing import Optional, List

from pydantic import BaseModel, Field


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
    birthday: str = Field(..., description="Дата рождения пользователя (ISO)")
    gender: str = Field(..., description="Пол пользователя")
    about: str = Field(..., description="Краткая информация о пользователе")
    dating: Optional[bool] = Field(None, description="Согласие на дэйтинг")
    location: Optional[Coordinates] = None

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






