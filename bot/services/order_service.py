from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from models.order import Order, OrderResponse, OrderCompletion, OrderReceipt, OrderPhoto
from models.staff import OrderReview


async def get_user_orders(
    session: AsyncSession,
    user_id: int,
    statuses: list[str] | None = None,
) -> list[Order]:
    """Заявки, созданные пользователем (клиентом)."""
    query = select(Order).where(Order.customer_id == user_id)
    if statuses:
        query = query.where(Order.status.in_(statuses))
    query = query.order_by(Order.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_orders_for_manager(
    session: AsyncSession,
    manager_id: int,
    scope: str | None = None,
    statuses: list[str] | None = None,
) -> list[Order]:
    """Все заявки, за которые отвечает менеджер."""
    from models.staff import StaffRole
    
    query = select(Order).join(
        StaffRole, StaffRole.user_id == manager_id
    ).where(
        StaffRole.kind == "manager",
        StaffRole.scope == scope if scope else True,
    )
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


async def get_executor_active_orders(
    session: AsyncSession,
    user_id: int,
) -> list[Order]:
    """Все активные заказы исполнителя (в работе и на проверке)."""
    query = select(Order).where(
        Order.executor_id == user_id,
        Order.status.in_(["in_progress", "pending_review"]),
    ).order_by(Order.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_executor_completed_orders(
    session: AsyncSession,
    user_id: int,
) -> list[Order]:
    """Все завершённые заказы исполнителя."""
    query = select(Order).where(
        Order.executor_id == user_id,
        Order.status == "done",
    ).order_by(Order.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_my_responses(session: AsyncSession, user_id: int) -> list[OrderResponse]:
    """Получить все отклики пользователя на заказы."""
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
    description: str | None = None,
    address: str | None = None,
    price: float | None = None,
    deadline: datetime | None = None,
    project_id: int | None = None,
) -> Order:
    """Создать новый заказ."""
    order = Order(
        customer_id=customer_id,
        category=category,
        title=title,
        description=description,
        address=address,
        price=price,
        deadline=deadline,
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
    """Создать отклик исполнителя на заказ."""
    r = OrderResponse(
        order_id=order_id, user_id=user_id, response=response, comment=comment
    )
    session.add(r)
    await session.flush()
    return r


async def accept_order_by_executor(
    session: AsyncSession,
    order_id: int,
    executor_id: int,
) -> Order:
    """Исполнитель принимает заказ (переводит статус в in_progress)."""
    order = await session.get(Order, order_id)
    if order:
        order.executor_id = executor_id
        order.status = "in_progress"
        order.start_date = datetime.now()
        await session.flush()
    return order


async def submit_completion(
    session: AsyncSession,
    order_id: int,
    executor_id: int,
    notes: str | None = None,
) -> OrderCompletion:
    """Исполнитель отправляет отчёт о выполнении."""
    order = await session.get(Order, order_id)
    if order:
        order.status = "pending_review"
        await session.flush()
    
    completion = OrderCompletion(
        order_id=order_id,
        executor_id=executor_id,
        status="submitted",
        notes=notes,
    )
    session.add(completion)
    await session.flush()
    return completion


async def approve_completion(
    session: AsyncSession,
    order_id: int,
    manager_id: int,
) -> Order:
    """Менеджер одобрил выполнение и закрыл заказ."""
    order = await session.get(Order, order_id)
    if order:
        order.status = "done"
        order.responsible_id = manager_id
        order.end_date = datetime.now()
        await session.flush()
    
    # Обновляем статус отчёта
    completion = await session.execute(
        select(OrderCompletion).where(OrderCompletion.order_id == order_id)
    )
    comp = completion.scalar_one_or_none()
    if comp:
        comp.status = "approved"
        comp.reviewed_at = datetime.now()
        await session.flush()
    
    return order


async def reject_completion(
    session: AsyncSession,
    order_id: int,
    manager_id: int,
    comment: str | None = None,
    suggested_solution: str | None = None,
    new_deadline: datetime | None = None,
) -> OrderReview:
    """Менеджер отклонил выполнение и требует доработки."""
    order = await session.get(Order, order_id)
    if order:
        order.status = "needs_revision"
        await session.flush()
    
    review = OrderReview(
        order_id=order_id,
        manager_id=manager_id,
        status="needs_revision",
        comment=comment,
        suggested_solution=suggested_solution,
        new_deadline=new_deadline,
    )
    session.add(review)
    await session.flush()
    return review


async def add_receipt(
    session: AsyncSession,
    order_id: int,
    file_url: str,
    amount: float | None = None,
    receipt_type: str = "sent",
    uploaded_by: int | None = None,
) -> OrderReceipt:
    """Добавить чек или документ к заказу."""
    receipt = OrderReceipt(
        order_id=order_id,
        file_url=file_url,
        amount=amount,
        type=receipt_type,
        uploaded_by=uploaded_by,
    )
    session.add(receipt)
    await session.flush()
    return receipt


async def add_photo(
    session: AsyncSession,
    order_id: int,
    file_url: str,
    uploaded_by: int | None = None,
) -> OrderPhoto:
    """Добавить фото к заказу."""
    photo = OrderPhoto(
        order_id=order_id,
        file_url=file_url,
        uploaded_by=uploaded_by,
    )
    session.add(photo)
    await session.flush()
    return photo


async def get_order_details(session: AsyncSession, order_id: int) -> Order | None:
    """Получить полные данные заказа со всеми отношениями."""
    result = await session.execute(
        select(Order).where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def update_order_status(
    session: AsyncSession,
    order_id: int,
    new_status: str,
    responsible_id: int | None = None,
) -> Order | None:
    """Обновить статус заказа."""
    order = await session.get(Order, order_id)
    if order:
        order.status = new_status
        if responsible_id:
            order.responsible_id = responsible_id
        await session.flush()
    return order
