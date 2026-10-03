from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from database import async_session
from keyboards.admin_staff import (
    add_role_kind_kb,
    add_role_scope_kb,
    staff_card_kb,
    staff_list_kb,
    staff_menu_kb,
)
from models.staff import StaffRole
from models.user import User
from services.staff_service import add_staff_role, remove_staff_role

router = Router()


def is_admin(user: User) -> bool:
    return user.role == "admin"


@router.callback_query(F.data == "admin:staff:menu")
async def staff_menu(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "🧑‍💼 <b>Сотрудники</b>\n\nВыберите раздел:",
        reply_markup=staff_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:staff:list:"))
async def staff_list(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    filter_ = callback.data.split(":")[3]

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.role == "staff").order_by(User.full_name)
        )
        users = list(result.scalars().all())

    if not users:
        await callback.message.edit_text(
            "Сотрудников пока нет.",
            reply_markup=staff_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"🧑‍💼 <b>Сотрудники</b> ({len(users)}):",
        reply_markup=staff_list_kb(users, filter_),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:staff:by_kind:"))
async def staff_by_kind(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    kind = callback.data.split(":")[3]

    async with async_session() as session:
        result = await session.execute(
            select(User)
            .join(StaffRole, StaffRole.user_id == User.id)
            .where(StaffRole.kind == kind)
            .order_by(User.full_name)
        )
        users = list(result.scalars().unique().all())

    if not users:
        await callback.message.edit_text(
            f"{'👔 Менеджеров' if kind == 'manager' else '🔧 Исполнителей'} пока нет.",
            reply_markup=staff_menu_kb(),
        )
        await callback.answer()
        return

    title = "👔 Менеджеры" if kind == "manager" else "🔧 Исполнители"
    await callback.message.edit_text(
        f"{title} ({len(users)}):",
        reply_markup=staff_list_kb(users, kind),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:staff:view:"))
async def staff_view(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    target_id = int(parts[3])
    filter_ = parts[4] if len(parts) > 4 else "all"

    async with async_session() as session:
        target = await session.get(User, target_id)
        if target is None:
            await callback.answer("Сотрудник не найден", show_alert=True)
            return
        result = await session.execute(
            select(StaffRole).where(StaffRole.user_id == target_id)
        )
        roles = list(result.scalars().all())

    roles_text = "\n".join(
        f"• {'👔' if r.kind == 'manager' else '🔧'} {r.scope}"
        + (f" (проект {r.project_id})" if r.project_id else " (глобально)")
        for r in roles
    ) or "—"

    text = (
        f"🧑‍💼 <b>{target.full_name}</b>\n\n"
        f"ID: <code>{target.id}</code>\n"
        f"Username: @{target.username or '—'}\n"
        f"Роль в системе: <b>{target.role}</b>\n"
        f"Статус: <b>{target.status}</b>\n\n"
        f"<b>Роли в подразделениях:</b>\n{roles_text}"
    )
    await callback.message.edit_text(
        text, reply_markup=staff_card_kb(target.id, filter_, roles)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:staff:add_role:"))
async def staff_add_role(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    target_id = int(parts[3])
    filter_ = parts[4]

    await callback.message.edit_text(
        "Выберите <b>тип роли</b>:",
        reply_markup=add_role_kind_kb(target_id, filter_),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:staff:add_kind:"))
async def staff_add_kind(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    target_id = int(parts[3])
    kind = parts[4]
    filter_ = parts[5]

    await callback.message.edit_text(
        f"Выберите <b>сферу</b>:",
        reply_markup=add_role_scope_kb(target_id, kind, filter_),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:staff:add_scope:"))
async def staff_add_scope(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    target_id = int(parts[3])
    kind = parts[4]
    scope = parts[5]
    filter_ = parts[6]

    async with async_session() as session:
        await add_staff_role(session, target_id, kind, scope, project_id=None)
        await session.commit()

    await callback.answer("Роль добавлена", show_alert=True)
    callback.data = f"admin:staff:view:{target_id}:{filter_}"
    await staff_view(callback, user)


@router.callback_query(F.data.startswith("admin:staff:del_role:"))
async def staff_del_role(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    target_id = int(parts[3])
    role_id = int(parts[4])
    filter_ = parts[5]

    async with async_session() as session:
        role = await session.get(StaffRole, role_id)
        if role is None:
            await callback.answer("Роль не найдена", show_alert=True)
            return
        await remove_staff_role(
            session,
            user_id=role.user_id,
            kind=role.kind,
            scope=role.scope,
            project_id=role.project_id,
        )
        await session.commit()

    await callback.answer("Роль удалена", show_alert=True)
    callback.data = f"admin:staff:view:{target_id}:{filter_}"
    await staff_view(callback, user)


@router.callback_query(F.data.startswith("admin:staff:to_user:"))
async def staff_to_user(callback: CallbackQuery, user: User):
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    target_id = int(parts[3])
    filter_ = parts[4]

    async with async_session() as session:
        target = await session.get(User, target_id)
        if target is None:
            await callback.answer("Сотрудник не найден", show_alert=True)
            return
        result = await session.execute(
            select(StaffRole).where(StaffRole.user_id == target_id)
        )
        for r in result.scalars().all():
            await remove_staff_role(
                session, r.user_id, r.kind, r.scope, r.project_id
            )
        target.role = "user"
        await session.commit()

    await callback.answer("Вернули в пользователи", show_alert=True)

    # Локальный импорт, чтобы не было циклической зависимости
    from handlers.admin_users import user_view

    callback.data = f"admin:user:view:{target_id}:all"
    await user_view(callback, user)