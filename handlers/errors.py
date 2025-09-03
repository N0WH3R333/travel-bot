import logging
import html
import json
import traceback
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError

# Импортируем новую конфигурацию и функции для работы с БД
from config import SUPER_ADMIN_ID
from services.database import get_all_admins

logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует ошибку и отправляет подробное сообщение всем администраторам."""
    logger.error("Произошло исключение при обработке обновления:", exc_info=context.error)

    # Форматируем трейсбек для отправки
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Форматируем объект update для наглядности
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    
    message = (
        f"<b>An error occurred in the bot</b>\n\n"
        f"<b>Error:</b>\n"
        f"<code>{html.escape(str(context.error))}</code>\n\n"
        f"<b>Update:</b>\n"
        f"<code>{html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</code>\n\n"
        f"<b>Chat Data:</b>\n"
        f"<code>{html.escape(str(context.chat_data))}</code>\n\n"
        f"<b>User Data:</b>\n"
        f"<code>{html.escape(str(context.user_data))}</code>\n\n"
        f"<b>Traceback:</b>\n"
        f"<code>{html.escape(tb_string)}</code>"
    )

    # Получаем ID всех администраторов (супер-админ + админы из БД)
    admin_ids = set(get_all_admins())
    if SUPER_ADMIN_ID:
        admin_ids.add(SUPER_ADMIN_ID)

    # Отправляем отформатированное сообщение об ошибке всем администраторам
    for admin_id in admin_ids:
        try:
            for i in range(0, len(message), 4096):
                await context.bot.send_message(
                    chat_id=admin_id, text=message[i:i + 4096], parse_mode=ParseMode.HTML
                )
        except TelegramError as e:
            logger.warning(f"Не удалось отправить сообщение об ошибке администратору {admin_id}: {e}")

    # Также отправляем пользователю-дружелюбное сообщение, если это возможно
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❗️ В боте произошла ошибка. Администраторы уже уведомлены."
            )
        except TelegramError as e:
            # Логируем, если не удалось отправить сообщение пользователю (например, бот заблокирован)
            logger.warning(f"Не удалось отправить сообщение об ошибке пользователю {update.effective_chat.id}: {e}")
