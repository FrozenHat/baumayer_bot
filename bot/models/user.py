from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class User(Base):
    __tablename__ = "users"

    # Telegram ID — первичный ключ
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)

    # Основные поля
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Роль: admin, foreman, engineer, worker и т.д.
    role: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)

    # Статус: active, blocked
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)

    # Когда зарегистрировался и когда последний раз писал
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} role={self.role}>"