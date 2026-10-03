from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from config import SUPERADMIN_IDS
from models.user import User

router = Router()


@router.message(F.text == "❓ Вопросы по сервису")
async def cmd_help(message: Message, user: User):
    """FAQ + связь с администратором."""
    text = (
        "❓ <b>Вопросы по сервису</b>\n\n"
        "Здесь вы найдёте ответы на частые вопросы и сможете "
        "связаться с администратором.\n\n"
        "📖 <b>FAQ (скоро):</b>\n"
        "• Как оставить заявку на услугу?\n"
        "• Как пополнить баланс?\n"
        "• Как посмотреть мои чеки?\n"
        "• Что делать при аварийной ситуации?\n\n"
        "💬 <b>Связаться с администратором:</b>\n"
        "Если у вас возник вопрос по работе бота — напишите администратору напрямую."
    )

    # Кнопка связи с админом (первый из списка SUPERADMIN_IDS)
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    kb_rows = []
    if SUPERADMIN_IDS:
        admin_id = SUPERADMIN_IDS[0]
        kb_rows.append([
            InlineKeyboardButton(
                text="💬 Написать администратору",
                url=f"tg://user?id={admin_id}",
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows) if kb_rows else None

    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "help:faq")
async def help_faq(callback: CallbackQuery):
    """Заглушка для FAQ."""
    await callback.message.answer(
        "📖 Раздел FAQ в разработке. Скоро здесь появятся ответы на частые вопросы."
    )
    await callback.answer()