from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.staff import StaffRole
from models.user import User


async def add_staff_role(
    session: AsyncSession,
    user_id: int,
    kind: str,
    scope: str,
    project_id: int | None = None,
) -> StaffRole:
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
    """Все менеджеры за scope (и глобальные, и по проектам)."""
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