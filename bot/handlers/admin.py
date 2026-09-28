from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from keyboards.admin import admin_panel_kb
from models.user import User

router = Router()


def is_admin(user: User) -> bool:
    return user.role == "admin"


@router.message(Command("admin"))
@router.message(F.text == "🛠️ Админ-панель")
async def cmd_admin(message: Message, user: User):
    if not is_admin(user):
        await message.answer("⛔ Доступ только для администратора.")
        return
    await message.answer(
        "🛠️ <b>Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=admin_panel_kb(),
    )


@router.callback_query(F.data == "admin:panel")
async def back_to_panel(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "🛠️ <b>Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=admin_panel_kb(),
    )
    await callback.answer()