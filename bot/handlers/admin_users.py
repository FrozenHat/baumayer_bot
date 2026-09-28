from aiogram import F, Router
from aiogram.types import CallbackQuery

from database import async_session
from keyboards.admin_users import (
    user_card_kb,
    users_list_kb,
    users_menu_kb,
)
from models.user import User

router = Router()


def is_admin(user: User) -> bool:
    return user.role == "admin"


@router.callback_query(F.data == "admin:users:menu")
async def users_menu(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "👥 <b>Пользователи</b>\n\nВыберите раздел:",
        reply_markup=users_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users:list:"))
async def users_list(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    filter_ = callback.data.split(":")[3]

    from sqlalchemy import select

    async with async_session() as session:
        query = select(User)
        if filter_ == "pending":
            query = query.where(User.role == "pending", User.status == "active")
        elif filter_ == "blocked":
            query = query.where(User.status == "blocked")
        elif filter_ == "all":
            query = query.where(User.role.in_(["user", "pending"]))
        # Сотрудники и админы сюда не попадают
        query = query.order_by(User.created_at.desc()).limit(50)
        result = await session.execute(query)
        users = list(result.scalars().all())

    if not users:
        await callback.message.edit_text(
            "Список пуст.",
            reply_markup=users_menu_kb(),
        )
        await callback.answer()
        return

    titles = {
        "all": "👥 Все пользователи",
        "pending": "⏳ Ожидают",
        "blocked": "🚫 Заблокированные",
    }
    await callback.message.edit_text(
        f"{titles.get(filter_, '👥 Пользователи')} ({len(users)}):",
        reply_markup=users_list_kb(users, filter_),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:view:"))
async def user_view(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    target_id = int(parts[3])
    filter_ = parts[4]

    async with async_session() as session:
        target = await session.get(User, target_id)
        if target is None:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

    text = (
        f"👤 <b>{target.full_name}</b>\n\n"
        f"ID: <code>{target.id}</code>\n"
        f"Username: @{target.username or '—'}\n"
        f"Роль: <b>{target.role}</b>\n"
        f"Статус: <b>{target.status}</b>\n"
        f"Создан: {target.created_at:%Y-%m-%d %H:%M}\n"
    )
    await callback.message.edit_text(
        text, reply_markup=user_card_kb(target.id, filter_)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:role:"))
async def user_set_role(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    target_id = int(parts[3])
    new_role = parts[4]
    filter_ = parts[5]

    async with async_session() as session:
        target = await session.get(User, target_id)
        if target is None:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        target.role = new_role
        await session.commit()

    await callback.answer(f"Роль: {new_role}", show_alert=True)
    callback.data = f"admin:user:view:{target_id}:{filter_}"
    await user_view(callback, user)


@router.callback_query(F.data.startswith("admin:user:make_staff:"))
async def user_make_staff(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    target_id = int(parts[3])
    filter_ = parts[4]

    async with async_session() as session:
        target = await session.get(User, target_id)
        if target is None:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        target.role = "staff"
        await session.commit()

    await callback.answer("Теперь сотрудник", show_alert=True)
    # Переходим сразу в карточку сотрудника
    callback.data = f"admin:staff:view:{target_id}:all"
    from handlers.admin_staff import staff_view
    await staff_view(callback, user)


@router.callback_query(F.data.startswith("admin:user:block:"))
async def user_block(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    target_id = int(parts[3])
    filter_ = parts[4] if len(parts) > 4 else "all"

    async with async_session() as session:
        target = await session.get(User, target_id)
        if target is None:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        target.status = "blocked"
        await session.commit()

    await callback.answer("Заблокирован", show_alert=True)
    callback.data = f"admin:user:view:{target_id}:{filter_}"
    await user_view(callback, user)


@router.callback_query(F.data.startswith("admin:user:unblock:"))
async def user_unblock(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    target_id = int(parts[3])
    filter_ = parts[4] if len(parts) > 4 else "all"

    async with async_session() as session:
        target = await session.get(User, target_id)
        if target is None:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        target.status = "active"
        await session.commit()

    await callback.answer("Разблокирован", show_alert=True)
    callback.data = f"admin:user:view:{target_id}:{filter_}"
    await user_view(callback, user)