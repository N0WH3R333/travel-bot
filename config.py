# c:\Users\Lenovo\Desktop\bottravel\config.py

import os
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

def get_env_variable(var_name):
    """Получает переменную из .env."""
    value = os.getenv(var_name)
    if not value:
        logging.warning(f"Переменная {var_name} не найдена в .env.")
    return value

def get_env_variable_int(var_name):
    """Получает числовую переменную из .env."""
    value = get_env_variable(var_name)
    if value:
        try:
            return int(value)
        except (ValueError, TypeError):
            logging.warning(
                f"Переменная {var_name} в .env имеет неверный формат."
            )
    return None

# --- Основные настройки ---
TOKEN = get_env_variable("TELEGRAM_BOT_TOKEN")
# ID главного администратора, который может назначать других
SUPER_ADMIN_ID = get_env_variable_int("SUPER_ADMIN_ID")

# --- ID каналов для главного меню ---
GROUP_ID_LIVE = get_env_variable_int("GROUP_ID_LIVE")
GROUP_ID_BUY = get_env_variable_int("GROUP_ID_BUY")
GROUP_ID_SELL = get_env_variable_int("GROUP_ID_SELL")

# --- Конфигурация кнопок-ссылок для главного меню ---
# Структура: (ID канала, Текст кнопки, Эмодзи)
CHANNEL_BUTTONS_CONFIG = [
    (GROUP_ID_LIVE, "Лайв канал", "🏎️"),
    (GROUP_ID_BUY, "Забрать авто", "🔑"),
    (GROUP_ID_SELL, "Продать / помощь в продаже", "💲"),
]
