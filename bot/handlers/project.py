from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database import async_session
from keyboards.projects import (
    project_card_kb,
    projects_list_kb,
)
from models.project import Project
from models.user import User
from services.project_service import (
    create_project,
    get_project_members,
    get_user_projects,
)

router = Router()


class CreateProject(StatesGroup):
    waiting_name = State()
    waiting_address = State()
    waiting_description = State()


@router.message(Command("myproject"))
@router.message(F.text == "🏗️ Моя стройка")
async def cmd_my_project(message: Message, user: User):
    async with async_session() as session:
        projects = await get_user_projects(session, user.id)

    # Нет проектов
    if not projects:
        if user.role == "admin":
            await message.answer(
                "У вас пока нет проектов.\n\n"
                "Создайте первый: /newproject"
            )
        else:
            await message.answer(
                "Вы пока не участник ни одного проекта.\n"
                "Обратитесь к администратору."
            )
        return

    # Один проект — сразу карточка
    if len(projects) == 1:
        await show_project_card(message, user, projects[0].id)
        return

    # Несколько — список
    await message.answer(
        "🏗️ <b>Ваши проекты</b>\n\nВыберите проект:",
        reply_markup=projects_list_kb(projects),
    )


@router.message(Command("newproject"))
async def cmd_new_project(message: Message, state: FSMContext, user: User):
    if user.role != "admin":
        await message.answer("Только администратор может создавать проекты.")
        return
    await state.set_state(CreateProject.waiting_name)
    await message.answer("Введите <b>название</b> проекта:")


@router.message(CreateProject.waiting_name)
async def new_project_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(CreateProject.waiting_address)
    await message.answer("Введите <b>адрес объекта</b> (или «—», чтобы пропустить):")


@router.message(CreateProject.waiting_address)
async def new_project_address(message: Message, state: FSMContext):
    value = message.text.strip()
    await state.update_data(address=None if value == "—" else value)
    await state.set_state(CreateProject.waiting_description)
    await message.answer("Введите <b>описание</b> (или «—», чтобы пропустить):")


@router.message(CreateProject.waiting_description)
async def new_project_description(message: Message, state: FSMContext, user: User):
    value = message.text.strip()
    description = None if value == "—" else value

    data = await state.get_data()
    async with async_session() as session:
        project = await create_project(
            session=session,
            name=data["name"],
            address=data["address"],
            description=description,
            owner_id=user.id,
        )
        await session.commit()
        project_id = project.id

    await state.clear()
    await message.answer(f"✅ Проект «{data['name']}» создан (ID: {project_id}).")
    await show_project_card(message, user, project_id)


@router.callback_query(F.data.startswith("project:open:"))
async def open_project(callback: CallbackQuery, user: User):
    project_id = int(callback.data.split(":")[2])
    await show_project_card(callback.message, user, project_id)
    await callback.answer()


@router.callback_query(F.data == "project:list")
async def back_to_list(callback: CallbackQuery, user: User):
    async with async_session() as session:
        projects = await get_user_projects(session, user.id)
    await callback.message.answer(
        "🏗️ <b>Ваши проекты</b>\n\nВыберите проект:",
        reply_markup=projects_list_kb(projects),
    )
    await callback.answer()


async def show_project_card(message: Message, user: User, project_id: int):
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if project is None:
            await message.answer("Проект не найден.")
            return
        members = await get_project_members(session, project_id)

    members_text = "\n".join(
        f"• {m.user.full_name if m.user else '—'} — <i>{m.role_in_project}</i>"
        for m in members
    ) or "—"

    text = (
        f"🏗️ <b>{project.name}</b>\n\n"
        f"<b>Адрес:</b> {project.address or '—'}\n"
        f"<b>Статус:</b> {project.status}\n"
        f"<b>Описание:</b> {project.description or '—'}\n\n"
        f"<b>Участники:</b>\n{members_text}"
    )
    await message.answer(text, reply_markup=project_card_kb(project_id))