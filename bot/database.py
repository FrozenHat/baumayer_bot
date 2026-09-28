from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import DATABASE_URL


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


# Асинхронный движок
engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # Поставьте True, если хотите видеть все SQL-запросы
    pool_pre_ping=True,  # Проверка соединения перед использованием
)

# Фабрика сессий
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """Получить сессию для работы с БД (используется в зависимостях)."""
    async with async_session() as session:
        yield session


async def init_db():
    from models import (  # noqa: F401
        Order, OrderPhoto, OrderReceipt, OrderResponse,
        Profile, Project, ProjectMember,
        StaffRole, Transaction, User, Wallet,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)