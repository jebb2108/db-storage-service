import os
from dataclasses import dataclass
from datetime import timedelta, timezone

DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_PORT = os.getenv('POSTGRES_PORT')
DB_NAME = os.getenv('POSTGRES_DB')



@dataclass
class PurposeConfig:
    add_user = 'ADD_USER'
    add_profile = 'ADD_PROFILE'
    add_location = 'ADD_LOCATION'
    create_payment = 'CREATE_PAYMENT_PURPOSE'


@dataclass
class PortsConfig:
    api = int(os.getenv('DATABASE_PORT'))

@dataclass
class RabbitConfig:

    url = 'amqp://guest:guest@rabbit:5672/'
    queue: "QueueConfig" = None

    def __post_init__(self):
        if not self.queue: self.queue = QueueConfig()


@dataclass(frozen=True)
class DatabaseConfig:
    url = f'postgresql://{DB_USER}:{DB_PASSWORD}@postgres:{DB_PORT}/{DB_NAME}'
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