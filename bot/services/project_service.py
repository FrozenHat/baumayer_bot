from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project, ProjectMember


async def get_user_projects(session: AsyncSession, user_id: int) -> list[Project]:
    """Все проекты, где пользователь — участник."""
    result = await session.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(
            ProjectMember.user_id == user_id,
            ProjectMember.status == "active",
            Project.status != "archived",
        )
        .order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())


async def get_project_members(session: AsyncSession, project_id: int) -> list[ProjectMember]:
    result = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.status == "active",
        )
    )
    return list(result.scalars().all())


async def get_member_role(
    session: AsyncSession, project_id: int, user_id: int
) -> str | None:
    """Роль пользователя в конкретном проекте (первая найденная)."""
    result = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
            ProjectMember.status == "active",
        )
    )
    member = result.scalars().first()
    return member.role_in_project if member else None


async def create_project(
    session: AsyncSession,
    name: str,
    address: str | None,
    description: str | None,
    owner_id: int,
) -> Project:
    project = Project(
        name=name,
        address=address,
        description=description,
        owner_id=owner_id,
    )
    session.add(project)
    await session.flush()

    # Создатель автоматически становится клиентом проекта
    session.add(
        ProjectMember(
            project_id=project.id,
            user_id=owner_id,
            role_in_project="client",
        )
    )
    await session.flush()
    return project