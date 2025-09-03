import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, constants
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from services.database import add_user
from config import CHANNEL_BUTTONS_CONFIG, SUPER_ADMIN_ID

logger = logging.getLogger(__name__)

# Константы для callback_data, чтобы избежать опечаток
CB_CALCULATOR = "calculator"
CB_ADMIN_PANEL = "admin_panel"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение с кнопками-ссылками на каналы."""
    user = update.effective_user
    
    # Добавляем пользователя в базу данных при первом запуске
    add_user(user_id=user.id, username=user.username, first_name=user.first_name)

    url_buttons = []
    # --- Создаем кнопки-ссылки на каналы ---
    for group_id, text, emoji in CHANNEL_BUTTONS_CONFIG:
        if not group_id:
            continue  # Пропускаем, если ID канала не задан в .env
        
        try:
            # Проверяем, есть ли ссылка в кэше
            url = context.bot_data.get(group_id)
            if not url:
                # Если ссылки нет, создаем новую и кэшируем ее
                link_obj = await context.bot.create_chat_invite_link(chat_id=group_id)
                url = link_obj.invite_link
                context.bot_data[group_id] = url
                logger.info(f"Создана и закэширована новая ссылка-приглашение для канала {group_id}.")
            
            url_buttons.append([InlineKeyboardButton(f"{emoji} {text}", url=url)])
        except TelegramError as e:
            # Если бот не админ или нет прав, кнопка не будет добавлена, а в лог запишется ошибка
            logger.error(
                f"Не удалось создать ссылку для канала {group_id}. "
                f"Убедитесь, что бот является администратором с правом приглашения. Ошибка: {e}"
            )

    # --- Добавляем стандартные кнопки ---
    action_buttons = [
        [InlineKeyboardButton("🧮 Калькулятор", callback_data=CB_CALCULATOR)],
    ]
    # Показываем админ-панель только супер-администратору
    if str(user.id) == str(SUPER_ADMIN_ID):
        action_buttons.append([InlineKeyboardButton("👑 Админ-панель", callback_data=CB_ADMIN_PANEL)])

    # Объединяем все кнопки: сначала ссылки на каналы, потом действия
    full_keyboard = url_buttons + action_buttons
    reply_markup = InlineKeyboardMarkup(full_keyboard) if full_keyboard else None

    welcome_text = (
        f"Привет, {user.mention_html()}!\n\n"
        "Добро пожаловать! Выберите интересующий вас раздел:"
    )

    # Если по какой-то причине кнопок нет, показываем более простое сообщение
    if not full_keyboard:
        welcome_text = (
            f"Привет, {user.mention_html()}!\n\n"
            "Добро пожаловать!"
        )

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=constants.ParseMode.HTML
    )
