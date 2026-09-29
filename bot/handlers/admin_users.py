from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from database import async_session
from models.user import User
from models.project import Project
from services.staff_service import add_staff_role, get_user_staff_roles

router = Router()


def is_admin(user: User) -> bool:
    return user.role == "admin"


class UserConvert(StatesGroup):
    waiting_role = State()
    waiting_confirmation = State()


def users_list_kb():
    """Клавиатура для выбора категории пользователей"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏳ Ожидают назначения", callback_data="admin:users:pending")],
            [InlineKeyboardButton(text="🧑‍💼 Сотрудники", callback_data="admin:users:staff")],
            [InlineKeyboardButton(text="👤 Базовые пользователи", callback_data="admin:users:basic")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:panel")],
        ]
    )


def user_card_kb(target_user: User | None, context: str = "staff"):
    """Клавиатура карточки пользователя"""
    if not target_user:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:menu")],
            ]
        )

    buttons = []
    
    if context == "pending" and target_user.role == "pending":
        buttons.append([InlineKeyboardButton(text="✅ Сделать сотрудником", callback_data=f"admin:users:promote:{target_user.id}")])
    
    if context == "staff" or target_user.role in ["manager", "executor"]:
        buttons.append([InlineKeyboardButton(text="➕ Добавить роль", callback_data=f"admin:users:add_role:{target_user.id}")])
        buttons.append([InlineKeyboardButton(text="❌ Заблокировать", callback_data=f"admin:users:block:{target_user.id}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def role_selection_kb():
    """Выбор типа роли"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👷 Менеджер", callback_data="admin:users:role:manager")],
            [InlineKeyboardButton(text="🔧 Исполнитель", callback_data="admin:users:role:executor")],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin:users:menu")],
        ]
    )


def confirm_kb(yes_callback: str, no_callback: str = "admin:users:menu"):
    """Клавиатура подтверждения"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=yes_callback),
                InlineKeyboardButton(text="❌ Нет", callback_data=no_callback),
            ],
        ]
    )


@router.callback_query(F.data == "admin:users:menu")
async def users_menu(callback: CallbackQuery, user: User):
    """Меню управления пользователями"""
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(User).order_by(User.created_at.desc()))
        all_users = result.scalars().all()

        pending = [u for u in all_users if u.role == "pending"]
        staff = [u for u in all_users if u.role in ["manager", "executor"]]
        basic = [u for u in all_users if u.role == "worker"]

    text = (
        f"👥 <b>Управление пользователями</b>\n\n"
        f"⏳ Ожидают назначения: <b>{len(pending)}</b>\n"
        f"🧑‍💼 Сотрудников: <b>{len(staff)}</b>\n"
        f"👤 Базовых пользователей: <b>{len(basic)}</b>\n\n"
        f"Выберите раздел:"
    )

    await callback.message.edit_text(text, reply_markup=users_list_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:users:pending")
async def pending_users_list(callback: CallbackQuery, user: User):
    """Список пользователей, ожидающих назначения"""
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.role == "pending").order_by(User.created_at.desc())
        )
        pending_users = result.scalars().all()

    if not pending_users:
        await callback.message.edit_text(
            "Нет пользователей, ожидающих назначения.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:menu")]]
            ),
        )
        await callback.answer()
        return

    buttons = []
    for u in pending_users:
        buttons.append(
            [InlineKeyboardButton(
                text=f"{u.full_name or u.username or 'Пользователь'} (ID: {u.id})",
                callback_data=f"admin:users:view:{u.id}",
            )]
        )

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:menu")])

    await callback.message.edit_text(
        "⏳ <b>Ожидают назначения</b>\n\nВыберите пользователя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:users:staff")
async def staff_users_list(callback: CallbackQuery, user: User):
    """Список сотрудников"""
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.role.in_(["manager", "executor"]))
            .order_by(User.created_at.desc())
        )
        staff_users = result.scalars().all()

    if not staff_users:
        await callback.message.edit_text(
            "Нет сотрудников.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:menu")]]
            ),
        )
        await callback.answer()
        return

    buttons = []
    for u in staff_users:
        role_emoji = "👷" if u.role == "manager" else "🔧"
        buttons.append(
            [InlineKeyboardButton(
                text=f"{role_emoji} {u.full_name or u.username or 'Пользователь'} (ID: {u.id})",
                callback_data=f"admin:users:view:{u.id}",
            )]
        )

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:menu")])

    await callback.message.edit_text(
        "🧑‍💼 <b>Сотрудники</b>\n\nВыберите сотрудника:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:users:basic")
async def basic_users_list(callback: CallbackQuery, user: User):
    """Список базовых пользователей"""
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.role == "worker").order_by(User.created_at.desc())
        )
        basic_users = result.scalars().all()

    if not basic_users:
        await callback.message.edit_text(
            "Нет базовых пользователей.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:menu")]]
            ),
        )
        await callback.answer()
        return

    buttons = []
    for u in basic_users:
        buttons.append(
            [InlineKeyboardButton(
                text=f"👤 {u.full_name or u.username or 'Пользователь'} (ID: {u.id})",
                callback_data=f"admin:users:view:{u.id}",
            )]
        )

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:menu")])

    await callback.message.edit_text(
        "👤 <b>Базовые пользователи</b>\n\nВыберите пользователя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users:view:"))
async def view_user_card(callback: CallbackQuery, user: User):
    """Карточка пользователя с опциями управления"""
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    target_user_id = int(callback.data.split(":")[3])

    async with async_session() as session:
        target_user = await session.get(User, target_user_id)
        if not target_user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

        staff_roles = await get_user_staff_roles(session, target_user_id)

    roles_text = "\n".join(
        f"• {r.kind} — {r.scope} (Проект: {r.project_id or 'глобально'})"
        for r in staff_roles
    ) or "Нет ролей"

    role_labels = {
        "pending": "⏳ Ожидает назначения",
        "admin": "👑 Администратор",
        "manager": "👷 Менеджер",
        "executor": "🔧 Исполнитель",
        "worker": "👤 Базовый пользователь",
    }

    text = (
        f"<b>Карточка пользователя</b>\n\n"
        f"<b>Имя:</b> {target_user.full_name}\n"
        f"<b>Username:</b> @{target_user.username or '—'}\n"
        f"<b>ID:</b> <code>{target_user.id}</code>\n"
        f"<b>Статус роли:</b> {role_labels.get(target_user.role, target_user.role)}\n"
        f"<b>Статус аккаунта:</b> {target_user.status}\n"
        f"<b>Дата создания:</b> {target_user.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<b>Роли в системе:</b>\n{roles_text}"
    )

    context = "pending" if target_user.role == "pending" else "staff"
    await callback.message.edit_text(
        text,
        reply_markup=user_card_kb(target_user, context),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users:promote:"))
async def promote_to_staff(callback: CallbackQuery, state: FSMContext, user: User):
    """Начать процесс преобразования пользователя в сотрудника"""
    if not is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return

    target_user_id = int(callback.data.split(":")[3])

    await state.update_data(target_user_id=target_user_id)
    await state.set_state(UserConvert.waiting_role)

    await callback.message.edit_text(
        "Выберите тип роли:",
        reply_markup=role_selection_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users:role:"), UserConvert.waiting_role)
async def select_staff_role(callback: CallbackQuery, state: FSMContext, user: User):
    """Выбрать тип роли (менеджер или исполнитель)"""
    if callback.data == "admin:users:role:manager":
        role_type = "manager"
        scopes = ["order", "material", "emergency"]
        text = "Выберите сферу ответственности менеджера:"
    elif callback.data == "admin:users:role:executor":
        role_type = "executor"
        scopes = ["builder", "foreman", "laborer", "buyer"]
        text = "Выберите специальность исполнителя:"
    else:
        await callback.answer()
        return

    await state.update_data(role_type=role_type)

    buttons = []
    for scope in scopes:
        buttons.append(
            [InlineKeyboardButton(text=scope, callback_data=f"admin:users:scope:{scope}")]
        )
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:menu")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users:scope:"), UserConvert.waiting_role)
async def select_staff_scope(callback: CallbackQuery, state: FSMContext, user: User):
    """Выбрать сферу ответственности"""
    scope = callback.data.split(":")[3]
    await state.update_data(scope=scope)

    async with async_session() as session:
        result = await session.execute(select(Project).where(Project.status == "active"))
        projects = result.scalars().all()

    buttons = []
    for project in projects:
        buttons.append(
            [InlineKeyboardButton(text=f"📦 {project.name}", callback_data=f"admin:users:project:{project.id}")]
        )
    buttons.append([InlineKeyboardButton(text="🌍 Глобально (без привязки)", callback_data="admin:users:project:0")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:menu")])

    await callback.message.edit_text(
        "Выберите проект (опционально):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users:project:"), UserConvert.waiting_role)
async def select_project_and_confirm(callback: CallbackQuery, state: FSMContext):
    """Выбрать проект и подтвердить"""
    project_id = int(callback.data.split(":")[3])
    await state.update_data(project_id=project_id if project_id != 0 else None)
    await state.set_state(UserConvert.waiting_confirmation)

    data = await state.get_data()
    target_user_id = data["target_user_id"]
    role_type = data["role_type"]
    scope = data["scope"]
    project_id_val = data.get("project_id")

    async with async_session() as session:
        target_user = await session.get(User, target_user_id)
        project = None
        if project_id_val:
            project = await session.get(Project, project_id_val)

    project_text = f"Проект: {project.name}" if project else "Проект: Глобально"

    text = (
        f"<b>Подтверждение назначения роли</b>\n\n"
        f"Пользователь: <b>{target_user.full_name}</b>\n"
        f"Тип роли: <b>{role_type}</b>\n"
        f"Сфера: <b>{scope}</b>\n"
        f"{project_text}\n\n"
        f"Согласны?"
    )

    await callback.message.edit_text(
        text,
        reply_markup=confirm_kb(f"admin:users:confirm_role:yes", "admin:users:menu"),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:users:confirm_role:yes", UserConvert.waiting_confirmation)
async def confirm_role_assignment(callback: CallbackQuery, state: FSMContext, user: User):
    """Подтвердить назначение роли"""
    data = await state.get_data()
    target_user_id = data["target_user_id"]
    role_type = data["role_type"]
    scope = data["scope"]
    project_id = data.get("project_id")

    async with async_session() as session:
        target_user = await session.get(User, target_user_id)

        await add_staff_role(session, target_user_id, role_type, scope, project_id)

        if target_user.role == "pending":
            target_user.role = "manager" if role_type == "manager" else "executor"

        await session.commit()

    await state.clear()

    await callback.message.edit_text(
        f"✅ Роль успешно добавлена пользователю {target_user.full_name}!",
        reply_markup=user_card_kb(target_user, "staff"),
    )
    await callback.answer()
