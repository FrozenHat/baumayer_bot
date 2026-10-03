from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def profile_menu_kb(has_project: bool = False) -> InlineKeyboardMarkup:
    """
    Меню раздела «Профиль».
    Кнопка «Моя стройка» — только если у пользователя есть проект.
    """
    buttons = [
        [InlineKeyboardButton(text="📄 Ваши данные", callback_data="profile:data")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="profile:balance")],
    ]
    if has_project:
        buttons.append(
            [InlineKeyboardButton(text="🏗️ Моя стройка", callback_data="profile:project")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def profile_data_kb() -> InlineKeyboardMarkup:
    """Кнопки редактирования данных."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ ФИО", callback_data="profile:edit:full_name")],
            [InlineKeyboardButton(text="✏️ Адрес", callback_data="profile:edit:address")],
            [InlineKeyboardButton(text="✏️ Банк", callback_data="profile:edit:bank")],
            [InlineKeyboardButton(text="✏️ ИП счёт", callback_data="profile:edit:ip_account")],
            [InlineKeyboardButton(text="✏️ Телефон", callback_data="profile:edit:phone")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile:menu")],
        ]
    )


def balance_menu_kb() -> InlineKeyboardMarkup:
    """Меню раздела «Баланс»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="balance:topup")],
            [InlineKeyboardButton(text="🧾 Чеки", callback_data="balance:receipts")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile:menu")],
        ]
    )


def back_to_profile_kb() -> InlineKeyboardMarkup:
    """Универсальная кнопка «Назад» в профиль."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile:menu")],
        ]
    )