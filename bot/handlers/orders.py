from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database import async_session
from keyboards.orders import (
    CATEGORY_LABELS,
    STATUS_LABELS,
    categories_kb,
    order_card_kb,
    orders_list_kb,
    orders_menu_kb,
)
from models.order import Order, OrderResponse
from models.profile import Profile
from models.staff import StaffRole
from models.user import User
from services.notify_service import notify_users
from services.order_service import (
    create_order,
    create_response,
    get_my_responses,
    get_orders_for_executor,
    get_orders_for_manager,
    get_user_orders,
)
from services.staff_service import get_all_managers

router = Router()


class OrderCreate(StatesGroup):
    waiting_category = State()
    waiting_title = State()
    waiting_description = State()


async def get_user_roles(session, user_id: int) -> dict:
    """Вернуть набор ролей пользователя в системе заказов."""
    result = await session.execute(
        select(StaffRole).where(StaffRole.user_id == user_id)
    )
    roles = list(result.scalars().all())
    return {
        "is_manager": any(r.kind == "manager" and r.scope == "order" for r in roles),
        "executor_scopes": [r.scope for r in roles if r.kind == "executor"],
    }


# --- Главное меню заказов ---
@router.message(Command("orders"))
@router.message(F.text == "📦 Заказы")
async def cmd_orders(message: Message, user: User):
    async with async_session() as session:
        roles = await get_user_roles(session, user.id)

    await message.answer(
        "📦 <b>Заказы</b>\n\nВыберите действие:",
        reply_markup=orders_menu_kb(
            is_manager=roles["is_manager"] or user.role == "admin",
            is_executor=bool(roles["executor_scopes"]),
        ),
    )


@router.callback_query(F.data == "order:menu")
async def back_to_orders_menu(callback: CallbackQuery, user: User):
    async with async_session() as session:
        roles = await get_user_roles(session, user.id)

    await callback.message.edit_text(
        "📦 <b>Заказы</b>\n\nВыберите действие:",
        reply_markup=orders_menu_kb(
            is_manager=roles["is_manager"] or user.role == "admin",
            is_executor=bool(roles["executor_scopes"]),
        ),
    )
    await callback.answer()


# --- Создание заявки ---
@router.callback_query(F.data == "order:create")
async def order_create_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderCreate.waiting_category)
    await callback.message.edit_text(
        "Выберите <b>категорию</b> заявки:",
        reply_markup=categories_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "order:cancel")
async def order_cancel(callback: CallbackQuery, state: FSMContext, user: User):
    await state.clear()
    async with async_session() as session:
        roles = await get_user_roles(session, user.id)
    await callback.message.edit_text(
        "📦 <b>Заказы</b>\n\nВыберите действие:",
        reply_markup=orders_menu_kb(
            is_manager=roles["is_manager"] or user.role == "admin",
            is_executor=bool(roles["executor_scopes"]),
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order:cat:"))
async def order_create_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[2]
    await state.update_data(category=category)
    await state.set_state(OrderCreate.waiting_title)
    await callback.message.edit_text(
        f"Категория: <b>{CATEGORY_LABELS[category]}</b>\n\n"
        f"Введите <b>краткое название</b> заявки:"
    )
    await callback.answer()


@router.message(OrderCreate.waiting_title)
async def order_create_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(OrderCreate.waiting_description)
    await message.answer("Введите <b>описание</b> (или «—», чтобы пропустить):")


@router.message(OrderCreate.waiting_description)
async def order_create_description(
    message: Message, state: FSMContext, user: User, bot: Bot
):
    value = message.text.strip()
    description = None if value == "—" else value
    data = await state.get_data()

    async with async_session() as session:
        order = await create_order(
            session=session,
            customer_id=user.id,
            category=data["category"],
            title=data["title"],
            description=description,
        )
        await session.flush()
        order_id = order.id
        order_title = order.title
        order_description = order.description

        managers = await get_all_managers(session, "order")
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Заявка <b>#{order_id}</b> создана и отправлена менеджерам."
    )

    if managers:
        text = (
            f"📦 <b>Новая заявка #{order_id}</b>\n\n"
            f"От: <b>{user.full_name}</b>\n"
            f"Категория: {CATEGORY_LABELS.get(data['category'], data['category'])}\n"
            f"Название: {order_title}\n"
            f"Описание: {order_description or '—'}\n\n"
            f"Откройте «📦 Заказы» → «📥 Все входящие»."
        )
        await notify_users(bot, managers, text)
    else:
        await message.answer(
            "⚠️ Менеджеры заказов не назначены. Обратитесь к администратору."
        )


# --- Списки ---
@router.callback_query(F.data.startswith("order:my:"))
async def order_my_list(callback: CallbackQuery, user: User):
    async with async_session() as session:
        orders = await get_user_orders(session, user.id)

    if not orders:
        await callback.message.edit_text("Заявок нет.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📋 <b>Мои заявки</b> ({len(orders)}):",
        reply_markup=orders_list_kb(orders),
    )
    await callback.answer()


@router.callback_query(F.data == "order:manager:incoming")
async def manager_incoming(callback: CallbackQuery, user: User):
    async with async_session() as session:
        roles = await get_user_roles(session, user.id)
        if not roles["is_manager"] and user.role != "admin":
            await callback.answer("Нет доступа", show_alert=True)
            return
        orders = await get_orders_for_manager(
            session, statuses=["new", "in_progress"]
        )

    if not orders:
        await callback.message.edit_text("Входящих нет.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📥 <b>Все входящие</b> ({len(orders)}):",
        reply_markup=orders_list_kb(orders),
    )
    await callback.answer()


@router.callback_query(F.data == "order:executor:available")
async def executor_available(callback: CallbackQuery, user: User):
    async with async_session() as session:
        roles = await get_user_roles(session, user.id)
        scopes = roles["executor_scopes"]
        if not scopes:
            await callback.answer("Вы не исполнитель", show_alert=True)
            return
        orders = await get_orders_for_executor(session, user.id, scopes)

    if not orders:
        await callback.message.edit_text("Нет доступных заявок.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"🔧 <b>Доступные заявки</b> ({len(orders)}):",
        reply_markup=orders_list_kb(orders),
    )
    await callback.answer()


@router.callback_query(F.data == "order:executor:my")
async def executor_my(callback: CallbackQuery, user: User):
    async with async_session() as session:
        responses = await get_my_responses(session, user.id)

    if not responses:
        await callback.message.edit_text("Откликов нет.")
        await callback.answer()
        return

    lines = []
    for r in responses:
        mark = "✅" if r.response == "accepted" else "❌"
        lines.append(f"{mark} Заявка #{r.order_id} — {r.created_at:%d.%m %H:%M}")

    await callback.message.edit_text(
        "📋 <b>Мои отклики</b>\n\n" + "\n".join(lines),
    )
    await callback.answer()


# --- Карточка заявки ---
@router.callback_query(F.data.startswith("order:view:"))
async def order_view(callback: CallbackQuery, user: User):
    order_id = int(callback.data.split(":")[2])

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        roles = await get_user_roles(session, user.id)
        is_responsible = roles["is_manager"] or user.role == "admin"

        customer_phone = None
        if order.customer_id:
            profile = await session.get(Profile, order.customer_id)
            if profile:
                customer_phone = profile.phone

    text = (
        f"📦 <b>Заявка #{order.id}</b>\n\n"
        f"<b>Название:</b> {order.title}\n"
        f"<b>Категория:</b> {CATEGORY_LABELS.get(order.category, order.category)}\n"
        f"<b>Статус:</b> {STATUS_LABELS.get(order.status, order.status)}\n"
        f"<b>Описание:</b> {order.description or '—'}\n"
        f"<b>Цена:</b> {order.price or '—'}\n"
    )
    await callback.message.edit_text(
        text,
        reply_markup=order_card_kb(order, is_responsible, customer_phone),
    )
    await callback.answer()


# --- Действия менеджера ---
@router.callback_query(F.data.startswith("order:accept:"))
async def order_accept(callback: CallbackQuery, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        order.status = "in_progress"
        order.responsible_id = user.id
        customer_id = order.customer_id
        managers = await get_all_managers(session, "order")
        await session.commit()

    other_managers = [m for m in managers if m.id != user.id]
    if other_managers:
        await notify_users(
            bot,
            other_managers,
            f"⚙️ Заявка <b>#{order_id}</b> принята в работу ({user.full_name}).",
        )

    if customer_id:
        try:
            await bot.send_message(
                customer_id,
                f"⚙️ Ваша заявка <b>#{order_id}</b> принята в работу.",
            )
        except Exception:
            pass

    await callback.answer("Принято", show_alert=True)
    await order_view(callback, user)


@router.callback_query(F.data.startswith("order:reject:"))
async def order_reject(callback: CallbackQuery, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        order.status = "rejected"
        order.responsible_id = user.id
        customer_id = order.customer_id
        managers = await get_all_managers(session, "order")
        await session.commit()

    other_managers = [m for m in managers if m.id != user.id]
    if other_managers:
        await notify_users(
            bot,
            other_managers,
            f"❌ Заявка <b>#{order_id}</b> отклонена ({user.full_name}).",
        )

    if customer_id:
        try:
            await bot.send_message(
                customer_id,
                f"❌ Ваша заявка <b>#{order_id}</b> отклонена.",
            )
        except Exception:
            pass

    await callback.answer("Отклонено", show_alert=True)
    await order_view(callback, user)


@router.callback_query(F.data.startswith("order:finish:"))
async def order_finish(callback: CallbackQuery, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        order.status = "done"
        customer_id = order.customer_id
        managers = await get_all_managers(session, "order")
        await session.commit()

    other_managers = [m for m in managers if m.id != user.id]
    if other_managers:
        await notify_users(
            bot,
            other_managers,
            f"✅ Заявка <b>#{order_id}</b> завершена ({user.full_name}).",
        )

    if customer_id:
        try:
            await bot.send_message(
                customer_id,
                f"✅ Ваша заявка <b>#{order_id}</b> завершена.",
            )
        except Exception:
            pass

    await callback.answer("Завершено", show_alert=True)
    await order_view(callback, user)


@router.callback_query(F.data.startswith("order:cancel_order:"))
async def order_cancel_order(callback: CallbackQuery, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        order.status = "cancelled"
        customer_id = order.customer_id
        managers = await get_all_managers(session, "order")
        await session.commit()

    other_managers = [m for m in managers if m.id != user.id]
    if other_managers:
        await notify_users(
            bot,
            other_managers,
            f"🚫 Заявка <b>#{order_id}</b> отменена ({user.full_name}).",
        )

    if customer_id:
        try:
            await bot.send_message(
                customer_id,
                f"🚫 Ваша заявка <b>#{order_id}</b> отменена.",
            )
        except Exception:
            pass

    await callback.answer("Отменено", show_alert=True)
    await order_view(callback, user)


# --- Отклик исполнителя ---
@router.callback_query(F.data.startswith("order:respond:"))
async def order_respond(callback: CallbackQuery, user: User, bot: Bot):
    parts = callback.data.split(":")
    order_id = int(parts[2])
    response = parts[3]

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        await create_response(session, order_id, user.id, response)
        managers = await get_all_managers(session, "order")
        await session.commit()

    mark = "принял" if response == "accepted" else "отклонил"
    text = (
        f"🔔 <b>Отклик на заявку #{order_id}</b>\n\n"
        f"<b>{user.full_name}</b> {mark} выполнение."
    )
    await notify_users(bot, managers, text)

    await callback.answer("Отклик отправлен", show_alert=True)
    await order_view(callback, user)