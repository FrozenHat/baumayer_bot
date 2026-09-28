from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database import async_session
from keyboards.profile import profile_kb
from models.profile import Profile
from models.user import User

router = Router()


class ProfileEdit(StatesGroup):
    waiting_value = State()


async def get_profile(session, user_id: int) -> Profile:
    result = await session.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user_id)
        session.add(profile)
        await session.commit()
    return profile


@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль")
async def cmd_profile(message: Message, user: User):
    async with async_session() as session:
        profile = await get_profile(session, user.id)

    text = (
        f"<b>👤 Профиль</b>\n\n"
        f"<b>ФИО:</b> {profile.full_name or '—'}\n"
        f"<b>Адрес объекта:</b> {profile.address or '—'}\n"
        f"<b>Банк:</b> {profile.bank_name or '—'}\n"
        f"<b>ИП счёт:</b> {profile.ip_account or '—'}\n\n"
        f"Выберите поле для редактирования:"
    )
    await message.answer(text, reply_markup=profile_kb())


@router.callback_query(F.data.startswith("profile:edit:"))
async def profile_edit_start(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[2]
    labels = {
        "full_name": "ФИО",
        "address": "адрес объекта",
        "bank": "название банка",
        "ip_account": "ИП расчётный счёт",
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
    }

    async with async_session() as session:
        profile = await get_profile(session, user.id)
        setattr(profile, field_map[field], value)
        await session.commit()

    await state.clear()
    await message.answer("✅ Сохранено. Откройте /profile снова, чтобы увидеть изменения.")