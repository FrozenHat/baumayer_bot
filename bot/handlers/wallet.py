from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from database import async_session
from models.user import User
from services.wallet_service import add_transaction, get_or_create_wallet

router = Router()


@router.message(F.text == "💰 Баланс")
async def cmd_wallet(message: Message, user: User):
    async with async_session() as session:
        wallet = await get_or_create_wallet(session, "user", user.id)
        await session.commit()
        balance = wallet.balance

    await message.answer(
        f"<b>💰 Ваш кошелёк</b>\n\n"
        f"Баланс: <b>{balance} ₽</b>\n\n"
        f"Нажмите «Запросить выплату», чтобы отправить запрос шефу."
    )


@router.message(F.text == "📥 Запросить выплату")
async def request_payout(message: Message, user: User):
    await message.answer(
        "💸 Запрос на выплату отправлен. Шеф увидит его и подтвердит."
    )
    # Здесь позже: уведомление шефу