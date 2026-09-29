# bot/models/staff.py

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    user = relationship("User", backref="staff_roles")
    project = relationship("Project", backref="staff_assignments")

    def __repr__(self) -> str:
        return f"<StaffRole user={self.user_id} kind={self.kind} scope={self.scope}>"


class StaffNotification(Base):
    """Уведомления для сотрудников о новых заказах и изменениях статуса"""
    __tablename__ = "staff_notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )

    # new_order / status_changed / needs_review / completion
    notification_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # read / unread
    status: Mapped[str] = mapped_column(String(16), default="unread", nullable=False)

    message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", backref="notifications")
    order = relationship("Order", backref="notifications")

    def __repr__(self) -> str:
        return f"<StaffNotification user={self.user_id} order={self.order_id} type={self.notification_type}>"


class OrderReview(Base):
    """Отзыв менеджера на выполнение заказа"""
    __tablename__ = "order_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )

    manager_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # approved / needs_revision / rejected
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Если нужна доработка - новый срок
    new_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    suggested_solution: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order = relationship("Order", backref="reviews")
    manager = relationship("User", backref="given_reviews")

    def __repr__(self) -> str:
        return f"<OrderReview order={self.order_id} status={self.status}>"
