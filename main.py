import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from database import Database
from blocked_database import BlockedDatabase
from handlers import common_router, user_router, admin_router, rating_router
from utils import setup_logging


async def main():
    # Настройка логирования
    setup_logging()
    logging.info("Запуск бота технической поддержки...")

    config = load_config()

    # Проверка токена
    if not config.BOT_TOKEN:
        logging.error("Токен бота не найден! Проверьте файл .env")
        return

    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация баз данных
    db = Database(config.DB_NAME)
    blocked_db = BlockedDatabase("blocked_users.db")

    # Включаем роутеры
    dp.include_router(common_router)
    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.include_router(rating_router)

    # Передаем зависимости
    dp["db"] = db
    dp["blocked_db"] = blocked_db
    dp["config"] = config

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Бот запущен успешно!")
        logging.info(f"ID чата поддержки: {config.SUPPORT_CHAT_ID}")
        logging.info(f"Администраторы: {config.ADMIN_IDS}")

        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()
        db.close()
        blocked_db.close()
        logging.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())