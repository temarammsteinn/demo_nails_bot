# -*- coding: utf-8 -*-
"""
Точка входа: запуск Telegram-бота для мастера маникюра
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database import init_db, get_db
from handlers import register_routers
from utils.scheduler import init_scheduler, shutdown_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    # Инициализация БД
    init_db()

    # Бот и диспетчер
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров (обработчиков)
    main_router = register_routers()
    dp.include_router(main_router)

    # Инициализация планировщика напоминаний (передаём бот для отправки)
    init_scheduler(bot)

    # Удаляем вебхук если был, и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен")

    try:
        await dp.start_polling(bot)
    finally:
        shutdown_scheduler()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
