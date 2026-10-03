from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Главное меню для обычного пользователя.
    Для админа добавляется кнопка «Админ-панель».
    """
    buttons = [
        [KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="🛠️ Услуги")],
        [KeyboardButton(text="🚨 Аварийка")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="🛠️ Админ-панель")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел…",
    )