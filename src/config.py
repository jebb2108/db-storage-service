import os
from dataclasses import dataclass
from datetime import timedelta, timezone
from dotenv import load_dotenv

load_dotenv('.env')


@dataclass
class PurposeConfig:
    add_user = 'ADD_USER'
    add_profile = 'ADD_PROFILE'
    add_location = 'ADD_LOCATION'
    create_payment = 'CREATE_PAYMENT_PURPOSE'


@dataclass
class PortsConfig:
    api = 8888

@dataclass
class RabbitConfig:

    url = 'amqp://guest:guest@rabbit:5672/'
    queue: "QueueConfig" = None

    def __post_init__(self):
        if not self.queue: self.queue = QueueConfig()


@dataclass(frozen=True)
class DatabaseConfig:
    url = f'postgresql://onlynone:pswd123@postgres:5432/mydb'
    min_size: int = 5
    max_size: int = 20
    timeout: int = 60


@dataclass
class QueueConfig:
    new_users = 'new_users'

@dataclass
class Config:
    debug = os.getenv('DEBUG')
    log_level = os.getenv('LOG_LEVEL')
    tz_info = timezone(timedelta(hours=3.0))

    ports: "PortsConfig" = None
    rabbit: "RabbitConfig" = None
    database: "DatabaseConfig" = None
    purpose: "PurposeConfig" = None

    def __post_init__(self):
        if not self.ports: self.ports = PortsConfig()
        if not self.rabbit: self.rabbit = RabbitConfig()
        if not self.database: self.database = DatabaseConfig()
        if not self.purpose: self.purpose = PurposeConfig()


config = Config()