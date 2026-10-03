from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from database import async_session
from keyboards.services import (
    SERVICES_CATEGORIES,
    STATUS_LABELS,
    after_order_kb,
    back_to_services_kb,
    cancel_fill_kb,
    executor_order_kb,
    executor_pick_kb,
    manager_order_card_kb,
    services_categories_kb,
    services_list_kb,
    services_menu_kb,
)
from models.order import Order, OrderResponse
from models.profile import Profile
from models.staff import StaffRole
from models.user import User
from services.notify_service import notify_users
from services.staff_service import get_all_managers

router = Router()


# =========================================================
# FSM
# =========================================================

class ServiceCreate(StatesGroup):
    waiting_category = State()
    waiting_description = State()


class ServiceLeavePhone(StatesGroup):
    waiting_phone = State()


class OrderFill(StatesGroup):
    waiting_address = State()
    waiting_start = State()
    waiting_end = State()
    waiting_notes = State()
    waiting_client_price = State()
    waiting_executor_price = State()


# =========================================================
# УТИЛИТЫ (проверка ролей)
# =========================================================

async def is_order_manager(session, user_id: int, role: str) -> bool:
    """Является ли пользователь менеджером заказов (или админом)."""
    if role == "admin":
        return True
    result = await session.execute(
        select(StaffRole).where(
            StaffRole.user_id == user_id,
            StaffRole.kind == "manager",
            StaffRole.scope == "order",
        )
    )
    return result.scalar_one_or_none() is not None


async def is_executor(session, user_id: int) -> bool:
    """Есть ли у пользователя хотя бы одна роль исполнителя."""
    result = await session.execute(
        select(StaffRole).where(
            StaffRole.user_id == user_id,
            StaffRole.kind == "executor",
        )
    )
    return result.scalar_one_or_none() is not None


# =========================================================
# ГЛАВНОЕ МЕНЮ «УСЛУГИ»
# =========================================================

@router.message(Command("services"))
@router.message(F.text == "🛠️ Услуги")
async def cmd_services(message: Message, user: User):
    async with async_session() as session:
        mgr = await is_order_manager(session, user.id, user.role)
        ex = await is_executor(session, user.id)

    await message.answer(
        "🛠️ <b>Услуги</b>\n\nВыберите действие:",
        reply_markup=services_menu_kb(is_manager=mgr, is_executor=ex),
    )


@router.callback_query(F.data == "srv:menu")
async def back_to_services(callback: CallbackQuery, user: User):
    async with async_session() as session:
        mgr = await is_order_manager(session, user.id, user.role)
        ex = await is_executor(session, user.id)

    await callback.message.edit_text(
        "🛠️ <b>Услуги</b>\n\nВыберите действие:",
        reply_markup=services_menu_kb(is_manager=mgr, is_executor=ex),
    )
    await callback.answer()


# =========================================================
# ИНСТРУКЦИЯ
# =========================================================

@router.callback_query(F.data == "srv:info")
async def services_info(callback: CallbackQuery, user: User):
    text = (
        "ℹ️ <b>Как работают заявки на услуги</b>\n\n"
        "1️⃣ Вы выбираете категорию услуги (доставка, грузчики, "
        "разнорабочие и т.д.).\n\n"
        "2️⃣ Описываете задачу одним текстом — как можно подробнее: "
        "что нужно сделать, где, в какие сроки.\n\n"
        "3️⃣ Заявка уходит менеджеру. Он обрабатывает её, "
        "уточняет детали и назначает исполнителя.\n\n"
        "4️⃣ Вы будете получать уведомления об изменении статуса. "
        "Текущие заявки всегда можно посмотреть в разделе "
        "«📂 Мои услуги».\n\n"
        "📞 Если хотите, чтобы менеджер перезвонил — нажмите "
        "кнопку «Оставить номер» после подачи заявки."
    )
    await callback.message.edit_text(text, reply_markup=back_to_services_kb())
    await callback.answer()


# =========================================================
# СОЗДАНИЕ ЗАЯВКИ (КЛИЕНТ)
# =========================================================

@router.callback_query(F.data == "srv:choose")
async def services_choose(callback: CallbackQuery, state: FSMContext, user: User):
    await state.set_state(ServiceCreate.waiting_category)
    await callback.message.edit_text(
        "📋 <b>Выберите категорию услуги:</b>",
        reply_markup=services_categories_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("srv:cat:"))
async def services_category_chosen(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[2]
    await state.update_data(category=category)
    await state.set_state(ServiceCreate.waiting_description)
    await callback.message.edit_text(
        f"<b>{SERVICES_CATEGORIES[category]}</b>\n\n"
        f"📝 Опишите задачу одним текстом: что нужно сделать, "
        f"где, в какие сроки и другие важные детали."
    )
    await callback.answer()


@router.message(ServiceCreate.waiting_description)
async def services_description(
    message: Message, state: FSMContext, user: User, bot: Bot
):
    description = message.text.strip()
    data = await state.get_data()
    category = data["category"]

    # Первая строка описания — как «название» заявки
    title = description[:60] + ("…" if len(description) > 60 else "")

    async with async_session() as session:
        order = Order(
            customer_id=user.id,
            category=category,
            title=title,
            description=description,
            status="new",
        )
        session.add(order)
        await session.flush()
        order_id = order.id
        managers = await get_all_managers(session, "order")
        await session.commit()

    await state.clear()

    # Уведомляем менеджеров
    if managers:
        text = (
            f"📥 <b>Новая заявка на услугу #{order_id}</b>\n\n"
            f"От: <b>{user.full_name}</b>\n"
            f"Категория: {SERVICES_CATEGORIES.get(category, category)}\n"
            f"Описание: {description}"
        )
        await notify_users(bot, managers, text)

    # Ответ клиенту
    await message.answer(
        f"✅ <b>Ваша заявка #{order_id} принята!</b>\n\n"
        f"Мы направили её менеджеру и уведомим вас об изменении статуса.\n\n"
        f"Вы можете посмотреть текущие заявки в разделе «📂 Мои услуги» "
        f"или заказать обратный звонок менеджера — оставьте номер.",
        reply_markup=after_order_kb(order_id),
    )


# =========================================================
# ОСТАВИТЬ НОМЕР ДЛЯ ЗВОНКА
# =========================================================

@router.callback_query(F.data.startswith("srv:leave_phone:"))
async def leave_phone_start(callback: CallbackQuery, state: FSMContext, user: User):
    order_id = int(callback.data.split(":")[2])
    await state.update_data(order_id=order_id)
    await state.set_state(ServiceLeavePhone.waiting_phone)
    await callback.message.answer(
        "📞 Введите ваш номер телефона — менеджер вам перезвонит:"
    )
    await callback.answer()


@router.message(ServiceLeavePhone.waiting_phone)
async def leave_phone_save(
    message: Message, state: FSMContext, user: User, bot: Bot
):
    phone = message.text.strip()
    data = await state.get_data()
    order_id = data.get("order_id")

    # Сохраняем номер в профиль пользователя
    async with async_session() as session:
        profile_result = await session.execute(
            select(Profile).where(Profile.user_id == user.id)
        )
        profile = profile_result.scalar_one_or_none()
        if profile is None:
            profile = Profile(user_id=user.id, phone=phone)
            session.add(profile)
        else:
            profile.phone = phone

        managers = await get_all_managers(session, "order")
        await session.commit()

    await state.clear()

    if managers:
        text = (
            f"📞 <b>Запрос на обратный звонок</b>\n\n"
            f"Клиент: <b>{user.full_name}</b>\n"
            f"Номер: <code>{phone}</code>\n"
            f"По заявке: <b>#{order_id}</b>\n\n"
            f"Пожалуйста, свяжитесь с клиентом."
        )
        await notify_users(bot, managers, text)

    await message.answer("✅ Спасибо! Менеджер свяжется с вами в ближайшее время.")


# =========================================================
# МОИ УСЛУГИ (КЛИЕНТ)
# =========================================================

@router.callback_query(F.data == "srv:my")
async def services_my(callback: CallbackQuery, user: User):
    async with async_session() as session:
        result = await session.execute(
            select(Order)
            .where(Order.customer_id == user.id)
            .order_by(Order.created_at.desc())
        )
        orders = list(result.scalars().all())

    if not orders:
        await callback.message.edit_text(
            "📂 <b>Мои услуги</b>\n\nУ вас пока нет заявок.",
            reply_markup=back_to_services_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📂 <b>Мои услуги</b> ({len(orders)}):",
        reply_markup=services_list_kb(orders),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("srv:view:"))
async def services_view(callback: CallbackQuery, user: User):
    order_id = int(callback.data.split(":")[2])

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None or order.customer_id != user.id:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

    text = (
        f"📋 <b>Заявка #{order.id}</b>\n\n"
        f"<b>Категория:</b> {SERVICES_CATEGORIES.get(order.category, order.category)}\n"
        f"<b>Статус:</b> {STATUS_LABELS.get(order.status, order.status)}\n\n"
        f"<b>Описание:</b>\n{order.description or '—'}"
    )
    await callback.message.edit_text(text, reply_markup=back_to_services_kb())
    await callback.answer()


# =========================================================
# МЕНЕДЖЕР
# =========================================================

@router.callback_query(F.data == "srv:manager:incoming")
async def manager_incoming(callback: CallbackQuery, user: User):
    async with async_session() as session:
        mgr = await is_order_manager(session, user.id, user.role)
        if not mgr:
            await callback.answer("Нет доступа", show_alert=True)
            return
        result = await session.execute(
            select(Order)
            .where(Order.status.in_(["new", "in_progress"]))
            .order_by(Order.created_at.desc())
        )
        orders = list(result.scalars().all())

    if not orders:
        await callback.message.edit_text(
            "📥 <b>Входящие заявки</b>\n\nПока ничего нет.",
            reply_markup=back_to_services_kb(),
        )
        await callback.answer()
        return

    buttons = [
        [InlineKeyboardButton(
            text=f"#{o.id} • {SERVICES_CATEGORIES.get(o.category, o.category)} • {o.title[:30]}",
            callback_data=f"srv:mgr:view:{o.id}",
        )]
        for o in orders
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="srv:menu")])

    await callback.message.edit_text(
        f"📥 <b>Входящие заявки</b> ({len(orders)}):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


async def _render_manager_card(callback: CallbackQuery, user: User, order_id: int):
    """Отрисовать карточку заявки для менеджера."""
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        customer = (
            await session.get(User, order.customer_id) if order.customer_id else None
        )
        executor = (
            await session.get(User, order.executor_id) if order.executor_id else None
        )
        responsible = (
            await session.get(User, order.responsible_id)
            if order.responsible_id
            else None
        )

        # Кто смотрит карточку — менеджер?
        is_manager = await is_order_manager(session, user.id, user.role)

    text = (
        f"📋 <b>Заявка #{order.id}</b>\n\n"
        f"<b>Категория:</b> {SERVICES_CATEGORIES.get(order.category, order.category)}\n"
        f"<b>Статус:</b> {STATUS_LABELS.get(order.status, order.status)}\n"
        f"<b>Клиент:</b> {customer.full_name if customer else '—'}\n"
        f"<b>Описание:</b>\n{order.description or '—'}\n\n"
        f"<b>Адрес:</b> {order.address or '—'}\n"
        f"<b>Срок начала:</b> "
        f"{order.start_date.strftime('%d.%m.%Y') if order.start_date else '—'}\n"
        f"<b>Срок окончания:</b> "
        f"{order.end_date.strftime('%d.%m.%Y') if order.end_date else '—'}\n"
        f"<b>Примечания:</b> {order.special_notes or '—'}\n\n"
        f"<b>Стоимость для клиента:</b> "
        f"{f'{order.client_price} ₽' if order.client_price is not None else '—'}\n"
        f"<b>Гонорар исполнителя:</b> "
        f"{f'{order.executor_price} ₽' if order.executor_price is not None else '—'}\n\n"
        f"<b>Ведущий менеджер:</b> {responsible.full_name if responsible else '—'}\n"
        f"<b>Исполнитель:</b> {executor.full_name if executor else '—'}"
    )
    await callback.message.edit_text(
        text, reply_markup=manager_order_card_kb(order, is_manager)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("srv:mgr:view:"))
async def manager_view(callback: CallbackQuery, user: User):
    order_id = int(callback.data.split(":")[3])
    await _render_manager_card(callback, user, order_id)


@router.callback_query(F.data.startswith("srv:mgr:accept:"))
async def manager_accept(callback: CallbackQuery, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[3])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        order.status = "in_progress"
        order.responsible_id = user.id
        customer_id = order.customer_id
        await session.commit()

    if customer_id:
        try:
            await bot.send_message(
                customer_id,
                f"⚙️ Ваша заявка <b>#{order_id}</b> принята в работу.",
            )
        except Exception:
            pass

    await callback.answer("Вы ведёте заявку", show_alert=True)
    await _render_manager_card(callback, user, order_id)


@router.callback_query(F.data.startswith("srv:mgr:finish:"))
async def manager_finish(callback: CallbackQuery, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[3])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        order.status = "done"
        customer_id = order.customer_id
        await session.commit()

    if customer_id:
        try:
            await bot.send_message(
                customer_id,
                f"🏁 Ваша заявка <b>#{order_id}</b> завершена. Спасибо!",
            )
        except Exception:
            pass

    await callback.answer("Заявка завершена", show_alert=True)
    await _render_manager_card(callback, user, order_id)


@router.callback_query(F.data.startswith("srv:mgr:cancel:"))
async def manager_cancel(callback: CallbackQuery, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[3])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        order.status = "cancelled"
        customer_id = order.customer_id
        await session.commit()

    if customer_id:
        try:
            await bot.send_message(
                customer_id,
                f"🚫 Ваша заявка <b>#{order_id}</b> отменена.",
            )
        except Exception:
            pass

    await callback.answer("Заявка отменена", show_alert=True)
    await _render_manager_card(callback, user, order_id)


# --- Заполнение карточки через FSM ---

@router.callback_query(F.data.startswith("srv:mgr:fill:"))
async def manager_fill_start(callback: CallbackQuery, state: FSMContext, user: User):
    order_id = int(callback.data.split(":")[3])
    await state.update_data(order_id=order_id)
    await state.set_state(OrderFill.waiting_address)
    await callback.message.answer(
        "✏️ <b>Заполнение карточки</b>\n\n"
        "Введите <b>адрес исполнения</b> (или «—», чтобы пропустить):",
        reply_markup=cancel_fill_kb(order_id),
    )
    await callback.answer()


@router.message(OrderFill.waiting_address)
async def fill_address(message: Message, state: FSMContext):
    value = message.text.strip()
    await state.update_data(address=None if value == "—" else value)
    await state.set_state(OrderFill.waiting_start)
    await message.answer("Введите <b>срок начала</b> в формате ДД.ММ.ГГГГ или «—»:")


@router.message(OrderFill.waiting_start)
async def fill_start(message: Message, state: FSMContext):
    value = message.text.strip()
    if value == "—":
        await state.update_data(start_date=None)
    else:
        try:
            dt = datetime.strptime(value, "%d.%m.%Y")
            await state.update_data(start_date=dt)
        except ValueError:
            await message.answer("Неверный формат. Введите ДД.ММ.ГГГГ или «—»:")
            return
    await state.set_state(OrderFill.waiting_end)
    await message.answer("Введите <b>срок окончания</b> в формате ДД.ММ.ГГГГ или «—»:")


@router.message(OrderFill.waiting_end)
async def fill_end(message: Message, state: FSMContext):
    value = message.text.strip()
    if value == "—":
        await state.update_data(end_date=None)
    else:
        try:
            dt = datetime.strptime(value, "%d.%m.%Y")
            await state.update_data(end_date=dt)
        except ValueError:
            await message.answer("Неверный формат. Введите ДД.ММ.ГГГГ или «—»:")
            return
    await state.set_state(OrderFill.waiting_notes)
    await message.answer("Введите <b>особые примечания</b> или «—»:")


@router.message(OrderFill.waiting_notes)
async def fill_notes(message: Message, state: FSMContext):
    value = message.text.strip()
    await state.update_data(special_notes=None if value == "—" else value)
    await state.set_state(OrderFill.waiting_client_price)
    await message.answer(
        "Введите <b>стоимость работ для клиента</b> в рублях или «—»:"
    )


@router.message(OrderFill.waiting_client_price)
async def fill_client_price(message: Message, state: FSMContext):
    value = message.text.strip()
    if value == "—":
        await state.update_data(client_price=None)
    else:
        try:
            await state.update_data(client_price=float(value.replace(",", ".")))
        except ValueError:
            await message.answer("Введите число или «—»:")
            return
    await state.set_state(OrderFill.waiting_executor_price)
    await message.answer("Введите <b>гонорар исполнителя</b> в рублях или «—»:")


@router.message(OrderFill.waiting_executor_price)
async def fill_executor_price(message: Message, state: FSMContext, user: User):
    value = message.text.strip()
    if value == "—":
        executor_price = None
    else:
        try:
            executor_price = float(value.replace(",", "."))
        except ValueError:
            await message.answer("Введите число или «—»:")
            return

    data = await state.get_data()
    order_id = data["order_id"]

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await state.clear()
            await message.answer("Заявка не найдена.")
            return
        order.address = data.get("address")
        order.start_date = data.get("start_date")
        order.end_date = data.get("end_date")
        order.special_notes = data.get("special_notes")
        order.client_price = data.get("client_price")
        order.executor_price = executor_price
        await session.commit()

    await state.clear()
    await message.answer("✅ Карточка заполнена.")

    # Отправляем обновлённую карточку менеджеру
    async with async_session() as session:
        order = await session.get(Order, order_id)
        customer = (
            await session.get(User, order.customer_id) if order.customer_id else None
        )
        executor = (
            await session.get(User, order.executor_id) if order.executor_id else None
        )
        responsible = (
            await session.get(User, order.responsible_id)
            if order.responsible_id
            else None
        )

    text = (
        f"📋 <b>Заявка #{order.id}</b>\n\n"
        f"<b>Категория:</b> {SERVICES_CATEGORIES.get(order.category, order.category)}\n"
        f"<b>Статус:</b> {STATUS_LABELS.get(order.status, order.status)}\n"
        f"<b>Клиент:</b> {customer.full_name if customer else '—'}\n"
        f"<b>Описание:</b>\n{order.description or '—'}\n\n"
        f"<b>Адрес:</b> {order.address or '—'}\n"
        f"<b>Срок начала:</b> "
        f"{order.start_date.strftime('%d.%m.%Y') if order.start_date else '—'}\n"
        f"<b>Срок окончания:</b> "
        f"{order.end_date.strftime('%d.%m.%Y') if order.end_date else '—'}\n"
        f"<b>Примечания:</b> {order.special_notes or '—'}\n\n"
        f"<b>Стоимость для клиента:</b> "
        f"{f'{order.client_price} ₽' if order.client_price is not None else '—'}\n"
        f"<b>Гонорар исполнителя:</b> "
        f"{f'{order.executor_price} ₽' if order.executor_price is not None else '—'}\n\n"
        f"<b>Ведущий менеджер:</b> {responsible.full_name if responsible else '—'}\n"
        f"<b>Исполнитель:</b> {executor.full_name if executor else '—'}"
    )
    await message.answer(text, reply_markup=manager_order_card_kb(order, True))


# --- Назначение исполнителя ---

@router.callback_query(F.data.startswith("srv:mgr:assign:"))
async def manager_assign(callback: CallbackQuery, user: User):
    order_id = int(callback.data.split(":")[3])

    async with async_session() as session:
        result = await session.execute(
            select(User)
            .join(StaffRole, StaffRole.user_id == User.id)
            .where(
                StaffRole.kind == "executor",
                User.status == "active",
            )
        )
        executors = list(result.scalars().unique().all())

    if not executors:
        await callback.answer("Нет доступных исполнителей", show_alert=True)
        return

    await callback.message.edit_text(
        "👤 <b>Выберите исполнителя:</b>",
        reply_markup=executor_pick_kb(order_id, executors),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("srv:mgr:assign_pick:"))
async def manager_assign_pick(callback: CallbackQuery, user: User, bot: Bot):
    parts = callback.data.split(":")
    order_id = int(parts[3])
    executor_id = int(parts[4])

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        order.executor_id = executor_id
        executor = await session.get(User, executor_id)
        await session.commit()

    # Уведомляем исполнителя
    if executor:
        text = (
            f"🔧 <b>Вам назначена задача #{order_id}</b>\n\n"
            f"Категория: {SERVICES_CATEGORIES.get(order.category, order.category)}\n"
            f"Описание: {order.description or '—'}\n\n"
            f"Адрес: {order.address or '—'}\n"
            f"Срок: "
            f"{order.start_date.strftime('%d.%m.%Y') if order.start_date else '—'} "
            f"— "
            f"{order.end_date.strftime('%d.%m.%Y') if order.end_date else '—'}\n"
            f"Примечания: {order.special_notes or '—'}\n"
            f"Гонорар: "
            f"{order.executor_price if order.executor_price is not None else '—'} ₽"
        )
        try:
            await bot.send_message(
                executor.id,
                text,
                reply_markup=executor_order_kb(order, has_response=False),
            )
        except Exception:
            pass

    await callback.answer("Исполнитель назначен", show_alert=True)
    await _render_manager_card(callback, user, order_id)


# =========================================================
# ИСПОЛНИТЕЛЬ
# =========================================================

@router.callback_query(F.data == "srv:ex:my")
async def executor_my(callback: CallbackQuery, user: User):
    async with async_session() as session:
        result = await session.execute(
            select(Order)
            .where(Order.executor_id == user.id)
            .order_by(Order.created_at.desc())
        )
        orders = list(result.scalars().all())

    if not orders:
        await callback.message.edit_text(
            "🔧 <b>Мои задачи</b>\n\nПока ничего нет.",
            reply_markup=back_to_services_kb(),
        )
        await callback.answer()
        return

    buttons = [
        [InlineKeyboardButton(
            text=f"#{o.id} • {STATUS_LABELS.get(o.status, o.status)} • {o.title[:30]}",
            callback_data=f"srv:ex:view:{o.id}",
        )]
        for o in orders
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="srv:menu")])

    await callback.message.edit_text(
        f"🔧 <b>Мои задачи</b> ({len(orders)}):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("srv:ex:view:"))
async def executor_view(callback: CallbackQuery, user: User):
    order_id = int(callback.data.split(":")[3])

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None or order.executor_id != user.id:
            await callback.answer("Задача не найдена", show_alert=True)
            return

        resp_result = await session.execute(
            select(OrderResponse).where(
                OrderResponse.order_id == order_id,
                OrderResponse.user_id == user.id,
            )
        )
        has_response = resp_result.scalar_one_or_none() is not None

    text = (
        f"🔧 <b>Задача #{order.id}</b>\n\n"
        f"<b>Статус:</b> {STATUS_LABELS.get(order.status, order.status)}\n"
        f"<b>Описание:</b>\n{order.description or '—'}\n\n"
        f"<b>Адрес:</b> {order.address or '—'}\n"
        f"<b>Срок:</b> "
        f"{order.start_date.strftime('%d.%m.%Y') if order.start_date else '—'} "
        f"— "
        f"{order.end_date.strftime('%d.%m.%Y') if order.end_date else '—'}\n"
        f"<b>Примечания:</b> {order.special_notes or '—'}\n"
        f"<b>Гонорар:</b> "
        f"{order.executor_price if order.executor_price is not None else '—'} ₽"
    )
    await callback.message.edit_text(
        text, reply_markup=executor_order_kb(order, has_response)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("srv:ex:accept:"))
async def executor_accept(callback: CallbackQuery, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[3])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Задача не найдена", show_alert=True)
            return
        session.add(
            OrderResponse(order_id=order_id, user_id=user.id, response="accepted")
        )
        responsible_id = order.responsible_id
        await session.commit()

    if responsible_id:
        try:
            await bot.send_message(
                responsible_id,
                f"✅ Исполнитель <b>{user.full_name}</b> принял "
                f"задачу <b>#{order_id}</b>.",
            )
        except Exception:
            pass

    await callback.answer("Принято", show_alert=True)
    await executor_view(callback, user)


@router.callback_query(F.data.startswith("srv:ex:decline:"))
async def executor_decline(callback: CallbackQuery, user: User, bot: Bot):
    order_id = int(callback.data.split(":")[3])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await callback.answer("Задача не найдена", show_alert=True)
            return
        session.add(
            OrderResponse(order_id=order_id, user_id=user.id, response="declined")
        )
        order.executor_id = None  # снимаем исполнителя
        responsible_id = order.responsible_id
        await session.commit()

    if responsible_id:
        try:
            await bot.send_message(
                responsible_id,
                f"❌ Исполнитель <b>{user.full_name}</b> отклонил "
                f"задачу <b>#{order_id}</b>.\n"
                f"Назначьте другого исполнителя.",
            )
        except Exception:
            pass

    await callback.answer("Отклонено", show_alert=True)
    await executor_view(callback, user)