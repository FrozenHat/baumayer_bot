from aiogram import F, Router
from aiogram.types import Message

from models.user import User

router = Router()


@router.message(F.text == "🛠️ Услуги")
async def cmd_services(message: Message, user: User):
    """Заглушка раздела «Услуги». Полноценно — на следующем этапе."""
    await message.answer(
        "🛠️ <b>Услуги</b>\n\n"
        "Раздел в разработке.\n\n"
        "Скоро здесь появится возможность заказать доставку, "
        "грузчиков, разнорабочих, оставить заявку на материал "
        "или ремонт под ключ."
    )