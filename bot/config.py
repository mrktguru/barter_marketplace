import os
from typing import List
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()


class Config:
    """Конфигурация бота"""

    # Telegram Bot
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    ADMIN_IDS: List[int] = [int(id_) for id_ in os.getenv('ADMIN_IDS', '').split(',') if id_.strip()]

    # Database
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: str = os.getenv('DB_PORT', '5432')
    DB_NAME: str = os.getenv('DB_NAME', 'barter_bot')
    DB_USER: str = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'postgres')

    # Redis
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))

    # Payment Systems
    YOOKASSA_SHOP_ID: str = os.getenv('YOOKASSA_SHOP_ID', '')
    YOOKASSA_SECRET_KEY: str = os.getenv('YOOKASSA_SECRET_KEY', '')

    # App Settings
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # Channel (заполняется через бота)
    CHANNEL_ID: str = os.getenv('CHANNEL_ID', '')
    CHANNEL_USERNAME: str = os.getenv('CHANNEL_USERNAME', '')

    @classmethod
    def is_admin(cls, telegram_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        return telegram_id in cls.ADMIN_IDS

    @classmethod
    def get_database_url(cls) -> str:
        """Получить URL подключения к базе данных"""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

    @classmethod
    def get_redis_url(cls) -> str:
        """Получить URL подключения к Redis"""
        return f"redis://{cls.REDIS_HOST}:{cls.REDIS_PORT}"


# Создание экземпляра конфигурации
config = Config()
