import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Основные настройки бота
TOKEN = os.getenv("BOT_TOKEN") 
SUPER_ADMIN_ID = os.getenv("SUPER_ADMIN_ID")


# Критически важная проверка: останавливаем бота, если токен не найден
if not TOKEN:
    # Это сообщение будет видно в логах systemd или screen
    raise ValueError("ОШИБКА: Токен бота не найден. Проверьте .env файл и имя переменной (должно быть BOT_TOKEN).")

# --- Конфигурация кнопок-ссылок для стартового меню ---
# Формат: (GROUP_ID_from_env, "Текст кнопки", "Эмодзи")
# Бот должен быть администратором в этих каналах с правом приглашения пользователей.
CHANNEL_BUTTONS_CONFIG = [
    (os.getenv("GROUP_ID_LIVE"), "Лайв канал", "📢"),
    (os.getenv("GROUP_ID_BUY"), "Забрать", "🛍️"),
    (os.getenv("GROUP_ID_SELL"), "Продажа/помощь в продаже", "🤝"),
    (os.getenv("GROUP_ID_DETAILING"), "BT Detailing Ставрополь", "🚗"),
]
