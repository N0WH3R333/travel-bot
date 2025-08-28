import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import GROUP_IDS # Импортируем словарь с ID групп
from services.database import log_group_join # Импортируем новую функцию

async def handle_group_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает нажатие на инлайн-кнопки для вступления в группы.
    Создает одноразовую ссылку-приглашение.
    """
    query = update.callback_query
    await query.answer()  # Обязательно "отвечаем" на нажатие кнопки

    callback_data = query.data
    group_id = GROUP_IDS.get(callback_data)

    if group_id:
        # Логируем выбор пользователя в базу данных
        log_group_join(user_id=query.from_user.id, group_key=callback_data)
        
        try:
            # Бот должен быть администратором в группе с правом "Приглашать пользователей по ссылкам"
            invite_link = await context.bot.create_chat_invite_link(
                chat_id=group_id,
                member_limit=1  # Ссылка действительна только для одного вступления
            )
            await query.edit_message_text(
                f"Отлично! Вот твоя персональная ссылка для вступления:\n{invite_link.invite_link}"
            )
        except Exception as e:
            logging.error(f"Не удалось создать ссылку-приглашение для группы {group_id}: {e}")
            await query.edit_message_text("Произошла ошибка при создании ссылки. Пожалуйста, попробуйте позже.")
    else:
        # Эта ветка сработает, если ID для нажатой кнопки не был загружен (например, отсутствует в .env)
        logging.warning(f"Попытка вступления в группу '{callback_data}', для которой не задан ID.")
        await query.edit_message_text("К сожалению, эта группа сейчас недоступна. Пожалуйста, выберите другую.")

