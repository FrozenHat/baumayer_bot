from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models.order import Order


CATEGORY_LABELS = {
    "delivery": "🚚 Доставка",
    "loaders": "💪 Грузчики",
    "laborers": "🔧 Разнорабочие",
    "other": "📦 Другое",
}

STATUS_LABELS = {
    "new": "🆕 Новая",
    "in_progress": "⚙️ В работе",
    "done": "✅ Выполнена",
    "rejected": "❌ Отклонена",
    "cancelled": "🚫 Отменена",
    "disputed": "⚖️ Спор",
}


def orders_menu_kb(is_manager: bool = False, is_executor: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🆕 Создать заявку", callback_data="order:create")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="order:my:all")],
    ]
    if is_manager:
        buttons.append([
            InlineKeyboardButton(
                text="📥 Все входящие (менеджер)",
                callback_data="order:manager:incoming",
            )
        ])
    if is_executor:
        buttons.append([
            InlineKeyboardButton(
                text="🔧 Доступные мне",
                callback_data="order:executor:available",
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="✅ Мои отклики",
                callback_data="order:executor:my",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def categories_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"order:cat:{cat}")]
        for cat, label in CATEGORY_LABELS.items()
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="order:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def orders_list_kb(orders: list[Order]) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{STATUS_LABELS.get(o.status, o.status)} {o.title[:30]}",
                callback_data=f"order:view:{o.id}",
            )
        ]
        for o in orders
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="order:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_card_kb(
    order: Order,
    is_responsible: bool,
    customer_phone: str | None = None,
) -> InlineKeyboardMarkup:
    buttons = []

    if is_responsible:
        if order.status == "new":
            buttons.append([
                InlineKeyboardButton(
                    text="✅ Принять в работу",
                    callback_data=f"order:accept:{order.id}",
                )
            ])
            buttons.append([
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"order:reject:{order.id}",
                )
            ])
        elif order.status == "in_progress":
            buttons.append([
                InlineKeyboardButton(
                    text="🏁 Завершить",
                    callback_data=f"order:finish:{order.id}",
                )
            ])
            buttons.append([
                InlineKeyboardButton(
                    text="🚫 Отменить",
                    callback_data=f"order:cancel_order:{order.id}",
                )
            ])

        if order.customer_id:
            buttons.append([
                InlineKeyboardButton(
                    text="💬 Написать клиенту",
                    url=f"tg://user?id={order.customer_id}",
                )
            ])
            if customer_phone:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"📞 Позвонить {customer_phone}",
                        url=f"tel:{customer_phone}",
                    )
                ])

    if not is_responsible and order.status in ("new", "in_progress"):
        buttons.append([
            InlineKeyboardButton(
                text="✅ Откликнуться",
                callback_data=f"order:respond:{order.id}:accepted",
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"order:respond:{order.id}:declined",
            ),
        ])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="order:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)