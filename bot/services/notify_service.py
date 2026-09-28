import logging

from aiogram import Bot

from models.user import User

logger = logging.getLogger(__name__)


async def notify_users(
    bot: Bot,
    users: list[User],
    text: str,
) -> int:
    """Отправить сообщение списку пользователей. Возвращает кол-во успешных."""
    sent = 0
    for u in users:
        try:
            await bot.send_message(u.id, text)
            sent += 1
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение {u.id}: {e}")
    return sent