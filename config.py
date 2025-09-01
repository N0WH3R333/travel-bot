import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Основные настройки бота
TOKEN = os.getenv("TOKEN")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID")) if os.getenv("SUPER_ADMIN_ID") else None

# --- Конфигурация кнопок-ссылок для стартового меню ---
# Формат: (GROUP_ID_from_env, "Текст кнопки", "Эмодзи")
# Бот должен быть администратором в этих каналах с правом приглашения пользователей.
CHANNEL_BUTTONS_CONFIG = [
    (os.getenv("GROUP_ID_REVIEWS"), "Отзывы", "🌟"),
    (os.getenv("GROUP_ID_CHAT"), "Наш чат", "💬"),
    (os.getenv("GROUP_ID_DETAILING"), "BT Detailing", "🚗"),
]