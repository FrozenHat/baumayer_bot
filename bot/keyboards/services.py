from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models.order import Order


# Порядок и метки категорий услуг
SERVICES_CATEGORIES = {
    "delivery": "🚚 Доставка",
    "loaders": "💪 Грузчики",
    "laborers": "🔧 Разнорабочие",
    "material": "📦 Заявка материала",
    "other": "📝 Другое",
    "turnkey": "🏠 Ремонт под ключ",
}


def services_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню раздела «Услуги»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Выбрать услугу", callback_data="srv:choose")],
            [InlineKeyboardButton(text="📂 Мои услуги", callback_data="srv:my")],
            [InlineKeyboardButton(text="ℹ️ Инструкция", callback_data="srv:info")],
        ]
    )


def services_categories_kb() -> InlineKeyboardMarkup:
    """Список категорий услуг + кнопка Отмена."""
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"srv:cat:{cat}")]
        for cat, label in SERVICES_CATEGORIES.items()
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="srv:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def after_order_kb(order_id: int) -> InlineKeyboardMarkup:
    """Кнопки после подачи заявки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📞 Оставить номер для звонка",
                callback_data=f"srv:leave_phone:{order_id}",
            )],
            [InlineKeyboardButton(
                text="📂 Мои услуги",
                callback_data="srv:my",
            )],
        ]
    )


def services_list_kb(orders: list[Order]) -> InlineKeyboardMarkup:
    """Список заявок пользователя."""
    buttons = [
        [InlineKeyboardButton(
            text=f"#{o.id} • {o.title[:40]}",
            callback_data=f"srv:view:{o.id}",
        )]
        for o in orders
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="srv:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_services_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="srv:menu")],
        ]
    )