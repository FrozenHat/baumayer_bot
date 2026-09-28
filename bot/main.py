import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, DEBUG
from database import init_db
from handlers import (
    admin,
    admin_staff,
    admin_users,
    orders,
    profile,
    project,
    start,
    wallet,
)
from middlewares.user import UserMiddleware

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Запуск бота...")

    # 1. Инициализируем базу данных (создаём таблицы)
    await init_db()
    logger.info("База данных инициализирована.")

    # 2. Создаём бота и диспетчер
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # 3. Подключаем middleware (регистрация пользователя)
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    # 4. Подключаем роутеры
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(wallet.router)
    dp.include_router(project.router)
    dp.include_router(admin_users.router)   # ← сначала пользователи
    dp.include_router(admin_staff.router)   # ← потом сотрудники
    dp.include_router(admin.router)         # ← в конце общая панель
    dp.include_router(orders.router)

    # 5. Запускаем polling
    logger.info("Бот запущен и слушает Telegram...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")