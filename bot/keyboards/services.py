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


def services_menu_kb(is_manager: bool = False, is_executor: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📋 Выбрать услугу", callback_data="srv:choose")],
        [InlineKeyboardButton(text="📂 Мои услуги", callback_data="srv:my")],
        [InlineKeyboardButton(text="ℹ️ Инструкция", callback_data="srv:info")],
    ]
    if is_manager:
        buttons.append([InlineKeyboardButton(
            text="📥 Входящие (менеджер)",
            callback_data="srv:manager:incoming",
        )])
    if is_executor:
        buttons.append([InlineKeyboardButton(
            text="🔧 Мои задачи (исполнитель)",
            callback_data="srv:ex:my",
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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

# ============ МЕНЕДЖЕР ============

STATUS_LABELS = {
    "new": "🆕 Новая",
    "in_progress": "⚙️ В работе",
    "done": "✅ Выполнена",
    "rejected": "❌ Отклонена",
    "cancelled": "🚫 Отменена",
    "disputed": "⚖️ Спор",
}


def manager_order_card_kb(order, is_lead: bool) -> InlineKeyboardMarkup:
    """
    Карточка заявки для менеджера.
    is_lead = True, если этот менеджер уже ведёт заявку.
    """
    buttons = []

    if order.status == "new":
        buttons.append([InlineKeyboardButton(
            text="✅ Принять в работу",
            callback_data=f"srv:mgr:accept:{order.id}",
        )])
    elif order.status == "in_progress" and is_lead:
        buttons.append([InlineKeyboardButton(
            text="✏️ Заполнить карточку",
            callback_data=f"srv:mgr:fill:{order.id}",
        )])
        buttons.append([InlineKeyboardButton(
            text="👤 Назначить исполнителя",
            callback_data=f"srv:mgr:assign:{order.id}",
        )])
        buttons.append([InlineKeyboardButton(
            text="🏁 Завершить",
            callback_data=f"srv:mgr:finish:{order.id}",
        )])
        buttons.append([InlineKeyboardButton(
            text="🚫 Отменить",
            callback_data=f"srv:mgr:cancel:{order.id}",
        )])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="srv:manager:incoming")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def executor_pick_kb(order_id: int, executors: list) -> InlineKeyboardMarkup:
    """Список исполнителей для назначения."""
    buttons = [
        [InlineKeyboardButton(
            text=f"{u.full_name}",
            callback_data=f"srv:mgr:assign_pick:{order_id}:{u.id}",
        )]
        for u in executors
    ]
    buttons.append([InlineKeyboardButton(
        text="⬅️ Отмена",
        callback_data=f"srv:mgr:view:{order_id}",
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_fill_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"srv:mgr:view:{order_id}")],
        ]
    )


# ============ ИСПОЛНИТЕЛЬ ============

def executor_order_kb(order, has_response: bool) -> InlineKeyboardMarkup:
    """Карточка задачи для исполнителя."""
    buttons = []

    if not has_response and order.status in ("new", "in_progress"):
        buttons.append([
            InlineKeyboardButton(text="✅ Принять", callback_data=f"srv:ex:accept:{order.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"srv:ex:decline:{order.id}"),
        ])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="srv:ex:my")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)