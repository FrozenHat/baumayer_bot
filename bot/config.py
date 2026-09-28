import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан! Проверьте файл .env")

# --- База данных ---
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "baumayer_db")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")

# Строка подключения для SQLAlchemy (пригодится позже)
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- Redis ---
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
# --- Супер-админы ---
# Список Telegram ID, которые автоматически получают роль admin
SUPERADMIN_IDS = [
    int(x) for x in os.getenv("SUPERADMIN_IDS", "").split(",") if x.strip().isdigit()
]
# --- Прочее ---
DEBUG = os.getenv("DEBUG", "true").lower() == "true"