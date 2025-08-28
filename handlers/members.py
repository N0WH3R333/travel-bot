import logging
from telegram import Update, ChatMember, ChatMemberUpdated
from telegram.ext import ContextTypes
from telegram.error import Forbidden, BadRequest
from services.database import add_subscription, remove_subscription

logger = logging.getLogger(__name__)

async def track_channel_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отслеживает изменения в составе участников каналов, где бот является админом,
    и отправляет приветствие тем, кто вступил самостоятельно.
    """
    result = update.chat_member
    if not result:
        return

    chat = result.chat
    user = result.new_chat_member.user
    
    # Определяем, что пользователь именно ВСТУПИЛ в канал
    was_member = result.old_chat_member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.CREATOR]
    is_member = result.new_chat_member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.CREATOR]

    # --- Логика для отслеживания вступления ---
    if not was_member and is_member:
        # Добавляем подписку в базу данных
        add_subscription(user_id=user.id, channel_id=chat.id)
        logger.info(f"Пользователь {user.full_name} (ID: {user.id}) вступил в канал '{chat.title}' (ID: {chat.id}). Запись добавлена в БД.")

        # --- Проверяем, как пользователь вступил ---
        # Мы отправляем сообщение, только если он вступил НЕ по ссылке бота.
        joined_via_bot_link = result.invite_link and result.invite_link.creator.id == context.bot.id

        if not joined_via_bot_link:
            logger.info(f"Пользователь вступил самостоятельно. Отправляем приветствие в ЛС.")
            
            welcome_text = (
                f"Привет, {user.first_name}! 👋\n\n"
                f"Спасибо за подписку на наш канал «{chat.title}»! "
                "Рады видеть вас в нашем сообществе."
            )
            
            try:
                # Пытаемся отправить сообщение в личку
                await context.bot.send_message(chat_id=user.id, text=welcome_text)
                logger.info(f"Приветственное сообщение успешно отправлено пользователю {user.id}.")
            except (Forbidden, BadRequest) as e:
                # Ошибка возникает, если пользователь не запускал бота или заблокировал его.
                # Это нормальное поведение, просто логируем его.
                logger.warning(
                    f"Не удалось отправить приветствие пользователю {user.id}. "
                    f"Возможно, он не начинал диалог с ботом. Ошибка: {e}"
                )
        else:
            logger.info(f"Пользователь вступил по ссылке бота. Приветствие не отправляем.")

    # --- Логика для отслеживания выхода ---
    elif was_member and not is_member:
        # Удаляем подписку из базы данных
        remove_subscription(user_id=user.id, channel_id=chat.id)
        logger.info(f"Пользователь {user.full_name} (ID: {user.id}) покинул канал '{chat.title}' (ID: {chat.id}). Запись удалена из БД.")
