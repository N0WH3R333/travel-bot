import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from config import SUPER_ADMIN_ID
from services.database import add_admin, remove_admin, get_all_admins

logger = logging.getLogger(__name__)

# Состояния
CHOOSING_MANAGE_ACTION, GET_ID_TO_ADD, GET_ID_TO_REMOVE = range(3)

# Callback Data
CB_ADD_ADMIN = "add_admin"
CB_REMOVE_ADMIN = "remove_admin"
CB_LIST_ADMINS = "list_admins"
CB_BACK_TO_MANAGE_MENU = "back_to_manage_menu"


async def manage_admins_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога управления администраторами."""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить админа", callback_data=CB_ADD_ADMIN)],
        [InlineKeyboardButton("➖ Удалить админа", callback_data=CB_REMOVE_ADMIN)],
        [InlineKeyboardButton("📋 Список админов", callback_data=CB_LIST_ADMINS)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Меню управления администраторами:", reply_markup=reply_markup)
    return CHOOSING_MANAGE_ACTION


async def ask_for_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает ID пользователя для добавления в админы."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Пришлите ID пользователя, которого хотите назначить администратором.")
    return GET_ID_TO_ADD


async def process_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ID и добавляет нового админа."""
    try:
        user_id = int(update.message.text)
        if add_admin(user_id):
            await update.message.reply_text(f"✅ Пользователь с ID {user_id} успешно назначен администратором.")
            logger.info(f"SuperAdmin {update.effective_user.id} added new admin: {user_id}")
        else:
            await update.message.reply_text(f"⚠️ Пользователь с ID {user_id} уже является администратором.")
    except (ValueError, TypeError):
        await update.message.reply_text("❌ Пожалуйста, отправьте корректный числовой ID.")

    # Возвращаемся в главное меню управления
    await manage_admins_start(update, context)
    return ConversationHandler.END


async def show_admins_for_removal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает список админов с кнопками для удаления."""
    query = update.callback_query
    await query.answer()
    admins = get_all_admins()

    if not admins:
        await query.edit_message_text("Список администраторов пуст.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=CB_BACK_TO_MANAGE_MENU)]]))
        return CHOOSING_MANAGE_ACTION

    keyboard = []
    for admin_id in admins:
        # Для получения имени можно было бы сделать запрос к БД или get_chat, но для простоты оставим ID
        keyboard.append([InlineKeyboardButton(f"Удалить {admin_id}", callback_data=f"remove_{admin_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=CB_BACK_TO_MANAGE_MENU)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите администратора для удаления:", reply_markup=reply_markup)
    return GET_ID_TO_REMOVE


async def process_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Удаляет выбранного администратора."""
    query = update.callback_query
    user_id_to_remove = int(query.data.split('_')[1])

    if remove_admin(user_id_to_remove):
        await query.answer(f"Администратор {user_id_to_remove} удален.", show_alert=True)
        logger.info(f"SuperAdmin {update.effective_user.id} removed admin: {user_id_to_remove}")
    else:
        await query.answer("Не удалось удалить администратора.", show_alert=True)

    # Обновляем список
    return await show_admins_for_removal(update, context)


async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает список всех администраторов."""
    query = update.callback_query
    await query.answer()
    admins = get_all_admins()
    
    if not admins:
        text = "Список администраторов пуст."
    else:
        text = "Текущие администраторы:\n" + "\n".join([f"• `{admin_id}`" for admin_id in admins])
    
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=CB_BACK_TO_MANAGE_MENU)]])
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='MarkdownV2')
    return CHOOSING_MANAGE_ACTION


async def back_to_manage_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возврат в меню управления админами."""
    query = update.callback_query
    await query.answer()
    # Просто вызываем стартовую функцию, чтобы перерисовать меню
    await manage_admins_start(query, context)
    # Завершаем текущий диалог, чтобы он не "завис"
    return ConversationHandler.END


manage_admins_handler = ConversationHandler(
    entry_points=[CommandHandler("manage_admins", manage_admins_start, filters=filters.User(user_id=SUPER_ADMIN_ID))],
    states={
        CHOOSING_MANAGE_ACTION: [
            CallbackQueryHandler(ask_for_admin_id, pattern=f"^{CB_ADD_ADMIN}$"),
            CallbackQueryHandler(show_admins_for_removal, pattern=f"^{CB_REMOVE_ADMIN}$"),
            CallbackQueryHandler(list_admins, pattern=f"^{CB_LIST_ADMINS}$"),
        ],
        GET_ID_TO_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_admin)],
        GET_ID_TO_REMOVE: [
            CallbackQueryHandler(process_remove_admin, pattern="^remove_"),
            CallbackQueryHandler(back_to_manage_menu, pattern=f"^{CB_BACK_TO_MANAGE_MENU}$"),
        ],
    },
    fallbacks=[CommandHandler("manage_admins", manage_admins_start)],
)