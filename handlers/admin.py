import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

logger = logging.getLogger(__name__)

from config import CHANNEL_BUTTONS_CONFIG
from services.database import get_all_users, get_channel_stats, get_user_ids_by_channel, full_resync_channel_members

# Импортируем логику калькулятора из соседнего файла
try:
    from .calculate import (
        commission_calculator_start,
        commission_calculator_receive_price,
        back_to_main_admin_menu as calculator_back_to_main,
        COMMISSION_CALCULATOR_INPUT,
        CB_ADMIN_COMMISSION_CALCULATOR,
        CB_ADMIN_BACK_TO_MAIN_FROM_CALCULATOR,
    )
except ImportError:
    logging.critical("Не удалось импортировать 'calculate.py'. Убедитесь, что файл находится в папке 'handlers'.")
    async def _dummy_unavailable_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.callback_query:
            await update.callback_query.answer("Ошибка: модуль калькулятора не найден.", show_alert=True)
        return ConversationHandler.END
    commission_calculator_start = _dummy_unavailable_handler
    commission_calculator_receive_price = _dummy_unavailable_handler
    calculator_back_to_main = _dummy_unavailable_handler
    COMMISSION_CALCULATOR_INPUT = -99
    CB_ADMIN_COMMISSION_CALCULATOR = "calculator_unavailable"
    CB_ADMIN_BACK_TO_MAIN_FROM_CALCULATOR = "calculator_back_unavailable"

# --- СОСТОЯНИЯ ДИАЛОГА ---
(
    CHOOSING_ACTION,
    SHOWING_STATS,
    # Состояния рассылки
    CHOOSE_TARGET,
    CHOOSE_TYPE,
    GET_CONTENT,
    CONFIRM_BROADCAST,
) = range(6)

# --- ДАННЫЕ ДЛЯ КНОПОК (CALLBACK DATA) ---
CB_BROADCAST_START = "broadcast_start"
CB_SHOW_STATS = "show_stats"
CB_BACK_TO_MAIN = "admin_back_to_main"
CB_SYNC_SUBSCRIBERS = "sync_subscribers"
CB_BROADCAST_CANCEL = "broadcast_cancel"

# === ГЛАВНОЕ МЕНЮ И НАВИГАЦИЯ ===
async def get_main_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Создает и возвращает клавиатуру главного меню админа."""
    keyboard = [
        [InlineKeyboardButton("Создать рассылку 📬", callback_data=CB_BROADCAST_START)],
        [InlineKeyboardButton("Статистика 📊", callback_data=CB_SHOW_STATS)],
        [InlineKeyboardButton("Калькулятор комиссии 🧮", callback_data=CB_ADMIN_COMMISSION_CALCULATOR)],
        [InlineKeyboardButton("🔄 Синхронизировать подписчиков", callback_data=CB_SYNC_SUBSCRIBERS)],
    ]
    return InlineKeyboardMarkup(keyboard)

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Точка входа в админ-панель. Отправляет главное меню."""
    text = "Добро пожаловать в админ-панель!"
    reply_markup = await get_main_admin_menu_keyboard()
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    return CHOOSING_ACTION

# === СЕКЦИЯ СТАТИСТИКИ ===
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает статистику и кнопку 'Назад'."""
    query = update.callback_query
    await query.answer()
    total_bot_users = len(get_all_users())
    channel_stats = get_channel_stats()
    channel_names = {config[0]: f"{config[2]} {config[1]}" for config in CHANNEL_BUTTONS_CONFIG if config[0]}
    
    stats_text = f"📊 <b>Статистика</b>\n\n"
    stats_text += f"Всего пользователей, запустивших бота: <code>{total_bot_users}</code>\n\n"
    stats_text += "<b>Подписчиков в отслеживаемых каналах:</b>\n"
    if channel_stats:
        for channel_id, count in channel_stats.items():
            name = channel_names.get(int(channel_id), f"Канал ID: {channel_id}")
            stats_text += f"  • {name}: <code>{count}</code>\n"
    else:
        stats_text += "<i>Пока нет данных о подписчиках в каналах.</i>"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=CB_BACK_TO_MAIN)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(stats_text, parse_mode='HTML', reply_markup=reply_markup)
    return SHOWING_STATS

# === СЕКЦИЯ СИНХРОНИЗАЦИИ ===
async def sync_subscribers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Принудительно синхронизирует базу данных с текущими подписчиками каналов."""
    query = update.callback_query
    await query.answer("Начинаю синхронизацию... Это может занять несколько минут.")
    all_bot_users = get_all_users()
    channels_to_sync = [config[0] for config in CHANNEL_BUTTONS_CONFIG if config[0]]
    total_synced_count = 0
    for channel_id in channels_to_sync:
        current_channel_members = []
        for user_id in all_bot_users:
            try:
                member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                if member.status in ['member', 'administrator', 'creator']:
                    current_channel_members.append(user_id)
            except Exception:
                continue
        full_resync_channel_members(channel_id, current_channel_members)
        total_synced_count += len(current_channel_members)
        logger.info(f"Синхронизация для канала {channel_id} завершена. Найдено {len(current_channel_members)} подписчиков.")
    await query.edit_message_text(
        f"✅ Синхронизация завершена!\n\nВсего найдено и записано в базу: {total_synced_count} подписок.",
        reply_markup=await get_main_admin_menu_keyboard()
    )
    return CHOOSING_ACTION

# === СЕКЦИЯ РАССЫЛКИ ===
async def start_broadcast_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога рассылки: спрашивает целевую аудиторию."""
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("Всем пользователям", callback_data="target_all")]]
    for group_id, text, emoji in CHANNEL_BUTTONS_CONFIG:
        if group_id:
            keyboard.append([InlineKeyboardButton(f"Подписчикам «{emoji} {text}»", callback_data=f"target_{group_id}")])
    keyboard.append([InlineKeyboardButton("Отмена", callback_data=CB_BROADCAST_CANCEL)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Кому вы хотите отправить рассылку?", reply_markup=reply_markup)
    return CHOOSE_TARGET

async def choose_broadcast_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет целевую аудиторию и спрашивает тип контента."""
    query = update.callback_query
    target = query.data.replace("target_", "")
    context.user_data['broadcast_target'] = target
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Одиночное сообщение", callback_data="type_single")],
        [InlineKeyboardButton("Группа фото/видео", callback_data="type_group")],
        [InlineKeyboardButton("Отмена", callback_data=CB_BROADCAST_CANCEL)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Какой тип рассылки вы хотите создать?", reply_markup=reply_markup)
    return CHOOSE_TYPE

async def ask_for_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает контент в зависимости от выбора типа."""
    query = update.callback_query
    choice = query.data
    await query.answer()
    context.user_data.pop('broadcast_messages', None)
    context.user_data.pop('limit_warning_sent', None)
    if choice == 'type_single':
        await query.edit_message_text(text="Пришлите сообщение для рассылки (текст, фото, видео, и т.д.).\n\nДля отмены введите /cancel.")
    elif choice == 'type_group':
        keyboard = [
            [InlineKeyboardButton("✅ Готово, я все отправил(а)", callback_data="group_done")],
            [InlineKeyboardButton("❌ Отмена", callback_data=CB_BROADCAST_CANCEL)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="Отправьте до 10 фото и видео одним альбомом. Текст, отправленный с первым файлом, станет общей подписью.\n\n"
                 "Когда закончите, нажмите 'Готово'.",
            reply_markup=reply_markup
        )
    return GET_CONTENT

async def get_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает контент для рассылки (одиночный или в составе группы)."""
    if 'broadcast_messages' not in context.user_data:
        context.user_data['broadcast_messages'] = []
    if update.message.media_group_id:
        if len(context.user_data['broadcast_messages']) < 10:
            context.user_data['broadcast_messages'].append(update.message)
        else:
            if not context.user_data.get('limit_warning_sent'):
                await update.message.reply_text("Достигнут лимит в 10 файлов. Пожалуйста, нажмите 'Готово'.")
                context.user_data['limit_warning_sent'] = True
        return GET_CONTENT
    else:
        context.user_data['broadcast_messages'] = [update.message]
        await ask_for_confirmation(update, context)
        return CONFIRM_BROADCAST

async def finish_group_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершает сбор медиагруппы и запрашивает подтверждение."""
    query = update.callback_query
    await query.answer()
    if not context.user_data.get('broadcast_messages'):
        await query.edit_message_text("Вы не отправили ни одного файла. Рассылка отменена.")
        context.user_data.clear()
        return await admin_start(update, context)
    await query.edit_message_text("Отлично! Группа медиафайлов собрана.")
    await ask_for_confirmation(update, context)
    return CONFIRM_BROADCAST

async def ask_for_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение с запросом на подтверждение рассылки."""
    keyboard = [
        [InlineKeyboardButton("✅ Начать рассылку", callback_data="broadcast_confirm")],
        [InlineKeyboardButton("❌ Отмена", callback_data=CB_BROADCAST_CANCEL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    num_messages = len(context.user_data.get('broadcast_messages', []))
    message_type = f"группу из {num_messages} медиа" if num_messages > 1 else "это сообщение"
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Вы уверены, что хотите разослать {message_type}?",
        reply_markup=reply_markup
    )

async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запускает процесс рассылки после подтверждения."""
    query = update.callback_query
    await query.answer()
    messages = context.user_data.get('broadcast_messages', [])
    target_group = context.user_data.get('broadcast_target')
    if not messages or not target_group:
        await query.edit_message_text("Ошибка: не найден контент или целевая аудитория для рассылки.")
        context.user_data.clear()
        return await admin_start(update, context)
    if target_group == 'all':
        user_ids = get_all_users()
    else:
        channel_id = int(target_group)
        user_ids = get_user_ids_by_channel(channel_id)
    if not user_ids:
        await query.edit_message_text("В выбранной аудитории нет пользователей для рассылки.")
        context.user_data.clear()
        return await admin_start(update, context)
    await query.edit_message_text(f"Начинаю рассылку для {len(user_ids)} пользователей. Это может занять некоторое время...")
    success_count = 0
    error_count = 0
    if len(messages) > 1:
        media_list = []
        caption = next((msg.caption for msg in messages if msg.caption), "")
        for i, msg in enumerate(messages):
            extra_args = {'caption': caption, 'parse_mode': ParseMode.HTML} if i == 0 and caption else {}
            if msg.photo:
                media_list.append(InputMediaPhoto(media=msg.photo[-1].file_id, **extra_args))
            elif msg.video:
                media_list.append(InputMediaVideo(media=msg.video.file_id, **extra_args))
        if not media_list:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Ошибка: не удалось собрать медиагруппу.")
        else:
            for user_id in user_ids:
                try:
                    await context.bot.send_media_group(chat_id=user_id, media=media_list, read_timeout=30, write_timeout=30)
                    success_count += 1
                    time.sleep(0.1)
                except Exception as e:
                    error_count += 1
                    logging.error(f"Не удалось отправить медиагруппу пользователю {user_id}: {e}")
    else:
        message_to_send = messages[0]
        for user_id in user_ids:
            try:
                await message_to_send.copy(chat_id=user_id)
                success_count += 1
                time.sleep(0.1)
            except Exception as e:
                error_count += 1
                logging.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ Рассылка завершена!\n\n👍 Отправлено: {success_count}\n👎 Ошибок: {error_count}"
    )
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущее действие и возвращает в главное меню."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("Действие отменено.")
    else:
        await update.message.reply_text("Действие отменено.")
    context.user_data.clear()
    time.sleep(1)
    return await admin_start(update, context)

# === ЕДИНЫЙ ОБРАБОТЧИК АДМИН-ПАНЕЛИ ===
admin_handler = ConversationHandler(
    entry_points=[CommandHandler("admin", admin_start)],
    states={
        CHOOSING_ACTION: [
            CallbackQueryHandler(start_broadcast_dialog, pattern=f"^{CB_BROADCAST_START}$"),
            CallbackQueryHandler(show_stats, pattern=f"^{CB_SHOW_STATS}$"),
            CallbackQueryHandler(sync_subscribers, pattern=f"^{CB_SYNC_SUBSCRIBERS}$"),
            CallbackQueryHandler(commission_calculator_start, pattern=f"^{CB_ADMIN_COMMISSION_CALCULATOR}$"),
        ],
        SHOWING_STATS: [CallbackQueryHandler(admin_start, pattern=f"^{CB_BACK_TO_MAIN}$")],
        COMMISSION_CALCULATOR_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, commission_calculator_receive_price),
            CallbackQueryHandler(calculator_back_to_main, pattern=f"^{CB_ADMIN_BACK_TO_MAIN_FROM_CALCULATOR}$"),
        ],
        CHOOSE_TARGET: [CallbackQueryHandler(choose_broadcast_target, pattern='^target_')],
        CHOOSE_TYPE: [CallbackQueryHandler(ask_for_content, pattern='^type_(single|group)$')],
        GET_CONTENT: [
            MessageHandler(filters.ALL & ~filters.COMMAND, get_content),
            CallbackQueryHandler(finish_group_collection, pattern='^group_done$')
        ],
        CONFIRM_BROADCAST: [CallbackQueryHandler(process_broadcast, pattern='^broadcast_confirm$')]
    },
    fallbacks=[
        CommandHandler('cancel', cancel_action),
        CallbackQueryHandler(cancel_action, pattern=f"^{CB_BROADCAST_CANCEL}$"),
        CallbackQueryHandler(admin_start, pattern=f"^{CB_BACK_TO_MAIN}$"),
    ],
    conversation_timeout=600,
    allow_reentry=True,
)
