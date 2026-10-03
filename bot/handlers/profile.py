from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database import async_session
from keyboards.profile import (
    back_to_profile_kb,
    balance_menu_kb,
    profile_data_kb,
    profile_menu_kb,
)
from models.profile import Profile
from models.user import User
from services.project_service import get_user_projects

router = Router()


class ProfileEdit(StatesGroup):
    waiting_value = State()


# --- Утилиты ---
async def get_profile(session, user_id: int) -> Profile:
    """Получить или создать профиль пользователя."""
    result = await session.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user_id)
        session.add(profile)
        await session.commit()
    return profile


async def user_has_project(user_id: int) -> bool:
    """Проверить, есть ли у пользователя хотя бы один проект."""
    async with async_session() as session:
        projects = await get_user_projects(session, user_id)
    return len(projects) > 0


# --- Главное меню профиля ---
@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль")
async def cmd_profile(message: Message, user: User):
    has_project = await user_has_project(user.id)
    await message.answer(
        "👤 <b>Профиль</b>\n\nВыберите раздел:",
        reply_markup=profile_menu_kb(has_project=has_project),
    )


@router.callback_query(F.data == "profile:menu")
async def profile_menu(callback: CallbackQuery, user: User):
    has_project = await user_has_project(user.id)
    await callback.message.edit_text(
        "👤 <b>Профиль</b>\n\nВыберите раздел:",
        reply_markup=profile_menu_kb(has_project=has_project),
    )
    await callback.answer()


# --- Раздел «Ваши данные» ---
@router.callback_query(F.data == "profile:data")
async def profile_data(callback: CallbackQuery, user: User):
    async with async_session() as session:
        profile = await get_profile(session, user.id)

    text = (
        "📄 <b>Ваши данные</b>\n\n"
        f"<b>ФИО:</b> {profile.full_name or '—'}\n"
        f"<b>Адрес объекта:</b> {profile.address or '—'}\n"
        f"<b>Банк:</b> {profile.bank_name or '—'}\n"
        f"<b>ИП счёт:</b> {profile.ip_account or '—'}\n"
        f"<b>Телефон:</b> {profile.phone or '—'}\n\n"
        f"Выберите поле для редактирования:"
    )
    await callback.message.edit_text(text, reply_markup=profile_data_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("profile:edit:"))
async def profile_edit_start(callback: CallbackQuery, state: FSMContext, user: User):
    field = callback.data.split(":")[2]
    labels = {
        "full_name": "ФИО",
        "address": "адрес объекта",
        "bank": "название банка",
        "ip_account": "ИП расчётный счёт",
        "phone": "номер телефона",
    }
    await state.update_data(field=field)
    await state.set_state(ProfileEdit.waiting_value)
    await callback.message.answer(f"Введите новое значение для «{labels[field]}»:")
    await callback.answer()


@router.message(ProfileEdit.waiting_value)
async def profile_edit_save(message: Message, state: FSMContext, user: User):
    data = await state.get_data()
    field = data["field"]
    value = message.text.strip()

    field_map = {
        "full_name": "full_name",
        "address": "address",
        "bank": "bank_name",
        "ip_account": "ip_account",
        "phone": "phone",
    }

    async with async_session() as session:
        profile = await get_profile(session, user.id)
        setattr(profile, field_map[field], value)
        await session.commit()

    await state.clear()

    # Возвращаемся в раздел «Ваши данные» — показываем обновлённые данные
    async with async_session() as session:
        profile = await get_profile(session, user.id)

    text = (
        "📄 <b>Ваши данные</b>\n\n"
        f"<b>ФИО:</b> {profile.full_name or '—'}\n"
        f"<b>Адрес объекта:</b> {profile.address or '—'}\n"
        f"<b>Банк:</b> {profile.bank_name or '—'}\n"
        f"<b>ИП счёт:</b> {profile.ip_account or '—'}\n"
        f"<b>Телефон:</b> {profile.phone or '—'}\n\n"
        f"✅ Изменения сохранены."
    )
    await message.answer(text, reply_markup=profile_data_kb())


# --- Раздел «Баланс» ---
@router.callback_query(F.data == "profile:balance")
async def profile_balance(callback: CallbackQuery, user: User):
    # Заглушка. Позже здесь будет реальный баланс из Wallet.
    text = (
        "💰 <b>Баланс</b>\n\n"
        "Ваш текущий баланс: <b>0 ₽</b>\n\n"
        "Здесь вы сможете пополнять кошелёк, "
        "оплачивать услуги и просматривать чеки."
    )
    await callback.message.edit_text(text, reply_markup=balance_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "balance:topup")
async def balance_topup(callback: CallbackQuery, user: User):
    """Заглушка — пополнение баланса."""
    await callback.message.edit_text(
        "💳 <b>Пополнение баланса</b>\n\n"
        "Здесь вы сможете сделать перевод средств на внутренний "
        "виртуальный кошелёк нашей системы.",
        reply_markup=back_to_profile_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "balance:receipts")
async def balance_receipts(callback: CallbackQuery, user: User):
    """Заглушка — чеки."""
    await callback.message.edit_text(
        "🧾 <b>Чеки</b>\n\n"
        "Здесь будут храниться все чеки по операциям оплаты:\n\n"
        "• чеки, которые вы прикладываете при оплате услуг,\n"
        "• чеки от компании после получения оплаты.",
        reply_markup=back_to_profile_kb(),
    )
    await callback.answer()


# --- Раздел «Моя стройка» ---
@router.callback_query(F.data == "profile:project")
async def profile_project(callback: CallbackQuery, user: User):
    """Заглушка — Моя стройка."""
    has_project = await user_has_project(user.id)
    if not has_project:
        await callback.answer("У вас пока нет проекта", show_alert=True)
        return

    await callback.message.edit_text(
        "🏗️ <b>Моя стройка</b>\n\n"
        "Здесь будет большой раздел, позволяющий отследить "
        "текущие процессы строительства и менеджмент средств, "
        "задач и сроков.",
        reply_markup=back_to_profile_kb(),
    )
    await callback.answer()