from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database import async_session
from keyboards.services import (
    SERVICES_CATEGORIES,
    after_order_kb,
    back_to_services_kb,
    services_categories_kb,
    services_list_kb,
    services_menu_kb,
)
from models.order import Order
from models.profile import Profile
from models.user import User
from services.notify_service import notify_users
from services.staff_service import get_all_managers

router = Router()


class ServiceCreate(StatesGroup):
    waiting_category = State()
    waiting_description = State()


class ServiceLeavePhone(StatesGroup):
    waiting_phone = State()


# --- Главное меню «Услуги» ---
@router.message(Command("services"))
@router.message(F.text == "🛠️ Услуги")
async def cmd_services(message: Message, user: User):
    await message.answer(
        "🛠️ <b>Услуги</b>\n\nВыберите действие:",
        reply_markup=services_menu_kb(),
    )


@router.callback_query(F.data == "srv:menu")
async def back_to_services(callback: CallbackQuery, user: User):
    await callback.message.edit_text(
        "🛠️ <b>Услуги</b>\n\nВыберите действие:",
        reply_markup=services_menu_kb(),
    )
    await callback.answer()


# --- Инструкция ---
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


# --- Выбор услуги ---
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
async def services_description(message: Message, state: FSMContext, user: User, bot: Bot):
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


# --- Оставить номер для звонка ---
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
async def leave_phone_save(message: Message, state: FSMContext, user: User, bot: Bot):
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

        # Уведомляем менеджеров
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

    await message.answer(
        "✅ Спасибо! Менеджер свяжется с вами в ближайшее время.",
    )


# --- Мои услуги ---
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

    status_labels = {
        "new": "🆕 Новая",
        "in_progress": "⚙️ В работе",
        "done": "✅ Выполнена",
        "rejected": "❌ Отклонена",
        "cancelled": "🚫 Отменена",
        "disputed": "⚖️ Спор",
    }

    text = (
        f"📋 <b>Заявка #{order.id}</b>\n\n"
        f"<b>Категория:</b> {SERVICES_CATEGORIES.get(order.category, order.category)}\n"
        f"<b>Статус:</b> {status_labels.get(order.status, order.status)}\n\n"
        f"<b>Описание:</b>\n{order.description or '—'}"
    )
    await callback.message.edit_text(text, reply_markup=back_to_services_kb())
    await callback.answer()