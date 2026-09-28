from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.order import Order, OrderResponse


async def get_user_orders(
    session: AsyncSession,
    user_id: int,
    statuses: list[str] | None = None,
) -> list[Order]:
    """Заявки, созданные пользователем."""
    query = select(Order).where(Order.customer_id == user_id)
    if statuses:
        query = query.where(Order.status.in_(statuses))
    query = query.order_by(Order.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_orders_for_manager(
    session: AsyncSession,
    statuses: list[str] | None = None,
) -> list[Order]:
    """Все заявки в системе (для менеджера)."""
    query = select(Order)
    if statuses:
        query = query.where(Order.status.in_(statuses))
    query = query.order_by(Order.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_orders_for_executor(
    session: AsyncSession,
    user_id: int,
    scopes: list[str],
    statuses: list[str] | None = None,
) -> list[Order]:
    """Заявки, доступные исполнителю по его сферам, на которые он ещё не откликнулся."""
    scope_to_category = {
        "builder": "other",
        "foreman": "other",
        "laborer": "laborers",
        "buyer": "delivery",
    }
    categories = list({scope_to_category.get(s, "other") for s in scopes})

    subq = select(OrderResponse.order_id).where(OrderResponse.user_id == user_id)

    query = (
        select(Order)
        .where(
            Order.category.in_(categories),
            Order.status.in_(["new", "in_progress"]),
            Order.id.not_in(subq),
        )
        .order_by(Order.created_at.desc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_my_responses(session: AsyncSession, user_id: int) -> list[OrderResponse]:
    result = await session.execute(
        select(OrderResponse)
        .where(OrderResponse.user_id == user_id)
        .order_by(OrderResponse.created_at.desc())
    )
    return list(result.scalars().all())


async def create_order(
    session: AsyncSession,
    customer_id: int,
    category: str,
    title: str,
    description: str | None,
    project_id: int | None = None,
) -> Order:
    order = Order(
        customer_id=customer_id,
        category=category,
        title=title,
        description=description,
        project_id=project_id,
        status="new",
    )
    session.add(order)
    await session.flush()
    return order


async def create_response(
    session: AsyncSession,
    order_id: int,
    user_id: int,
    response: str,
    comment: str | None = None,
) -> OrderResponse:
    r = OrderResponse(
        order_id=order_id, user_id=user_id, response=response, comment=comment
    )
    session.add(r)
    await session.flush()
    return r