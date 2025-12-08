import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.database import init_db
from bot.handlers import start, admin

# Настройка логирования
logging.basicConfig(
    level=logging.INFO if not config.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    # Проверка наличия токена
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен в переменных окружения!")
        return

    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    try:
        init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации базы данных: {e}")
        return

    # Создание бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(admin.router)
    # TODO: Добавить другие роутеры
    # dp.include_router(post_creator.router)

    logger.info("🤖 Бот запущен и готов к работе")

    # Запуск polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
