from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from keyboards.main_menu import main_menu_kb
from models.user import User

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, user: User):
    """
    Приветствие + главное меню.
    Показывается один раз при первом /start.
    """
    is_admin = user.role == "admin"

    text = (
        f"👋 Привет, <b>{user.full_name}</b>!\n\n"
        f"Добро пожаловать в бот для управления строительными проектами.\n\n"
        f"📌 <b>Что здесь есть:</b>\n\n"
        f"👤 <b>Профиль</b> — ваши данные, баланс, чеки и информация о вашей стройке.\n\n"
        f"🛠️ <b>Услуги</b> — заказ доставки, грузчиков, разнорабочих, "
        f"заявка на материал или ремонт под ключ.\n\n"
        f"🚨 <b>Аварийка</b> — экстренная связь с ответственными "
        f"за аварийные ситуации.\n\n"
        f"❓ Если что-то непонятно — нажмите «<b>Вопросы по сервису</b>» внизу."
    )

    await message.answer(text, reply_markup=main_menu_kb(is_admin=is_admin))


@router.message(Command("menu"))
async def cmd_menu(message: Message, user: User):
    """Команда /menu — вернуть главное меню без приветствия."""
    is_admin = user.role == "admin"
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_kb(is_admin=is_admin),
    )