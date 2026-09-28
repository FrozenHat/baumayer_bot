from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models.staff import StaffRole
from models.user import User


MANAGER_SCOPES = {
    "order": "📦 Заказы",
    "material": "📋 Материалы",
    "emergency": "🚨 Аварийка",
}

EXECUTOR_SCOPES = {
    "builder": "🏗️ Строитель",
    "foreman": "👷 Прораб",
    "laborer": "🔧 Разнорабочий",
    "buyer": "🛒 Закупщик",
}

SCOPE_LABELS = {**MANAGER_SCOPES, **EXECUTOR_SCOPES}


def staff_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧑‍💼 Все сотрудники", callback_data="admin:staff:list:all")],
            [InlineKeyboardButton(text="👔 Менеджеры", callback_data="admin:staff:by_kind:manager")],
            [InlineKeyboardButton(text="🔧 Исполнители", callback_data="admin:staff:by_kind:executor")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:panel")],
        ]
    )


def staff_list_kb(users: list[User], filter_: str) -> InlineKeyboardMarkup:
    buttons = []
    for u in users:
        mark = "🚫 " if u.status == "blocked" else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{mark}{u.full_name}",
                callback_data=f"admin:staff:view:{u.id}:{filter_}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:staff:menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def staff_card_kb(
    user_id: int,
    filter_: str,
    roles: list[StaffRole],
) -> InlineKeyboardMarkup:
    buttons = []

    # Существующие роли — кнопки удаления
    for r in roles:
        label = SCOPE_LABELS.get(r.scope, r.scope)
        kind_mark = "👔" if r.kind == "manager" else "🔧"
        proj = f" [{r.project_id}]" if r.project_id else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ {kind_mark} {label}{proj}",
                callback_data=f"admin:staff:del_role:{user_id}:{r.id}:{filter_}",
            )
        ])

    # Добавить роль
    buttons.append([
        InlineKeyboardButton(
            text="➕ Добавить роль",
            callback_data=f"admin:staff:add_role:{user_id}:{filter_}",
        )
    ])

    # Управление статусом
    buttons.append([
        InlineKeyboardButton(
            text="👤 Вернуть в пользователи",
            callback_data=f"admin:staff:to_user:{user_id}:{filter_}",
        )
    ])
    buttons.append([
        InlineKeyboardButton(
            text="🚫 Заблокировать",
            callback_data=f"admin:user:block:{user_id}:{filter_}",
        ),
        InlineKeyboardButton(
            text="✅ Разблокировать",
            callback_data=f"admin:user:unblock:{user_id}:{filter_}",
        ),
    ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ К списку", callback_data=f"admin:staff:list:{filter_}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def add_role_kind_kb(user_id: int, filter_: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="👔 Менеджер",
                callback_data=f"admin:staff:add_kind:{user_id}:manager:{filter_}",
            )],
            [InlineKeyboardButton(
                text="🔧 Исполнитель",
                callback_data=f"admin:staff:add_kind:{user_id}:executor:{filter_}",
            )],
            [InlineKeyboardButton(
                text="⬅️ Отмена",
                callback_data=f"admin:staff:view:{user_id}:{filter_}",
            )],
        ]
    )


def add_role_scope_kb(user_id: int, kind: str, filter_: str) -> InlineKeyboardMarkup:
    scopes = MANAGER_SCOPES if kind == "manager" else EXECUTOR_SCOPES
    buttons = [
        [InlineKeyboardButton(
            text=label,
            callback_data=f"admin:staff:add_scope:{user_id}:{kind}:{scope}:{filter_}",
        )]
        for scope, label in scopes.items()
    ]
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Отмена",
            callback_data=f"admin:staff:view:{user_id}:{filter_}",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)