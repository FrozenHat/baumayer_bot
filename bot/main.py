import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, DEBUG
from database import init_db
from middlewares.user import UserMiddleware

# Импортируем роутеры напрямую из модулей (не через пакет handlers)
from handlers.start import router as start_router
from handlers.profile import router as profile_router
from handlers.wallet import router as wallet_router
from handlers.project import router as project_router
from handlers.orders import router as orders_router
# from handlers.material import router as material_router
from handlers.services import router as services_router
from handlers.emergency import router as emergency_router
from handlers.help import router as help_router
from handlers.admin import router as admin_router
from handlers.admin_users import router as admin_users_router
from handlers.admin_staff import router as admin_staff_router


logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Запуск бота...")
    await init_db()
    logger.info("База данных инициализирована.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    # Подключаем роутеры. Конкретные — раньше, общий start — позже.
    dp.include_router(help_router)
    dp.include_router(services_router)
    dp.include_router(emergency_router)

    dp.include_router(profile_router)
    dp.include_router(wallet_router)
    dp.include_router(project_router)
    dp.include_router(orders_router)
    dp.include_router(material_router)

    dp.include_router(admin_users_router)
    dp.include_router(admin_staff_router)
    dp.include_router(admin_router)

    dp.include_router(start_router)

    logger.info("Бот запущен и слушает Telegram...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")