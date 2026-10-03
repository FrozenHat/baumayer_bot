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
from models.user import User
from services.notify_service import notify_users
from services.staff_service import get_all_managers

logger = logging.getLogger(__name__)
router = Router()

# Через сколько минут эскалировать (для теста можно уменьшить до 0.5)
ESCALATION_MINUTES = 5


class EmergencyCreate(StatesGroup):
    waiting_description = State()


# =========================================================
# МЕНЮ И ПОДАЧА
# =========================================================

@router.message(Command("emergency"))
@router.message(F.text == "🚨 Аварийка")
async def cmd_emergency(message: Message, state: FSMContext, user: User):
    await state.set_state(EmergencyCreate.waiting_description)
    await message.answer(
        "🚨 <b>Аварийка</b>\n\n"
        "Опишите ситуацию в свободной форме — что случилось, где, "
        "насколько срочно. Все ответственные за аварийку получат "
        "уведомление немедленно.\n\n"
        "Если через "
        f"{ESCALATION_MINUTES} минут никто не отреагирует, "
        "мы пришлём вам телефон для прямой связи."
    )


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

    # Запускаем таймер эскалации
    asyncio.create_task(
        _escalate_if_no_response(bot, emergency_id, user.id)
    )


# =========================================================
# ЭСКАЛАЦИЯ
# =========================================================

async def _escalate_if_no_response(bot: Bot, emergency_id: int, customer_id: int):
    """Спит N минут. Если заявку не приняли — шлёт клиенту телефон ответственного."""
    await asyncio.sleep(ESCALATION_MINUTES * 60)

    async with async_session() as session:
        emergency = await session.get(Emergency, emergency_id)
        if emergency is None or emergency.status != "new":
            # Заявку уже кто-то взял или она удалена — ничего не делаем
            return

        # Ищем телефон любого ответственного за аварийку
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
                f"Заявку уже взял {emergency.status}", show_alert=True
            )
            return

        emergency.status = "in_progress"
        emergency.responsible_id = user.id
        emergency.responded_at = datetime.now(timezone.utc)
        customer_id = emergency.created_by
        await session.commit()

    # Уведомляем клиента
    if customer_id:
        try:
            await bot.send_message(
                customer_id,
                f"⚡ <b>Ваша аварийная заявка #{emergency_id} принята в работу.</b>\n\n"
                f"Ответственный: <b>{user.full_name}</b>",
            )
        except Exception:
            pass

    # Обновляем сообщение у ответственного — убираем кнопку
    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ <b>Вы взяли заявку в работу.</b>",
    )

    # Кнопка «Решено»
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🏁 Отметить решённой",
                callback_data=f"emerg:resolve:{emergency_id}",
            )],
        ]
    )
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("Взято в работу", show_alert=True)


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

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.edit_text(
        callback.message.text + f"\n\n🏁 <b>Заявка решена.</b>"
    )
    await callback.answer("Решено", show_alert=True)