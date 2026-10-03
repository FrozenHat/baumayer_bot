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

    # Кто исполняет (назначается менеджером)
    executor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Кто менеджер, ведущий заявку (тот, кто первый откликнулся)
    responsible_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Категория: delivery / loaders / laborers / material / other / turnkey
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="other")

    # Краткое «название» — первые 60 символов описания
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # Полное описание от клиента
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Устаревшее поле цены (оставляем для совместимости)
    price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    # --- Поля, заполняемые менеджером ---
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    special_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    executor_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Даты
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # new / in_progress / done / rejected / cancelled / disputed
    status: Mapped[str] = mapped_column(String(16), default="new", nullable=False)

    # Привязка к проекту (опционально)
    project_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    photos = relationship(
        "OrderPhoto", back_populates="order", cascade="all, delete-orphan"
    )
    receipts = relationship(
        "OrderReceipt", back_populates="order", cascade="all, delete-orphan"
    )


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


class OrderResponse(Base):
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