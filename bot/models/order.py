from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Кто создал заявку
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Кто исполняет (назначается ответственным)
    executor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Кто ответственный, кто обрабатывает заявку (менеджер)
    responsible_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Категория: delivery / loaders / laborers / other
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="other")

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # new / in_progress / pending_review / done / rejected / cancelled / disputed / needs_revision
    status: Mapped[str] = mapped_column(String(16), default="new", nullable=False)

    # Привязка к проекту (опционально)
    project_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )

    # Срок выполнения работ
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Отношения
    customer = relationship("User", foreign_keys=[customer_id], backref="created_orders")
    executor = relationship("User", foreign_keys=[executor_id], backref="executed_orders")
    responsible = relationship("User", foreign_keys=[responsible_id], backref="managed_orders")

    photos = relationship("OrderPhoto", back_populates="order", cascade="all, delete-orphan")
    receipts = relationship("OrderReceipt", back_populates="order", cascade="all, delete-orphan")
    responses = relationship("OrderResponse", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Order id={self.id} title={self.title} status={self.status}>"


class OrderPhoto(Base):
    __tablename__ = "order_photos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order = relationship("Order", back_populates="photos")

    def __repr__(self) -> str:
        return f"<OrderPhoto order={self.order_id} url={self.file_url[:30]}>"


class OrderResponse(Base):
    """Отклик исполнителя на заявку."""
    __tablename__ = "order_responses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # accepted / declined
    response: Mapped[str] = mapped_column(String(16), nullable=False)

    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order = relationship("Order", back_populates="responses")
    user = relationship("User", backref="order_responses")

    def __repr__(self) -> str:
        return f"<OrderResponse order={self.order_id} user={self.user_id} response={self.response}>"


class OrderReceipt(Base):
    __tablename__ = "order_receipts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    # sent / received
    type: Mapped[str] = mapped_column(String(16), default="sent", nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order = relationship("Order", back_populates="receipts")

    def __repr__(self) -> str:
        return f"<OrderReceipt order={self.order_id} type={self.type}>"


class OrderCompletion(Base):
    """Отчёт об выполнении заказа от сотрудника"""
    __tablename__ = "order_completions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )

    executor_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # submitted / under_review / approved / rejected / needs_revision
    status: Mapped[str] = mapped_column(String(16), default="submitted", nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", backref="completions")
    executor = relationship("User", backref="completion_reports")

    def __repr__(self) -> str:
        return f"<OrderCompletion order={self.order_id} status={self.status}>"
