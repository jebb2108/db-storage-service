from datetime import datetime, timedelta
from typing import Optional, List

from pydantic import BaseModel, Field

from config import config


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


class Payment(BaseModel):
    """
    Модель платежа (для базы данных).
    """

    user_id: int = Field(..., description="User ID")
    amount: Optional[float] = Field(
        199.00, description="Amount of payment in rubles user agreed to pay"
    )
    period: Optional[str] = Field(
        "trial", description="Period of payment", examples=["month", "year"]
    )
    trial: Optional[bool] = Field(True, description="If it is trial period for user")
    until: Optional[datetime] = (
        datetime.now(tz=config.tz_info) + timedelta(days=3)
    )

    currency: Optional[str] = Field("RUB", description="Currency of payment")
    payment_id: Optional[str] = Field(None, description="Payment ID")

    @property
    def until_naive(self) -> Optional[datetime]:
        """ Возвращает untill как naive datetime для хранения в БД """
        if self.until:
            return self.until.replace(tzinfo=None)
        return None

    @property
    def created_at(self) -> datetime:
        """ Возвращает текущий timestamp для истории транзакций БД """
        return datetime.now(tz=config.tz_info)


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






