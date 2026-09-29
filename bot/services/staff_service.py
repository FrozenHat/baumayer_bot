from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.staff import StaffRole, StaffNotification
from models.user import User
from models.order import Order


async def add_staff_role(
    session: AsyncSession,
    user_id: int,
    kind: str,
    scope: str,
    project_id: int | None = None,
) -> StaffRole:
    """Добавить роль сотруднику. Если уже есть — вернуть существующую."""
    result = await session.execute(
        select(StaffRole).where(
            StaffRole.user_id == user_id,
            StaffRole.kind == kind,
            StaffRole.scope == scope,
            StaffRole.project_id == project_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    role = StaffRole(
        user_id=user_id, kind=kind, scope=scope, project_id=project_id
    )
    session.add(role)
    await session.flush()
    return role


async def remove_staff_role(
    session: AsyncSession,
    user_id: int,
    kind: str,
    scope: str,
    project_id: int | None = None,
) -> bool:
    """Удалить роль сотрудника."""
    result = await session.execute(
        delete(StaffRole).where(
            StaffRole.user_id == user_id,
            StaffRole.kind == kind,
            StaffRole.scope == scope,
            StaffRole.project_id == project_id,
        )
    )
    return result.rowcount > 0


async def list_staff(
    session: AsyncSession,
    kind: str | None = None,
    scope: str | None = None,
    project_id: int | None = None,
) -> list[StaffRole]:
    """Получить список сотрудников с заданными фильтрами."""
    query = select(StaffRole)
    if kind:
        query = query.where(StaffRole.kind == kind)
    if scope:
        query = query.where(StaffRole.scope == scope)
    if project_id is not None:
        query = query.where(StaffRole.project_id == project_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_all_managers(session: AsyncSession, scope: str) -> list[User]:
    """Получить всех менеджеров за определённый скоп."""
    query = select(User).join(StaffRole, StaffRole.user_id == User.id).where(
        StaffRole.kind == "manager",
        StaffRole.scope == scope,
        User.status == "active",
    )
    result = await session.execute(query)
    return list(result.scalars().unique().all())


async def get_manager_users(
    session: AsyncSession,
    scope: str,
    project_id: int | None = None,
) -> list[User]:
    """Получить менеджеров за скоп, опционально привязанных к проекту."""
    query = select(User).join(StaffRole, StaffRole.user_id == User.id).where(
        StaffRole.kind == "manager",
        StaffRole.scope == scope,
        User.status == "active",
    )
    if project_id is not None:
        query = query.where(
            (StaffRole.project_id == project_id) | (StaffRole.project_id.is_(None))
        )
    else:
        query = query.where(StaffRole.project_id.is_(None))
    result = await session.execute(query)
    return list(result.scalars().unique().all())


async def get_executor_users(
    session: AsyncSession,
    scope: str,
    project_id: int | None = None,
) -> list[User]:
    """Получить исполнителей за скоп, опционально привязанных к проекту."""
    query = select(User).join(StaffRole, StaffRole.user_id == User.id).where(
        StaffRole.kind == "executor",
        StaffRole.scope == scope,
        User.status == "active",
    )
    if project_id is not None:
        query = query.where(
            (StaffRole.project_id == project_id) | (StaffRole.project_id.is_(None))
        )
    result = await session.execute(query)
    return list(result.scalars().unique().all())


async def get_user_staff_roles(session: AsyncSession, user_id: int) -> list[StaffRole]:
    """Получить все роли пользователя как сотрудника."""
    result = await session.execute(
        select(StaffRole).where(StaffRole.user_id == user_id)
    )
    return list(result.scalars().all())


async def is_executor(session: AsyncSession, user_id: int) -> bool:
    """Проверить, является ли пользователь исполнителем."""
    result = await session.execute(
        select(StaffRole).where(
            StaffRole.user_id == user_id,
            StaffRole.kind == "executor"
        )
    )
    return result.scalar_one_or_none() is not None


async def is_manager(session: AsyncSession, user_id: int) -> bool:
    """Проверить, является ли пользователь менеджером."""
    result = await session.execute(
        select(StaffRole).where(
            StaffRole.user_id == user_id,
            StaffRole.kind == "manager"
        )
    )
    return result.scalar_one_or_none() is not None


async def create_notification(
    session: AsyncSession,
    user_id: int,
    order_id: int,
    notification_type: str,
    message: str | None = None,
) -> StaffNotification:
    """Создать уведомление для сотрудника."""
    notification = StaffNotification(
        user_id=user_id,
        order_id=order_id,
        notification_type=notification_type,
        message=message,
        status="unread",
    )
    session.add(notification)
    await session.flush()
    return notification


async def get_unread_notifications(
    session: AsyncSession, user_id: int
) -> list[StaffNotification]:
    """Получить непрочитанные уведомления пользователя."""
    result = await session.execute(
        select(StaffNotification)
        .where(
            StaffNotification.user_id == user_id,
            StaffNotification.status == "unread",
        )
        .order_by(StaffNotification.created_at.desc())
    )
    return list(result.scalars().all())


async def mark_notification_as_read(
    session: AsyncSession, notification_id: int
) -> None:
    """Отметить уведомление как прочитанное."""
    notification = await session.get(StaffNotification, notification_id)
    if notification:
        notification.status = "read"
        await session.flush()
