# bot/models/staff.py

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class StaffRole(Base):
    """Роль сотрудника фирмы: менеджер или исполнитель.

    kind = 'manager'  → ответственный за этап (order / material / emergency)
    kind = 'executor' → исполнитель с одной или несколькими сферами
    """
    __tablename__ = "staff_roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # manager / executor
    kind: Mapped[str] = mapped_column(String(16), nullable=False)

    # Для manager: order / material / emergency
    # Для executor: builder / foreman / laborer / buyer
    scope: Mapped[str] = mapped_column(String(32), nullable=False)

    # Привязка к проекту (если NULL — глобально)
    project_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )