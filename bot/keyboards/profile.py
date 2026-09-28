from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать ФИО", callback_data="profile:edit:full_name")],
            [InlineKeyboardButton(text="✏️ Редактировать адрес", callback_data="profile:edit:address")],
            [InlineKeyboardButton(text="✏️ Редактировать банк", callback_data="profile:edit:bank")],
            [InlineKeyboardButton(text="✏️ Редактировать ИП счёт", callback_data="profile:edit:ip_account")],
        ]
    )