from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.wallet import Transaction, Wallet


async def get_or_create_wallet(
    session: AsyncSession, owner_type: str, owner_id: int
) -> Wallet:
    """Получить кошелёк или создать его."""
    result = await session.execute(
        select(Wallet).where(
            Wallet.owner_type == owner_type,
            Wallet.owner_id == owner_id,
        )
    )
    wallet = result.scalar_one_or_none()

    if wallet is None:
        wallet = Wallet(owner_type=owner_type, owner_id=owner_id)
        session.add(wallet)
        await session.flush()

    return wallet


async def add_transaction(
    session: AsyncSession,
    wallet: Wallet,
    type_: str,
    amount: Decimal,
    description: str | None = None,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
) -> Transaction:
    """Добавить транзакцию и обновить баланс."""
    transaction = Transaction(
        wallet_id=wallet.id,
        type=type_,
        amount=amount,
        description=description,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    session.add(transaction)

    if type_ == "deposit":
        wallet.balance += amount
    elif type_ == "withdrawal":
        wallet.balance -= amount
    elif type_ == "freeze":
        wallet.balance -= amount
        wallet.frozen += amount
    elif type_ == "unfreeze":
        wallet.frozen -= amount
        wallet.balance += amount

    await session.flush()
    return transaction