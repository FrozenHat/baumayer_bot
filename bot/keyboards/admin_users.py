from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models.user import User


def users_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin:users:list:all")],
            [InlineKeyboardButton(text="⏳ Ожидают", callback_data="admin:users:list:pending")],
            [InlineKeyboardButton(text="🚫 Заблокированные", callback_data="admin:users:list:blocked")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:panel")],
        ]
    )


def users_list_kb(users: list[User], filter_: str) -> InlineKeyboardMarkup:
    buttons = []
    for u in users:
        mark = ""
        if u.status == "blocked":
            mark = "🚫 "
        elif u.role == "pending":
            mark = "⏳ "
        buttons.append([
            InlineKeyboardButton(
                text=f"{mark}{u.full_name} [{u.role}]",
                callback_data=f"admin:user:view:{u.id}:{filter_}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_card_kb(user_id: int, filter_: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🧑‍💼 Сделать сотрудником",
                callback_data=f"admin:user:make_staff:{user_id}:{filter_}",
            )],
            [InlineKeyboardButton(
                text="👤 Сделать пользователем",
                callback_data=f"admin:user:role:{user_id}:user:{filter_}",
            )],
            [InlineKeyboardButton(
                text="⏳ Сбросить в ожидание",
                callback_data=f"admin:user:role:{user_id}:pending:{filter_}",
            )],
            [
                InlineKeyboardButton(
                    text="🚫 Заблокировать",
                    callback_data=f"admin:user:block:{user_id}:{filter_}",
                ),
                InlineKeyboardButton(
                    text="✅ Разблокировать",
                    callback_data=f"admin:user:unblock:{user_id}:{filter_}",
                ),
            ],
            [InlineKeyboardButton(
                text="⬅️ К списку",
                callback_data=f"admin:users:list:{filter_}",
            )],
        ]
    )