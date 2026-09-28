from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy import select

from config import SUPERADMIN_IDS
from database import async_session
from models.user import User


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")

        if tg_user is not None and not tg_user.is_bot:
            async with async_session() as session:
                result = await session.execute(
                    select(User).where(User.id == tg_user.id)
                )
                user = result.scalar_one_or_none()

                if user is None:
                    # Первый раз — создаём
                    # Если это супер-админ из .env — сразу admin
                    initial_role = (
                        "admin" if tg_user.id in SUPERADMIN_IDS else "pending"
                    )
                    user = User(
                        id=tg_user.id,
                        username=tg_user.username,
                        full_name=tg_user.full_name,
                        role=initial_role,
                        status="active",
                    )
                    session.add(user)
                else:
                    # Обновляем данные
                    user.username = tg_user.username
                    user.full_name = tg_user.full_name
                    user.last_seen_at = datetime.now(timezone.utc)

                    # Если ID в SUPERADMIN_IDS, но роль ещё не admin — повышаем
                    if tg_user.id in SUPERADMIN_IDS and user.role != "admin":
                        user.role = "admin"

                await session.commit()
                data["user"] = user

        return await handler(event, data)