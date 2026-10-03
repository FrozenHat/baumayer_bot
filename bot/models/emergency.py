from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Emergency(Base):
    __tablename__ = "emergencies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Кто создал
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Кто взял в работу (ответственный)
    responsible_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Привязка к проекту (опционально)
    project_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )

    # Описание — свободная форма
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Геолокация (опционально, заполним позже)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)

    # new / in_progress / resolved
    status: Mapped[str] = mapped_column(String(16), default="new", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    media = relationship(
        "EmergencyMedia",
        back_populates="emergency",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class EmergencyMedia(Base):
    __tablename__ = "emergency_media"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    emergency_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("emergencies.id", ondelete="CASCADE"), nullable=False
    )

    # photo / video
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    emergency = relationship("Emergency", back_populates="media")