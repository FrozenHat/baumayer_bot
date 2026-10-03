from aiogram import F, Router
from aiogram.types import Message

from models.user import User

router = Router()


@router.message(F.text == "🚨 Аварийка")
async def cmd_emergency(message: Message, user: User):
    """Заглушка раздела «Аварийка». Полноценно — на Этапе 7."""
    await message.answer(
        "🚨 <b>Аварийка</b>\n\n"
        "Раздел в разработке.\n\n"
        "Скоро здесь можно будет подать заявление об аварийной ситуации — "
        "с описанием, фото и геолокацией. Все ответственные за аварийку "
        "получат уведомление немедленно."
    )