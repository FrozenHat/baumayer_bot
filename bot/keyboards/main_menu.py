from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📦 Заказы")],
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📋 Заявка материала")],
        [KeyboardButton(text="🏗️ Моя стройка"), KeyboardButton(text="🚨 Аварийка")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="🛠️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)