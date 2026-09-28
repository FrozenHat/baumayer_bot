from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from models.user import User
from keyboards.main_menu import main_menu_kb

router = Router()


# @router.message(CommandStart())
# async def cmd_start(message: Message, user: User):
#     role_labels = {
#         "pending": "⏳ Ожидает назначения",
#         "admin": "👑 Администратор",
#         "foreman": "👷 Прораб",
#         "engineer": "📐 Инженер",
#         "worker": "🔧 Рабочий",
#     }
@router.message(CommandStart())
async def cmd_start(message: Message, user: User):
    is_admin = user.role == "admin"
    await message.answer(
        f"Привет, <b>{user.full_name}</b>! 👋\n\nВыберите раздел:",
        reply_markup=main_menu_kb(is_admin=is_admin),
    )
    # role_text = role_labels.get(user.role, user.role)

    # await message.answer(
    #     f"Привет, <b>{user.full_name}</b>! 👋\n\n"
    #     f"Твой Telegram ID: <code>{user.id}</code>\n"
    #     f"Роль: <b>{role_text}</b>\n\n"
    #     f"Используй /help, чтобы узнать доступные команды."
    # )