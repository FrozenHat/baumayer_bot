from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models.project import Project


def projects_list_kb(projects: list[Project]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=p.name, callback_data=f"project:open:{p.id}")]
        for p in projects
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def project_card_kb(project_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📂 Мои проекты", callback_data="project:list")],
            # Заглушки для будущих разделов
            [InlineKeyboardButton(text="👥 Исполнители", callback_data=f"project:members:{project_id}")],
            [InlineKeyboardButton(text="📊 Смета", callback_data=f"project:budget:{project_id}")],
            [InlineKeyboardButton(text="✅ Выполнение работ", callback_data=f"project:progress:{project_id}")],
            [InlineKeyboardButton(text="📐 Архитектор", callback_data=f"project:architect:{project_id}")],
            [InlineKeyboardButton(text="🎨 Дизайнер", callback_data=f"project:designer:{project_id}")],
        ]
    )