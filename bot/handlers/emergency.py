import asyncio
import logging
from datetime import datetime, timezone

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
from models.emergency import Emergency
from models.profile import Profile
from models.staff import StaffRole
from models.user import User
from services.staff_service import get_all_managers

logger = logging.getLogger(__name__)
router = Router()

# Через сколько минут эскалировать (для теста можно уменьшить до 0.5)
ESCALATION_MINUTES = 5

STATUS_LABELS = {
    "new": "🆕 Новая",
    "in_progress": "⚡ В работе",
    "resolved": "✅ Решена",
}


class EmergencyCreate(StatesGroup):
    waiting_description = State()


# =========================================================
# ПРОВЕРКА РОЛИ
# =========================================================

async def is_emergency_manager(session, user_id: int, role: str) -> bool:
    if role == "admin":
        return True
    result = await session.execute(
        select(StaffRole).where(
            StaffRole.user_id == user_id,
            StaffRole.kind == "manager",
            StaffRole.scope == "emergency",
        )
    )
    return result.scalar_one_or_none() is not None


# =========================================================
# МЕНЮ АВАРИЙКИ
# =========================================================

def emergency_menu_kb(is_manager: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text="🚨 Подать заявку",
            callback_data="emerg:create",
        )],
    ]
    if is_manager:
        buttons.append([InlineKeyboardButton(
            text="📥 Активные заявки",
            callback_data="emerg:list:active",
        )])
        buttons.append([InlineKeyboardButton(
            text="✅ Решённые",
            callback_data="emerg:list:resolved",
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("emergency"))
@router.message(F.text == "🚨 Аварийка")
async def cmd_emergency(message: Message, user: User):
    async with async_session() as session:
        mgr = await is_emergency_manager(session, user.id, user.role)

    await message.answer(
        "🚨 <b>Аварийка</b>\n\n"
        "Здесь можно подать заявление об аварийной ситуации. "
        "Все ответственные получат уведомление немедленно.\n\n"
        "Выберите действие:",
        reply_markup=emergency_menu_kb(is_manager=mgr),
    )


@router.callback_query(F.data == "emerg:menu")
async def emergency_back_to_menu(callback: CallbackQuery, user: User):
    async with async_session() as session:
        mgr = await is_emergency_manager(session, user.id, user.role)
    await callback.message.edit_text(
        "🚨 <b>Аварийка</b>\n\nВыберите действие:",
        reply_markup=emergency_menu_kb(is_manager=mgr),
    )
    await callback.answer()


# =========================================================
# ПОДАЧА ЗАЯВКИ
# =========================================================

@router.callback_query(F.data == "emerg:create")
async def emergency_create_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EmergencyCreate.waiting_description)
    await callback.message.edit_text(
        "🚨 <b>Подача аварийной заявки</b>\n\n"
        "Опишите ситуацию в свободной форме — что случилось, где, "
        "насколько срочно. Все ответственные получат уведомление "
        "немедленно.\n\n"
        f"Если через {ESCALATION_MINUTES} минут никто не отреагирует, "
        "мы пришлём вам телефон для прямой связи."
    )
    await callback.answer()


@router.message(EmergencyCreate.waiting_description)
async def emergency_description(
    message: Message, state: FSMContext, user: User, bot: Bot
):
    description = message.text.strip()
    if len(description) < 5:
        await message.answer("Опишите ситуацию подробнее.")
        return

    async with async_session() as session:
        emergency = Emergency(
            created_by=user.id,
            description=description,
            status="new",
        )
        session.add(emergency)
        await session.flush()
        emergency_id = emergency.id
        managers = await get_all_managers(session, "emergency")
        await session.commit()

    await state.clear()

    # Уведомляем всех ответственных за аварийку
    if managers:
        text = (
            f"🚨 <b>АВАРИЙНАЯ ЗАЯВКА #{emergency_id}</b>\n\n"
            f"От: <b>{user.full_name}</b>\n\n"
            f"{description}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="⚡ Взять в работу",
                    callback_data=f"emerg:accept:{emergency_id}",
                )],
            ]
        )
        for mgr in managers:
            try:
                await bot.send_message(mgr.id, text, reply_markup=kb)
            except Exception as e:
                logger.warning(f"Не удалось отправить аварийку {mgr.id}: {e}")

    await message.answer(
        f"✅ <b>Заявка #{emergency_id} принята.</b>\n\n"
        f"Все ответственные оповещены. Если через "
        f"{ESCALATION_MINUTES} минут никто не отреагирует, "
        f"мы пришлём вам телефон для прямой связи."
    )

    asyncio.create_task(_escalate_if_no_response(bot, emergency_id, user.id))


# =========================================================
# СПИСКИ ДЛЯ МЕНЕДЖЕРА
# =========================================================

@router.callback_query(F.data.startswith("emerg:list:"))
async def emergency_list(callback: CallbackQuery, user: User):
    async with async_session() as session:
        mgr = await is_emergency_manager(session, user.id, user.role)
        if not mgr:
            await callback.answer("Нет доступа", show_alert=True)
            return

        kind = callback.data.split(":")[2]
        if kind == "active":
            statuses = ["new", "in_progress"]
            title = "📥 <b>Активные заявки</b>"
        else:
            statuses = ["resolved"]
            title = "✅ <b>Решённые заявки</b>"

        result = await session.execute(
            select(Emergency)
            .where(Emergency.status.in_(statuses))
            .order_by(Emergency.created_at.desc())
            .limit(50)
        )
        emergencies = list(result.scalars().all())

    if not emergencies:
        await callback.message.edit_text(
            f"{title}\n\nПока ничего нет.",
            reply_markup=emergency_menu_kb(is_manager=True),
        )
        await callback.answer()
        return

    buttons = [
        [InlineKeyboardButton(
            text=f"#{e.id} • {STATUS_LABELS.get(e.status, e.status)} • "
                 f"{e.description[:30]}…",
            callback_data=f"emerg:view:{e.id}",
        )]
        for e in emergencies
    ]
    buttons.append([InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="emerg:menu",
    )])

    await callback.message.edit_text(
        f"{title} ({len(emergencies)}):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


# =========================================================
# КАРТОЧКА ЗАЯВКИ ДЛЯ МЕНЕДЖЕРА
# =========================================================

def emergency_card_kb(emergency) -> InlineKeyboardMarkup:
    buttons = []

    if emergency.status == "new":
        buttons.append([InlineKeyboardButton(
            text="⚡ Взять в работу",
            callback_data=f"emerg:accept:{emergency.id}",
        )])
    elif emergency.status == "in_progress":
        buttons.append([InlineKeyboardButton(
            text="🏁 Отметить решённой",
            callback_data=f"emerg:resolve:{emergency.id}",
        )])

    buttons.append([InlineKeyboardButton(
        text="⬅️ К списку",
        callback_data="emerg:list:active",
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _render_emergency_card(
    callback: CallbackQuery, user: User, emergency_id: int
):
    async with async_session() as session:
        emergency = await session.get(Emergency, emergency_id)
        if emergency is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        customer = (
            await session.get(User, emergency.created_by)
            if emergency.created_by
            else None
        )
        responsible = (
            await session.get(User, emergency.responsible_id)
            if emergency.responsible_id
            else None
        )
        customer_profile = (
            await session.get(Profile, emergency.created_by)
            if emergency.created_by
            else None
        )

    text = (
        f"🚨 <b>Заявка #{emergency.id}</b>\n\n"
        f"<b>Статус:</b> {STATUS_LABELS.get(emergency.status, emergency.status)}\n"
        f"<b>От:</b> {customer.full_name if customer else '—'}\n"
        f"<b>Телефон:</b> {customer_profile.phone if customer_profile and customer_profile.phone else '—'}\n"
        f"<b>Создана:</b> {emergency.created_at:%d.%m.%Y %H:%M}\n"
    )
    if responsible:
        text += f"<b>Ответственный:</b> {responsible.full_name}\n"
    if emergency.responded_at:
        text += f"<b>Взята в работу:</b> {emergency.responded_at:%d.%m.%Y %H:%M}\n"
    if emergency.resolved_at:
        text += f"<b>Решена:</b> {emergency.resolved_at:%d.%m.%Y %H:%M}\n"

    text += f"\n<b>Описание:</b>\n{emergency.description}"

    await callback.message.edit_text(
        text, reply_markup=emergency_card_kb(emergency)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("emerg:view:"))
async def emergency_view(callback: CallbackQuery, user: User):
    emergency_id = int(callback.data.split(":")[2])
    await _render_emergency_card(callback, user, emergency_id)


# =========================================================
# ДЕЙСТВИЯ ОТВЕТСТВЕННОГО
# =========================================================

@router.callback_query(F.data.startswith("emerg:accept:"))
async def emergency_accept(callback: CallbackQuery, user: User, bot: Bot):
    emergency_id = int(callback.data.split(":")[2])

    async with async_session() as session:
        emergency = await session.get(Emergency, emergency_id)
        if emergency is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        if emergency.status != "new":
            await callback.answer(
                "Заявку уже кто-то взял", show_alert=True
            )
            return

        emergency.status = "in_progress"
        emergency.responsible_id = user.id
        emergency.responded_at = datetime.now(timezone.utc)
        customer_id = emergency.created_by
        await session.commit()

    if customer_id:
        try:
            await bot.send_message(
                customer_id,
                f"⚡ <b>Ваша аварийная заявка #{emergency_id} "
                f"принята в работу.</b>\n\n"
                f"Ответственный: <b>{user.full_name}</b>",
            )
        except Exception:
            pass

    await callback.answer("Взято в работу", show_alert=True)
    await _render_emergency_card(callback, user, emergency_id)


@router.callback_query(F.data.startswith("emerg:resolve:"))
async def emergency_resolve(callback: CallbackQuery, user: User, bot: Bot):
    emergency_id = int(callback.data.split(":")[2])

    async with async_session() as session:
        emergency = await session.get(Emergency, emergency_id)
        if emergency is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        emergency.status = "resolved"
        emergency.resolved_at = datetime.now(timezone.utc)
        customer_id = emergency.created_by
        await session.commit()

    if customer_id:
        try:
            await bot.send_message(
                customer_id,
                f"🏁 <b>Аварийная заявка #{emergency_id} решена.</b>",
            )
        except Exception:
            pass

    await callback.answer("Решено", show_alert=True)
    await _render_emergency_card(callback, user, emergency_id)


# =========================================================
# ЭСКАЛАЦИЯ
# =========================================================

async def _escalate_if_no_response(bot: Bot, emergency_id: int, customer_id: int):
    await asyncio.sleep(ESCALATION_MINUTES * 60)

    async with async_session() as session:
        emergency = await session.get(Emergency, emergency_id)
        if emergency is None or emergency.status != "new":
            return

        managers = await get_all_managers(session, "emergency")
        phone = None
        for mgr in managers:
            profile = await session.get(Profile, mgr.id)
            if profile and profile.phone:
                phone = profile.phone
                break

    if phone:
        text = (
            f"⏰ <b>Аварийная заявка #{emergency_id}</b>\n\n"
            f"К сожалению, никто из ответственных пока не отреагировал.\n\n"
            f"📞 <b>Позвоните напрямую:</b>\n<code>{phone}</code>\n\n"
            f"Нажмите на номер, чтобы скопировать."
        )
    else:
        text = (
            f"⏰ <b>Аварийная заявка #{emergency_id}</b>\n\n"
            f"Пока никто не отреагировал. Телефон ответственного "
            f"не указан в системе — свяжитесь с администратором."
        )

    try:
        await bot.send_message(customer_id, text)
    except Exception as e:
        logger.warning(f"Не удалось отправить эскалацию клиенту {customer_id}: {e}")